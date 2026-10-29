# hr-assistant-vllm-topology

Declares the hr-assistant-vllm SUSE AI topology to SUSE Observability up front,
instead of relying on the SUSE AI collector to infer it from live spans:

```
hr-assistant ──uses──> hr-policy-db ──uses──> qdrant, opensearch
     │ └─────uses────> employee-handbook
     └──uses──> vllm <──uses── hr-policy-db, employee-handbook
                 └──runs──> Qwen/Qwen2.5-7B-Instruct
```

A post-install/post-upgrade Job sends the topology as OpenTelemetry metrics to
the shared SUSE AI collector (`otlpEndpoint`), and a CronJob refreshes it
(`refreshSchedule`, every 5 minutes). Each component and relation is one data
point of the `suse_ai_declared_component` / `suse_ai_declared_relation` gauge.
The SUSE AI Declared Topology StackPack maps them to the collector's own
identifiers (`urn:suse-ai:product:<type>:<name>`), so declared and inferred
components merge into one node; with no traffic, the nodes and edges stay.
After an uninstall they expire 15 minutes after the last refresh.

This chart is one component of the `hr-assistant-vllm` SUSE AI Factory blueprint
(`catalog/blueprints/hr-assistant-vllm-1-7-0.yaml`). Unlike the other
components it does not vendor `charts/hr-assistant-vllm`.

## Prerequisite: the SUSE AI Declared Topology StackPack

SUSE Observability 2.12 or later, with the StackPack 2.0 in
`stackpacks/suse-ai-declared-topology` installed after the SUSE AI StackPack:

```bash
sts stackpack test-deploy -d stackpacks/suse-ai-declared-topology
```

No API key or secret is needed: the collector forwards the metrics to SUSE
Observability with its own credentials.

## Values

| Value | Default | |
|---|---|---|
| `otlpEndpoint` | `http://opentelemetry-collector.observability.svc.cluster.local:4318` | OTLP/HTTP endpoint of the shared SUSE AI collector |
| `model` | `Qwen/Qwen2.5-7B-Instruct` | Name of the llm-model component |
| `topology.components` / `topology.relations` | the graph above | `type` is the identifier segment (must match the collector's `suse.ai.component.type`), `typeName` the SUSE Observability component type |
| `refreshSchedule` | `*/5 * * * *` | Keep well under the 15-minute expiry |

## Check it

```bash
kubectl logs -n <namespace> job/<release>-topology-init   # "Declared topology sent ... (HTTP 200)"
sts topology inspect --type agent --tag suse.ai.topology.source:declared
```
