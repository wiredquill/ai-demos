# HR Assistant — SUSE AI Factory + SUSE Observability Demo

This demo app is deliberately tiny. It exists so you can see **how a small AI
application appears in SUSE Observability's SUSE AI section** — which
components show up, which metrics flow, and which code produces them.

## What you see in SUSE Observability

Open SUSE Observability → **SUSE AI** and you get these topics:

| Topic | Component in this demo | How it is produced |
|---|---|---|
| AI Applications | `hr-assistant`, `employee-handbook`, `hr-policy-db` | OpenLIT-instrumented apps emitting `gen_ai.*` metrics; collector's `infer-applications` pipeline tags them `suse.ai.component.type=application` |
| Inference Engines | `ollama` | Resource attribute `gen_ai.provider.name=ollama`; collector's `infer-providers` pipeline creates the engine + app→engine relation |
| LLM Models | `llama3.2:1b`, `llama3.2:latest`, `bge-large` | Resource attribute `gen_ai.request.model`; collector's `infer-models` pipeline creates the model + engine→model relation |
| Vector Databases | `qdrant` | Prometheus scrape of `qdrant:6333/metrics`; collector's `transform/qdrant` tags it `suse.ai.component.type=vectordb` |
| Search Engines | `opensearch` | Collector's `elasticsearch` receiver polls the OpenSearch REST API; `resource/opensearch` tags it `suse.ai.component.type=search-engine` |
| GPU Nodes | dev-ai node | `gpu-metrics` Prometheus scrape of `nvidia-dcgm-exporter` (DCGM) |
| All GenAI Components | everything above | Union of all component types |

## How the code maps to the categories

### AI Applications — `main.py` + `apps/*.py`

`main.py` calls `openlit.init(...)` with an `application_name` and the chart
passes `OTEL_SERVICE_NAME` + `OTEL_RESOURCE_ATTRIBUTES` (see
`charts/hr-assistant/templates/_helpers.tpl`). Every LLM call inside
`@openlit.trace` functions emits `gen_ai.*` metrics, which the collector's
`infer-applications` pipeline turns into an **AI Application** component.

### Inference Engines + LLM Models — `_helpers.tpl`

The chart sets, as *resource* attributes:

```
gen_ai.provider.name=ollama
gen_ai.request.model=llama3.2:1b
```

The collector's `infer-providers` and `infer-models` pipelines read these and
create the **Inference Engine** and **LLM Model** components, plus the
relations `hr-policy-db → ollama → llama3.2`.

### Vector Databases — `apps/rag101.py` + `templates/otel-collector-values-suse-ai.yaml`

`seed_qdrant()` / `search_qdrant()` talk to Qdrant over its REST API. The
collector scrapes Qdrant's `/metrics` and `transform/qdrant` tags the series
`vectordb`, so a **Vector Database** component appears. Every `search_qdrant`
call also bumps the `_rag_stats` counter surfaced on `/stats`.

### Search Engines — `apps/rag101.py` + collector

`seed_opensearch()` / `search_opensearch()` talk to OpenSearch's REST API. The
collector's `elasticsearch` receiver polls OpenSearch's `_cluster/health` and
`_nodes/stats`, and `resource/opensearch` tags them `search-engine`.

## Dashboard — `/`

The app serves a single-file Apple-design dashboard at `/` (the service's
landing page). It polls `/stats` (request counters + RAG activity) and `/logs`
(stdout ring buffer) same-origin. It is not a replacement for SUSE
Observability — it just makes the demo feel alive and shows the same workload
that appears in the SUSE AI view. `/health` serves the plain JSON status
check that used to live at `/`.

- `main.py` — `/health` status endpoint, `/stats` endpoint (requests, errors,
  uptime, RAG counters), `/logs` endpoint (ring buffer fed by a stdout tee),
  `/` dashboard route
- `dashboard.html` — self-contained HTML/CSS/JS, no build step

## Running it

Deploy from the Rancher UI (Apps → ai-demos → hr-assistant) or:

```bash
helm upgrade --install hr-assistant charts/hr-assistant -n hr-assistant \
  -f <your-values.yaml> --wait
```

The `qdrant.enabled` and `opensearch.enabled` questions toggle the Vector
Database and Search Engine components. The load-generator Deployment (default
`loadGenerator.intervalSeconds: 120`) hits `/ask` every two minutes so
telemetry keeps flowing — the topology TTL expires components ~2 minutes after
the last signal.

## Files

```
app/hr-assistant/
  main.py            FastAPI app: OpenLIT init, /ask, /health, /stats, /logs, / (dashboard)
  dashboard.html     Apple-design live dashboard (single file)
  apps/rag101.py     RAG app: Milvus (local) + Qdrant + OpenSearch traffic
  apps/rag102.py     Employee handbook RAG (LangChain + Milvus)
  apps/simple.py     Plain chat app
charts/hr-assistant/
  templates/
    deployment-qdrant.yaml      Vector DB component
    deployment-opensearch.yaml  Search Engine component
    deployment-hr-policy-db.yaml  RAG app (envs point at qdrant/opensearch)
    deployment-load-generator.yaml  Persistent load-gen Deployment
  values.yaml        qdrant / opensearch toggle + images + loadGenerator config
templates/otel-collector-values-suse-ai.yaml   shared collector reference:
    transform/qdrant, resource/opensearch, elasticsearch receiver, qdrant job
```
