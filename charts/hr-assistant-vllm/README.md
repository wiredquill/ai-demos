# hr-assistant-vllm — SUSE AI Observability Demo Chart (SUSE vLLM variant)

Same demo as `hr-assistant`, with SUSE's Application Collection **vLLM**
serving engine in place of Ollama. Shows how an AI application (and its data
stores) appear in **SUSE Observability's SUSE AI section**: applications,
inference engines, LLM models, vector databases, search engines, GPU nodes —
and the **token usage + cost** attached to each LLM call, PLUS the native
engine-level GenAI metrics vLLM exposes on `/metrics` that Ollama cannot
(tokens/sec, time-to-first-token, per-token latency, KV-cache utilization).
See [`docs/hr-assistant-vllm.md`](../../docs/hr-assistant-vllm.md) for the
full metric comparison against the Ollama variant.

Everything the demo needs is deployed by this chart: three OpenLIT-instrumented
apps, a vLLM inference engine + router (vendored SUSE Application Collection
chart, `charts/vllm`), Qdrant (vector DB) and OpenSearch (search engine), plus
a persistent load-generator Deployment that polls the apps every 2 minutes so
the topology stays alive.

> The application code and its observability mapping are documented in
> [`app/hr-assistant/README.md`](../../app/hr-assistant/README.md). This file is
> about installing the chart and reading the results in SUSE Observability.

---

## 1. Find your OTLP collector endpoint

The apps must report to the cluster's OpenTelemetry collector.

**You usually do not need to set this at all.** If the **OTLP Endpoint** question
is left blank, the chart auto-discovers the collector at install time: it looks
up Services in the `observability` namespace (configurable via the **Collector
Namespace** question) for one whose name contains `opentelemetry-collector`, and
uses `http://<service>.<ns>.svc.cluster.local:4318` automatically.

If you do supply a value, a **pre-install connectivity check** runs before the
apps deploy: a small hook Job resolves and probes the endpoint. If the collector
cannot be reached, the install **aborts with the auto-discovered correct URL in
the Rancher helm log** — so a wrong collector address fails loudly at install
time instead of silently deploying apps that report no telemetry.

To find the collector URL by hand (e.g. to verify what the chart discovered):

```bash
kubectl get svc -n observability -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep opentelemetry
```

Then use the resulting service name (commonly
`open-telemetry-collector-opentelemetry-collector`) in the OTLP endpoint:

```bash
OTLP_ENDPOINT="http://$(kubectl get svc -n observability -l app.kubernetes.io/name=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}').observability.svc.cluster.local:4318"
echo "Collector OTLP HTTP endpoint: $OTLP_ENDPOINT"
```

That value (or the bare service name) is what you paste into the **OTLP
Endpoint** question in the Rancher UI form, or set via `--set
otlpEndpoint=$OTLP_ENDPOINT`.

Verify it resolves from inside the cluster before blaming telemetry:

```bash
kubectl exec -n <your-namespace> deploy/<release>-hr-policy-db -- \
  sh -c "getent hosts $(echo $OTLP_ENDPOINT | sed -E 's#http://([^:]+).*#\1#') || echo 'DOES NOT RESOLVE'"
```

---

## 2. What the demo deploys

```
                    ┌─────────────────────────────────────────────┐
                    │        SUSE Observability (backend)         │
                    │  https://observability.<your-host>          │
                    │  SUSE AI section                            │
                    └──────────────────▲──────────────────────────┘
                                       │ OTLP (4318) + topology exporter
                    ┌──────────────────┴──────────────────────────┐
                    │  OpenTelemetry Collector (shared, ns obs.)  │
                    │  infer-applications / infer-providers /     │
                    │  infer-models / transform-qdrant /          │
                    │  transform-vllm / elasticsearch /           │
                    │  topology exporter                          │
                    └──┬───────────┬───────────┬──────────┬───────┘
                       │           │           │          │
        ┌──────────────┴──┐   ┌────┴────┐  ┌───┴────┐  ┌──┴─────────┐
        │ hr-assistant    │   │  vllm   │  │ qdrant │  │ opensearch │
        │ employee-       │   │ (LLM    │  │ (vector│  │ (search    │
        │ handbook        │   │  engine)│  │  DB)   │  │  engine)   │
        │ hr-policy-db    │   │ Qwen2.5 │  │        │  │            │
        └─────────────────┘   └─────────┘  └────────┘  └────────────┘
              ▲
              └── Load-Generator Deployment (polls /ask every 120s) ──┐
                                                                    │
        The three apps also talk to qdrant/opensearch (RAG) so the  │
        topology shows app → vectordb and app → search-engine edges.│
```

The apps call vLLM's OpenAI-compatible router for every answer, so the
collector sees `gen_ai.provider.name=vllm` and `gen_ai.request.model=<HF repo
id>` on every span and builds the app → engine → model relations
automatically — same mechanism as the Ollama variant. On top of that, the
vLLM engine's own `/metrics` endpoint is scraped directly (job `vllm`,
`transform/vllm`), so SUSE Observability also gets native
`vllm_generation_tokens_total`, `vllm_time_to_first_token_seconds`, and
`vllm_gpu_cache_usage_perc` — engine-level signal Ollama never exposes.

---

## 3. What you see under each SUSE AI heading

Open **SUSE Observability → SUSE AI**. Each topic shows the components below.
To see token usage/cost, click any component (e.g. **inference-engine vllm**
or the app) and open its **GenAI / Token** drill-down or the GenAI dashboards.

| SUSE AI topic | Components in this demo | How produced |
|---|---|---|
| AI Applications | `hr-assistant`, `employee-handbook`, `hr-policy-db` | OpenLIT apps emitting `gen_ai.*` metrics; collector's `infer-applications` pipeline tags them `suse.ai.component.type=application` |
| Inference Engines | `vllm` | `gen_ai.provider.name=vllm` resource attr (app-level); ALSO the engine's own `/metrics` scraped natively (job `vllm`, `transform/vllm`) — both overlay the same `inference-engine` component |
| LLM Models | the HF repo id set in `vllm.servingEngineSpec.modelSpec` (default `Qwen/Qwen2.5-7B-Instruct`) | `gen_ai.request.model` resource attr; `infer-models` pipeline creates model + engine→model relation |
| Vector Databases | `qdrant` | Prometheus scrape of `qdrant:6333/metrics`; `transform/qdrant` tags it `suse.ai.component.type=vectordb` |
| Search Engines | `opensearch` | Collector `elasticsearch` receiver polls the OpenSearch REST API; `resource/opensearch` tags it `suse.ai.component.type=search-engine` |
| GPU Nodes | the dev-ai node | `gpu-metrics` Prometheus scrape of `nvidia-dcgm-exporter` (DCGM) |
| All GenAI Components | everything above | Union of all component types |

### Engine-level metrics only vLLM provides

Query these directly in SUSE Observability's metric explorer/dashboards —
Ollama has no equivalent (see `docs/hr-assistant-vllm.md` for the full list
and PromQL):

- `rate(vllm_generation_tokens_total[1m])` — **tokens/sec**, engine-wide
- `vllm_time_to_first_token_seconds` — real engine-side TTFT
- `vllm_time_per_output_token_seconds` — per-token latency
- `vllm_gpu_cache_usage_perc` — KV-cache pressure (capacity planning)

### Token usage and cost — where it shows up

Token usage and cost are emitted by OpenLIT **per LLM call** as
`gen_ai.client.token.usage` (histogram: input/output/total tokens) and
`gen_ai.usage.cost` (USD). SUSE Observability's SUSE AI StackPack turns these
into the per-component **Token Usage** and **Cost** drill-downs:

1. **Where the numbers come from:** every `/ask` handled by the apps calls
   vLLM's OpenAI-compatible router; OpenLIT records prompt/completion tokens
   and computes cost from `app/hr-assistant/pricing.json`. No extra
   configuration is needed — the chart's `pricing.json` ships in the image.
2. **Where they show up:**
   - Click **inference-engine vllm** (or any app) in the SUSE AI topology →
     the **GenAI** tab shows request count, **token usage** (input/output/
     total), and **cost** over the selected time range.
   - The SUSE AI dashboards (e.g. "GenAI Token Usage", "GenAI Cost") aggregate
     the same series across all components.
3. **If token costing looks empty:**
   - Give it a few minutes — the load generator only runs every 2 minutes and
     the topology exporter expires components ~2 min after last telemetry, so
     the view can briefly look empty between cycles. The collector log shows a
     healthy cadence of `topology sent components=N relations=N status=200`.
   - Check the collector is actually receiving app telemetry:
     `kubectl exec -n observability deploy/open-telemetry-collector-opentelemetry-collector -- sh -c '...'`
     (the otlp receiver counters `otelcol_receiver_accepted_metric_points_total`
     and `otelcol_receiver_accepted_spans_total` must grow when the load
     generator fires — see §1 for the endpoint check first).
   - Confirm the apps' `OTEL_RESOURCE_ATTRIBUTES` contain
     `gen_ai.provider.name=vllm,gen_ai.request.model=<model>` (set by the
     chart on every deployment).

---

## 4. Installing

Via Rancher UI: **Apps → Charts → hr-assistant-vllm → Install**, fill in the form.
Key questions:

- **OTLP Endpoint** (Observability group) — the collector URL from §1.
- **Model** (vLLM Deployment) — GPU-VRAM-class model dropdown, same table as
  `docs/rancher-ai-vllm.md`.
- **Service Type / NodePort** (Dashboard / Service Access) — `NodePort` +
  `30080` exposes the built-in dashboard at
  `http://<node-ip>:30080/` (served by `hr-policy-db`).
- **Qdrant / OpenSearch** (Observability Demo Components) — enabled by default.

Or via helm:

```bash
helm dependency build charts/hr-assistant-vllm   # builds charts/vllm from the local file:// dependency
helm install hr-assistant-vllm charts/hr-assistant-vllm -n hr-assistant-vllm --create-namespace \
  --set otlpEndpoint=http://open-telemetry-collector-opentelemetry-collector.observability.svc.cluster.local:4318 \
  --set service.type=NodePort \
  --set service.nodePort=30081
```

---

## 5. Verifying it works

```bash
# 1. All pods Running (incl. qdrant, opensearch, the vllm engine + router)
kubectl get pods -n hr-assistant-vllm

# 2. vLLM engine is serving the model (first start downloads weights - can take a while)
kubectl exec -n hr-assistant-vllm deploy/<release>-router-deployment -- \
  curl -s http://localhost/v1/models

# 3. Load generator pod is running and generating traffic
kubectl get pods -n hr-assistant-vllm -l app.component=load-generator
kubectl logs -n hr-assistant-vllm deploy/<release>-load-gen --tail=20

# 4. Collector is pushing topology to SUSE Observability
kubectl logs deploy/open-telemetry-collector-opentelemetry-collector -n observability \
  --tail=100 | grep "topology sent"

# 5. Dashboard responds (if NodePort enabled)
curl -s -o /dev/null -w "%{http_code}\n" http://<node-ip>:30081/

# 6. App answers /ask
curl -s http://<node-ip>:30081/ask | head -c 200

# 7. Native vLLM engine metrics are being scraped
kubectl exec -n observability deploy/open-telemetry-collector-opentelemetry-collector -- \
  wget -qO- localhost:8888/metrics | grep vllm_generation_tokens_total
```

Healthy topology cadence looks like:
```
topology sent components=5 relations=4 status=200
topology sent components=0 relations=0 status=200   # between load bursts — normal
topology sent components=5 relations=4 status=200
```

---

## 6. Troubleshooting cheat-sheet

| Symptom | Likely cause / fix |
|---|---|
| Apps log `NameResolutionError ... opentelemetry-collector...` | Wrong OTLP endpoint — run §1 and set the real collector FQDN |
| Collector logs `no such host ... qdrant/opensearch.hr-assistant-vllm...` | Release name != `hr-assistant-vllm`; the collector template's `SUSE_AI_RELEASE` env must match your release name (services are `<release>-qdrant`, `<release>-opensearch`) |
| `topology sent components=0` permanently | No app traffic — check the load-generator pod is running; or `SUSE_AI_NAMESPACE` in the collector points at the wrong namespace |
| Empty SUSE AI view after install | Wait for 1–2 load cycles; check §1 endpoint resolves; check the collector's `infer-*` transforms exist in its relay config |
| vLLM engine pod `Pending` | No node with enough GPU — check `kubectl describe pod`; MIG resource names must match the GPU Operator config |
| No `vllm_*` metrics in SUSE Observability | Confirm the collector's `vllm` scrape job (§4 of `docs/hr-assistant-vllm.md`) matches the `<release>-engine-scrape` Service's `app.kubernetes.io/part-of=vllm` label |
| Image pull `NotFound` | ghcr tag typo or private package — verify the tag exists: `curl -s https://ghcr.io/token?scope=repository:wiredquill/ai-demos/genai-demo:pull ...` then list tags |

---

## 7. Chart versions

- **0.1.0** — Initial hr-assistant-vllm: cloned from hr-assistant, swapped
  Ollama for the vendored SUSE Application Collection `vllm` chart
  (engine + router), added the native `vllm` Prometheus scrape/transform to
  the shared collector, and ported the app's LLM calls to the OpenAI-
  compatible/tool-calling shape vLLM speaks (see `docs/hr-assistant-vllm.md`).
