# syntax=docker/dockerfile:1
# Hermes Agent (Nous Research) as an OpenShell sandbox workload, on a SUSE OS.
# One Dockerfile, two bases (build from the repo root):
#   docker build -f images/hermes/Dockerfile -t hermes-openshell .
#   docker build -f images/hermes/Dockerfile -t hermes-openshell-opensuse \
#     --build-arg BASE=registry.opensuse.org/opensuse/leap:16.0 .
#
# Runs as uid 10001 (OpenShell rejects root). Everything the agent may write is
# under /home/hermes and /tmp; the profiles in
# charts/hermes-openshell decide what else it can touch.
ARG BASE=registry.suse.com/bci/bci-base:16.0

# ---- build stage: Hermes in a self-contained virtualenv ------------------------
FROM ${BASE} AS builder
ARG HERMES_VERSION=0.19.0
# OpenTelemetry for the model calls (sitecustomize.py turns it on); same pin as
# the ai-compare app. Resolves cleanly against hermes-agent's exact pins.
ARG OPENLIT_VERSION=1.44.0
RUN zypper -n install --no-recommends python313 python313-pip && zypper -n clean -a
# a venv pins its own sys.path, so it works whatever env the sandbox keeps.
# PyPI hermes-agent 0.19.0 supports Python 3.11-3.13; its deps are exact-pinned.
RUN python3.13 -m venv --without-pip /opt/hermes \
 && python3.13 -m pip --python /opt/hermes/bin/python install --no-cache-dir \
      "hermes-agent==${HERMES_VERSION}" "openlit==${OPENLIT_VERSION}"
# loaded by every start of the venv's python; does nothing without
# OTEL_EXPORTER_OTLP_ENDPOINT
COPY images/hermes/sitecustomize.py /opt/hermes/lib/python3.13/site-packages/sitecustomize.py

# ttyd serves the browser terminal the client pod forwards out of the sandbox.
FROM ${BASE} AS ttyd
ARG TARGETARCH
ARG TTYD_VERSION=1.7.7
# sha256 of the release's static binaries (SHA256SUMS)
ARG TTYD_SHA256_AMD64=8a217c968aba172e0dbf3f34447218dc015bc4d5e59bf51db2f2cd12b7be4f55
ARG TTYD_SHA256_ARM64=b38acadd89d1d396a0f5649aa52c539edbad07f4bc7348b27b4f4b7219dd4165
RUN zypper -n install --no-recommends curl && zypper -n clean -a
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) arch=x86_64;  sum=$TTYD_SHA256_AMD64 ;; \
      arm64) arch=aarch64; sum=$TTYD_SHA256_ARM64 ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSLo /usr/local/bin/ttyd https://github.com/tsl0922/ttyd/releases/download/$TTYD_VERSION/ttyd.$arch; \
    echo "$sum  /usr/local/bin/ttyd" | sha256sum -c -; \
    chmod 755 /usr/local/bin/ttyd

# kubectl for the chart's platform option (cluster access for platform
# engineers). Without it the sandbox has no kubeconfig and no network rule to
# an API server, so it can't reach a cluster with it.
FROM ${BASE} AS kubectl
ARG TARGETARCH
ARG KUBECTL_VERSION=1.35.10
# sha256 from https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/<arch>/kubectl.sha256
ARG KUBECTL_SHA256_AMD64=c49a28f1f4efc4d475ed05f47f2ce8e563bf7bef69ed77fe1b924ea6d83b6327
ARG KUBECTL_SHA256_ARM64=283f1be6a46b3695b625e25030106b8ffe18bd0d3a900f5b65c259ca407f04f5
RUN zypper -n install --no-recommends curl && zypper -n clean -a
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) sum=$KUBECTL_SHA256_AMD64 ;; \
      arm64) sum=$KUBECTL_SHA256_ARM64 ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v$KUBECTL_VERSION/bin/linux/$TARGETARCH/kubectl; \
    echo "$sum  /usr/local/bin/kubectl" | sha256sum -c -; \
    chmod 755 /usr/local/bin/kubectl

# helm and yq for the agent to read releases and YAML with. Upstream static
# binaries, checked like kubectl.
FROM ${BASE} AS tools
ARG TARGETARCH
ARG HELM_VERSION=4.3.1
# sha256 from https://get.helm.sh/helm-v$HELM_VERSION-linux-<arch>.tar.gz.sha256sum
ARG HELM_SHA256_AMD64=0403a88ae20913d11b10a2467b50087721fea7581736da6b9d3992f5357fe54b
ARG HELM_SHA256_ARM64=8cf8f66ecbc252ac8f7f06cca68aba88508ddfde3a6a34feb1678ad1694b4f88
ARG YQ_VERSION=4.54.1
# sha256 from the release's checksums file (SHA-256 column)
ARG YQ_SHA256_AMD64=8e34fc298390875de416e6a4afcb8cabeceb25d9aa8506c1a2f9353cf702ea5f
ARG YQ_SHA256_ARM64=189088da0c6429ec5178dfaab1a114805f6cab0b61b165ab236efedf1d57a71b
RUN zypper -n install --no-recommends curl tar gzip && zypper -n clean -a
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) helm_sum=$HELM_SHA256_AMD64; yq_sum=$YQ_SHA256_AMD64 ;; \
      arm64) helm_sum=$HELM_SHA256_ARM64; yq_sum=$YQ_SHA256_ARM64 ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSLo /tmp/helm.tgz https://get.helm.sh/helm-v$HELM_VERSION-linux-$TARGETARCH.tar.gz; \
    echo "$helm_sum  /tmp/helm.tgz" | sha256sum -c -; \
    tar -xzf /tmp/helm.tgz -C /tmp; \
    install -m 755 /tmp/linux-$TARGETARCH/helm /usr/local/bin/helm; \
    curl -fsSLo /usr/local/bin/yq https://github.com/mikefarah/yq/releases/download/v$YQ_VERSION/yq_linux_$TARGETARCH; \
    echo "$yq_sum  /usr/local/bin/yq" | sha256sum -c -; \
    chmod 755 /usr/local/bin/yq

# ---- runtime stage ------------------------------------------------------------------
FROM ${BASE}
LABEL org.opencontainers.image.title="Hermes Agent for OpenShell" \
      org.opencontainers.image.description="Nous Research Hermes Agent with a ttyd web terminal, built to run as an NVIDIA OpenShell sandbox" \
      org.opencontainers.image.source="https://github.com/wiredquill/ai-demos"

# The agent's terminal tool runs commands right here, so give it the usual
# tools; what they may reach is up to the OpenShell profile, not the image.
# The sandbox can't install anything itself (no root, no package repos), so
# what the agent reaches for goes in here; hermes-sandbox-start lists it in
# AGENTS.md. python3 is the name models try first.
RUN zypper -n install --no-recommends python313 git-core curl tar gzip which less \
      util-linux shadow jq gawk openssl && zypper -n clean -a \
 && ln -s /usr/bin/python3.13 /usr/local/bin/python3
COPY --from=builder /opt/hermes /opt/hermes
COPY --from=ttyd /usr/local/bin/ttyd /usr/local/bin/ttyd
COPY --from=kubectl /usr/local/bin/kubectl /usr/local/bin/kubectl
COPY --from=tools /usr/local/bin/helm /usr/local/bin/yq /usr/local/bin/
COPY images/hermes/hermes-sandbox-start /usr/local/bin/hermes-sandbox-start
# SUSE brand skins (suse-dark, suse-light); hermes-sandbox-start copies them
# into ~/.hermes/skins, so the chart's skin dropdown can name them
COPY images/hermes/skins/ /opt/hermes/skins/
RUN ln -s /opt/hermes/bin/hermes /usr/local/bin/hermes \
 && printf '%s\n' '# OpenShell sets HOME=/sandbox; the profiles allow writes under /home/hermes' \
      'export HOME=/home/hermes' > /etc/profile.d/hermes-home.sh

RUN useradd --system --uid 10001 --create-home --home-dir /home/hermes hermes \
 && mkdir -p /home/hermes/workspace && chown -R 10001:10001 /home/hermes
USER 10001
WORKDIR /home/hermes/workspace
ENV HOME=/home/hermes
EXPOSE 7681

ENTRYPOINT ["/usr/local/bin/hermes-sandbox-start"]
