# hermes-openshell

Hermes Agent (Nous Research, `hermes-agent` 0.19.0 from PyPI) as an NVIDIA
OpenShell 0.1.5 sandbox, with four security profiles. Component of the
`hermes-openshell` and `hermes-openshell-vllm` blueprints
(`catalog/blueprints/hermes-openshell*.yaml`). Hand-written, not generated.

## How it runs

```
browser ──NodePort──▶ client pod (openshell CLI) ══ gateway (mTLS) ══▶ sandbox pod
                       images/hermes-client                              images/hermes
                       registers the gateway                             ttyd :7681 → hermes
                       creates the model provider                        uid 10001, no inbound network
                       creates the sandbox under profiles/<profile>.yaml
                       forwards :7681 out of the sandbox
```

The model is reached through an OpenShell **provider**, not a policy rule. The
client imports a custom provider profile (`<sandbox>-llm`) for the model's host
and port, then attaches it to the sandbox. With an API key (external backend),
the profile binds the key to that host: the sandbox's `HERMES_LLM_API_KEY` holds
a placeholder, and the gateway's proxy swaps in the real key only on requests to
the model. OpenShell 0.1.5 has no `inference.local` route.

## Profiles

Each is a full OpenShell policy in `profiles/`; the form's `profile` picks one.
Lint them with `openshell policy lint -f profiles/<name>.yaml`.

| | lockdown | research | developer | dangerous |
|---|---|---|---|---|
| Model endpoint | yes | yes | yes | yes |
| Web, read-only (GET/HEAD/OPTIONS) | | Wikipedia, arXiv, GitHub, docs.python.org, *.suse.com, *.opensuse.org, docs.nvidia.com | same | |
| GitHub read-write (push, PRs; no DELETE) | | | yes | |
| PyPI | | | yes | |
| Any host on 80/443 | | | | every `**.*.<tld>` for ~45 common TLDs plus ~30 bare domains (no raw IPs, no cluster Services; see below) |
| Binaries allowed out | | python3.13, curl | + git, git-remote-http* | all (`/**`) |
| Writable | /home/hermes, /tmp | same | + /var/tmp | /home, /tmp, /var/tmp |
| Landlock | hard_requirement | hard_requirement | hard_requirement | best_effort |
| Hermes `approvals.mode` | manual | smart | smart | off |

**dangerous** is as open as OpenShell 0.1.5 gets, and still not "any host".
Tested on ai-4090:
- A wildcard needs a label under the TLD (`**.*.com`; `*.com` and `**.com` are
  rejected), so bare domains such as `github.com` are listed by name.
- Hostnames are only approved by host rules. An `allowed_ips`-only rule can't
  approve a lookup (`policy_dns_ineligible`), and `0.0.0.0/0` is rejected
  outright because it contains always-blocked ranges.
- Host rules and `allowed_ips` ranges in one policy make the 0.1.5 gateway fail
  `policy set` (FAILED_PRECONDITION / RESOURCE_EXHAUSTED), so raw IPs are out.
- Wildcard hosts never reach private addresses (`policy_dns_no_valid_address`),
  so cluster Services stay unreachable.

OpenShell enforces these whatever the profile says: no root, no loopback,
link-local or cloud metadata (169.254.169.254), no Kubernetes API/etcd/kubelet
ports (6443, 2379, 2380, 10250, 10255), and `read_write` may not contain `/`.

Filesystem, Landlock and process rules apply when the sandbox starts, so
changing the profile in the form recreates the sandbox. Network rules can be
swapped live from the client pod; all four profiles are mounted at
`/etc/hermes/profiles/` (see NOTES.txt).

## Hermes options

The form's **Hermes options** page:

- **Skin** for each profile: lockdown `mono`, research `poseidon`, developer `slate`, dangerous
  `charizard`. The image ships two SUSE brand
  skins, `suse-dark` and `suse-light` (`images/hermes/skins/`); any built-in
  Hermes skin can be picked too. Skins in the image under `/opt/hermes/skins/`
  are copied to `~/.hermes/skins/` at start.
- **Session** (`hermes.session.*`, on by default): words that say which
  session this is, whatever the skin. The profile goes in the prompt
  (`research ❯`), the response header (`Hermes · research`) and the browser
  tab title, and Hermes starts with a welcome line saying what the profile
  allows, its approvals mode (`hermes.session.welcome.<profile>`
  holds the first part).
- **Branding** (`hermes.branding.*`): agent name, welcome and goodbye
  messages, response label, prompt symbol and /help header. The sandbox writes
  a copy of the chosen skin with just that text changed, so colors and
  spinners stay the skin's. Fields set here win over the session's words.
- **Cron job** (`hermes.cron.*`): a Hermes cron job created at start, and a
  scheduler that ticks once a minute (Hermes runs cron jobs only while
  something ticks). The default prompt asks for one short fact a minute:
  steady, cheap token traffic for the observability demo. `hermes cron list`
  in the terminal shows it; results go to `~/.hermes/cron/output/`.

## OpenTelemetry

On by default (`observability.enabled`, the form's **Observability** page):
GenAI telemetry from inside the sandbox to the cluster's SUSE AI collector.
A blank `observability.otlpEndpoint` is found at install time the way the
hr-assistant chart does it: an `*opentelemetry-collector*` Service in
`collectorNamespace`, `observability` or `suse-observability`.

- The sandbox image carries OpenLit and `sitecustomize.py` in Hermes's venv.
  Every start of that python instruments the openai SDK when
  `OTEL_EXPORTER_OTLP_ENDPOINT` is set, and does nothing otherwise.
- The client pod passes every `OTEL_*` and `HERMES_OTEL_*` variable to
  `openshell sandbox create --env`.
- The policy (and each profile mounted for live switching) gets one more rule,
  `otel-collector`: `/usr/bin/python3.13` may reach the collector's host and
  port, nothing else. It names the collector by hostname, because only an
  explicit host rule can reach a private address.

Each model call becomes a span with `gen_ai.*` attributes (model, token usage,
cost, finish reason, time to first token) plus the `gen_ai.client.*` metrics.
`captureContent=false` keeps the prompts and replies out. Exporter errors go to
`/tmp/hermes-otel.log` in the sandbox, not into the terminal.

Each delivery shows in the sandbox pod's log as an OpenShell decision:
`ALLOWED POST http://...:4318/v1/traces [policy:otel-collector]`. If nothing
arrives, look there for a denial and at the exporter log:

```bash
kubectl -n <ns> exec deploy/<release>-client -- \
  openshell sandbox exec <sandbox> -- cat /tmp/hermes-otel.log
```

OpenLit 1.44.0 fails on vLLM's non-streaming replies (`prompt_tokens_details:
null`) and drops their token counts; `sitecustomize.py` patches that.

## Images

| Image | Built from |
|---|---|
| `ghcr.io/wiredquill/hermes-openshell` | `images/hermes/Dockerfile` (SUSE BCI 16) |
| `ghcr.io/wiredquill/hermes-openshell-opensuse` | same, `--build-arg BASE=registry.opensuse.org/opensuse/leap:16.0` |
| `ghcr.io/wiredquill/hermes-openshell-client` | `images/hermes-client/Dockerfile` |

Build from the repository root; both Dockerfiles copy their scripts from `images/`.
