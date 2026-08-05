# Shared OpenTelemetry collector: group SUSE AI components per namespace

The `open-telemetry-collector` release in the `observability` namespace runs a
revision of SUSE's GenAI pipeline that predates the `service.namespace` lookup. It
stamps every SUSE AI component with the collector's own `SUSE_AI_NAMESPACE`, so
applications from every namespace land under one label.

Current upstream, from `integrations/otel-collector/otel-values.yaml` in
https://github.com/SUSE/suse-ai-observability-extension, reads `service.namespace`
off the resource first and only falls back to the env var when an application did
not declare one. Applications that set `service.namespace` then group correctly
while a single collector keeps serving the whole cluster.

## The change

In each of the three `transform/infer-*` processors, replace the single
`k8s.namespace.name` statement with a pair. For `transform/infer-applications`:

```yaml
# before
- set(attributes["k8s.namespace.name"], "${env:SUSE_AI_NAMESPACE}")
# after
- set(attributes["k8s.namespace.name"], attributes["service.namespace"]) where attributes["service.namespace"] != nil
- set(attributes["k8s.namespace.name"], "${env:SUSE_AI_NAMESPACE}") where attributes["service.namespace"] == nil
```

For `transform/infer-models` (guarded on `gen_ai.request.model`) and
`transform/infer-providers` (guarded on `gen_ai.provider.name`), keep the existing
guard and add the namespace test to it:

```yaml
# before
- set(attributes["k8s.namespace.name"], "${env:SUSE_AI_NAMESPACE}") where attributes["gen_ai.provider.name"] != nil
# after
- set(attributes["k8s.namespace.name"], attributes["service.namespace"]) where attributes["gen_ai.provider.name"] != nil and attributes["service.namespace"] != nil
- set(attributes["k8s.namespace.name"], "${env:SUSE_AI_NAMESPACE}") where attributes["gen_ai.provider.name"] != nil and attributes["service.namespace"] == nil
```

`SUSE_AI_NAMESPACE` stays set. It becomes the fallback for telemetry with no
`service.namespace` of its own - Milvus, OpenSearch, and vLLM scraped over
Prometheus.

The processor ordering does not need to change: `k8s_attributes` still runs after
the transforms, and never overwrites an attribute that is already set.

## Applying it

```bash
helm get values open-telemetry-collector -n observability > otel-values.yaml
# edit the three transform/infer-* processors as above
helm upgrade open-telemetry-collector open-telemetry/opentelemetry-collector \
  -n observability -f otel-values.yaml
```

## Verifying

Set the fallback to a value that is not a real namespace, send some traffic, and
confirm it never appears:

```bash
kubectl set env deployment/open-telemetry-collector-opentelemetry-collector \
  -n observability SUSE_AI_NAMESPACE=SENTINEL-FALLBACK
kubectl logs -n observability deploy/open-telemetry-collector-opentelemetry-collector \
  | grep -o 'k8s.namespace.name: Str([^)]*)' | sort -u
```

Every component should report its own namespace, and `SENTINEL-FALLBACK` should not
appear. Restore the real value afterwards.

## Applications

An application only groups correctly if it declares `service.namespace`. The
hr-assistant chart sets it automatically via `OTEL_RESOURCE_ATTRIBUTES`; for anything
else, add it:

```yaml
- name: OTEL_RESOURCE_ATTRIBUTES
  value: "service.namespace=my-namespace,gen_ai.provider.name=ollama"
```
