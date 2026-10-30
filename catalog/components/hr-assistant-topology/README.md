# hr-assistant-topology

Declares the demo's SUSE AI topology (apps -> ollama -> model, hr-policy-db -> Qdrant / OpenSearch) to SUSE Observability up front, so it shows before the first request. Needs SUSE Observability 2.12+ with the SUSE AI Declared Topology StackPack (stackpacks/suse-ai-declared-topology).

This chart is one component of the `hr-assistant` SUSE AI Factory blueprint (`catalog/blueprints/hr-assistant-1-2-0.yaml`). It vendors `charts/hr-assistant` (alias `hr`) and enables only this workload. See `charts/hr-assistant/README.md` for the full component list, how the components connect, and how to install the blueprint.
