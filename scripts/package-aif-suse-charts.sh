#!/usr/bin/env bash
# Republish SUSE Application Collection charts unchanged except for an added
# questions.yaml (catalog/charts/<chart>/questions.yaml), so the SUSE AI
# Factory UI shows an install form for them. The chart name and version stay
# SUSE's, so blueprints still show e.g. "vllm 0.1.10".
#
# Usage: scripts/package-aif-suse-charts.sh <output-dir>
# Needs: helm registry login dp.apps.rancher.io
set -euo pipefail

OUT=${1:?usage: $0 <output-dir>}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHARTS=(
  "vllm 0.1.10"
  "opensearch 3.8.0"
)

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

for entry in "${CHARTS[@]}"; do
  read -r chart version <<<"$entry"
  helm pull "oci://dp.apps.rancher.io/charts/$chart" --version "$version" -d "$WORK" >/dev/null
  tar -xzf "$WORK/$chart-$version.tgz" -C "$WORK"
  cp "$ROOT/catalog/charts/$chart/questions.yaml" "$WORK/$chart/questions.yaml"
  helm package "$WORK/$chart" -d "$OUT"
  rm -rf "${WORK:?}/$chart" "$WORK/$chart-$version.tgz"
done
