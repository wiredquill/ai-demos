#!/usr/bin/env bash
# Vendor NVIDIA's OpenShell chart into charts/openshell-gateway/charts/ as a
# packaged .tgz, with charts/openshell-gateway/nvidia-chart.patch applied.
#
# Committed as a .tgz (not a directory) so the chart installs straight from a
# git ClusterRepo without `helm dependency build`, and Rancher doesn't list the
# vendored chart as an app of its own.
#
#   scripts/vendor-openshell-chart.sh [version]    # default 0.1.5
set -euo pipefail

VERSION=${1:-0.1.5}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST=$ROOT/charts/openshell-gateway/charts
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

helm pull oci://ghcr.io/nvidia/openshell/helm-chart --version "$VERSION" -d "$WORK" >/dev/null
tar -xzf "$WORK/helm-chart-$VERSION.tgz" -C "$WORK"
rm -rf "$WORK/helm-chart/tests"   # helm-unittest suites, not part of the install
patch -s -p1 -d "$WORK/helm-chart" < "$ROOT/charts/openshell-gateway/nvidia-chart.patch"
rm -rf "$DEST" && mkdir -p "$DEST"
helm package "$WORK/helm-chart" -d "$DEST" >/dev/null
ls "$DEST"
