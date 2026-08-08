# rancher-ai-vllm

vLLM model serving optimized for **SUSE Rancher AI (Liz)**, wrapping the SUSE
Application Collection `vllm` chart (engine + router) and adding a Prometheus
scrape target for **SUSE Observability**.

## Why no proxy?

vLLM exposes token counts natively via `/metrics`
(`vllm:prompt_tokens_total`, `vllm:generation_tokens_total`,
`vllm:time_per_output_token_seconds`, ...). The cluster-level collector scrapes
the engine Service, renames `vllm:` → `vllm_`, and SUSE Observability graphs
tokens, tokens/sec, TTFT, and KV-cache pressure.

## Highlights

- Model dropdown organized by GPU VRAM class (16/24/64/100 GB)
- OpenAI-compatible router endpoint (port 80) — the sanctioned Rancher AI hook
- Model weights cached in a PVC (fast restarts), optional shared storage class
- Scrape target Service `<release>-engine-scrape` labelled
  `app.kubernetes.io/part-of=vllm` (+ `prometheus.io/*` annotations)
- Router traces via `routerSpec.otel.endpoint` (gRPC → collector)
- Native ingress via `routerSpec.ingress` for cross-cluster Rancher AI access

## Quick start (Rancher UI)

1. Add the ai-demos Cluster Repo
2. Apps → Charts → rancher-ai-vllm → Install
3. Pick your GPU class model, storage class, ingress host
4. Point Rancher AI at `http://<release>-router-service:80/v1`

Full walkthrough: [docs/rancher-ai-vllm.md](../../docs/rancher-ai-vllm.md)
Metrics & tokens/sec: [docs/rancher-ai-observability.md](../../docs/rancher-ai-observability.md)

## Notes

- Dependency: `vllm` 0.1.10 from `oci://dp.apps.rancher.io/charts` (vendored in
  `charts/`). Bump via `helm dependency update`.
- The collector scrape job lives in
  `templates/otel-collector-values-suse-ai.yaml` (cluster-level, not part of
  this chart).
