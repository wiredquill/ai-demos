# rancher-ai-ollama

Ollama model serving optimized for **SUSE Rancher AI (Liz)**, fronted by a
**LiteLLM gateway** so every prompt's **token usage, cost, and latency** can be
tracked in **SUSE Observability**.

```
                         ┌─────────────────────────────────────────────┐
                         │           SUSE Observability (mort)         │
                         │   gen_ai.client.token.usage  ·  duration    │
                         │   litellm.cost.*  ·  traces + spans         │
                         └──────────────▲──────────────────────────────┘
                                        │ OTLP/HTTP :4318 (gen_ai.* metrics + traces)
                                        │
                         ┌──────────────┴───────────────┐
                         │   OpenTelemetry Collector    │
                         │   (observability ns)         │
                         └──────────────▲────────────────┘
                                        │ OTLP/HTTP
                    ┌───────────────────┴────────────────────┐
                    │           LiteLLM gateway (:4000)      │
                    │   OpenAI-compatible /v1 API            │
                    │   LITELLM_OTEL_V2=true (+metrics)      │
                    │   master key auth                      │
                    └───────────────────▲────────────────────┘
                                        │ /api/chat · /api/generate
                    ┌───────────────────┴────────────────────┐
                    │            Ollama (:11434)             │
                    │   gpt-oss:20b (or your model)          │
                    │   GPU-accelerated                      │
                    └────────────────────────────────────────┘
                                        ▲
                    ┌───────────────────┴────────────────────┐
                    │            Rancher AI (Liz)            │
                    │   openaiUrl → LiteLLM /v1              │
                    │   openaiApiKey → LiteLLM master key    │
                    └────────────────────────────────────────┘
```

## Why LiteLLM in front of Ollama?

Ollama has **no native OpenTelemetry export** (verified against source: no OTel
code, no `OLLAMA_OTEL_*` env vars, no `/metrics`). Token counts only exist in
the `/api/chat|generate` responses — so there is no way to see who used how many
tokens, or what it cost, without a proxy in front.

LiteLLM is the lightest proxy that solves this:

- One small pod, DB-less by default, OTLP/HTTP straight to the shared collector
- `LITELLM_OTEL_V2=true` emits `gen_ai.*` **spans** (traces)
- `LITELLM_OTEL_INTEGRATION_ENABLE_METRICS=true` additionally emits the
  **metric histograms** — `gen_ai.client.token.usage`,
  `gen_ai.client.operation.duration`, `gen_ai.client.response.duration`,
  `litellm.cost.total` — which power the token/cost dashboards
- OpenAI-compatible `/v1` endpoint — the **sanctioned Rancher AI hook**

> **Gotcha (fixed 2026-08-10):** `LITELLM_OTEL_V2=true` alone only exports
> traces. Token counts are *span attributes* on traces and do NOT become
> queryable metrics until `LITELLM_OTEL_INTEGRATION_ENABLE_METRICS=true` is set.
> This chart sets both by default (`litellm.observability.enableMetrics`).

## Highlights

- Model dropdown organized by GPU VRAM class (16/24/64/100 GB)
- LiteLLM OpenAI-compatible endpoint — ClusterIP (in-cluster), **NodePort**
  (each node's IP), or **LoadBalancer** (external IP) — pick in the UI
- Auto-generated master key (Secret `<release>-litellm-masterkey`), or supply
  your own via `litellm.masterkey` / reference an existing Secret via
  `litellm.masterkeySecret`
- Token/cost/latency metrics → SUSE Observability (`gen_ai.*`, `litellm.cost.*`)
- Optional shared model cache: PVC `existingClaim`, storage class, or NFS
  pre-warm
- Optional Ollama OTel sidecar (status/health only)
- Optional Ingress for cross-cluster Rancher AI access

## Quick start (Rancher UI)

1. Add the **ai-demos** Cluster Repo
2. Apps → Charts → **rancher-ai-ollama** → Install
3. Choose your GPU class model and storage
4. Choose how LiteLLM is exposed:
   - **ClusterIP** (default) — in-cluster only; fine if Rancher AI runs in the
     same cluster
   - **NodePort** — exposes on every node's IP, e.g. `http://<node-ip>:30080/v1`
   - **LoadBalancer** — static external IP (cloud / MetalLB)
5. If you need an **image pull secret** for the SUSE Registry
   (`registry.suse.com`), set `imagePullSecretName` (e.g. `suse-ai-registry`)
6. For a stable API key across upgrades, set `litellm.masterkey` or
   `litellm.masterkeySecret` instead of letting the chart generate one

### Point Rancher AI at it

In the Rancher AI config (llm-secret / model config):

```yaml
ACTIVE_LLM: openai
OPENAI_MODEL: gpt-oss:20b
OPENAI_URL: http://<litellm-address>/v1        # e.g. http://10.9.0.113:30080/v1
OPENAI_API_KEY: <litellm master key>           # from the litellm-masterkey Secret
```

If LiteLLM returns `No connected db.` errors, the API key does not match the
LiteLLM master key (litellm tries to validate a non-master key against its
internal DB, which is not configured) — put the real master key in the Rancher
AI secret and restart the agent.

## Install via Helm (CLI)

```bash
helm upgrade --install rancher-ai-ollama-0-1786389856 \
  /data/ai-demos/charts/rancher-ai-ollama -n liz \
  --set ollama.persistence.accessMode=ReadWriteOnce \
  --set litellm.resources.limits.memory=4Gi \
  --set litellm.service.type=NodePort \
  --set litellm.service.nodePort=30080
```

## Verification

```bash
# LiteLLM alive + OpenAI endpoint
curl http://<litellm-address>/health/liveliness     # → "I'm alive!"
curl -H "Authorization: Bearer $KEY" http://<litellm-address>/v1/chat/completions \
  -d '{"model":"gpt-oss:20b","messages":[{"role":"user","content":"hi"}]}'

# Token metrics reaching the collector
kubectl logs -n observability deploy/open-telemetry-collector-opentelemetry-collector \
  | grep gen_ai.client.token.usage
```

Tokens/sec query for SUSE Observability:

```promql
sum(rate(gen_ai_client_token_usage_sum[1m])) by (gen_ai_token_type)
```

## Values

See `values.yaml`. Key defaults: Ollama
`dp.apps.rancher.io/containers/ollama:0.21.2-11.48`, LiteLLM
`litellm/litellm:1.94.2` (public; swap to
`registry.suse.com/ai/containers/litellm` for SUSE AI customers), collector
endpoint
`http://open-telemetry-collector-opentelemetry-collector.observability.svc.cluster.local:4318`.

Full walkthrough: [docs/rancher-ai-ollama.md](../../docs/rancher-ai-ollama.md)
Metrics & tokens/sec: [docs/rancher-ai-observability.md](../../docs/rancher-ai-observability.md)
