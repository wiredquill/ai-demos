#!BuildTag: apache-tika:${VERSION}-%RELEASE%
#!BuildTag: apache-tika:${VERSION}
annotations:
  helm.sh/images: |
    - image: ${CONTAINER_REGISTRY}/containers/apache-tika:${APP_VERSION}
      name: apache-tika
apiVersion: v2
appVersion: ${APP_VERSION}
description: Apache Tika is a toolkit for detecting and extracting metadata and structured text content from various documents using existing parser libraries.
home: https://apps.rancher.io/applications/apache-tika
icon: https://apps.rancher.io/logos/apache-tika.png
maintainers:
  - name: SUSE LLC
    url: https://www.suse.com/
name: apache-tika
version: ${VERSION}
