# hr-assistant-vllm-router

SUSE vLLM router: the OpenAI-compatible entry point (Service vllm-router-service when installed as release vllm). Discovers the engine pods in the namespace by label.

This chart is one component of the `hr-assistant-vllm` SUSE AI Factory blueprint (`catalog/blueprints/hr-assistant-vllm-1-3-0.yaml`). It vendors `charts/hr-assistant-vllm` (alias `hr`) and enables only this workload. See `charts/hr-assistant-vllm/README.md` for the full component list, how the components connect, and how to install the blueprint.
