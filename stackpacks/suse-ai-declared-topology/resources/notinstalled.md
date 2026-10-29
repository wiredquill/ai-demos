## Prerequisites

Install the **SUSE AI Observability** StackPack first: declared components merge
with its components and use its component types.

Applications declare their topology as OpenTelemetry metrics sent through their
collector: a `suse_ai_declared_component` and a `suse_ai_declared_relation`
gauge, from instrumentation scope `suse-ai-declared-topology`, on a resource
with the attribute `suse.ai.topology.declared`.
