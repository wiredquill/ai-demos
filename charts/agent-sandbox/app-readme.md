# OpenShell 1 - Agent Sandbox controller

**Install this first, and only once per cluster.** It is cluster-scoped: the controller
always runs in `agent-sandbox-system`, whatever namespace you pick here, and it serves every
OpenShell gateway on the cluster. If it is already installed, skip it.

The `Sandbox` custom resource (`agents.x-k8s.io`) and its controller, from
[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) v1.0.8.
The OpenShell gateway's Kubernetes driver creates one `Sandbox` per agent sandbox, and this
controller turns each one into a pod.

**Install order** (steps 2 and 3 in the same namespace, e.g. `openshell`):
1. **OpenShell 1 - Agent Sandbox controller** (this app, once per cluster)
2. **OpenShell 2 - Gateway** (the control plane; creates no sandbox)
3. **OpenShell 3 - can-i sandbox** and/or **OpenShell 3 - Hermes Agent sandbox** (these create
   the sandbox and its web UI)

The chart README has the architecture diagram.

Install it into the **agent-sandbox-system** namespace (Rancher's default for this app).
If the cluster already has the Sandbox CRD, turn off **Install the Sandbox CRD**. If it already
runs the controller from `kubectl apply -f .../sandbox.yaml`, don't install this app at all.
