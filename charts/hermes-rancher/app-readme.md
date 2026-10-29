# Hermes for Rancher

[Hermes Agent](https://github.com/NousResearch/hermes-agent) from Nous Research for **platform engineers**:
an [NVIDIA OpenShell](https://docs.nvidia.com/openshell/) 0.1.5 sandbox on SUSE BCI 16 or openSUSE Leap 16,
with `kubectl` on this cluster. Ask it why a pod is crashing, what changed in a namespace, or which nodes are
under pressure.

| Cluster access | What the agent's ServiceAccount can do |
|---|---|
| **view** (default) | read everything except Secrets |
| **operator** | view, plus restart and scale Deployments, StatefulSets and DaemonSets, and delete Pods |

The agent never gets a pod token of its own. The sandbox's policy lets only `kubectl` reach the API server,
and the security profile (default **research**) decides what else it can reach.

**Who can use it:** anyone who can open the terminal gets this access. The Service is ClusterIP, so the terminal
is reached with `kubectl port-forward` by people allowed into this namespace.

**Before you install**
- **OpenShell 1 - Agent Sandbox controller** (once per cluster) and **OpenShell 2 - Gateway**, with this app in the gateway's namespace.
- A model: the SUSE **vLLM** router in the same namespace, or an OpenAI-compatible API key.
