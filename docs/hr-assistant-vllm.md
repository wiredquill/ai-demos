# hr-assistant-vllm — what you see differently vs. hr-assistant (Ollama)

`charts/hr-assistant-vllm` is the same three-app HR demo as `charts/hr-assistant`,
with SUSE's Application Collection **vLLM** chart (vendored at
`charts/hr-assistant-vllm/charts/vllm`, v0.1.10) serving the model instead of
Ollama. Both charts share the same app image (`app/hr-assistant`) — the app is
provider-aware (`LLM_PROVIDER` env var), not forked per backend. This doc is
the answer to "what would actually look different in SUSE Observability if we
swapped backends."

## Two independent sources of telemetry, same as the research behind this chart

| | hr-assistant (Ollama) | hr-assistant-vllm |
|---|---|---|
| App-level `gen_ai.*` (OpenLit) | `patch/openlit_ollama.py` wraps the app's own OpenAI-SDK/native-client calls | `patch/openlit_vllm.py` wraps the same calls, provider=`vllm` |
| Engine-level native metrics | **None** — Ollama exposes no `/metrics` | vLLM's own `/metrics`, scraped directly by the shared collector (job `vllm`, `transform/vllm` in `templates/otel-collector-values-suse-ai.yaml`) |

The app-level path is what makes both variants show up identically in the
SUSE AI topology (`app → inference-engine → model`). The engine-level path is
new, vLLM-only, and is what actually answers the original research question:
does swapping backends surface anything SUSE Observability couldn't show
before.

## Metric reference

### App-level (both variants) — `gen_ai.*` semantic conventions

| Metric | Meaning |
|---|---|
| `gen_ai.client.token.usage` (histogram, `gen_ai_token_type`=input/output) | tokens per request |
| `gen_ai.usage.cost` / `gen_ai.client.operation.cost` | estimated cost per request (`app/hr-assistant/pricing.json`) |
| `gen_ai.total.requests` | SUSE AI StackPack's GenAI acceptance-gate counter |

### Engine-level (vLLM only) — native metrics, renamed `vllm_`

| Metric | Meaning |
|---|---|
| `vllm_prompt_tokens_total` | cumulative prompt (input) tokens |
| `vllm_generation_tokens_total` | cumulative generation (output) tokens |
| `vllm_num_requests_total` | cumulative requests |
| `vllm_time_to_first_token_seconds` (histogram) | real engine-side TTFT |
| `vllm_time_per_output_token_seconds` (histogram) | per-token latency (→ tokens/sec per request) |
| `vllm_e2e_request_latency_seconds` (histogram) | end-to-end request latency |
| `vllm_gpu_cache_usage_perc` | KV-cache utilization — capacity planning signal Ollama cannot provide |

## Tokens per second — yes, and two ways to get it

**Engine-wide throughput (vLLM only, the more accurate number under load):**
```promql
rate(vllm_generation_tokens_total[1m])
```

**Per-request (either variant, from the app-level histogram):**
```promql
sum(rate(gen_ai_client_token_usage_sum{gen_ai_token_type="output"}[1m]))
  / sum(rate(gen_ai_client_token_usage_count[1m]))
```

**Per-request from vLLM's own per-token latency (inverse of seconds/token):**
```promql
1 / histogram_quantile(0.95, sum(rate(vllm_time_per_output_token_seconds_bucket[5m])) by (le))
```

## Recommended dashboards/alerts

- **Tokens/sec** — `rate(vllm_generation_tokens_total[1m])`, the number Ollama
  can never produce natively.
- **KV-cache pressure** — alert when `vllm_gpu_cache_usage_perc > 0.9`
  sustained (signal to add replicas / tensor parallelism).
- **TTFT & per-token latency** — p50/p95 from `vllm_time_to_first_token_seconds`
  / `vllm_time_per_output_token_seconds`.
- **Cost** — `sum(rate(gen_ai_client_operation_cost_sum[1h])) by (gen_ai_request_model)`
  (same as the Ollama variant; requires pricing entries in `pricing.json` for
  whichever Hugging Face model id is selected).

## Collector wiring (what actually makes this work)

`templates/otel-collector-values-suse-ai.yaml` (the shared cluster collector
every release reports to — not something either chart installs itself):

- Prometheus scrape job `vllm` — dynamic `kubernetes_sd_configs` by Service
  label (`app.kubernetes.io/part-of=vllm`), same release-name-independent
  pattern as the existing `qdrant` job, since Rancher's catalog install names
  releases unpredictably. Matches the `<release>-engine-scrape` Service the
  vendored `vllm` subchart's `extraObjects` renders (see
  `charts/hr-assistant-vllm/values.yaml`).
- `transform/vllm` processor tags the scrape's `service.name=="vllm"` metrics
  `suse.ai.component.type=inference-engine` — the same type the app-level
  `transform/infer-providers` pipeline already assigns, so both telemetry
  sources overlay one topology node instead of creating two.
- `vllm:` → `vllm_` metric rename in the scrape job's `metric_relabel_configs`
  (colons in metric names are rejected/silently dropped by some backends).

## Gotchas

- **Same app image, provider-branched code** — `app/hr-assistant/main.py`
  reads `LLM_PROVIDER` (defaults to `ollama`) to decide which endpoint env var
  to read and which OpenLit patch module owns chat-completions telemetry.
  `apps/rag101.py`'s tool-calling path and `apps/rag102.py`'s LangChain
  integration are both branched the same way — see the comments in those
  files for exactly what differs (OpenAI-SDK tool-calling shape vs. Ollama's
  native client, `ChatOpenAI` vs. `OllamaLLM`).
- **Double-counting risk (already handled, but worth knowing why):** on the
  vLLM path, `apps/rag101.py`'s `_vllm_chat()` and `apps/rag102.py`'s
  `ChatOpenAI` both ultimately call
  `openai.resources.chat.completions.Completions.create`, which
  `patch/openlit_vllm.py` already wraps with full span + SUSE AI metric
  recording. Both files skip their own manual `record_suse_ai_metrics()` call
  when `LLM_PROVIDER=vllm` for exactly this reason.
- **A new image tag is required** — the vLLM code paths above didn't exist in
  the image tag `charts/hr-assistant-vllm/values.yaml` currently pins
  (`topology-orchestration-10`). Rebuild via
  `.github/workflows/build-hr-assistant.yml` and bump `image.tag`/
  `policyDb.image.tag` before installing this chart for real.
- **GPU VRAM is not managed by Kubernetes device-plugin time-slicing** — if
  vLLM shares a physical GPU with another workload (e.g. the Ollama demo's
  model), vLLM's `vllmConfig.gpuMemoryUtilization` (fraction of *total* device
  memory it tries to reserve, default ~0.9) must be lowered to leave headroom
  for whatever else is resident, or the engine pod OOMs on startup.
