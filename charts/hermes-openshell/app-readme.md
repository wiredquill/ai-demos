# OpenShell 3 - Hermes Agent sandbox

[Hermes Agent](https://github.com/NousResearch/hermes-agent) from Nous Research, running as an
[NVIDIA OpenShell](https://docs.nvidia.com/openshell/) 0.1.5 sandbox on SUSE BCI 16 or openSUSE Leap 16.
Pick a **security profile** and watch what the agent can and can't do under it.

| Profile | Network (besides the model) | Files | Hermes approvals |
|---|---|---|---|
| **lockdown** | none | home + /tmp only | manual |
| **research** | read-only (GET) to Wikipedia, arXiv, GitHub, docs sites | home + /tmp | smart |
| **developer** | + GitHub push/PRs (no deletes), PyPI | home, /tmp, /var/tmp | smart |
| **dangerous** | any subdomain of the common TLDs plus popular bare domains, on 80/443, any program | Landlock best effort | off |

Even under **dangerous**, OpenShell keeps the agent off root, cloud metadata, loopback and the
Kubernetes API, etcd and kubelet ports.

**Before you install**
- **OpenShell 1 - Agent Sandbox controller** (once per cluster) and **OpenShell 2 - Gateway**, with this app in the gateway's namespace.
- A model: the SUSE **vLLM** router in the same namespace, or an OpenAI-compatible API key.

Open the terminal on the Service's NodePort. The page runs `hermes`, and each browser tab gets its own session.
