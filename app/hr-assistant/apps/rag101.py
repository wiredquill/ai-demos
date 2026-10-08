import json
import os
import threading
import time

import openlit
import requests
from openlit.__helpers import get_chat_model_cost
from patch.suse_ai_metrics import record_suse_ai_metrics
from pymilvus import model
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
MODEL = os.getenv("MODEL", "llama3.2")

# openlit's native ollama instrumentor already sets gen_ai.usage.cost as a span
# attribute correctly (confirmed by reading openlit/instrumentation/ollama/utils.py),
# but never records it as a metric, and never records the gen_ai.total.requests
# counter the SUSE AI StackPack uses as its "is this a GenAI app" gate - see
# patch/suse_ai_metrics.py. This wraps every raw chat call here so
# HRPolicyDatabase gets the same cost/request charts HRAssistant already has.
_openlit_conf = openlit.OpenlitConfig()

# vLLM's OpenAI-compatible endpoint is instrumented by patch/openlit_vllm.py
# (wrapping openai.resources.chat.completions.Completions.create, the same
# path apps/simple.py and apps/rag102.py use for vLLM) — imported lazily so
# the ollama package stays optional when LLM_PROVIDER=vllm.
_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        _openai_client = OpenAI(base_url=f"{LLM_ENDPOINT}/v1", api_key="unused")
    return _openai_client


def _vllm_chat(messages, tools=None):
    """Calls vLLM's OpenAI-compatible chat endpoint and normalizes the reply
    into the same dict shape ollama.Client().chat() returns, so every
    downstream consumer in this file (which expects Ollama's native
    response["message"]["tool_calls"]/["content"] shape) works unchanged
    regardless of provider.
    """
    client = _get_openai_client()
    kwargs = {"model": MODEL, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
    completion = client.chat.completions.create(**kwargs)
    message = completion.choices[0].message
    tool_calls = None
    if message.tool_calls:
        tool_calls = [
            {
                # id + type are needed when this assistant message is replayed
                # back in the second ollama_chat(messages) call below — vLLM's
                # OpenAI-compatible schema validates both (Ollama's native API
                # requires neither, so they're simply absent on that path).
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in message.tool_calls
        ]
    usage = completion.usage
    return {
        "message": {"role": "assistant", "content": message.content or "", "tool_calls": tool_calls},
        "prompt_eval_count": usage.prompt_tokens if usage else 0,
        "eval_count": usage.completion_tokens if usage else 0,
    }


def ollama_chat(messages, tools=None):
    """Chat call (Ollama native client, or vLLM's OpenAI-compatible endpoint
    when LLM_PROVIDER=vllm) plus the SUSE AI metrics openlit's native
    instrumentors omit. Named ollama_chat for the Ollama path's history;
    provider-branched internally so callers don't need to know which backend
    is active.
    """
    if LLM_PROVIDER == "vllm":
        # _vllm_chat() goes through openai.chat.completions.create, which
        # patch/openlit_vllm.py already wraps with full span + SUSE AI metric
        # recording — recording again here would double-count requests/cost.
        return _vllm_chat(messages, tools=tools)

    import ollama

    client = ollama.Client()
    kwargs = {"model": MODEL, "messages": messages}
    if tools is not None:
        kwargs["tools"] = tools
    response = client.chat(**kwargs)
    try:
        input_tokens = response.get("prompt_eval_count", 0)
        output_tokens = response.get("eval_count", 0)
        cost = get_chat_model_cost(MODEL, _openlit_conf.pricing_info, input_tokens, output_tokens)
        record_suse_ai_metrics(_openlit_conf.application_name, _openlit_conf.environment, LLM_PROVIDER, MODEL, cost)
    except Exception as e:
        print(f"SUSE AI metrics recording failed (non-fatal): {e}")
    return response


# Vector Database (Qdrant) and Search Engine (OpenSearch) endpoints.
#
# These are the "Vector Databases" and "Search Engines" components in the
# SUSE AI section of SUSE Observability:
#   - Qdrant is scraped by the shared collector (job "qdrant"), whose
#     transform/qdrant tags the metrics suse.ai.component.type=vectordb.
#   - OpenSearch is polled by the collector's elasticsearch receiver, whose
#     resource/opensearch processor tags it suse.ai.component.type=search-engine.
# Every request below generates spans + metrics, so the topology view shows
# hr-policy-db depending on both.
QDRANT_URL = os.getenv("QDRANT_URL", "http://hr-assistant-qdrant:6333")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://hr-assistant-opensearch:9200")
QDRANT_COLLECTION = "hr_policies"
OPENSEARCH_INDEX = "hr_policies"

# Simple counters surfaced via /stats so the demo dashboard can show RAG
# activity (vector searches, search-engine queries, seeds). These are
# in-memory only — they exist to make the dashboard live, not to be a
# production telemetry store.
_rag_stats = {"qdrant_searches": 0, "opensearch_searches": 0, "seeds": 0}

# One-shot datastore init. Seed the collections once at module import so that
# every /ask only does real searches (qdrant_searches/opensearch_searches) and
# never re-seeds the stores. Seeding on every request made the "Store Seeds"
# counter climb by 2 per request while searches only climbed by 1 — the
# dashboard's "2 seeds but 1 rag / 1 search" was this. Guarded so re-imports
# and repeated /ask calls never re-seed.
_init_lock = threading.Lock()
_init_done = False


def get_rag_stats() -> dict:
    """Snapshot of RAG activity for the /stats endpoint."""
    return dict(_rag_stats)


def ensure_datastores_seeded() -> None:
    """Seed Qdrant + OpenSearch once per process (idempotent, retried lazily).

    Call this from /ask (or at startup) instead of seeding inline. On first
    call it upserts the HR policy documents; any failure is swallowed so a
    transient datastore outage at boot doesn't 500 the request — the next /ask
    retries the seed. Successful seed increments `seeds` exactly once.
    """
    global _init_done
    with _init_lock:
        if _init_done:
            return
        try:
            seed_qdrant()
            seed_opensearch()
            _init_done = True
            print("RAG datastores seeded (qdrant + opensearch)")
            _start_datastore_relation_refresher()
        except Exception as e:
            print(f"RAG datastore seeding failed, will retry on next request: {e}")


# SUSE Observability's topology view only renders the hr-policy-db -> qdrant /
# hr-policy-db -> opensearch edges for a moment right after a real search
# span, then drops them - unlike components (which persist ~2 minutes after
# their last telemetry), relations appear to need a much tighter, near-
# continuous stream of matching spans to stay rendered. /ask only touches
# these datastores once per ~45s load-generator cycle, far too infrequent.
# This background loop re-runs the real, properly-instrumented search calls
# on a fast interval so the topology edges stay lit continuously instead of
# flickering in and out between /ask calls.
_refresher_started = False
_refresher_lock = threading.Lock()
DATASTORE_REFRESH_INTERVAL_SECONDS = int(os.getenv("DATASTORE_REFRESH_INTERVAL_SECONDS", "10"))


def _datastore_relation_refresh_loop():
    query = "vacation benefits"
    while True:
        time.sleep(DATASTORE_REFRESH_INTERVAL_SECONDS)
        try:
            search_qdrant(query)
        except Exception as e:
            print(f"Datastore relation refresh (qdrant) failed: {e}")
        try:
            search_opensearch(query)
        except Exception as e:
            print(f"Datastore relation refresh (opensearch) failed: {e}")


def _start_datastore_relation_refresher():
    global _refresher_started
    with _refresher_lock:
        if _refresher_started:
            return
        threading.Thread(target=_datastore_relation_refresh_loop, daemon=True).start()
        _refresher_started = True


embedding_fn = model.DefaultEmbeddingFunction()

documents = [
    "Employees are entitled to 20 days of paid vacation per year after one year of service.",
    "Remote work policy allows up to 3 days per week with manager approval.",
    "Health insurance coverage includes medical, dental, and vision with company contribution.",
]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_benefits_information",
            "description": "Get employee benefits information including vacation, health insurance, and policies",
            "parameters": {
                "type": "object",
                "properties": {
                    "benefit_type": {
                        "type": "string",
                        "description": "The type of benefit (vacation, health, remote_work)",
                    },
                    "employee_level": {
                        "type": "string",
                        "description": "Employee level (junior, senior, manager)",
                    },
                },
                "required": ["benefit_type", "employee_level"],
            },
        },
    },
]


# --- Vector Database (Qdrant) -----------------------------------------------
#
# Qdrant is the "Vector Databases" component in SUSE Observability. Health for
# this category comes from OpenLIT's own vectordb instrumentation - the SUSE
# AI StackPack's health monitor (extracted from the
# suse-ai-observability-extension-setup image: stackpack/monitors/monitors.yaml)
# queries sum(db_requests_total{}) by (db_system), which is exactly the metric
# OpenLIT's native qdrant_client instrumentor emits automatically on
# create_collection/upsert/query_points - but only when the official
# qdrant-client SDK is used. The collector's own Prometheus scrape of
# Qdrant's /metrics never feeds that monitor at all (different metric
# entirely); it's kept below (see transform/qdrant in the collector config)
# for utilization numbers, not health. Using QdrantClient here instead of raw
# requests calls is what actually makes hr-policy-db -> qdrant get a health
# state, the same way every GenAI app already gets one.
_qdrant_client = None


def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantClient(url=QDRANT_URL)
    return _qdrant_client


@openlit.trace
def seed_qdrant():
    """Upsert the HR policy documents into Qdrant (idempotent)."""
    client = get_qdrant_client()
    vectors = embedding_fn.encode_documents(documents)
    points = [
        PointStruct(id=i, vector=vectors[i].tolist(), payload={"text": documents[i], "subject": "policy"})
        for i in range(len(documents))
    ]
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
    client.upsert(collection_name=QDRANT_COLLECTION, points=points)
    _rag_stats["seeds"] += 1
    return {"points": len(points)}


@openlit.trace
def search_qdrant(query: str) -> str:
    """Vector search over HR policies; returns the top 2 matching documents."""
    _rag_stats["qdrant_searches"] += 1
    client = get_qdrant_client()
    query_vector = embedding_fn.encode_queries([query])[0].tolist()
    res = client.query_points(collection_name=QDRANT_COLLECTION, query=query_vector, limit=2, with_payload=True)
    return json.dumps([{"id": p.id, "score": p.score, "payload": p.payload} for p in res.points])


# --- Search Engine (OpenSearch) ---------------------------------------------
#
# OpenSearch is the "Search Engines" component in SUSE Observability. The
# collector's elasticsearch receiver polls its REST API and
# resource/opensearch tags the metrics suse.ai.component.type=search-engine.
# These calls make the topology show hr-policy-db -> opensearch.


@openlit.trace
def seed_opensearch():
    """Index the HR policy documents into OpenSearch (idempotent)."""
    # Explicitly create the index with 0 replicas before the first doc PUT
    # auto-creates it with OpenSearch's default (1 replica): a single-node
    # cluster can never assign that replica shard, which permanently reports
    # cluster health "yellow" - DEVIATING under the SUSE AI health monitor -
    # even though everything is actually fine. No unassigned shards possible
    # with 0 replicas, so a single healthy node reports "green".
    requests.put(
        f"{OPENSEARCH_URL}/{OPENSEARCH_INDEX}",
        json={"settings": {"index": {"number_of_replicas": 0}}},
        timeout=5,
    )
    created = 0
    for i, doc in enumerate(documents):
        res = requests.put(
            f"{OPENSEARCH_URL}/{OPENSEARCH_INDEX}/_doc/{i}",
            json={"text": doc, "subject": "policy"},
            timeout=5,
        )
        if res.status_code in (200, 201):
            created += 1
    _rag_stats["seeds"] += 1
    return {"indexed": created}


@openlit.trace
def search_opensearch(query: str) -> str:
    """Full-text search over HR policies; returns the top 2 hits."""
    _rag_stats["opensearch_searches"] += 1
    res = requests.post(
        f"{OPENSEARCH_URL}/{OPENSEARCH_INDEX}/_search",
        json={
            "size": 2,
            "query": {"match": {"text": query}},
        },
        timeout=5,
    )
    hits = res.json().get("hits", {}).get("hits", [])
    # .get() throughout — a hit is not guaranteed to carry _score, and the
    # demo app must never 500 on a quirky backend response.
    return json.dumps([{"text": h.get("_source", {}).get("text", ""), "score": h.get("_score")} for h in hits])


# Simulates an API call to get flight times
# In a real application, this would fetch data from a live database or API
@openlit.trace
def get_benefits_information(benefit_type: str, employee_level: str) -> str:
    benefits = {
        "vacation-junior": {
            "days": "15 days",
            "accrual": "1.25 days per month",
            "carryover": "5 days max",
        },
        "vacation-senior": {
            "days": "20 days",
            "accrual": "1.67 days per month",
            "carryover": "10 days max",
        },
        "health-all": {
            "medical": "90% coverage",
            "dental": "80% coverage",
            "vision": "100% coverage",
        },
        "remote_work-all": {
            "days_per_week": "3 days max",
            "approval": "Manager required",
            "equipment": "Company provided",
        },
        "vacation-manager": {
            "days": "25 days",
            "accrual": "2.08 days per month",
            "carryover": "15 days max",
        },
        "health-manager": {
            "medical": "95% coverage",
            "dental": "90% coverage",
            "vision": "100% coverage",
        },
    }
    key = f"{benefit_type}-{employee_level}".lower()
    return json.dumps(benefits.get(key, {"error": "Benefit information not found"}))


@openlit.trace
def send_query_to_hr_ai(messages):
    # First API call: Send the query and function description to the model
    return ollama_chat(messages, tools=tools)


@openlit.trace
def process_hr_ai_response(messages, response):
    # Process function calls made by the model
    if response["message"].get("tool_calls"):
        available_functions = {
            "get_benefits_information": get_benefits_information,
        }

        for tool in response["message"]["tool_calls"]:
            function_name = tool["function"]["name"]
            function_to_call = available_functions.get(function_name)
            if function_to_call is None:
                print(f"Unknown tool call: {function_name}, skipping")
                continue

            # The model sometimes returns arguments as a JSON string, and
            # small models (llama3.2:1b) occasionally emit malformed
            # arguments (e.g. the function description as a kwarg name).
            # Tolerate both so the request never 500s.
            function_args = tool["function"]["arguments"]
            if isinstance(function_args, str):
                try:
                    function_args = json.loads(function_args)
                except Exception:
                    print(f"Malformed JSON tool args for {function_name}, skipping: {function_args}")
                    continue
            if not isinstance(function_args, dict):
                print(f"Unexpected tool args type for {function_name}, skipping")
                continue

            try:
                function_response = function_to_call(**function_args)
            except TypeError as e:
                # Drop invalid keys that the model hallucinated (e.g. the
                # function description as a kwarg name) and retry with only
                # the keys the function accepts.
                import inspect

                valid = inspect.signature(function_to_call).parameters
                filtered = {k: v for k, v in function_args.items() if k in valid}
                print(f"Tool call {function_name} got bad args ({e}); retrying with {filtered}")
                try:
                    function_response = function_to_call(**filtered)
                except Exception as e2:
                    print(f"Tool call {function_name} failed even after filtering: {e2}")
                    continue
            except Exception as e:
                print(f"Tool call {function_name} failed: {e}")
                continue
            # Add function response to the conversation. vLLM's OpenAI-compatible
            # schema requires tool_call_id to correlate this reply with the call
            # above; Ollama's native API doesn't need it (tool.get("id") is None
            # there, so the key is simply omitted).
            tool_message = {"role": "tool", "content": function_response}
            if tool.get("id"):
                tool_message["tool_call_id"] = tool["id"]
            messages.append(tool_message)
    # Second API call: Get final response from the model
    final_response = ollama_chat(messages)
    print(final_response["message"]["content"])
    return final_response


@openlit.trace
def handle_hr_inquiry(question: str):
    # Initialize conversation with a user query

    messages = [{"role": "user", "content": question}]

    # First API call: Send the query and function description to the model
    response = send_query_to_hr_ai(messages)

    # Add the model's response to the conversation history
    messages.append(response["message"])

    # Check if the model decided to use the provided function
    if not response["message"].get("tool_calls"):
        print("The model didn't use the function. Its response was:")
        print(response["message"]["content"])
        return

    # Process function calls made by the model
    return process_hr_ai_response(messages, response)


@openlit.trace
def start_hr_policy_system():
    try:
        # Seed the datastores once (first call only).
        # This keeps SUSE Observability showing hr-policy-db -> qdrant and
        # hr-policy-db -> opensearch in the topology without re-seeding on
        # every single request.
        ensure_datastores_seeded()

        question = "What are the vacation benefits for senior employees?"
        handle_hr_inquiry(question)
        # Exercise the vector database and search engine so telemetry flows
        # even when the LLM decides not to call its search tools.
        try:
            print("Qdrant search:", search_qdrant(question)[:120])
            print("OpenSearch search:", search_opensearch(question)[:120])
        except Exception as e:
            print(f"Datastore search failed: {e}")

        question = "What is our remote work policy?"
        return handle_hr_inquiry(question)
    except Exception as e:
        # Fall back to a plain LLM answer if the vector store is unavailable.
        # Keeps /ask returning 200 (and telemetry flowing) during vector-store
        # outages instead of surfacing a 500 to the load generator.
        print(f"RAG unavailable, falling back to plain LLM: {e}")
        response = ollama_chat([{"role": "user", "content": "What is our remote work policy?"}])
        return response
