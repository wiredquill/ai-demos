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

# ---- runtime stage ------------------------------------------------------------------
FROM ${BASE}
LABEL org.opencontainers.image.title="Hermes Agent for OpenShell" \
      org.opencontainers.image.description="Nous Research Hermes Agent with a ttyd web terminal, built to run as an NVIDIA OpenShell sandbox" \
      org.opencontainers.image.source="https://github.com/wiredquill/ai-demos"

# The agent's terminal tool runs commands right here, so give it the usual
# tools; what they may reach is up to the OpenShell profile, not the image.
RUN zypper -n install --no-recommends python313 git-core curl tar gzip which less \
      util-linux shadow && zypper -n clean -a
COPY --from=builder /opt/hermes /opt/hermes
COPY --from=ttyd /usr/local/bin/ttyd /usr/local/bin/ttyd
COPY images/hermes/hermes-sandbox-start /usr/local/bin/hermes-sandbox-start
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
