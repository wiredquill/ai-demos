# ai-observability-collector

Deploy a SUSE AI OpenTelemetry collector **once**, then every new app that
carries the standard discovery labels/annotations is collected automatically —
no collector re-deploy on every app change.

Managed by the [OpenTelemetry Operator](https://opentelemetry.io/docs/platforms/kubernetes/operator/),
using the **SUSE AI collector image** (which ships the proprietary `topology`
exporter that powers the SUSE AI topology view).

## Why

With a hand-written collector you end up editing `values.yaml` and redeploying
every time you add a service, change a namespace, or spin up a new Qdrant /
OpenSearch / vLLM / model. This chart replaces all of that with **label-driven
auto-discovery**:

- Prometheus receiver uses dynamic Kubernetes service discovery
  (`role: pod`), kept only on standard markers.
- No hardcoded `job_name` per app, no namespace-pinned scrape blocks, no
  endpoint edits.
- Optional **auto-instrumentation** (Instrumentation CRs) gives zero-code
  tracing for Python / Node.js / Java apps via a single annotation.
- Same verified SUSE AI relay config (infer-* pipelines, tail-sampling,
  topology exporter) as the manual setup — but parameterized.

## Requirements

- **OpenTelemetry Operator** installed (SUSE Application Collection chart):
  ```bash
  helm install opentelemetry-operator oci://dp.apps.rancher.io/charts/opentelemetry-operator \
    --namespace observability --version <pin> \
    --set global.imagePullSecrets={application-collection} \
    --set manager.autoInstrumentation.python.enabled=true \
    --set manager.autoInstrumentation.nodejs.enabled=true \
    --set manager.autoInstrumentation.java.enabled=true
  ```
  (Rancher UI: Apps > Charts > opentelemetry-operator, from the SUSE
  Application Collection catalog.)
- **API key**: a secret named `open-telemetry-collector` with key `API_KEY`
  exists in the `sourceNamespace` (default `observability`), or is created in
  the release namespace by the pre-install hook (it copies it).
- SUSE AI / Rancher AI clusters auto-create the `application-collection` +
  `suse-registry` imagePullSecrets in every namespace.

## Install

```bash
helm install ai-obs oci://dp.apps.rancher.io/charts/ai-observability-collector \
  --namespace ai-observability --create-namespace
```

Or install from the Rancher UI (Apps & Marketplace) using the `questions.yaml`
form — set the cluster name and your SUSE Observability endpoints.

Collector endpoint for apps: `http://<name>-collector.<namespace>.svc.cluster.local:4318`

## Onboarding an app (zero collector changes)

Add these to your workload's pod template:

```yaml
metadata:
  labels:
    observability/enabled: "true"      # label-driven discovery (OR the annotation below)
  annotations:
    prometheus.io/scrape: "true"       # standard prometheus convention
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
    instrumentation.opentelemetry.io/inject-python: "true"   # optional: zero-code tracing
```

The collector picks it up automatically on the next scrape interval.

> ⚠️ Do **not** add the `instrumentation.opentelemetry.io/inject-*` annotation
> to apps that already bundle an OTel SDK (e.g. OpenLIT apps) — that produces
> duplicate spans.

## Verify

```bash
kubectl get otelcollector -n ai-observability          # STATUS: READY
kubectl get pods -n ai-observability                   # collector Running
kubectl logs deploy/ai-observability-collector -n ai-observability -c otc-container | grep -iE 'topology sent|error'
```

## Values / FAQ

| Value | Default | Purpose |
|-------|---------|---------|
| `collector.clusterName` | `dev-ai` | `k8s.cluster.name`; must match the StackPack instance |
| `collector.image` / `.tag` | SUSE AI `0.156.0` | SUSE AI collector image (has `topology` exporter) |
| `collector.backendEndpoint` | `https://observability.mort.dna-42.com` | Topology exporter endpoint |
| `collector.otlpEndpoint` | `otlp-observability.mort.dna-42.com:443` | OTLP gRPC ingest |
| `discovery.gpu.enabled` | `true` | Scrape DCGM GPU metrics |
| `instrumentation.python/nodejs/java.enabled` | py `true` | Create the matching Instrumentation CR |
| `sampleApp.enabled` | `false` | Deploy the demo app to verify the pipeline |

SUSE docs: [AI Factory — AI monitoring with OTel Operator](https://documentation.suse.com/suse-ai-factory/latest/html/AI-monitoring/ai-monitoring-otel-operator.html)
