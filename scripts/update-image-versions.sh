#!/bin/bash
# update-image-versions.sh
#
# Queries GitHub releases for latest Ollama and Open WebUI versions, then
# updates all 4 demo chart values.yaml files (ai-compare, ai-compare-suse,
# ai-compare-opentelemetry, hr-assistant) and bumps chart patch versions.
#
# SUSE Application Collection images (dp.apps.rancher.io) follow the same
# version tags as upstream. Pipelines uses a date-stamped build tag that must
# be updated manually from the SUSE App Collection catalog.
#
# Usage:
#   ./scripts/update-image-versions.sh [--dry-run]
#
# Requirements:
#   - gh CLI (github.com/cli/gh) authenticated
#   - sed, awk

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHARTS_DIR="${PROJECT_ROOT}/charts"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Fetch latest versions via gh CLI ─────────────────────────────────────────
fetch_latest_tag() {
    local repo="$1"
    gh api "repos/${repo}/releases/latest" --jq '.tag_name' 2>/dev/null \
        | sed 's/^v//'   # strip leading 'v'
}

info "Fetching latest component versions from GitHub..."

# IMPORTANT: SUSE Application Collection images use the format <upstream-version>-<build>
# e.g. dp.apps.rancher.io/containers/ollama:0.21.2-11.48
# These are fetched from the SUSE App Collection helm chart, NOT from upstream GitHub tags.
# Run: helm show values oci://dp.apps.rancher.io/charts/ollama | grep tag:
# Run: helm show values oci://dp.apps.rancher.io/charts/open-webui | grep tag:
# Run: helm show values oci://dp.apps.rancher.io/charts/open-webui-pipelines | grep tag:
#
# Upstream versions (ai-compare) should match the base version of the SUSE App Collection image
# e.g. if SUSE uses 0.21.2-11.48 then upstream uses 0.21.2

SUSE_OLLAMA_TAG=$(helm show values oci://dp.apps.rancher.io/charts/ollama 2>/dev/null | grep 'tag:' | head -1 | tr -d ' "' | sed 's/tag://') \
  || { warn "helm pull failed for ollama — using hardcoded fallback"; SUSE_OLLAMA_TAG="0.21.2-11.48"; }
SUSE_WEBUI_TAG=$(helm show values oci://dp.apps.rancher.io/charts/open-webui 2>/dev/null | grep 'tag:' | grep -v redis | head -1 | tr -d ' "' | sed 's/tag://') \
  || { warn "helm pull failed for open-webui — using hardcoded fallback"; SUSE_WEBUI_TAG="0.6.41-14.20"; }
SUSE_PIPELINES_TAG=$(helm show values oci://dp.apps.rancher.io/charts/open-webui-pipelines 2>/dev/null | grep 'tag:' | head -1 | tr -d ' "' | sed 's/tag://') \
  || { warn "helm pull failed for pipelines — using hardcoded fallback"; SUSE_PIPELINES_TAG="0.20250819.030501-8.19"; }

# Derive upstream versions by stripping the -build suffix
OLLAMA_VERSION=$(echo "$SUSE_OLLAMA_TAG" | cut -d- -f1)
WEBUI_VERSION=$(echo "$SUSE_WEBUI_TAG" | cut -d- -f1)

info "  Ollama:     ${OLLAMA_VERSION}  (SUSE: ${SUSE_OLLAMA_TAG})"
info "  Open WebUI: ${WEBUI_VERSION}  (SUSE: ${SUSE_WEBUI_TAG})"
info "  Pipelines:  (SUSE: ${SUSE_PIPELINES_TAG}, upstream: main)"

# ── Helper: in-place sed that works on macOS and Linux ───────────────────────
sed_inplace() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# ── Update a values.yaml field ────────────────────────────────────────────────
# update_image_tag <file> <current_tag> <new_tag> <description>
update_image_tag() {
    local file="$1" current="$2" new="$3" desc="$4"
    if grep -q "\"${current}\"" "$file" 2>/dev/null; then
        if [[ "$DRY_RUN" == "true" ]]; then
            info "  [dry-run] Would update ${desc}: ${current} → ${new}  (${file##*/charts/})"
        else
            sed_inplace "s/\"${current}\"/\"${new}\"/" "$file"
            success "Updated ${desc}: ${current} → ${new}  (${file##*/charts/})"
        fi
    else
        info "  No change needed for ${desc} in ${file##*/charts/} (not at ${current})"
    fi
}

# ── Bump chart patch version ──────────────────────────────────────────────────
bump_chart_version() {
    local chart_yaml="$1"
    local current new major minor patch
    current=$(grep '^version:' "$chart_yaml" | awk '{print $2}')
    major=$(echo "$current" | cut -d. -f1)
    minor=$(echo "$current" | cut -d. -f2)
    patch=$(echo "$current" | cut -d. -f3)
    new="${major}.${minor}.$((patch + 1))"

    if [[ "$DRY_RUN" == "true" ]]; then
        info "  [dry-run] Would bump chart version: ${current} → ${new}  (${chart_yaml##*/charts/})"
    else
        sed_inplace "s/^version: ${current}/version: ${new}/" "$chart_yaml"
        success "Bumped chart version: ${current} → ${new}  (${chart_yaml##*/charts/})"
    fi
}

# ── Charts configuration ──────────────────────────────────────────────────────
# Format: "chart_dir|registry_type"
# registry_type: suse = dp.apps.rancher.io (versioned build tags)
#                upstream = ghcr.io / docker hub (plain version tags)
#                hr = suse App Collection only (no webui)
declare -a CHARTS=(
    "ai-compare|upstream"
    "ai-compare-suse|suse"
    "ai-compare-opentelemetry|suse"
    "hr-assistant|hr"
)

echo
info "Updating image tags across charts..."
echo

for entry in "${CHARTS[@]}"; do
    IFS='|' read -r chart_dir registry_type <<< "$entry"
    values="${CHARTS_DIR}/${chart_dir}/values.yaml"
    chart_yaml="${CHARTS_DIR}/${chart_dir}/Chart.yaml"

    info "── ${chart_dir} (${registry_type}) ──"

    if [[ ! -f "$values" ]]; then
        warn "  values.yaml not found, skipping"
        continue
    fi

    if [[ "$registry_type" == "upstream" ]]; then
        ollama_new="$OLLAMA_VERSION"
        webui_new="$WEBUI_VERSION"
    else
        # suse and hr both use SUSE App Collection tags
        ollama_new="$SUSE_OLLAMA_TAG"
        webui_new="$SUSE_WEBUI_TAG"
    fi

    # Find and update Ollama tag (first tag: line in the ollama section)
    cur_ollama=$(grep -A2 'repository:.*ollama' "$values" | grep 'tag:' | head -1 | tr -d ' "' | sed 's/tag://' | cut -d'#' -f1 | tr -d ' ')
    if [[ -n "$cur_ollama" ]]; then
        update_image_tag "$values" "$cur_ollama" "$ollama_new" "Ollama"
    fi

    # Open WebUI (not in hr-assistant)
    if [[ "$registry_type" != "hr" ]]; then
        cur_webui=$(grep -A2 'repository:.*open-webui[^-]' "$values" | grep 'tag:' | head -1 | tr -d ' "' | sed 's/tag://' | cut -d'#' -f1 | tr -d ' ')
        if [[ -n "$cur_webui" ]]; then
            update_image_tag "$values" "$cur_webui" "$webui_new" "Open WebUI"
        fi

        # Pipelines (SUSE only; upstream uses 'main' which stays)
        if [[ "$registry_type" == "suse" ]]; then
            cur_pipelines=$(grep -A2 'open-webui-pipelines' "$values" | grep 'tag:' | head -1 | tr -d ' "' | sed 's/tag://' | cut -d'#' -f1 | tr -d ' ')
            if [[ -n "$cur_pipelines" ]]; then
                update_image_tag "$values" "$cur_pipelines" "$SUSE_PIPELINES_TAG" "Pipelines"
            fi
        fi
    fi

    # Bump chart version
    bump_chart_version "$chart_yaml"
    echo
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo
if [[ "$DRY_RUN" == "true" ]]; then
    warn "Dry run complete — no files were modified."
    warn "Run without --dry-run to apply changes."
else
    success "All charts updated."
    info "Component versions now at:"
    info "  Ollama:     ${OLLAMA_VERSION}  (upstream + SUSE Application Collection)"
    info "  Open WebUI: ${WEBUI_VERSION}  (upstream + SUSE Application Collection)"
    warn "  Pipelines (SUSE): ${SUSE_PIPELINES_TAG} — verify latest tag at dp.apps.rancher.io"
    echo
    info "Review changes with: git diff charts/"
    info "Commit when ready."
fi
