# SUSE AI Factory blueprints

```text
blueprints/ai-helpdesk/blueprint.yaml   Blueprint CR (AI Helpdesk 1.0.0), exported from the reference cluster
charts/open-webui/                      AppCo open-webui 18.3.0 + questions.yaml (install form)
charts/ollama/                          AppCo ollama 1.95.0 + questions.yaml (install form)
charts/open-webui-mcpo/                 AppCo open-webui-mcpo 2.0.0 + questions.yaml (install form)
```

## How it fits together

- All three components of the blueprint use the `forgejo-blueprints` ClusterRepo: create a
  git-backed ClusterRepo with that name pointing at this repository.
- The chart copies are the unmodified AppCo charts plus `questions.yaml`. To update, re-pull
  the chart and copy `questions.yaml` over.

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
