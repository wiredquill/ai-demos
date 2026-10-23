# ai-compare-load-gen

Keeps the demo busy by calling the AI Compare HTTP API on an interval, and (with OpenTelemetry on) emits health-check spans for Ollama, Open WebUI and Pipelines so they get a health state in SUSE Observability.

This chart is one component of the `ai-compare` SUSE AI Factory blueprint (`catalog/blueprints/ai-compare-suse-1-3-0.yaml`, `catalog/blueprints/ai-compare-1-3-0.yaml`). It vendors `charts/ai-compare` (alias `aic`) and enables only this workload. See the repository README ("SUSE AI Factory Blueprints") for the component list and how to install the blueprint.
