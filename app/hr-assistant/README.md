# HR Assistant — Clean Application

This is the clean baseline of the HR Assistant demo: a small AI application
with **no observability instrumentation** (no OpenLIT, no OpenTelemetry, no
collector, no load generator). It is the reference "clean app" that the
`feat/stackpack-v2` branch uses as the starting point for SUSE Observability
StackPack v2 instrumentation — see `docs/stackpack-v2.md` for how to take a
clean app like this one and add StackPack v2 with a single AI prompt.

## What the app does

Three FastAPI services (one codebase, three `APP_NAME` variants) plus their
backends:

| Service | Role | Backends |
|---|---|---|
| `hr-assistant` | HRAssistant — orchestrator: generates an HR inquiry, consults the other two services in parallel, produces a professional response | Ollama, hr-policy-db, employee-handbook |
| `hr-policy-db` | HRPolicyDatabase — RAG with tool calling: seeds + searches Qdrant (vector) and OpenSearch (full-text) | Ollama, Qdrant, OpenSearch |
| `employee-handbook` | EmployeeHandbook — direct LLM Q&A on onboarding procedures | Ollama |

Backends: Ollama (subchart, optional GPU), Qdrant, OpenSearch — all deployed
by the `charts/hr-assistant` Helm chart.

## Endpoints

Each service exposes:

- `/ask` — the app's workflow (LLM chain; RAG variant runs tool calls +
  datastore searches)
- `/health` — `{"Status": "Ready"}`
- `/stats` — in-memory counters (requests, errors, uptime, RAG activity for
  hr-policy-db)
- `/logs` — recent application log lines (stdout ring buffer)
- `/` — single-file live dashboard (`dashboard.html`) polling `/stats` and
  `/logs`; it just makes the demo feel alive, nothing more

## Running it

Deploy from the Rancher UI (Apps → ai-demos → hr-assistant) or:

```bash
helm upgrade --install hr-assistant charts/hr-assistant -n hr-assistant \
  -f <your-values.yaml> --wait
```

The `qdrant.enabled` and `opensearch.enabled` questions toggle the RAG
backends. Ollama is deployed by the bundled subchart (or point
`ollamaEndpoint` at an existing server with `ollama.enabled=false`).

## Files

```
app/hr-assistant/
  main.py            FastAPI app: /ask, /health, /stats, /logs, / (dashboard)
  dashboard.html     Apple-design live dashboard (single file)
  apps/simple.py     HRAssistant: orchestrator, parallel downstream /ask calls
  apps/rag101.py     HRPolicyDatabase: Qdrant + OpenSearch RAG with tool calling
  apps/rag102.py     EmployeeHandbook: LangChain LLM Q&A
  Dockerfile         SUSE BCI two-stage build (poetry)
charts/hr-assistant/
  templates/
    deployment-hr-assistant.yaml      orchestrator
    deployment-hr-policy-db.yaml      RAG app (envs point at qdrant/opensearch)
    deployment-employee-handbook.yaml LLM Q&A
    deployment-qdrant.yaml            Vector DB
    deployment-opensearch.yaml        Search Engine
    job-ollama-model-puller.yaml      pre-pulls configured models
    service-*.yaml, serviceaccount.yaml
  values.yaml        toggles + images + resource config
  questions.yaml     Rancher UI form
```
