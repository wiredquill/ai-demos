# HR Assistant (vLLM): Declared topology (CronJob)

Declares the demo's SUSE AI topology (apps -> vllm -> model, hr-policy-db -> Qdrant / OpenSearch) to SUSE Observability up front, so it shows before the first request. Needs SUSE Observability 2.12+ with the SUSE AI Declared Topology StackPack (stackpacks/suse-ai-declared-topology).

Part of the **hr-assistant-vllm** SUSE AI Factory blueprint (SUSE vLLM, Qdrant and OpenSearch plus four app components). Install all components into the same namespace (the blueprint does this for you).
