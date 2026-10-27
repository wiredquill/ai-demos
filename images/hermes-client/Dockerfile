# syntax=docker/dockerfile:1
# Hermes client: the openshell CLI plus a script that runs Hermes as an
# OpenShell sandbox and forwards its web terminal.  Deployed by
# catalog/components/hermes-openshell.  Build from the repo root:
#   docker build -f images/hermes-client/Dockerfile -t hermes-openshell-client .

FROM registry.suse.com/bci/bci-base:16.0 AS cli
ARG TARGETARCH
ARG OPENSHELL_VERSION=0.1.5
# sha256 of the release's musl CLI tarballs (openshell-checksums-sha256.txt)
ARG OPENSHELL_SHA256_AMD64=ca1ad6e6fbb4a6cd407e95763391b8ecff02912e7d9c467e7ca22696fe80af69
ARG OPENSHELL_SHA256_ARM64=30c949b4ac07a9c8245c1248eb82e4eb241615134fcabf3c9bf30dec7d00addf
RUN zypper -n install --no-recommends curl tar gzip && zypper -n clean -a
RUN set -eu; \
    case "$TARGETARCH" in \
      amd64) arch=x86_64;  sum=$OPENSHELL_SHA256_AMD64 ;; \
      arm64) arch=aarch64; sum=$OPENSHELL_SHA256_ARM64 ;; \
      *) echo "unsupported arch: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    tgz=openshell-$arch-unknown-linux-musl.tar.gz; \
    curl -fsSLo /tmp/$tgz https://github.com/NVIDIA/OpenShell/releases/download/v$OPENSHELL_VERSION/$tgz; \
    echo "$sum  /tmp/$tgz" | sha256sum -c -; \
    tar -xzf /tmp/$tgz -C /usr/local/bin openshell; \
    /usr/local/bin/openshell --version

FROM registry.suse.com/bci/bci-base:16.0
LABEL org.opencontainers.image.title="Hermes OpenShell client" \
      org.opencontainers.image.description="openshell CLI that runs Hermes Agent as an OpenShell sandbox and forwards its web terminal" \
      org.opencontainers.image.source="https://github.com/wiredquill/ai-demos"
COPY --from=cli /usr/local/bin/openshell /usr/local/bin/openshell
COPY images/hermes-client/hermes-client /usr/local/bin/hermes-client
RUN useradd --system --uid 10001 --create-home client
USER 10001
WORKDIR /home/client
ENTRYPOINT ["/usr/local/bin/hermes-client"]
