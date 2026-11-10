#!/usr/bin/env bash
# Package stackpack/genai-insights into dist/genai-insights-<version>.sts (stored ZIP, deterministic).
set -euo pipefail
src=$(cd "${1:-stackpack/genai-insights}" && pwd)
out="${2:-dist}"; mkdir -p "$out"; out=$(cd "$out" && pwd)
ver=$(sed -nE 's/^version: ([0-9]+\.[0-9]+\.[0-9]+)$/\1/p' "$src/stackpack.yaml")
[[ -n "$ver" ]] || { echo "no version in stackpack.yaml" >&2; exit 1; }
cd "$src"
rm -f "$out/genai-insights-$ver.sts"
find README.md stackpack.yaml settings resources icons includes -type f ! -name .DS_Store | sort | zip -q -X -0 "$out/genai-insights-$ver.sts" -@
echo "$out/genai-insights-$ver.sts"
