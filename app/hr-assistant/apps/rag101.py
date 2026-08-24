import json
import os

import ollama
import openlit
import requests
from pymilvus import MilvusClient, model

MILVUS_URL = "./rag101.db"
MODEL = os.getenv("MODEL", "llama3.2")
EMBEDDING_MODEL = "bge-large"

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


def get_rag_stats() -> dict:
    """Snapshot of RAG activity for the /stats endpoint."""
    return dict(_rag_stats)


embedding_fn = model.DefaultEmbeddingFunction()

# Keep a single MilvusClient for the lifetime of the process. milvus-lite's
# embedded server is bound to the client that started it; creating a fresh
# MilvusClient per request (the pymilvus 2.x pattern) lets the old embedded
# server on 127.0.0.1:<port> die, and the next request fails with
# "Fail connecting to server ... server unavailable". A module-level client
# keeps the server alive across /ask calls.
_milvus_client = None


def get_milvus_client():
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient(MILVUS_URL)
    return _milvus_client


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
    {
        "type": "function",
        "function": {
            "name": "search_policy_database",
            "description": "Search HR policies and employee guidelines in the policy database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


@openlit.trace
def initialize_policy_database():
    vectors = embedding_fn.encode_documents(documents)
    # The output vector has 768 dimensions, matching the collection that we just created.
    print("Dim:", embedding_fn.dim, vectors[0].shape)  # Dim: 768 (768,)

    # Each entity has id, vector representation, raw text, and a subject label.
    data = [{"id": i, "vector": vectors[i], "text": documents[i], "subject": "history"} for i in range(len(vectors))]
    print("Data has", len(data), "entities, each with fields: ", data[0].keys())
    print("Vector dim:", len(data[0]["vector"]))
    return data


@openlit.trace
def build_policy_vault():
    data = initialize_policy_database()
    # Create a collection and insert the data
    client = get_milvus_client()
    client.create_collection(
        collection_name="demo_collection",
        dimension=768,
    )
    client.insert(collection_name="demo_collection", data=data)


# --- Vector Database (Qdrant) -----------------------------------------------
#
# Qdrant is the "Vector Databases" component in SUSE Observability. The
# collector's transform/qdrant tags its scraped metrics
# suse.ai.component.type=vectordb. These calls make the topology show
# hr-policy-db -> qdrant. All wrapped in @openlit.trace so every upsert and
# search produces a span (and gen_ai metrics when the embedding model runs).


@openlit.trace
def seed_qdrant():
    """Upsert the HR policy documents into Qdrant (idempotent)."""
    vectors = embedding_fn.encode_documents(documents)
    points = [
        {
            "id": i,
            "vector": vectors[i].tolist(),
            "payload": {"text": documents[i], "subject": "policy"},
        }
        for i in range(len(documents))
    ]
    # Create collection if it does not exist (ignore "already exists").
    requests.put(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}",
        json={"vectors": {"size": 768, "distance": "Cosine"}},
        timeout=5,
    )
    # Upsert points (idempotent).
    requests.put(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points",
        json={"points": points},
        timeout=5,
    )
    _rag_stats["seeds"] += 1
    return {"points": len(points)}


@openlit.trace
def search_qdrant(query: str) -> str:
    """Vector search over HR policies; returns the top 2 matching documents."""
    _rag_stats["qdrant_searches"] += 1
    query_vector = embedding_fn.encode_queries([query])[0].tolist()
    res = requests.post(
        f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search",
        json={"vector": query_vector, "limit": 2, "with_payload": True},
        timeout=5,
    )
    return json.dumps(res.json())


# --- Search Engine (OpenSearch) ---------------------------------------------
#
# OpenSearch is the "Search Engines" component in SUSE Observability. The
# collector's elasticsearch receiver polls its REST API and
# resource/opensearch tags the metrics suse.ai.component.type=search-engine.
# These calls make the topology show hr-policy-db -> opensearch.


@openlit.trace
def seed_opensearch():
    """Index the HR policy documents into OpenSearch (idempotent)."""
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


# Search data related to Artificial Intelligence in a vector database


@openlit.trace
def search_policy_database(query: str) -> str:
    query_vectors = embedding_fn.encode_queries([query])
    client = get_milvus_client()
    res = client.search(
        collection_name="demo_collection",
        data=query_vectors,
        limit=2,
        output_fields=["text", "subject"],  # specifies fields to be returned
    )
    print(res)
    return json.dumps(res)


@openlit.trace
def send_query_to_hr_ai(messages):
    # First API call: Send the query and function description to the model
    client = ollama.Client()
    response = client.chat(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    return response


@openlit.trace
def process_hr_ai_response(messages, response):
    # Process function calls made by the model
    if response["message"].get("tool_calls"):
        available_functions = {
            "get_benefits_information": get_benefits_information,
            "search_policy_database": search_policy_database,
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
            # Add function response to the conversation
            messages.append(
                {
                    "role": "tool",
                    "content": function_response,
                }
            )
    # Second API call: Get final response from the model
    client = ollama.Client()
    final_response = client.chat(model=MODEL, messages=messages)
    print(final_response["message"]["content"])
    return final_response


@openlit.trace
def handle_hr_inquiry(question: str):
    client = ollama.Client()

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
        build_policy_vault()
        # Seed the Qdrant vector store and OpenSearch index (idempotent).
        # These make SUSE Observability show hr-policy-db -> qdrant and
        # hr-policy-db -> opensearch in the topology.
        try:
            seed_qdrant()
            seed_opensearch()
        except Exception as e:
            print(f"Datastore seeding failed (will retry next cycle): {e}")

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
        client = ollama.Client()
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "What is our remote work policy?"}],
        )
        return response
