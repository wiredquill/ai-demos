# OpenShell 1 - Agent Sandbox controller

> **Install this first, and only once per cluster.**
> It is cluster-scoped: one CRD and one controller in `agent-sandbox-system` serve every
> OpenShell gateway on the cluster, whatever namespace those gateways are in. Installing it
> a second time (in another namespace, or as another release) fails, because the CRD and
> the controller already belong to the first release.

The `Sandbox` custom resource (`agents.x-k8s.io`) and its controller, from
[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) v1.0.8.
The OpenShell gateway's Kubernetes driver creates one `Sandbox` per agent sandbox, and this
controller turns each `Sandbox` into a pod.

## The OpenShell apps

Install them in this order. Every app after the first goes into the **same namespace**
(for example `openshell`): the sandbox apps read the gateway's `openshell-client-tls` Secret
and call `https://openshell:8080`.

| # | Rancher app | Installs | How many |
|---|---|---|---|
| 1 | **OpenShell 1 - Agent Sandbox controller** | `Sandbox` CRD + controller in `agent-sandbox-system` | **one per cluster** |
| 2 | **OpenShell 2 - Gateway** | the OpenShell control plane, `statefulset/openshell` and `svc/openshell:8080`. **It creates no sandbox.** | one per namespace |
| 3 | **OpenShell 3 - can-i sandbox** | a client pod that creates the `can-i` sandbox and serves its dashboard | any number, in the gateway's namespace |
| 3 | **OpenShell 3 - Hermes Agent sandbox** | a client pod that creates the `hermes` sandbox and serves its browser terminal | any number, in the gateway's namespace |

Only step 3 creates a sandbox and a web UI. A namespace with just the gateway has no sandbox
pod and nothing to open in a browser.

## Architecture

```
  cluster-wide
 ┌───────────────────────────────────────────────┐
 │ 1  OpenShell 1 - Agent Sandbox controller     │  namespace agent-sandbox-system
 │    Sandbox CRD + controller                   │  ONE PER CLUSTER
 └───────────────────────▲───────────────┬───────┘
                         │ watches       │ creates the pod
                         │ Sandbox       │ for each Sandbox
  namespace "openshell"  │ resources     │
 ┌───────────────────────┼───────────────┼───────────────────────────────┐
 │                       │               ▼                               │
 │ ┌─────────────────────┴───────┐   ┌───────────────────────────────┐   │
 │ │ 2  OpenShell 2 - Gateway    │   │ sandbox pod  (e.g. "can-i")   │   │
 │ │    statefulset/openshell    │──►│ workload image + OpenShell    │   │
 │ │    svc/openshell:8080 mTLS  │   │ supervisor (policy: network,  │   │
 │ │    creates the Sandbox,     │◄──│ Landlock, seccomp)            │   │
 │ │    pushes its policy        │   │ NO inbound network            │   │
 │ └─────────────▲───────────────┘   └───────────────────────────────┘   │
 │               │ openshell CLI over mTLS                               │
 │               │ (sandbox create, policy, exec, forward)               │
 │ ┌─────────────┴───────────────┐                                       │
 │ │ 3  OpenShell 3 - can-i or   │  client pod: deploy/can-i or         │
 │ │    Hermes Agent sandbox     │  deploy/hermes. Forwards the UI       │
 │ │                             │  from the sandbox through the gateway │
 │ └─────────────▲───────────────┘                                       │
 │               │ svc/can-i or svc/hermes (NodePort by default)        │
 └───────────────┼───────────────────────────────────────────────────────┘
                 │
              browser   http://<node-ip>:<nodePort>
```

The browser never talks to the sandbox pod directly. Sandboxes have no inbound network,
so the client pod runs `openshell forward` through the gateway and publishes the result on
its own Service.

## Check it

```bash
kubectl get crd sandboxes.agents.x-k8s.io
kubectl -n agent-sandbox-system rollout status deploy/agent-sandbox-controller

# after step 3: the Sandbox resources and their pods, in the gateway's namespace
kubectl -n openshell get sandboxes,pods
```

## Already installed with kubectl?

If the cluster already has the controller from `kubectl apply -f .../sandbox.yaml`, skip
this app: Helm can't take over resources it didn't create. Go straight to step 2.
