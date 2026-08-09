# rancher-ai-ollama

Ollama model serving optimized for **SUSE Rancher AI (Liz)** with a **LiteLLM**
gateway that exports token/cost/latency metrics (`gen_ai.*`) to **SUSE
Observability**.

## Why LiteLLM?

Ollama has **no native OpenTelemetry export** (verified against source: no OTel
code, no `OLLAMA_OTEL_*` env vars, no `/metrics`). Token counts only exist in
`/api/chat|generate` responses, so a proxy is required to produce token
metrics. LiteLLM with `LITELLM_OTEL_V2=true` is the lightest path: one small
pod, DB-less by default, OTLP/HTTP straight to the shared collector.

## Highlights

- Model dropdown organized by GPU VRAM class (16/24/64/100 GB)
- LiteLLM OpenAI-compatible endpoint (:4000) — the sanctioned Rancher AI hook
- Auto-generated master key (Secret `<release>-rancher-ai-ollama-litellm-masterkey`)
- Optional shared model cache: PVC `existingClaim`, storage class, or NFS
  pre-warm (hr-assistant / ai-compare pattern)
- Optional Ollama OTel sidecar (status/health only)
- Optional Ingress for cross-cluster Rancher AI access

## Quick start (Rancher UI)

1. Add the ai-demos Cluster Repo
2. Apps → Charts → rancher-ai-ollama → Install
3. Pick your GPU class model, storage, and (if cross-cluster) ingress host
4. Point Rancher AI at `http://<release>-rancher-ai-ollama-litellm:4000/v1`
   with the master key

Full walkthrough: [docs/rancher-ai-ollama.md](../../docs/rancher-ai-ollama.md)
Metrics & tokens/sec: [docs/rancher-ai-observability.md](../../docs/rancher-ai-observability.md)

## Values

See `values.yaml`. Key defaults: Ollama `dp.apps.rancher.io/containers/ollama:0.21.2-11.48`,
LiteLLM `litellm/litellm:1.94.2` (public; swap to
`registry.suse.com/ai/containers/litellm` for SUSE AI customers),
collector endpoint `http://open-telemetry-collector-opentelemetry-collector.observability.svc.cluster.local:4318`.
