#!/usr/bin/env bash
# Package the SUSE AI Factory charts onto the aif/charts branch, the git
# ClusterRepo (catalog/clusterrepos/wiredquill-ai-demos.yaml) the blueprints
# read as chartRepo: wiredquill-ai-demos. Rancher's git catalog indexes only a
# root index.yaml plus packaged .tgz files on the tracked branch.
#
#   scripts/publish-aif-charts.sh          # package + commit on aif/charts
#   scripts/publish-aif-charts.sh --push   # ... and push it
#
# Packages the per-workload component charts (catalog/components/*) and the
# hr-assistant base charts. Published versions are immutable and never removed:
# blueprints pin exact chart versions, so dropping or replacing one breaks every
# blueprint that uses it. Bump a chart's version to ship a change.
#
# The republished SUSE Application Collection charts (vllm, ollama, opensearch,
# open-webui, open-webui-pipelines) need a dp.apps.rancher.io login, so they
# stay manual: scripts/package-aif-charts.sh <dir>, then copy them in.
set -euo pipefail

BRANCH=aif/charts
URL=https://github.com/wiredquill/ai-demos
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PUSH=${1:-}

WORK=$(mktemp -d)
trap 'git -C "$ROOT" worktree remove --force "$WORK/branch" 2>/dev/null || true; rm -rf "$WORK"' EXIT

for c in "$ROOT"/charts/hr-assistant "$ROOT"/charts/hr-assistant-vllm "$ROOT"/catalog/components/*/; do
  # skip leftover directories that hold no chart
  [ -f "$c/Chart.yaml" ] || continue
  helm package "$c" --dependency-update -d "$WORK/pkg" >/dev/null
done
ls "$WORK/pkg"

git -C "$ROOT" fetch -q origin "$BRANCH:refs/remotes/origin/$BRANCH"
git -C "$ROOT" worktree add -q --detach "$WORK/branch" "origin/$BRANCH"
cd "$WORK/branch"

added=()
for t in "$WORK"/pkg/*.tgz; do
  name=$(basename "$t")
  if [ -e "$name" ]; then
    echo "skip $name: already published (bump the chart version to publish changes)"
  else
    cp "$t" .
    added+=("$name")
  fi
done
if [ ${#added[@]} -eq 0 ]; then
  echo "nothing new to publish"
  exit 0
fi

# --merge keeps every existing entry as it is; only the new packages are added
helm repo index . --url "$URL" --merge index.yaml
git add index.yaml "${added[@]}"
git commit -q -s -m "chore(aif): publish ${added[*]}"
git log --oneline -1
if [ "$PUSH" = --push ]; then
  git push -q origin "HEAD:$BRANCH"
  echo "pushed $BRANCH; refresh the wiredquill-ai-demos ClusterRepo in Rancher to pick it up"
fi
