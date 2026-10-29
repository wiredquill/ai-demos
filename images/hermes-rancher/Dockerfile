# syntax=docker/dockerfile:1
# Hermes for Rancher's sandbox image: the hermes-openshell image plus Rancher's
# agent CLI (`rancher`) and the agent skill it ships. Build from the repo root:
#   docker buildx build --platform linux/amd64 -f images/hermes-rancher/Dockerfile \
#     --build-arg HERMES_IMAGE=ghcr.io/wiredquill/hermes-openshell:<sha> .
#
# The CLI's repository is private, so its linux/amd64 release binary is kept
# here, gzipped (rancher-linux-amd64.gz). It ships for amd64 only, so this
# image is amd64 only. To move to a new release: replace the .gz and set
# RANCHER_CLI_VERSION and RANCHER_CLI_SHA256 (of the uncompressed binary).
#
# No credentials in here: the sandbox gets RANCHER_CLI_URL and a placeholder
# RANCHER_CLI_TOKEN, and the OpenShell gateway injects the real token on
# requests to Rancher.
ARG HERMES_IMAGE=ghcr.io/wiredquill/hermes-openshell:latest

FROM ${HERMES_IMAGE}
ARG RANCHER_CLI_VERSION=v0.1.0-alpha.7
ARG RANCHER_CLI_SHA256=6baeb1a448ff6480f1994ffdcae250838f0a9887b89cc4ce56a6f9091c739b4f
LABEL org.opencontainers.image.title="Hermes for Rancher" \
      org.opencontainers.image.description="Hermes Agent for OpenShell with Rancher's agent CLI ${RANCHER_CLI_VERSION} and its skill" \
      org.opencontainers.image.source="https://github.com/wiredquill/ai-demos"

# this branch's start script, which copies the skill (the base image may predate it)
COPY images/hermes/hermes-sandbox-start /usr/local/bin/hermes-sandbox-start
COPY images/hermes-rancher/rancher-linux-amd64.gz /tmp/rancher.gz
USER 0
# The skill is embedded in the binary; `skill install` writes it under
# ~/.agents/skills when ~/.agents exists. hermes-sandbox-start copies
# /opt/hermes/skills/* into ~/.hermes/skills.
RUN set -eu; \
    gzip -dc /tmp/rancher.gz > /usr/local/bin/rancher; rm /tmp/rancher.gz; \
    echo "$RANCHER_CLI_SHA256  /usr/local/bin/rancher" | sha256sum -c -; \
    chmod 755 /usr/local/bin/rancher; \
    tmp=$(mktemp -d); mkdir "$tmp/.agents"; \
    HOME=$tmp RANCHER_CLI_CONFIG_DIR=$tmp/config rancher skill install --agent agents; \
    mkdir -p /opt/hermes/skills; \
    mv "$tmp/.agents/skills/rancher" /opt/hermes/skills/rancher; \
    rm -rf "$tmp"; \
    test -s /opt/hermes/skills/rancher/SKILL.md
USER 10001
