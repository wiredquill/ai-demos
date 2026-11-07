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
| `suse_ai_declared_component` | component | `type` (SUSE AI component type, e.g. `inference-engine`), `name`, optional `type_name` (e.g. `inference-engine.vllm`), optional `instance`, optional `namespace`, optional `product` (the `suse.ai.product` tag, e.g. `vllm`) |
| `suse_ai_declared_relation` | relation | `source.type`, `source.name`, `target.type`, `target.name`, optional `type` (default `uses`), optional `source.instance` / `target.instance`, optional `source.namespace` / `target.namespace` |

`settings/component-mappings/declared-component.sty` turns each component data
point into the identifier SUSE Observability gives the same component from live
telemetry, so the declared and observed components are one node. The first
rule that applies wins:

- `instance` (the `service.instance.id` the component reports) with a
  `k8s.namespace.name` resource attribute:
  `urn:suse-ai:urn:opentelemetry:namespace/<namespace>:service/<name>:serviceInstance/<instance>`.
- `namespace` (the `service.namespace` the component reports, or that its
  callers report for an inference engine or database seen in their traces):
  `urn:opentelemetry:namespace/<namespace>:service/<name>`, type `otel service`.
  This is the OpenTelemetry service the SUSE AI and OpenTelemetry StackPacks
  create for an application, inference engine, vector database or search
  engine, and what the SUSE AI view shows. Use it for those.
- neither: `urn:suse-ai:product:<type>:<name>`, which every namespace shares.
  Use it for something SUSE AI has no single component for, such as a model
  (it tracks model usage per calling application).

`settings/relation-mappings/declared-relation.sty` connects them, identifying
each end the same way. Elements expire 15 minutes after the last data point,
so send them every few minutes. `charts/hr-assistant-vllm` and
`charts/hr-assistant` (`templates/topology.yaml`) are senders.

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
