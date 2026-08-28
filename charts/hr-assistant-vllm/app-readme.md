## Introduction

The HR Assistant is an AI-powered application that simulates a comprehensive HR assistant for employees to ask HR-related questions. It demonstrates enterprise-grade LLM integration with comprehensive observability through OpenTelemetry and OpenLit, showcasing how organizations can monitor and trace AI/LLM interactions in production.

## Core Applications

### HR Assistant
The main conversational interface that answers employee questions about company policies, benefits, procedures, and more using an AI language model.

### Employee Handbook
A specialized RAG (Retrieval Augmented Generation) application that indexes HR documents (employee handbook, benefits guide, company policies) into a vector database and retrieves relevant information to answer employee questions with accuracy.

### HR Policy Database
A backend service that provides structured access to HR policies and procedures, supporting the other applications with verified policy information.

## Key Features

- **Intelligent Document Retrieval**: Uses LangChain with Milvus vector database to index and search HR documents
- **Multi-Model Support**: Leverages SUSE Application Collection's vLLM for high-throughput local LLM serving (e.g. Qwen2.5-7B-Instruct for generation)
- **Comprehensive Observability**: Full OpenTelemetry instrumentation to monitor and trace all LLM interactions
- **Load Generator (Deployment)**: Persistent pod that polls all app /ask endpoints on a fixed interval to keep topology fresh (replaces the old per-cycle CronJob that caused pod churn)
- **Production-Ready**: Deployed on Kubernetes with proper health checks and resource management

## Observability with SUSE Observability

The applications are instrumented with OpenLit and report GenAI telemetry that SUSE
Observability turns into a SUSE AI topology: each application, the vLLM inference
engine, and every model it calls appear as components, with token usage and cost
attached. vLLM's own `/metrics` endpoint is also scraped natively, adding
engine-level tokens/sec, TTFT, per-token latency, and KV-cache metrics that
Ollama cannot provide.

Two resource attributes make that work, and the chart sets both on every pod:

- `gen_ai.provider.name` - what SUSE Observability draws the inference engine from,
  and what links each application to the models it calls. OpenLit only emits the
  older `gen_ai.system` span attribute, so the chart supplies this explicitly.
  Override with `genai.providerName` if the apps point at a different engine.
- `service.namespace` - the namespace this release's components are grouped under.
  SUSE's collector reads this first and only falls back to its own
  `SUSE_AI_NAMESPACE` when an application does not declare one. Defaults to the
  release namespace; override with `observability.serviceNamespace`.

### One collector, many namespaces

Because each application names its own namespace, **a single shared collector can
serve the whole cluster** and still group every application correctly. A collector
per namespace is not required.

Set `observability.mode`:

- `existing` (default) - point `otlpEndpoint` at a collector that already runs in
  the cluster. Nothing extra is installed.
- `operator` - the OpenTelemetry Operator creates a SUSE AI collector dedicated to
  this release, pre-wired with the GenAI topology pipeline. Useful when a release
  needs its own ingestion path or the shared collector is out of reach. The
  applications are pointed at it automatically and the SUSE Observability API key is
  copied in by a pre-install hook, so there is no token to paste.

```bash
helm install hr-assistant-vllm . -n hr-assistant-vllm \
  --set observability.mode=operator \
  --set opentelemetry.operator.suseObservability.apiUrl=https://observability.example.com \
  --set opentelemetry.operator.suseObservability.otlpEndpoint=otlp-observability.example.com:443
```

Set `opentelemetry.operator.debug=true` to also log telemetry, including the inferred
SUSE AI components, to the collector's stdout when checking a demo.

If a shared collector is grouping everything under one namespace, it is running a
revision of SUSE's pipeline that predates the `service.namespace` lookup. See
`integrations/otel-collector/otel-values.yaml` in SUSE/suse-ai-observability-extension
for the current version.
