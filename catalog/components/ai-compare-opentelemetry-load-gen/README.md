# ai-compare-opentelemetry-load-gen

Keeps the demo busy by calling the AI Compare HTTP API on an interval, and emits health-check spans for Ollama, Open WebUI and Pipelines so they get a health state in SUSE Observability.

This chart is one component of the `ai-compare-opentelemetry` SUSE AI Factory blueprint (`catalog/blueprints/ai-compare-opentelemetry-1-4-0.yaml`). It vendors `charts/ai-compare-opentelemetry` (alias `aic`) and enables only this workload. See the repository README ("SUSE AI Factory Blueprints") for the component list and how to install the blueprint.
