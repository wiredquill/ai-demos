# HR Assistant (vLLM): Load generator + health-check emitter

Keeps the demo busy: polls the three apps' /ask endpoints, and emits health-check spans for Qdrant and OpenSearch so they get a health state in SUSE Observability.

Part of the **hr-assistant-vllm** SUSE AI Factory blueprint, which deploys each of its eight pods as a separate component. Install all eight into the same namespace (the blueprint does this for you).
