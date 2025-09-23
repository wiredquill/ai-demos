# SPDX-License-Identifier: MIT
#!BuildTag: charts/open-webui:${VERSION}-%RELEASE%
#!BuildTag: charts/open-webui:${VERSION}
annotations:
  licenses: MIT
  helm.sh/images: |
    - image: ${CONTAINER_REGISTRY}/containers/open-webui:${APP_VERSION}
      name: open-webui
apiVersion: v2
name: open-webui
version: ${VERSION}
appVersion: ${APP_VERSION}

home: https://apps.rancher.io/applications/open-webui
icon: https://apps.rancher.io/logos/open-webui.png

description: "Open WebUI is an extensible, feature-rich, and user-friendly self-hosted WebUI designed to operate entirely offline. It supports various LLM runners, including Ollama and OpenAI-compatible APIs."
keywords:
  - llm
  - chat
  - web-ui

maintainers:
  - url: https://www.suse.com
    name: SUSE LLC

dependencies:
  - name: ollama
    version: 1.26.0
    repository: oci://dp.apps.rancher.io/charts
    import-values:
      - child: service
        parent: ollama.service
    condition: ollama.enabled
  - name: open-webui-pipelines
    alias: pipelines
    version: 0.5.0
    repository: oci://dp.apps.rancher.io/charts
    import-values:
      - child: service
        parent: pipelines.service
    condition: pipelines.enabled
  - name: apache-tika
    alias: tika
    repository: oci://dp.apps.rancher.io/charts
    version: 3.2.2
    condition: tika.enabled
