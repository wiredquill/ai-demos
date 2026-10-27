# OpenShell 2 - Gateway

The control plane of [NVIDIA OpenShell](https://docs.nvidia.com/openshell/latest/) 0.1.5,
the sandbox runtime for autonomous agents. The gateway stores sandbox records, policies and
providers. Its Kubernetes driver turns each sandbox into an Agent Sandbox `Sandbox`
resource, and an OpenShell supervisor in the sandbox pod enforces the policy: network (L4 + L7),
Landlock and seccomp.

**This app installs the gateway only. It runs no sandbox and has no web UI.** Sandboxes are
created afterwards by a step 3 app, or with the `openshell` CLI.

## Install order

| # | Rancher app | How many |
|---|---|---|
| 1 | OpenShell 1 - Agent Sandbox controller | once per cluster |
| 2 | **OpenShell 2 - Gateway** (this app) | one per namespace, e.g. `openshell` |
| 3 | OpenShell 3 - can-i sandbox, OpenShell 3 - Hermes Agent sandbox | in this app's namespace |

The architecture diagram is in the Agent Sandbox controller's README.

## What it installs

Everything is named `openshell`, whatever the release is called, so the step 3 apps find it.

| Resource | Purpose |
|---|---|
| `statefulset/openshell` | the gateway server, with a SQLite volume for its database (1Gi by default) |
| `svc/openshell` port 8080 | gRPC over mTLS. ClusterIP by default; NodePort or LoadBalancer in the form |
| Secret `openshell-server-tls` | the gateway's certificate, generated once by the `openshell-certgen` hook Job |
| Secret `openshell-client-tls` | the client certificate the step 3 apps and your CLI present |
| Secret `openshell-credential-storage-key-encryption-key` | encrypts provider credentials (API keys) in the database |
| ServiceAccounts, Roles and RoleBindings | let the gateway create `Sandbox` resources in the sandbox namespace |
| ClusterRole `openshell-node-reader-<namespace>` | reads nodes, to schedule sandboxes |
| NetworkPolicy `openshell-sandbox-ssh` | only the gateway may connect in to sandbox pods |

Sandbox pods go into this app's namespace unless you set **Sandbox namespace**. The
**Sandbox defaults** in the form only apply to sandboxes created later with no image or
RuntimeClass of their own.

## Before you install

- **OpenShell 1 - Agent Sandbox controller** on the cluster. The install fails if its CRD
  is missing.
- A CNI that enforces `NetworkPolicy`. RKE2's Canal, Calico and Cilium all do.
- A default StorageClass, or set one in the form, for the gateway database.

## Check it

```bash
kubectl -n openshell rollout status statefulset/openshell
kubectl -n openshell get svc openshell
```

## Use the CLI from your workstation

Copy `ca.crt`, `tls.crt` and `tls.key` from the `openshell-client-tls` Secret into
`~/.config/openshell/gateways/<name>/mtls/`, then:

```bash
kubectl -n openshell port-forward svc/openshell 17680:8080
openshell gateway add https://127.0.0.1:17680 --local --name <name>
```

For direct access without a port-forward, set the Service to NodePort or LoadBalancer and add
the address you will dial to **Extra certificate names**. The CLI checks the gateway's
certificate against that address. The certificate is generated only once, so to add names
later, delete the `openshell-server-tls` Secret and upgrade the app.

**Lab defaults:** *Allow unauthenticated users* is on, so anyone who can read the
`openshell-client-tls` Secret can create and control sandboxes. Turn it off on shared clusters.
