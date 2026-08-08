# Rancher AI — Observability in SUSE Observability

How token/cost metrics from the `rancher-ai-ollama` (LiteLLM) and
`rancher-ai-vllm` (vLLM) charts land in **SUSE Observability**, and how to
query them — including **tokens/sec**.

## Architecture summary

| Chart | Instrumentation | Metrics path |
|---|---|---|
| rancher-ai-ollama | LiteLLM OTel v2 (`LITELLM_OTEL_V2=true`) | `gen_ai.*` metrics via OTLP/HTTP → shared collector |
| rancher-ai-vllm | vLLM native `/metrics` Prometheus endpoint | `vllm:*` metrics scraped by shared collector, renamed `vllm_*` |
| rancher-ai-ollama (optional sidecar) | OTel collector sidecar | Ollama HTTP status/health only |

Both ship their metrics to the **same shared collector** already running in the
cluster (see `templates/otel-collector-values-suse-ai.yaml` in this repo),
which forwards them to SUSE Observability with GenAI enrichment
(infer-models/infer-providers pipelines).

## Metric reference

### LiteLLM (rancher-ai-ollama) — gen_ai.* semantic conventions

Exported by the proxy with `LITELLM_OTEL_V2=true`. After the collector's
transform pipelines they appear with `gen_ai.request.model` and
`gen_ai.provider.name` attributes (provider = `ollama`):

| Metric (OTel semantic convention) | Meaning |
|---|---|
| `gen_ai.client.token.usage` (histogram, `gen_ai_token_type` = input/output) | tokens per request |
| `gen_ai.usage.cost` | estimated cost per request |
| `gen_ai.server.time_to_first_token` (histogram) | TTFT latency |
| `gen_ai.server.time_per_output_token` (histogram) | per-token latency (→ tokens/sec per request) |
| `litellm_proxy_total_requests_*` (via `/metrics`) | request counters (optional extra scrape) |

### vLLM (rancher-ai-vllm) — native metrics, renamed `vllm_`

The collector's `vllm` scrape job renames `vllm:` → `vllm_` so SUSE
Observability accepts the names:

| Metric | Meaning |
|---|---|
| `vllm_prompt_tokens_total` | cumulative prompt (input) tokens |
| `vllm_generation_tokens_total` | cumulative generation (output) tokens |
| `vllm_num_requests_total` | cumulative requests |
| `vllm_time_to_first_token_seconds` (histogram) | TTFT |
| `vllm_time_per_output_token_seconds` (histogram) | per-token latency |
| `vllm_e2e_request_latency_seconds` (histogram) | end-to-end latency |
| `vllm_gpu_cache_usage_perc` | KV cache utilization (capacity planning) |

## Tokens per second — yes, it's available

Both paths give you tokens/sec with plain PromQL in SUSE Observability
dashboards and alerts:

**vLLM (throughput, whole engine):**
```promql
# generation tokens per second
rate(vllm_generation_tokens_total[1m])
# prompt tokens per second (ingestion)
rate(vllm_prompt_tokens_total[1m])
```

**vLLM (per-request latency view, inverse = tokens/sec per request):**
```promql
# p50 / p95 time per output token (seconds/token)
histogram_quantile(0.95, sum(rate(vllm_time_per_output_token_seconds_bucket[5m])) by (le))
# tokens/sec per request
1 / histogram_quantile(0.95, sum(rate(vllm_time_per_output_token_seconds_bucket[5m])) by (le))
```

**LiteLLM (per model, input vs output):**
```promql
# tokens per second, split input/output
sum(rate(gen_ai_client_token_usage_sum[1m])) by (gen_ai_token_type, gen_ai_request_model)
```

These are OTel histogram metrics — SUSE Observability auto-computes
percentiles; the `_sum`/`_count` series are what you use for rates.

## Recommended dashboards/alerts

- **Tokens/sec by model** — `rate(vllm_generation_tokens_total[1m])` +
  LiteLLM equivalent, `sum by (gen_ai_request_model)`.
- **Token volume by input/output** — `sum(rate(gen_ai_client_token_usage_sum[5m])) by (gen_ai_token_type)`.
- **TTFT & per-token latency** — p50/p95 from the histograms above.
- **KV cache pressure (vLLM)** — alert when
  `vllm_gpu_cache_usage_perc > 0.9` sustained (add replicas / model parallelism).
- **Cost** — `sum(rate(gen_ai_usage_cost_sum[1h])) by (gen_ai_request_model)`
  (requires pricing in LiteLLM config; DB-less mode skips per-key cost tables).

## Collector configuration delta

The repo's collector values template (`templates/otel-collector-values-suse-ai.yaml`)
includes the `vllm` scrape job:

- matches Services labelled `app.kubernetes.io/part-of=vllm` **or** legacy
  `app=vllm` (one keep rule over the joined label pair)
- honors `prometheus.io/port` annotations (`<release>-engine-scrape` sets port 80)
- renames `vllm:*` → `vllm_*` via `metric_relabel_configs`

Deploying the collector values:

```bash
helm upgrade --install opentelemetry-collector oci://registry.suse.com/ai/charts/suse-ai-opentelemetry-collector \
  --namespace observability \
  --reset-values \
  --values templates/otel-collector-values-suse-ai.yaml \
  --set extraEnvsFrom[0].secretRef.name=<your collector secret>
```

> The template carries dev-ai-specific bits (cluster name, `ac3` namespace,
> DCGM node labels, `mort.dna-42.com` backend). Edit `extraEnvs`/`extraEnvsFrom`
> and the topology exporter endpoint per cluster.

## Gotchas

- **Ollama has no native OTel** — never expect `OLLAMA_OTEL_*` env vars or
  `/metrics`; token data for Ollama REQUIRES LiteLLM (or another proxy).
- **Metric names with colons** (`vllm:...`) are rejected/silently dropped by
  some backends — always keep the `vllm_` rename.
- **Traces are optional for costing** — the vLLM router OTLP setting only
  enables tracing; token dashboards work from metrics alone.
- **DB-less LiteLLM** disables the per-key spend log; token metrics still
  export. Add the Postgres subchart later only if you need per-key cost
  attribution.
