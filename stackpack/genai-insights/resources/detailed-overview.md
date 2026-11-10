AI-aware health for LLM applications: latency regressions against each model's own
baseline, token and cost burn rate, and vLLM generation-speed, queueing and
KV-cache pressure signals. Replaces the fixed 5 s span-duration threshold, which
flags healthy LLM calls as degraded.

## Monitors

| Monitor | Signal | Fires when |
| --- | --- | --- |
| Model latency regression | p95 call duration, 5 m vs 6 h baseline | 2x slower than the model's own norm |
| Token burn spike | tokens/s, 5 m vs 1 h baseline | 3x the recent rate (runaway loop, prompt bloat) |
| Cost burn rate | USD per hour | above the hourly budget |
| vLLM slow generation | p95 time per output token | above 150 ms |
| vLLM request queueing | p95 queue time | above 2 s |
| vLLM KV-cache preemptions | preemptions/s | sustained preemption (cache thrash) |
