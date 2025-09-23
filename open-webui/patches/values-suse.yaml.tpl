global:

  tls:
    # options: suse-private-ai, letsEncrypt, secret
    source: suse-private-ai
    issuerName: suse-private-ai

    # This section to be filled out when using letsEncrypt as the tls source
    letsEncrypt:
      environment: staging
      email: none@example.com
      ingress:
        class: ""

    # Additional Trusted CAs.
    # Enable this flag and add your CA certs as a secret named tls-ca-additional in the suse-private-ai namespace.
    additionalTrustedCAs: false

image:
  registry: ${CONTAINER_REGISTRY}
  repository: containers/open-webui
  tag: ${APP_VERSION}
pipelines:
  enabled: false
ingress:
  enabled: true
  class: ""
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  host: ""
  tls: true
  existingSecret: ""
websocket:
  enabled: true
  redis:
    enabled: true
    image:
      registry: ${CONTAINER_REGISTRY}
      repository: containers/redis
      tag: "8.0.2"
