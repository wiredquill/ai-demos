# SPDX-License-Identifier: MIT
#!BuildTag: charts/open-webui-pipelines:${VERSION}-%RELEASE%
#!BuildTag: charts/open-webui-pipelines:${VERSION}
annotations:
  licenses: MIT
  helm.sh/images: |
    - image: ${CONTAINER_REGISTRY}/containers/open-webui-pipelines:${APP_VERSION}
      name: open-webui-pipelines
apiVersion: v2
appVersion: ${APP_VERSION}
description: 'Pipelines bring modular, customizable workflows to any UI client supporting OpenAI API specs and much more! Easily extend functionalities, integrate unique logic, and create dynamic workflows with just a few lines of code.'
home: https://apps.rancher.io/applications/open-webui-pipelines
icon: https://apps.rancher.io/logos/open-webui-pipelines.png
keywords:
  - ai
  - llm
  - chat
  - web-ui
sources:
  - https://github.com/open-webui/pipelines
name: open-webui-pipelines
version: ${VERSION}
maintainers:
  - url: https://www.suse.com/
    name: SUSE LLC
