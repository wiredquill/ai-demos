# HR Assistant (vLLM): Load generator + health-check emitter

Keeps the demo busy: polls the three apps' /ask endpoints, and emits health-check spans for Qdrant and OpenSearch so they get a health state in SUSE Observability.

Part of the **hr-assistant-vllm** SUSE AI Factory blueprint (SUSE vLLM, Qdrant and OpenSearch plus four app components). Install all components into the same namespace (the blueprint does this for you).
