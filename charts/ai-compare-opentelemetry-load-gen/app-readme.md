# AI Compare (OpenTelemetry): Load generator + health-check emitter

Keeps the demo busy by calling the AI Compare HTTP API on an interval, and emits health-check spans for Ollama, Open WebUI and Pipelines so they get a health state in SUSE Observability.

Part of the **ai-compare-opentelemetry** SUSE AI Factory blueprint (Ollama, Open WebUI and Pipelines plus the AI Compare components). Install all components into the same namespace (the blueprint does this for you).
