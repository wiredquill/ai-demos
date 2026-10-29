# hermes-rancher (Hermes for Rancher)

Hermes Agent (Nous Research, `hermes-agent` 0.19.0 from PyPI) for platform
engineers: an NVIDIA OpenShell 0.1.5 sandbox with `kubectl` on the cluster it
runs on, under a ServiceAccount of its own. Same images, profiles and Hermes
options as `charts/hermes-openshell`, plus cluster access. Component of the
`hermes-rancher` blueprint (`catalog/blueprints/hermes-rancher-*.yaml`).
Hand-written, not generated.

## How it runs

```
browser ──port-forward──▶ client pod (openshell CLI) ══ gateway (mTLS) ══▶ sandbox pod
                           images/hermes-client                              images/hermes
                           registers the gateway                             ttyd :7681 → hermes
                           creates the model provider                        kubectl, ~/.kube/config
                           creates the sandbox under profiles/<profile>.yaml  uid 10001, no inbound network
                           uploads a kubeconfig (ServiceAccount token)
                           forwards :7681 out of the sandbox
```

## Cluster access

`platform.access` picks what Hermes may do; the chart creates a ServiceAccount
`<release>-platform` with a token Secret, and binds it:

| Access | RBAC |
|---|---|
| **view** (default) | the built-in `view` ClusterRole (namespaced resources, no Secrets), plus `<ns>-<release>-cluster-read`: nodes, PVs, StorageClasses and other storage objects, CRDs, APIServices, PriorityClasses, RuntimeClasses, IngressClasses, and `kubectl top` |
| **operator** | `view`, plus `patch` on Deployments/StatefulSets/DaemonSets (`kubectl rollout restart`), `get/patch/update` on their `scale`, and `delete` on Pods |

How the access gets to the agent, and what fences it:

- **No ambient credentials.** OpenShell sandbox pods run with
  `automountServiceAccountToken: false`, so without this chart the agent has
  no token. Only the client pod mounts `<release>-platform-token`; once the
  sandbox is up it pipes a kubeconfig into `/home/hermes/.kube/config` (mode
  600) through `openshell sandbox exec`, so the token never lands on the
  client's disk. (`sandbox create --upload` can't be combined with a start
  command, and `sandbox upload` needs ssh and git in the client image.)
- **One network rule.** The policy (and each live-switch profile) gets
  `cluster-api`: `/usr/local/bin/kubectl` and `/usr/local/bin/helm`, and
  nothing else, may reach `kubernetes.default.svc.cluster.local:443`. Python,
  curl and git still can't.
- **`tls: skip`, so RBAC is the limit.** OpenShell's L7 proxy re-encrypts
  inspected HTTPS and checks the upstream against its own trust store, which
  lacks the cluster CA (`NET:FAIL` in the supervisor log). OpenShell 0.1.5 has
  `--additional-ca-bundle` for this, but only its Podman driver sets it. So the
  API traffic is passed through untouched: no method filtering, and the token
  is in the sandbox rather than injected by the gateway. kubectl checks the
  API server against the cluster CA in the kubeconfig.
- **Who can use it.** Anyone who can open the terminal drives the agent and
  its cluster access. The Service is `ClusterIP` by default, reached with
  `kubectl port-forward`, so only by people allowed into this namespace (a
  Rancher project role). `NodePort` exposes it to anyone who can reach a node.
- **What Hermes knows.** The sandbox writes `~/workspace/AGENTS.md` (Hermes
  puts it in its system prompt): the cluster's name, its access, investigate
  before answering, and ask before any change.

Check it:

```bash
kubectl -n <ns> exec deploy/<release>-client -- \
  openshell sandbox exec <sandbox> --no-tty -- kubectl get nodes
kubectl auth can-i --list --as system:serviceaccount:<ns>:<release>-platform | head
```

### Through Rancher (`platform.via: rancher`)

Instead of a ServiceAccount on this cluster, Hermes uses a Rancher API token,
on every cluster Rancher lets that token's user into:

```yaml
platform:
  access: view
  via: rancher
  rancher:
    url: https://rancher.example.com
    existingSecret: rancher-cli   # key "token": access-key:secret, no scope
```

- **The token's user is the limit.** Create a user for Hermes (Standard User)
  with only the cluster roles it should have, and an API key with no scope as
  that user. The chart creates no ServiceAccount and no `cluster-api` rule.
- **The gateway holds the token.** The client binds it to Rancher's host as an
  OpenShell provider (`<sandbox>-rancher`), as it does the model's key. The
  sandbox's `RANCHER_CLI_TOKEN` is a placeholder the proxy swaps for the token
  on requests to Rancher; only `/usr/local/bin/rancher`,
  `/usr/local/bin/kubectl` and `/usr/local/bin/helm` may make them. Rancher's certificate must be
  publicly trusted, since the proxy terminates this TLS to add the token.
- **view is reads only, twice.** The provider's endpoint is `access:
  read-only`, so the proxy refuses anything but GET/HEAD/OPTIONS (shown as
  `DENIED POST ...` in the sandbox's supervisor log), and the CLI runs with
  `RANCHER_CLI_READONLY`. operator lets writes through to Rancher's RBAC and
  tells Hermes to use the CLI's `--dry-run`/`--apply` loop.
- **kubectl goes through Rancher too.** At start the sandbox runs
  `rancher-kubeconfig` (in `images/hermes-rancher`): it lists the clusters the
  token can see from Rancher's `/v1` API and writes one context per cluster,
  `https://<rancher>/k8s/clusters/<id>` with the placeholder token. Not
  `rancher kubeconfig`, whose exec plugin mints a token per cluster (a POST,
  refused under view). `rancher get clusters` reads through Rancher's `local`
  cluster and is refused to users without access to it; the cluster list in
  AGENTS.md comes from `rancher-kubeconfig` instead.
- **Hermes knows it.** AGENTS.md names Rancher, the clusters (by name and id)
  and the access, and the image carries the CLI's own agent skill.

Tested on ai-4090 with a Standard User holding view roles on three clusters:
`rancher get pods/nodes`, `rancher usage`, `rancher inspect cluster` and
`kubectl get`/`top` work; Secrets are forbidden by Rancher; deletes and
patches are refused by the proxy; curl can't reach Rancher.

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
The `cluster-api` rule is the one way to the API server: its Service on 443,
for kubectl only.

Filesystem, Landlock and process rules apply when the sandbox starts, so
changing the profile in the form recreates the sandbox. Network rules can be
swapped live from the client pod; all four profiles are mounted at
`/etc/hermes/profiles/` (see NOTES.txt).

## Hermes options

The form's **Hermes options** page:

- **Skin** for each profile: `suse-dark` for every profile. The image ships two SUSE brand
  skins, `suse-dark` and `suse-light` (`images/hermes/skins/`); any built-in
  Hermes skin can be picked too. Skins in the image under `/opt/hermes/skins/`
  are copied to `~/.hermes/skins/` at start.
- **Session** (`hermes.session.*`, on by default): words that say which
  session this is, whatever the skin. The profile goes in the prompt
  (`research ❯`), the response header (`Hermes · research`) and the browser
  tab title, and Hermes starts with a welcome line saying what the profile
  allows, its approvals mode, the cluster access (`hermes.session.welcome.<profile>`
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

## Tools in the sandbox

The sandbox can't install anything (no root, and no profile reaches a package
repository), so the image carries what an agent reaches for: kubectl, helm
4.3.1, yq 4.54.1, jq, gawk, openssl, python3 (`python3.13`), curl, git, and
`rancher` in `hermes-rancher`. AGENTS.md lists them, so Hermes doesn't probe.
helm keeps release data in Secrets, which view can't read, so `helm list`
needs a role with Secret access. For more, build an image `FROM
ghcr.io/wiredquill/hermes-rancher` and set `sandbox.image: custom`.

## Images

| Image | Built from |
|---|---|
| `ghcr.io/wiredquill/hermes-rancher` (sandbox) | `images/hermes-rancher/Dockerfile`: the `hermes-openshell` image (`images/hermes`, SUSE BCI 16) of the same commit, plus Rancher's agent CLI and its skill. linux/amd64 only |
| `ghcr.io/wiredquill/hermes-openshell-client` | `images/hermes-client/Dockerfile` |

Build from the repository root; the Dockerfiles copy their scripts from `images/`.
The workflow `build-hermes-openshell.yml` builds `hermes-rancher` after the
Hermes images, on the sandbox image it just pushed.

The `rancher` CLI (v0.1.0-alpha.7) comes from a private repository, so its
linux/amd64 binary is kept gzipped in `images/hermes-rancher/`, checked
against a pinned SHA-256 at build. The image also extracts the CLI's agent
skill (`rancher skill install`) to `/opt/hermes/skills/rancher`, which the
sandbox copies into `~/.hermes/skills` at start.
