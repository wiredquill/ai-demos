# Rancher AI — vLLM Serving (rancher-ai-vllm)

Deploy a **vLLM** serving engine + router (SUSE Application Collection chart)
wired for **SUSE Rancher AI (Liz)** and **SUSE Observability** token metrics.

vLLM exposes token counts natively via its `/metrics` Prometheus endpoint
(`vllm:prompt_tokens_total`, `vllm:generation_tokens_total`, ...). No proxy or
sidecar is needed — the cluster-level collector scrapes the engine Service and
renames the metrics (`vllm:` → `vllm_`) so SUSE Observability can graph them.
This chart is a thin wrapper: it passes values into the SUSE `vllm` chart and
adds a labelled scrape target.

```
                    ┌───────────────────────────────┐
  Rancher AI (Liz)  │  rancher-ai-vllm chart        │
  openaiUrl ───────▶│  router :80 ──▶ engine :8000  │
                    │       │            │           │
                    │       └─ traces ────┘           │
                    │  Prom scrape (vllm_*) ──▶ shared│
                    │       collector                │
                    └───────────────────────────────┘
```

## Prerequisites

- Rancher cluster with **SUSE Application Collection** installed
  (`application-collection` secret + `dp.apps.rancher.io` registry).
- **GPU Operator** on the worker nodes (vLLM engine uses `runtimeClassName:
  nvidia` and requests `nvidia.com/gpu`).
- **SUSE Observability** collector deployed with the vLLM scrape job
  (see the collector template in this repo — the `vllm` job now matches
  `app.kubernetes.io/part-of=vllm` and renames `vllm:` metrics).
- Enough VRAM for the model + KV cache; model weights download into a PVC on
  first start (needs network access to Hugging Face).

## Install via Rancher UI

1. Add the ai-demos chart repo (published `gh-pages` branch) as a Cluster Repo.
2. **Apps → Charts → rancher-ai-vllm → Install**.
3. Work through the questions:

### General
| Question | Value |
|---|---|
| Cluster Name | your SUSE Observability cluster name, e.g. `h100-prod` |

### Model
| Question | Value |
|---|---|
| Model (by GPU VRAM class) | dropdown — see table below |
| Model Deployment Name | short resource name, e.g. `qwen3.6-35b` |
| GPUs per Replica | `1` (more for tensor parallelism on big models) |
| GPU Resource Name | `nvidia.com/gpu` or MIG profile |
| CPU / Memory Request | `8` / `32Gi` defaults, tune for the model |

The dropdown is organized by VRAM class (Hugging Face IDs; VRAM depends on
quantization — these are the values we verified):

| GPU VRAM | Models (HF ID) |
|---|---|
| 16 GB | `Qwen/Qwen2.5-7B-Instruct` (~16GB fp16) |
| 24 GB | `Qwen/Qwen3.6-35B-A3B` (AWQ/GPTQ weights ~19GB) |
| 64 GB | `Qwen/Qwen3.6-35B-A3B` (fp8 ~35GB), `meta-llama/Llama-3.3-70B-Instruct` (AWQ ~40GB) |
| 100 GB | `openai/gpt-oss-120b` (~68GB), `Qwen/Qwen3.6-35B-A3B` (bf16 ~70GB) |

> For 24GB-class Qwen, vLLM needs quantized weights — point `modelURL` at an
> AWQ/GPTQ repo or add `--quantization` args (see the SUSE `vllm` chart
> `vllmConfig` values).

### Storage
| Question | Value |
|---|---|
| Model Cache PVC Size | `100Gi`+ — vLLM downloads weights into this PVC (fast restarts) |
| Storage Class | empty = default; use a shared RWX class to reuse one cache |

### Router / Ingress
| Question | Value |
|---|---|
| Router Service Type | `ClusterIP` (same cluster as Liz), `NodePort`/`LoadBalancer` for external |
| OTLP Endpoint (traces) | collector gRPC endpoint `...:4317` (traces only) |
| Enable Ingress | `true` if Liz is on a different cluster |
| Ingress Hostname | e.g. `vllm.wiredquill.com` |

## Point Rancher AI (Liz) at it

Use the **OpenAI-compatible** provider:

```
activeLlm:    openai
openaiUrl:    http://<release>-router-service:80/v1     # same cluster
              # or https://vllm.wiredquill.com/v1        # via ingress
openaiLlmModel: Qwen/Qwen3.6-35B-A3B     # the HF model ID you selected
openaiApiKey:  <any non-empty value, or the vllmApiKey if you set one>
```

## Verify

```bash
kubectl get svc | grep -E 'router|engine|scrape'

# Model readiness (vLLM OpenAI-compatible):
curl -s http://<release>-router-service:80/v1/models | jq

# Token metrics (scraped by the collector, renamed vllm_*):
# in SUSE Observability: vllm_generation_tokens_total, vllm_prompt_tokens_total
# tokens/sec: rate(vllm_generation_tokens_total[1m])
```

The `extraObjects` in the chart create a Service named
`<release>-engine-scrape` labelled `app.kubernetes.io/part-of=vllm` with
`prometheus.io/*` annotations. The collector's `vllm` scrape job matches it
(and the chart's own engine Service, which also carries the label).

## Troubleshooting

- **Engine pod Pending**: no node with enough GPU — check
  `kubectl describe pod` for scheduling errors; MIG resource names must match
  the GPU Operator configuration.
- **Model download slow/failing**: engine init downloads from Hugging Face —
  check engine pod logs (`kubectl logs <pod> -n <ns> -c vllm`). For air-gapped
  clusters, pre-fetch the model and mount it via `extraVolumes` +
  `initContainer` (SUSE AI docs 4.13 "Loading prefetched models from persistent
  storage" pattern).
- **No metrics in SUSE Observability**: confirm the collector template has the
  `vllm` scrape job (with the part-of label match), the namespace is reachable,
  and the metric rename landed (`vllm_*`, not `vllm:*`).
- **OOM**: raise `requestMemory` and add `limitMemory`/`limitCPU` (see the SUSE
  `vllm` chart values) for large models.
