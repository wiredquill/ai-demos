# SUSE AI Declared Topology StackPack

A StackPack 2.0 (SUSE Observability 2.12 or later) that lets an application
declare its SUSE AI topology up front instead of waiting for the SUSE AI
collector to infer it from live spans. Requires the SUSE AI Observability
StackPack.

An application sends two gauges through its OpenTelemetry collector, on a
resource with the attribute `suse.ai.topology.declared` and instrumentation
scope `suse-ai-declared-topology`:

| Metric | One data point per | Data point attributes |
|---|---|---|
| `suse_ai_declared_component` | component | `type` (SUSE AI component type, e.g. `inference-engine`), `name`, optional `type_name` (e.g. `inference-engine.vllm`) |
| `suse_ai_declared_relation` | relation | `source.type`, `source.name`, `target.type`, `target.name`, optional `type` (default `uses`) |

`settings/component-mappings/declared-component.sty` turns each component data
point into `urn:suse-ai:product:<type>:<name>`, the SUSE AI collector's own
identifier, so the declared and inferred components are one node (the SUSE AI
sync's name and type win). `settings/relation-mappings/declared-relation.sty`
connects them. Elements expire 15 minutes after the last data point, so send
them every few minutes. `charts/hr-assistant-vllm` (`templates/topology.yaml`) is a
sender.

## Install

```bash
sts stackpack test-deploy -d stackpacks/suse-ai-declared-topology   # package, upload, install or upgrade
```

Upgrading from 0.1.0 (the Receiver API DataSource and Sync, before StackPacks
2.0): uninstall it first.

```bash
sts stackpack uninstall --name suse-ai-declared-topology --id <instance id>   # from sts stackpack list-instances
```

## Check it

```bash
sts otel-component-mapping status --identifier urn:stackpack:suse-ai-declared-topology:shared:otel-component-mapping:declared-component
sts topology inspect --type agent --tag suse.ai.topology.source:declared
```
