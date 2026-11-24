# SUSE AI Factory blueprints

```text
blueprints/ai-helpdesk/blueprint-1.0.0.yaml   AI Helpdesk 1.0.0: open-webui 18.3.0 (one back), ollama 1.95.0, mcpo 2.0.0
blueprints/ai-helpdesk/blueprint-1.1.0.yaml   AI Helpdesk 1.1.0: open-webui 18.4.0 (the upgrade target)
charts/open-webui/{18.2.0,18.3.0,18.4.0}/     AppCo open-webui + questions.yaml
charts/ollama/{1.93.0,1.94.0,1.95.0}/         AppCo ollama + questions.yaml
charts/open-webui-mcpo/2.0.0/                 AppCo open-webui-mcpo + questions.yaml
```

## Upgrade demo

Deploy blueprint 1.0.0 (Open WebUI chart 18.3.0, app 0.13.3), then upgrade the workload to 1.1.0
(chart 18.4.0, app 0.13.4). The blueprints do not pin `image.tag`, so the chart's default image
follows the chart version. Every chart version is available in the repo, so any of the three
can be selected.

## How it fits together

- All three components of the blueprint use the `forgejo-blueprints` ClusterRepo: create a
  git-backed ClusterRepo with that name pointing at this repository.
- The chart copies are the unmodified AppCo charts plus `questions.yaml`. Each chart version lives in
  its own folder. To add a version, pull the chart into a new folder and copy `questions.yaml` over.

## questions.yaml conventions

- The first group is the first page of the form:
  - open-webui: Service & Ingress, then Storage, Advanced
  - ollama: Model & GPU, then Service, Ingress & Certificate, Storage, Advanced
  - open-webui-mcpo: Service, Advanced
- Service-type dependent fields (NodePort, LoadBalancer IP/class) use `show_if`.
- Defaults mirror the AI Helpdesk blueprint values.
- List values (`extraEnvVars`, `extraEnv`, `ollama.models.pull`) are addressed by index, so the
  order of entries in the blueprint matters.
- Fields that would render invalid manifests when empty (for example resource requests) are
  intentionally not exposed.
- open-webui-mcpo 2.0.0 has no Ingress question: its ingress template references a missing
  `mcp-library` and fails to render.
