# Rancher AI — Ollama Serving (rancher-ai-ollama)

Deploy an **Ollama** model server with a **LiteLLM** gateway in front, wired for
**SUSE Rancher AI (Liz)** and **SUSE Observability** token costing.

Ollama itself has **no OpenTelemetry export** (verified against source: no OTel
code, no `OLLAMA_OTEL_*` env vars, no `/metrics` endpoint). Token counts only
exist in `/api/chat|generate` responses, so the LiteLLM proxy is what produces
token metrics. This is the "lightest touch" path:

```
                    ┌─────────────────────────────┐
  Rancher AI (Liz)  │  rancher-ai-ollama chart    │
  openaiUrl ───────▶│  LiteLLM :4000 ──▶ Ollama   │
                    │      │                       │
                    │      └── OTel v2 ──▶ shared  │
                    │           gen_ai.* metrics   │
                    │           collector          │
                    └─────────────────────────────┘
```

## Prerequisites

- A Rancher cluster with the **SUSE Application Collection** catalog installed
  (provides the `application-collection` image pull secret + `dp.apps.rancher.io`
  registry access).
- **GPU Operator** (or device plugin) on the worker nodes you plan to use.
- A **SUSE Observability** instance with the shared OTel collector deployed
  (see `templates/otel-collector-values-suse-ai.yaml` in this repo). Note the
  collector Service DNS name and port (4318 for OTLP/HTTP).
- (Optional) an existing model-cache PVC or NFS share to avoid re-downloading
  models on every cluster (see Storage below).

## Install via Rancher UI

1. Make sure the ai-demos chart repo is added as a Cluster Repo
   (the published `gh-pages` branch of wiredquill/ai-demos).
2. **Apps → Charts → rancher-ai-ollama → Install**.
3. Work through the questions:

### General
| Question | Value |
|---|---|
| Cluster Name | your SUSE Observability cluster name, e.g. `h100-prod` (stamps `k8s.cluster.name`) |
| Enable GPU Acceleration | `true` (requires device plugin) |
| GPU Vendor | `nvidia` (or `amd` for ROCm) |
| GPUs per Replica | `1` (raise for model parallelism / time-sliced slices) |
| GPU Resource Name | `nvidia.com/gpu` for full/time-sliced GPUs; `nvidia.com/mig-4g.71gb` etc. for MIG on H100/A100 |

### Model
| Question | Value |
|---|---|
| Primary Model (by GPU VRAM class) | dropdown — see table below |
| Additional Models | optional comma-separated list, e.g. `gemma4:12b,bge-large:latest` |

The dropdown is organized by VRAM class:

| GPU VRAM | Models (Ollama tags, verified sizes) |
|---|---|
| 16 GB | `gpt-oss:20b` (14GB), `gemma4:12b` (7.6GB) |
| 24 GB | `gpt-oss:20b`, `gemma4:26b` (18GB), `gemma4:31b` (20GB), `qwen3.6-35b-a3b:q4-24gbGPU` (community) |
| 64 GB | `qwen3.6-35b-a3b:q6` (community, ~27GB), `gpt-oss:20b` |
| 100 GB | `gpt-oss:120b` (65GB), `qwen3.6-35b-a3b:q8` (community, ~39GB) |

> `qwen3.6-35b-a3b:*` tags are **community** GGUF builds of
> `Qwen/Qwen3.6-35B-A3B` (no official Ollama library page). `gpt-oss:*` and
> `gemma4:*` are official. For the 24GB+ classes on Ollama, prefer the official
> tags; use the vLLM chart for the Qwen model at higher fidelity.

### Ollama
| Question | Value |
|---|---|
| Enable Model Persistence | `true` (PVC so models survive restarts) |
| Existing PVC Name | leave empty to create one, or point at a shared cache (hr-assistant / ai-compare pattern) |
| Model Storage Size | `100Gi`+ depending on model set |
| Storage Class | empty = default; use a shared RWX class (longhorn/NFS) to share one cache |
| Enable NFS Model Cache | optional pre-warm from an NFS share (server + path) |

### LiteLLM (this is the token-costing gateway — leave enabled)
| Question | Value |
|---|---|
| Enable LiteLLM Gateway | `true` — required for token metrics |
| LiteLLM Master Key | optional; leave empty to auto-generate (see NOTES / below) |
| Enable OTel v2 Token Metrics | `true` |
| OTLP HTTP Endpoint | `http://open-telemetry-collector-opentelemetry-collector.observability.svc.cluster.local:4318` (adjust to your collector) |
| Collector API Key Secret | optional; name of a secret with key `API_KEY` holding the bearer token |

### Observability / Ingress
| Question | Value |
|---|---|
| Ollama OTel Sidecar | optional status/health only — not needed for tokens |
| Enable Ingress | `true` if Liz is on a different cluster |
| Ingress Hostname | e.g. `llm.wiredquill.com` |

## Point Rancher AI (Liz) at it

In the Rancher AI UI (or `rancher-ai-agent` config) use the **OpenAI-compatible**
provider — this is the sanctioned hook for LiteLLM:

```
activeLlm:    openai
openaiUrl:    http://<release>-rancher-ai-ollama-litellm:4000/v1   # same cluster
              # or https://llm.wiredquill.com/v1                   # via ingress
openaiLlmModel: gpt-oss:20b        # the primary model you selected
openaiApiKey:  <LiteLLM master key>
```

Get the master key:

```bash
kubectl get secret <release>-rancher-ai-ollama-litellm-masterkey \
  -o jsonpath='{.data.masterkey}' | base64 -d
```

> Using the native Ollama provider (`ollamaUrl: http://<release>-rancher-ai-ollama:11434`)
> works but **bypasses LiteLLM, so you get NO token metrics**. Always point Liz
> at LiteLLM for costing.

## Verify

```bash
# Endpoints
kubectl get svc | grep -E 'ollama|litellm'

# Token metrics are exported by LiteLLM (OTLP) — confirm the collector receives them:
# in SUSE Observability, search for metric gen_ai.client.token.usage
# or run a quick chat through the proxy:
curl -s http://<release>-rancher-ai-ollama-litellm:4000/v1/chat/completions \
  -H "Authorization: Bearer <masterkey>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-oss:20b","messages":[{"role":"user","content":"hi"}]}'
```

See [rancher-ai-observability.md](rancher-ai-observability.md) for the metric
reference, tokens/sec PromQL, and dashboard pointers.

## Troubleshooting

- **LiteLLM pod CrashLoopBackOff**: check the proxy config
  `kubectl get cm <release>-rancher-ai-ollama-litellm-config -o yaml` — the
  `model_list` entries must be the same tags Ollama pulled.
- **No token metrics in SUSE Observability**: confirm
  `litellm.observability.enabled=true`, the OTLP endpoint is reachable from the
  LiteLLM pod (`kubectl exec ... -- wget -qO- <endpoint>`), and the collector's
  API key (if configured) is set via `litellm.observability.apiKeySecret`.
- **Ollama stuck pulling**: the model pull happens in an init container —
  `kubectl logs <pod> -c ollama-pull-model`. Large models on slow networks take
  a while; the PVC cache makes restarts fast.
- **OOM during model load**: raise `ollama.resources.limits.memory` (values
  override) — 120b wants ~32-48Gi RAM for weights + KV cache.
