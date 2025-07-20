# Chart Version Management

This document describes how to manage versions for the AI Compare Helm charts to ensure the upstream and SUSE variants remain synchronized.

## Overview

The AI Compare project maintains two Helm chart variants:
- **ai-compare**: Upstream variant using standard container images
- **ai-compare-suse**: SUSE variant using SUSE BCI (Base Container Images)

Both charts must maintain **identical version numbers** to ensure consistency across deployments.

## Version Synchronization

### Automated Checks

1. **CI/CD Pipeline**: Every commit automatically checks version synchronization
2. **Pre-commit Hook**: Optional local check before commits (see setup below)
3. **Script Validation**: Manual verification available

### Manual Version Management

Use the version synchronization script for all version operations:

```bash
# Check if versions are synchronized
./scripts/sync-chart-versions.sh --check

# Sync SUSE chart to upstream version
./scripts/sync-chart-versions.sh --sync-to-upstream

# Sync upstream chart to SUSE version  
./scripts/sync-chart-versions.sh --sync-to-suse

# Bump patch version on both charts (0.1.142 → 0.1.143)
./scripts/sync-chart-versions.sh --bump-patch

# Bump minor version on both charts (0.1.142 → 0.2.0)
./scripts/sync-chart-versions.sh --bump-minor

# Set specific chart version on both
./scripts/sync-chart-versions.sh --set-version 0.2.0

# Set specific app version on both
./scripts/sync-chart-versions.sh --set-app-version 1.1.0
```

## Version Types

### Chart Version (`version`)
- Helm chart packaging version
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Increment when chart templates or configuration change
- Must be identical across both variants

### App Version (`appVersion`)
- Application/container image version being deployed
- References the actual AI Compare application version
- Must be identical across both variants

## Development Workflow

### When Making Chart Changes

1. **Make your changes** to chart templates or values
2. **Decide version bump type**:
   - **Patch** (`0.1.142` → `0.1.143`): Bug fixes, small improvements
   - **Minor** (`0.1.142` → `0.2.0`): New features, significant changes
   - **Major** (`0.1.142` → `1.0.0`): Breaking changes

3. **Update versions** using the script:
   ```bash
   # For patch updates
   ./scripts/sync-chart-versions.sh --bump-patch
   
   # For minor updates
   ./scripts/sync-chart-versions.sh --bump-minor
   ```

4. **Commit changes**:
   ```bash
   git add charts/*/Chart.yaml
   git commit -m "Bump chart version to 0.1.143"
   ```

### When Adding New Features

1. Implement features in both chart variants
2. Bump minor version if significant, patch if minor
3. Update app version if container images change
4. Commit all changes together

## Setup Pre-commit Hook (Optional)

To automatically check version sync before every commit:

```bash
# Install the pre-commit hook
ln -s ../../scripts/pre-commit-version-check.sh .git/hooks/pre-commit

# Make it executable
chmod +x .git/hooks/pre-commit
```

The hook will:
- Check if Chart.yaml files are being committed
- Verify version synchronization
- Block commits if versions don't match
- Provide fix instructions

## CI/CD Integration

The version check is integrated into the Helm test pipeline:

1. **Version Check Job**: First job validates synchronization
2. **Helm Lint**: Only runs after version check passes
3. **Integration Tests**: Full test suite with version validation

## Troubleshooting

### "Versions are not synchronized" Error

If you see this error:

1. **Check current versions**:
   ```bash
   ./scripts/sync-chart-versions.sh --check
   ```

2. **Choose sync direction**:
   ```bash
   # If upstream is correct
   ./scripts/sync-chart-versions.sh --sync-to-upstream
   
   # If SUSE is correct  
   ./scripts/sync-chart-versions.sh --sync-to-suse
   ```

3. **Commit the sync**:
   ```bash
   git add charts/*/Chart.yaml
   git commit -m "Synchronize chart versions"
   ```

### CI Pipeline Failing

If the CI pipeline fails on version check:

1. Pull latest changes: `git pull`
2. Run version sync locally: `./scripts/sync-chart-versions.sh --check`
3. Fix any mismatches and push

## Best Practices

1. **Always use the sync script** - Never manually edit version numbers
2. **Coordinate with team** - Communicate version changes in PRs
3. **Test both variants** - Ensure changes work in upstream and SUSE charts
4. **Document breaking changes** - Update this file for major version bumps
5. **Use semantic versioning** - Follow semver.org guidelines

## Version History

- `0.1.142`: Current synchronized version
- `0.1.141`: Added NeuVector integration 
- `0.1.140`: Initial chart version synchronization