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
- **Multi-Model Support**: Leverages Ollama for running local LLM models (llama3.2:1b for generation, bge-large for embeddings)
- **Comprehensive Observability**: Full OpenTelemetry instrumentation to monitor and trace all LLM interactions
- **CronJob Automation**: Scheduled testing of all services to ensure continuous availability
- **Production-Ready**: Deployed on Kubernetes with proper health checks and resource management

## Observability with SUSE Observability

The applications are instrumented with OpenLit and report GenAI telemetry that SUSE
Observability turns into a SUSE AI topology: each application, the Ollama inference
engine, and every model it calls appear as components, with token usage and cost
attached.

That topology is built from the `gen_ai.provider.name` resource attribute, so the
chart sets it (along with `gen_ai.request.model`) on every application pod. Change
it with `genai.providerName` if the apps are pointed at a different inference engine.

### Sending telemetry

Two options:

- **Shared collector** (default): set `otlpEndpoint` to an existing OpenTelemetry
  collector that already has the SUSE AI GenAI pipeline configured.
- **OpenTelemetry Operator**: set `opentelemetry.operator.enabled=true` and the chart
  asks the OpenTelemetry Operator to create a SUSE AI collector dedicated to this
  release, already wired with that pipeline. The applications are pointed at it
  automatically and the SUSE AI components are grouped under the release namespace.
  This needs the OpenTelemetry Operator installed in the cluster, plus the SUSE
  Observability URL, OTLP endpoint and an API key.

```bash
helm install hr-assistant . -n hr-assistant \
  --set opentelemetry.operator.enabled=true \
  --set opentelemetry.operator.clusterName=my-cluster \
  --set opentelemetry.operator.suseObservability.apiUrl=https://observability.example.com \
  --set opentelemetry.operator.suseObservability.otlpEndpoint=otlp-observability.example.com:443 \
  --set opentelemetry.operator.suseObservability.existingSecret=suse-obs-otlp
```

Set `opentelemetry.operator.debug=true` to also log the telemetry, including the
inferred SUSE AI components, to the collector's stdout when checking a demo.
