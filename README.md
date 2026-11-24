# SUSE AI Factory blueprints

```text
blueprints/ai-helpdesk/blueprint.yaml   Blueprint CR (AI Helpdesk 1.0.0), exported from the reference cluster
charts/open-webui/                      AppCo open-webui 18.3.0 + questions.yaml (install form)
charts/ollama/                          AppCo ollama 1.95.0 + questions.yaml (install form)
```

## How it fits together

- `open-webui-mcpo` is still pulled from the `application-collection` ClusterRepo.
- `open-webui` and `ollama` use the copies in `charts/` so they can carry a `questions.yaml`.
  The blueprint's `chartRepo` for those two components is `forgejo-blueprints`:
  create a git-backed ClusterRepo with that name pointing at this repository.
- The chart copies are the unmodified AppCo charts plus `questions.yaml`. To update, re-pull
  the chart and copy `questions.yaml` over.

## questions.yaml conventions

- Groups: Service, Ingress & Certificate, Storage, Advanced (plus Model and GPU for Ollama).
- Service-type dependent fields (NodePort, LoadBalancer IP/class) use `show_if`.
- Defaults mirror the AI Helpdesk blueprint values.
- List values (`extraEnvVars`, `extraEnv`, `ollama.models.pull`) are addressed by index, so the
  order of entries in the blueprint matters.
- Fields that would render invalid manifests when empty (for example resource requests) are
  intentionally not exposed.
