# Agent Sandbox controller

The `Sandbox` custom resource (`agents.x-k8s.io`) and its controller, from
[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) v1.0.8.
The OpenShell gateway's Kubernetes driver creates one `Sandbox` per agent sandbox, so this
must be on the cluster before the **OpenShell gateway** app.

It is cluster-scoped: install it **once per cluster**. The controller always runs in the
`agent-sandbox-system` namespace, whatever namespace this app is installed into.

If the cluster already has it from `kubectl apply -f .../sandbox.yaml`, don't install
this app: Helm can't take over resources it didn't create.
