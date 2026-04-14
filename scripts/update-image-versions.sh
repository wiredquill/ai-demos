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

OLLAMA_VERSION=$(fetch_latest_tag "ollama/ollama")       || error "Failed to get Ollama version"
WEBUI_VERSION=$(fetch_latest_tag "open-webui/open-webui") || error "Failed to get Open WebUI version"

info "  Ollama:     ${OLLAMA_VERSION}"
info "  Open WebUI: ${WEBUI_VERSION}"

# Pipelines has no formal releases — uses date-stamped SUSE App Collection builds.
# Update SUSE_PIPELINES_TAG manually when a new build is available.
SUSE_PIPELINES_TAG="0.20250329.151219"
warn "  Pipelines (SUSE): ${SUSE_PIPELINES_TAG} (update manually from dp.apps.rancher.io)"

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
# Format: "chart_dir|ollama_registry|webui_registry|has_pipelines"
declare -a CHARTS=(
    "ai-compare|ollama/ollama|ghcr.io/open-webui/open-webui|upstream"
    "ai-compare-suse|dp.apps.rancher.io/containers/ollama|dp.apps.rancher.io/containers/open-webui|suse"
    "ai-compare-opentelemetry|dp.apps.rancher.io/containers/ollama|dp.apps.rancher.io/containers/open-webui|suse"
    "hr-assistant|dp.apps.rancher.io/containers/ollama|||none"
)

echo
info "Updating image tags across charts..."
echo

# Track current values for diffs — read once before changes
CURRENT_OLLAMA=$(grep -h "tag:.*0\." "${CHARTS_DIR}/ai-compare-suse/values.yaml" | head -1 | tr -d ' "' | sed 's/tag://')

for entry in "${CHARTS[@]}"; do
    IFS='|' read -r chart_dir _ollama_repo _webui_repo pipelines_type <<< "$entry"
    values="${CHARTS_DIR}/${chart_dir}/values.yaml"
    chart_yaml="${CHARTS_DIR}/${chart_dir}/Chart.yaml"

    info "── ${chart_dir} ──"

    if [[ ! -f "$values" ]]; then
        warn "  values.yaml not found, skipping"
        continue
    fi

    # Get current Ollama tag from this chart
    cur_ollama=$(grep 'tag:' "$values" | head -1 | tr -d ' "' | sed 's/tag://')

    # Ollama image
    update_image_tag "$values" "$cur_ollama" "$OLLAMA_VERSION" "Ollama"

    # Open WebUI image (not in hr-assistant)
    if [[ "$pipelines_type" != "none" ]]; then
        cur_webui=$(grep -A1 'open-webui' "$values" | grep 'tag:' | head -1 | tr -d ' "#.*' | sed 's/tag://')
        if [[ -n "$cur_webui" ]]; then
            update_image_tag "$values" "$cur_webui" "$WEBUI_VERSION" "Open WebUI"
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
