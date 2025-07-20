#!/bin/bash

# Chart Version Synchronization Script for AI Compare
# Ensures upstream and SUSE chart variants have the same version

set -e

UPSTREAM_CHART="charts/ai-compare/Chart.yaml"
SUSE_CHART="charts/ai-compare-suse/Chart.yaml"

echo "========================================"
echo "📦 AI Compare Chart Version Sync"
echo "========================================"

# Function to get version from Chart.yaml
get_chart_version() {
    local chart_file="$1"
    grep "^version:" "$chart_file" | awk '{print $2}' | tr -d '"'
}

# Function to get appVersion from Chart.yaml
get_app_version() {
    local chart_file="$1"
    grep "^appVersion:" "$chart_file" | awk '{print $2}' | tr -d '"'
}

# Function to update version in Chart.yaml
update_chart_version() {
    local chart_file="$1"
    local new_version="$2"
    sed -i.bak "s/^version:.*/version: $new_version/" "$chart_file"
    rm "${chart_file}.bak"
}

# Function to update appVersion in Chart.yaml
update_app_version() {
    local chart_file="$1"
    local new_version="$2"
    sed -i.bak "s/^appVersion:.*/appVersion: \"$new_version\"/" "$chart_file"
    rm "${chart_file}.bak"
}

# Check current versions
UPSTREAM_VERSION=$(get_chart_version "$UPSTREAM_CHART")
SUSE_VERSION=$(get_chart_version "$SUSE_CHART")
UPSTREAM_APP_VERSION=$(get_app_version "$UPSTREAM_CHART")
SUSE_APP_VERSION=$(get_app_version "$SUSE_CHART")

echo "Current versions:"
echo "  Upstream chart:    $UPSTREAM_VERSION (app: $UPSTREAM_APP_VERSION)"
echo "  SUSE chart:        $SUSE_VERSION (app: $SUSE_APP_VERSION)"
echo ""

# Check if versions are synchronized
VERSIONS_SYNCED=true
if [ "$UPSTREAM_VERSION" != "$SUSE_VERSION" ]; then
    echo "⚠️  Chart versions are not synchronized!"
    VERSIONS_SYNCED=false
fi

if [ "$UPSTREAM_APP_VERSION" != "$SUSE_APP_VERSION" ]; then
    echo "⚠️  App versions are not synchronized!"
    VERSIONS_SYNCED=false
fi

if [ "$VERSIONS_SYNCED" = true ] && [ "$1" = "--check" ]; then
    echo "✅ All versions are synchronized!"
    exit 0
fi

if [ "$VERSIONS_SYNCED" = true ] && [ -z "$1" ]; then
    echo "✅ All versions are synchronized!"
    echo ""
    echo "Usage:"
    echo "  $0 --check                    # Check if versions are synced"
    echo "  $0 --sync-to-upstream         # Sync SUSE to upstream versions"
    echo "  $0 --sync-to-suse             # Sync upstream to SUSE versions"
    echo "  $0 --bump-patch               # Bump patch version on both charts"
    echo "  $0 --bump-minor               # Bump minor version on both charts"
    echo "  $0 --set-version X.Y.Z        # Set specific version on both charts"
    echo "  $0 --set-app-version X.Y.Z    # Set specific app version on both charts"
    exit 0
fi

# Handle different sync operations
case "$1" in
    --check)
        echo "❌ Versions are not synchronized!"
        exit 1
        ;;
    --sync-to-upstream)
        echo "🔄 Syncing SUSE chart to upstream versions..."
        update_chart_version "$SUSE_CHART" "$UPSTREAM_VERSION"
        update_app_version "$SUSE_CHART" "$UPSTREAM_APP_VERSION"
        echo "✅ SUSE chart synchronized to upstream versions"
        ;;
    --sync-to-suse)
        echo "🔄 Syncing upstream chart to SUSE versions..."
        update_chart_version "$UPSTREAM_CHART" "$SUSE_VERSION"
        update_app_version "$UPSTREAM_CHART" "$SUSE_APP_VERSION"
        echo "✅ Upstream chart synchronized to SUSE versions"
        ;;
    --bump-patch)
        NEW_VERSION=$(echo "$UPSTREAM_VERSION" | awk -F. '{printf "%d.%d.%d", $1, $2, $3+1}')
        echo "🔢 Bumping patch version to $NEW_VERSION..."
        update_chart_version "$UPSTREAM_CHART" "$NEW_VERSION"
        update_chart_version "$SUSE_CHART" "$NEW_VERSION"
        echo "✅ Patch version bumped on both charts"
        ;;
    --bump-minor)
        NEW_VERSION=$(echo "$UPSTREAM_VERSION" | awk -F. '{printf "%d.%d.%d", $1, $2+1, 0}')
        echo "🔢 Bumping minor version to $NEW_VERSION..."
        update_chart_version "$UPSTREAM_CHART" "$NEW_VERSION"
        update_chart_version "$SUSE_CHART" "$NEW_VERSION"
        echo "✅ Minor version bumped on both charts"
        ;;
    --set-version)
        if [ -z "$2" ]; then
            echo "❌ Please provide a version (e.g., --set-version 0.2.0)"
            exit 1
        fi
        NEW_VERSION="$2"
        echo "🔢 Setting chart version to $NEW_VERSION..."
        update_chart_version "$UPSTREAM_CHART" "$NEW_VERSION"
        update_chart_version "$SUSE_CHART" "$NEW_VERSION"
        echo "✅ Chart version set to $NEW_VERSION on both charts"
        ;;
    --set-app-version)
        if [ -z "$2" ]; then
            echo "❌ Please provide an app version (e.g., --set-app-version 1.1.0)"
            exit 1
        fi
        NEW_APP_VERSION="$2"
        echo "🔢 Setting app version to $NEW_APP_VERSION..."
        update_app_version "$UPSTREAM_CHART" "$NEW_APP_VERSION"
        update_app_version "$SUSE_CHART" "$NEW_APP_VERSION"
        echo "✅ App version set to $NEW_APP_VERSION on both charts"
        ;;
    *)
        echo "❌ Versions are not synchronized!"
        echo ""
        echo "Available sync options:"
        echo "  $0 --sync-to-upstream         # Sync SUSE to upstream versions"
        echo "  $0 --sync-to-suse             # Sync upstream to SUSE versions"
        echo "  $0 --bump-patch               # Bump patch version on both charts"
        echo "  $0 --bump-minor               # Bump minor version on both charts"
        echo "  $0 --set-version X.Y.Z        # Set specific version on both charts"
        echo "  $0 --set-app-version X.Y.Z    # Set specific app version on both charts"
        exit 1
        ;;
esac

# Show final versions
echo ""
echo "Final versions:"
FINAL_UPSTREAM_VERSION=$(get_chart_version "$UPSTREAM_CHART")
FINAL_SUSE_VERSION=$(get_chart_version "$SUSE_CHART")
FINAL_UPSTREAM_APP_VERSION=$(get_app_version "$UPSTREAM_CHART")
FINAL_SUSE_APP_VERSION=$(get_app_version "$SUSE_CHART")

echo "  Upstream chart:    $FINAL_UPSTREAM_VERSION (app: $FINAL_UPSTREAM_APP_VERSION)"
echo "  SUSE chart:        $FINAL_SUSE_VERSION (app: $FINAL_SUSE_APP_VERSION)"