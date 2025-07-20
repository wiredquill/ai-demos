#!/bin/bash

# Pre-commit hook to check chart version synchronization
# Install: ln -s ../../scripts/pre-commit-version-check.sh .git/hooks/pre-commit

set -e

echo "🔍 Checking chart version synchronization..."

# Check if chart files are being committed
CHART_FILES_CHANGED=$(git diff --cached --name-only | grep -E "charts/.*/Chart\.yaml$" || true)

if [ -n "$CHART_FILES_CHANGED" ]; then
    echo "Chart.yaml files are being committed, checking version sync..."
    echo "Changed files:"
    echo "$CHART_FILES_CHANGED"
    echo ""
    
    # Run version check
    if ./scripts/sync-chart-versions.sh --check; then
        echo "✅ Chart versions are synchronized"
        exit 0
    else
        echo ""
        echo "❌ COMMIT BLOCKED: Chart versions are not synchronized!"
        echo ""
        echo "Please run one of the following to fix version sync:"
        echo "  ./scripts/sync-chart-versions.sh --sync-to-upstream"
        echo "  ./scripts/sync-chart-versions.sh --sync-to-suse"
        echo "  ./scripts/sync-chart-versions.sh --bump-patch"
        echo ""
        echo "Then add the changes and commit again:"
        echo "  git add charts/*/Chart.yaml"
        echo "  git commit"
        exit 1
    fi
else
    echo "✅ No chart files being committed, skipping version check"
    exit 0
fi