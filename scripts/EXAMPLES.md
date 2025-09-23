# SUSE Application Collection Sync - Usage Examples

This document provides practical examples of using the SUSE Application Collection synchronization agent for common scenarios.

## Table of Contents

1. [Quick Start Examples](#quick-start-examples)
2. [AI Demos Project Examples](#ai-demos-project-examples)
3. [Configuration Examples](#configuration-examples)
4. [Troubleshooting Examples](#troubleshooting-examples)
5. [CI/CD Integration Examples](#cicd-integration-examples)

## Quick Start Examples

### Example 1: First Time Setup

```bash
# 1. Navigate to the scripts directory
cd scripts/

# 2. Install dependencies
pip install -r requirements.txt

# 3. Check what the current configuration would do (dry run)
./sync-suse-versions.sh --dry-run --verbose

# Example output:
# [INFO] Starting SUSE Application Collection synchronization...
# [INFO] Working directory: /Users/user/ai-demos
# [WARNING] DRY RUN MODE - No changes will be made
# [INFO] Checking prerequisites...
# [INFO] Found Helm: v3.12.0
# [INFO] Found Python: Python 3.11.5
# ✅ SUCCESS - ollama -> ai-compare-suse
#   Changes would be made:
#     • Updated ollama.image.tag: 0.11.3 -> 0.11.4
```

### Example 2: Apply Updates

```bash
# After reviewing dry run results, apply the changes
./sync-suse-versions.sh --verbose

# Example output:
# [INFO] Starting SUSE Application Collection synchronization...
# [SUCCESS] SYNCHRONIZATION COMPLETED SUCCESSFULLY
# [INFO] Changes have been applied to the target charts
# [INFO] Report files generated:
#   - suse-sync.log
#   - sync-summary-20240115-143025.txt
```

## AI Demos Project Examples

### Example 3: Sync AI Demos Charts

```bash
# Use the ai-demos specific configuration
./sync-suse-versions.sh --config ai-demos-sync-config.yaml --dry-run

# Expected output showing all ai-compare charts:
# Processing chart sync: ollama
# Processing chart sync: open-webui
#
# SUMMARY:
#   Total charts processed: 6
#   - charts/ai-compare-suse (ollama, open-webui)
#   - charts/ai-compare-opentelemetry (ollama, open-webui)
#   - charts/ai-compare (ollama, open-webui with upstream transform)
```

### Example 4: Check Current Versions

```bash
# Quick check of current versions in ai-demos charts
grep -r "tag:" charts/*/values.yaml | grep -E "(ollama|open-webui)"

# Example output:
# charts/ai-compare-suse/values.yaml:    tag: "0.11.4"
# charts/ai-compare-suse/values.yaml:    tag: "0.6.18"
# charts/ai-compare-opentelemetry/values.yaml:    tag: "0.11.4"
# charts/ai-compare-opentelemetry/values.yaml:    tag: "0.6.18"
# charts/ai-compare/values.yaml:    tag: "0.11.4"
# charts/ai-compare/values.yaml:    tag: "0.6.18"
```

### Example 5: Verify Registry Transformations

```bash
# Check that registry paths are correctly transformed
./sync-suse-versions.sh --config ai-demos-sync-config.yaml --dry-run --verbose 2>&1 | grep -E "(repository|registry)"

# Expected output showing transformations:
# DEBUG: Source repository: dp.apps.rancher.io/containers/ollama
# DEBUG: Target repository (SUSE charts): dp.apps.rancher.io/containers/ollama
# DEBUG: Target repository (upstream): ollama/ollama (transformed)
```

## Configuration Examples

### Example 6: Custom Project Configuration

Create a configuration for a different project:

```yaml
# my-project-sync.yaml
global:
  registry_transforms:
    suse_to_upstream:
      "dp.apps.rancher.io/containers/postgresql": "postgres"
      "dp.apps.rancher.io/containers/redis": "redis"

chart_syncs:
  - name: "postgresql"
    source_chart: "oci://dp.apps.rancher.io/charts/postgresql"
    target_charts:
      - "charts/my-app-suse"
      - "charts/my-app-upstream"
    image_mappings:
      - source_path: "image"
        target_path: "postgresql.image"
        registry_transform: null
      - source_path: "image"
        target_path: "postgresql.image"
        registry_transform: "suse_to_upstream"
```

### Example 7: Single Chart Update

```yaml
# single-chart-sync.yaml - Update only one chart
chart_syncs:
  - name: "ollama-only"
    source_chart: "oci://dp.apps.rancher.io/charts/ollama"
    target_charts:
      - "charts/ai-compare-suse"
    image_mappings:
      - source_path: "image"
        target_path: "ollama.image"
        registry_transform: null
```

```bash
# Use the single chart configuration
./sync-suse-versions.sh --config single-chart-sync.yaml --dry-run
```

## Troubleshooting Examples

### Example 8: Debug Registry Access Issues

```bash
# Test registry access manually
helm registry login dp.apps.rancher.io
helm show chart oci://dp.apps.rancher.io/charts/ollama

# Run sync with verbose logging
./sync-suse-versions.sh --verbose --dry-run 2>&1 | tee debug.log

# Check for specific errors
grep -i error debug.log
grep -i "registry\|login\|auth" debug.log
```

### Example 9: Validate Helm Charts After Update

```bash
# After running sync, validate the updated charts
cd charts/ai-compare-suse
helm template . --dry-run

cd ../ai-compare-opentelemetry
helm template . --dry-run

cd ../ai-compare
helm template . --dry-run
```

### Example 10: Manual Image Version Check

```bash
# Manually check what versions are available in SUSE Application Collection
helm pull oci://dp.apps.rancher.io/charts/ollama --untar --untardir /tmp/
cat /tmp/ollama/values.yaml | grep -A 3 -B 3 image

# Compare with current chart values
cat charts/ai-compare-suse/values.yaml | grep -A 3 -B 3 "ollama:" | grep -A 3 image
```

## CI/CD Integration Examples

### Example 11: GitHub Actions Manual Trigger

```bash
# Trigger via GitHub CLI
gh workflow run sync-suse-versions.yml \
  -f config_file=ai-demos-sync-config.yaml \
  -f dry_run=true \
  -f verbose=true

# Check workflow status
gh run list --workflow=sync-suse-versions.yml --limit=5
```

### Example 12: Local CI/CD Simulation

```bash
# Simulate CI/CD pipeline locally
export CI=true

# Run as CI would (with error handling)
if ./sync-suse-versions.sh --config ai-demos-sync-config.yaml --dry-run; then
  echo "✅ CI: Dry run passed"

  if ./sync-suse-versions.sh --config ai-demos-sync-config.yaml; then
    echo "✅ CI: Sync completed"

    # Check for changes (like CI would)
    if git diff --quiet; then
      echo "ℹ️ CI: No changes to commit"
    else
      echo "📝 CI: Changes detected - would create PR"
      git diff --stat
    fi
  else
    echo "❌ CI: Sync failed"
    exit 1
  fi
else
  echo "❌ CI: Dry run failed"
  exit 1
fi
```

### Example 13: Pre-commit Hook Integration

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit hook to ensure SUSE versions are current

cd scripts/

echo "🔍 Checking SUSE Application Collection versions..."

if ./sync-suse-versions.sh --config ai-demos-sync-config.yaml --dry-run --quiet; then
  echo "✅ SUSE versions are current"
else
  echo "⚠️ SUSE versions may need updating"
  echo "Run: cd scripts && ./sync-suse-versions.sh --config ai-demos-sync-config.yaml"
  # Don't fail the commit, just warn
fi
```

## Advanced Examples

### Example 14: Batch Processing Multiple Configs

```bash
# Process multiple configurations in sequence
configs=("ai-demos-sync-config.yaml" "suse-sync-config.yaml")

for config in "${configs[@]}"; do
  echo "Processing $config..."
  if ./sync-suse-versions.sh --config "$config" --dry-run; then
    echo "✅ $config: Ready for sync"
  else
    echo "❌ $config: Issues detected"
  fi
done
```

### Example 15: Version History Tracking

```bash
# Track version changes over time
mkdir -p version-history
date=$(date +%Y%m%d)

# Extract current versions
{
  echo "# Version snapshot: $(date)"
  echo "## AI Compare SUSE"
  grep -E "tag:" charts/ai-compare-suse/values.yaml
  echo "## AI Compare OpenTelemetry"
  grep -E "tag:" charts/ai-compare-opentelemetry/values.yaml
  echo "## AI Compare Upstream"
  grep -E "tag:" charts/ai-compare/values.yaml
} > "version-history/versions-$date.md"

# Run sync and capture new versions
./sync-suse-versions.sh --config ai-demos-sync-config.yaml

# Show differences
if [[ -f "version-history/versions-$date.md" ]]; then
  echo "Version changes:"
  diff "version-history/versions-$date.md" <(
    echo "# Version snapshot: $(date) - AFTER SYNC"
    grep -E "tag:" charts/*/values.yaml
  ) || true
fi
```

### Example 16: Integration with Package Managers

```bash
# Integration with package managers (for dependencies)

# Using Poetry
if [[ -f pyproject.toml ]]; then
  poetry install
  poetry run python suse-app-collection-sync.py --config ai-demos-sync-config.yaml --dry-run
fi

# Using pipenv
if [[ -f Pipfile ]]; then
  pipenv install
  pipenv run python suse-app-collection-sync.py --config ai-demos-sync-config.yaml --dry-run
fi

# Using conda
if [[ -f environment.yml ]]; then
  conda env update -f environment.yml
  conda run python suse-app-collection-sync.py --config ai-demos-sync-config.yaml --dry-run
fi
```

## Real-World Scenarios

### Scenario 1: Weekly Maintenance Window

```bash
#!/bin/bash
# weekly-suse-maintenance.sh

echo "🕒 Starting weekly SUSE Application Collection maintenance..."

# 1. Backup current state
git add .
git commit -m "backup: before SUSE sync $(date)" || true

# 2. Run synchronization
cd scripts/
if ./sync-suse-versions.sh --config ai-demos-sync-config.yaml; then
  echo "✅ Synchronization completed"

  # 3. Run tests (if available)
  if [[ -f ../run-tests.sh ]]; then
    echo "🧪 Running tests..."
    ../run-tests.sh
  fi

  # 4. Create commit
  git add ..
  git commit -m "chore: weekly SUSE Application Collection sync $(date)"

  echo "📝 Maintenance completed successfully"
else
  echo "❌ Synchronization failed - rolling back"
  git reset --hard HEAD~1
  exit 1
fi
```

### Scenario 2: Emergency Version Update

```bash
#!/bin/bash
# emergency-update.sh - Quick update for security patches

# Override normal schedule for urgent updates
./sync-suse-versions.sh --config ai-demos-sync-config.yaml --verbose

if [[ $? -eq 0 ]]; then
  # Fast-track the changes
  git add charts/
  git commit -m "security: emergency SUSE version update"

  # Deploy immediately (example)
  helm upgrade ai-compare-prod charts/ai-compare-suse/ --wait

  echo "🚨 Emergency update deployed"
else
  echo "❌ Emergency update failed"
  exit 1
fi
```

### Scenario 3: Multi-Environment Sync

```bash
#!/bin/bash
# multi-env-sync.sh - Sync across development, staging, production

environments=("dev" "staging" "prod")

for env in "${environments[@]}"; do
  echo "🔄 Syncing $env environment..."

  # Use environment-specific config
  config="configs/${env}-sync-config.yaml"

  if [[ -f "$config" ]]; then
    ./sync-suse-versions.sh --config "$config" --dry-run

    read -p "Apply changes to $env? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
      ./sync-suse-versions.sh --config "$config"
      echo "✅ $env updated"
    else
      echo "⏭️ Skipping $env"
    fi
  else
    echo "⚠️ Config not found: $config"
  fi
done
```

These examples demonstrate the flexibility and power of the SUSE Application Collection synchronization agent for various use cases and environments.
