# hr-assistant-vllm-load-gen

Keeps the demo busy: polls the three apps' /ask endpoints, and emits health-check spans for Qdrant and OpenSearch so they get a health state in SUSE Observability.

This chart is one component of the `hr-assistant-vllm` SUSE AI Factory blueprint (`catalog/blueprints/hr-assistant-vllm-1-3-0.yaml`). It vendors `charts/hr-assistant-vllm` (alias `hr`) and enables only this workload. See `charts/hr-assistant-vllm/README.md` for the full component list, how the components connect, and how to install the blueprint.
