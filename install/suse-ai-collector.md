# Shared SUSE AI collector (one per cluster)

Every SUSE AI demo app (hr-assistant, hr-assistant-vllm,
ai-compare-opentelemetry) sends OTLP to one shared collector per cluster:
`opentelemetry-collector` in namespace `observability`, installed from
`charts/ai-observability-collector`. It runs the SUSE AI collector image
(`ghcr.io/suse/suse-ai-opentelemetry-collector`), which has the `topology`
exporter that builds the SUSE AI view. The Application Collection
`opentelemetry-collector` image does not, so the SUSE AI view stays empty with
it.

With this collector in place the apps need no observability settings: their
default `observability.mode=existing` finds it automatically.

## What it collects

- OTLP traces and metrics from the apps, with the SUSE AI topology inference
  (app -> inference engine -> model, app -> vector DB / search engine)
- vLLM serving engines, any namespace (`vllm:` renamed to `vllm_`, plus the two
  vLLM 0.19 aliases the SUSE AI dashboard queries)
- Qdrant, any namespace (feeds the SUSE AI Qdrant health monitors)
- OpenSearch, any namespace (elasticsearch receiver per pod labelled
  `app.component=opensearch`; feeds the OpenSearch health monitors, which
  expect the cluster to be named `opensearch-cluster`)
- NVIDIA DCGM GPU metrics
- span metrics for service health; OTLP logs are dropped (SUSE Observability
  2.10 has no OTLP logs service, the agent collects logs)

## Prerequisites

- OpenTelemetry Operator in the cluster
- Secret `open-telemetry-collector` (key `API_KEY`) in `observability`

## Install

```bash
cat > values-<cluster>.yaml <<EOF
collector:
  clusterName: <cluster>      # must match the cluster name in SUSE Observability
  backendEndpoint: https://observability.mort.dna-42.com
  otlpEndpoint: otlp-observability.mort.dna-42.com:443
EOF

helm upgrade --install opentelemetry-collector charts/ai-observability-collector \
  -n observability -f values-<cluster>.yaml
```

## Replacing an existing Application Collection collector

If the cluster already has an `OpenTelemetryCollector` named
`opentelemetry-collector` (and a Service of the same name) that was created
with `kubectl apply`, hand both to the Helm release first, then install with
`--force-conflicts` so Helm takes over the fields `kubectl` owned. The
operator rolls the collector in place; Service names do not change, so apps
keep sending to the same address.

```bash
for r in opentelemetrycollector/opentelemetry-collector service/opentelemetry-collector; do
  kubectl annotate -n observability $r --overwrite \
    meta.helm.sh/release-name=opentelemetry-collector \
    meta.helm.sh/release-namespace=observability
  kubectl label -n observability $r --overwrite app.kubernetes.io/managed-by=Helm
done

helm upgrade --install opentelemetry-collector charts/ai-observability-collector \
  -n observability -f values-<cluster>.yaml --force-conflicts
```
