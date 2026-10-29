# HR Assistant (vLLM): Declared topology

Declares the demo's SUSE AI topology (apps -> vLLM -> model, apps -> Qdrant / OpenSearch) to SUSE Observability up front, so the topology does not depend on live traffic.

Requires SUSE Observability 2.12+ with the **SUSE AI Declared Topology** StackPack 1.0.0 (`stackpacks/suse-ai-declared-topology`), and the shared SUSE AI collector. Part of the **hr-assistant-vllm** SUSE AI Factory blueprint.
