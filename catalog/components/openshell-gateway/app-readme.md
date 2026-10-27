# OpenShell gateway

[NVIDIA OpenShell](https://docs.nvidia.com/openshell/latest/) 0.1.5 is the sandbox runtime
for autonomous agents. The gateway is its control plane: it holds the policies and
providers, and its Kubernetes driver runs each sandbox as a pod with a supervisor that
enforces network policy (L4 + L7), Landlock and seccomp.

This app is NVIDIA's official chart with the openshell-lab defaults and an install form.

**Before you install**
- The **Agent Sandbox controller** app (or `kubectl apply` of its `sandbox.yaml`) on this cluster.
- A CNI that enforces `NetworkPolicy` (RKE2's Canal/Calico/Cilium do).
- To deploy **can-i** with its own app, install it into this same namespace: it reads the
  `openshell-client-tls` Secret this chart creates.

**Using the CLI from your workstation**
```bash
kubectl -n <namespace> port-forward svc/openshell 17680:8080
```
Then register the gateway as `openshell-lab/k8s/setup.sh` does, with the client bundle from
the `openshell-client-tls` Secret.

**Reaching the gateway from outside the cluster**

The CLI talks gRPC over mTLS to port 8080 and checks the server certificate against the
address it dials. Pick one way in:
- **ClusterIP** (default): `kubectl port-forward svc/openshell 17680:8080`, then use
  `https://127.0.0.1:17680` (`127.0.0.1` is always on the certificate).
- **NodePort** or **LoadBalancer**: set the Service type and add the node IP or load
  balancer address to **Extra certificate names**.

Either way the CLI needs the client bundle (`ca.crt`, `tls.crt`, `tls.key`) from the
`openshell-client-tls` Secret in `~/.config/openshell/gateways/<name>/mtls/`, then
`openshell gateway add <endpoint> --local --name <name>`.

The certificate is generated once. To add names later, delete the `openshell-server-tls`
Secret and upgrade the app.

Sandboxes are never exposed directly: they have no inbound network. You reach them through
the gateway (`openshell sandbox connect`, `exec`, `forward`), and the can-i app publishes
its dashboard with its own Service.
