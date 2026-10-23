# hr-assistant-load-gen

Keeps the demo busy: polls the three apps' /ask endpoints, and emits health-check spans for Qdrant and OpenSearch so they get a health state in SUSE Observability.

This chart is one component of the `hr-assistant` SUSE AI Factory blueprint (`catalog/blueprints/hr-assistant-1-1-0.yaml`). It vendors `charts/hr-assistant` (alias `hr`) and enables only this workload. See `charts/hr-assistant/README.md` for the full component list, how the components connect, and how to install the blueprint.
