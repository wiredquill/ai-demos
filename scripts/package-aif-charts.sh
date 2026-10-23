#!/usr/bin/env bash
# Republish third-party charts with an install form for SUSE AI Factory.
#
#   suse      SUSE Application Collection charts (dp.apps.rancher.io), for the
#             wiredquill-ai-demos ClusterRepo (branch aif/hr-assistant-vllm).
#   upstream  The equivalent community charts, for the wiredquill-upstream
#             ClusterRepo (branch aif/upstream-charts). They are the same chart and
#             app versions as the SUSE ones where upstream has them, so the
#             SUSE-vs-upstream blueprints compare like for like.
#
# Each chart gets questions.yaml from catalog/charts/<form>/ (upstream ships none),
# plus any catalog/charts/<form>/*.patch where the templates misread form values.
# Chart names and versions are kept, so blueprints still show e.g. "vllm 0.1.10".
#
# Usage: scripts/package-aif-charts.sh <output-dir> [suse|upstream]
# Needs: helm registry login dp.apps.rancher.io (for suse)
set -euo pipefail

OUT=${1:?usage: $0 <output-dir> [suse|upstream]}
SET=${2:-suse}
ROOT=$(cd "$(dirname "$0")/.." && pwd)

# <chart> <version> <source> <form dir under catalog/charts>
SUSE_CHARTS=(
  "vllm 0.1.10 oci://dp.apps.rancher.io/charts/vllm vllm"
  "opensearch 3.8.0 oci://dp.apps.rancher.io/charts/opensearch opensearch"
  "ollama 1.91.0 oci://dp.apps.rancher.io/charts/ollama ollama"
  "open-webui 8.19.1 oci://dp.apps.rancher.io/charts/open-webui open-webui"
  "open-webui-pipelines 0.9.2 oci://dp.apps.rancher.io/charts/open-webui-pipelines open-webui-pipelines"
)
# SUSE's open-webui 8.19.1 and open-webui-pipelines 0.9.2 are SUSE patch builds of
# upstream 8.19.0 and 0.9.0, the closest upstream releases.
UPSTREAM_CHARTS=(
  "ollama 1.91.0 https://github.com/otwld/ollama-helm/releases/download/ollama-1.91.0/ollama-1.91.0.tgz ollama"
  "open-webui 8.19.0 https://github.com/open-webui/helm-charts/releases/download/open-webui-8.19.0/open-webui-8.19.0.tgz open-webui"
  "pipelines 0.9.0 https://github.com/open-webui/helm-charts/releases/download/pipelines-0.9.0/pipelines-0.9.0.tgz open-webui-pipelines"
)

case "$SET" in
  suse) CHARTS=("${SUSE_CHARTS[@]}") ;;
  upstream) CHARTS=("${UPSTREAM_CHARTS[@]}") ;;
  *) echo "unknown set: $SET (suse|upstream)" >&2; exit 1 ;;
esac

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

for entry in "${CHARTS[@]}"; do
  read -r chart version source form <<<"$entry"
  case "$source" in
    oci://*) helm pull "$source" --version "$version" -d "$WORK" >/dev/null ;;
    *) curl -fsSL -o "$WORK/$chart-$version.tgz" "$source" ;;
  esac
  tar -xzf "$WORK/$chart-$version.tgz" -C "$WORK"
  cp "$ROOT/catalog/charts/$form/questions.yaml" "$WORK/$chart/questions.yaml"
  for p in "$ROOT/catalog/charts/$form"/*.patch; do
    [ -e "$p" ] || continue
    patch -s -p1 -d "$WORK/$chart" < "$p"
  done
  # A patch that applies with an offset leaves *.orig backups, and Helm renders
  # every file under templates/ (a second Deployment). A *.rej means it failed.
  if find "$WORK/$chart" -name '*.rej' | grep -q .; then
    echo "$chart $version: patch rejected, update catalog/charts/$form/*.patch" >&2; exit 1
  fi
  find "$WORK/$chart" -name '*.orig' -delete
  helm package "$WORK/$chart" -d "$OUT"
  rm -rf "${WORK:?}/$chart" "$WORK/$chart-$version.tgz"
done
