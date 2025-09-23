# SUSE Application Collection Synchronization Agent

A comprehensive automation tool for synchronizing container versions between SUSE Application Collection charts and local application Helm charts. This agent helps maintain consistency across SUSE Enterprise and upstream variants of your applications.

## Overview

This synchronization agent automatically:

1. **Pulls latest versions** of specified Helm charts from SUSE Application Collection (`oci://dp.apps.rancher.io/charts/`)
2. **Extracts container image versions** from the pulled charts
3. **Updates multiple target Helm charts** (like ai-compare-suse, ai-compare-opentelemetry) with the latest SUSE versions
4. **Updates upstream charts** to mirror the SUSE versions for consistency
5. **Generates comprehensive summary reports** of all changes made

## Features

- ✅ **Flexible Configuration**: YAML-based configuration for defining source/target mappings
- ✅ **Registry Transformation**: Automatic conversion between SUSE and upstream registry paths
- ✅ **Dry Run Mode**: Preview changes without making modifications
- ✅ **Comprehensive Reporting**: Detailed reports with before/after comparisons
- ✅ **Error Handling**: Robust error handling with detailed logging
- ✅ **Backup Support**: Automatic backup of modified files
- ✅ **Multiple Chart Support**: Update multiple target charts from single source
- ✅ **Validation**: Helm template validation and accessibility checks

## Quick Start

### Prerequisites

- **Helm 3.x** installed and accessible in PATH
- **Python 3.7+** with pip
- **Access to SUSE Application Collection** registry
- **Write permissions** to target chart directories

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x sync-suse-versions.sh
   ```

### Basic Usage

1. **Dry run to see what would be changed:**
   ```bash
   ./sync-suse-versions.sh --dry-run
   ```

2. **Apply changes:**
   ```bash
   ./sync-suse-versions.sh
   ```

3. **Verbose output with custom config:**
   ```bash
   ./sync-suse-versions.sh --verbose --config ai-demos-sync-config.yaml
   ```

## Configuration

### Default Configuration Files

- **`suse-sync-config.yaml`**: Generic configuration template
- **`ai-demos-sync-config.yaml`**: Specific configuration for ai-demos project

### Configuration Structure

```yaml
# Global settings
global:
  registry_transforms:
    suse_to_upstream:
      "dp.apps.rancher.io/containers/ollama": "ollama/ollama"
      "dp.apps.rancher.io/containers/open-webui": "ghcr.io/open-webui/open-webui"

# Chart synchronization definitions
chart_syncs:
  - name: "ollama"
    source_chart: "oci://dp.apps.rancher.io/charts/ollama"
    target_charts:
      - "charts/ai-compare-suse"
      - "charts/ai-compare-opentelemetry"
      - "charts/ai-compare"
    image_mappings:
      - source_path: "image"
        target_path: "ollama.image"
        registry_transform: null  # Keep SUSE registry
      - source_path: "image"
        target_path: "ollama.image"
        registry_transform: "suse_to_upstream"  # Transform for upstream
```

### Image Mapping Configuration

Image mappings define how to extract and apply image versions:

- **`source_path`**: Path in source chart values (e.g., `"image"` or `"ollama.image"`)
- **`target_path`**: Path in target chart values (e.g., `"ollama.image"`)
- **`registry_transform`**: How to transform registry paths (`null`, `"suse_to_upstream"`, `"upstream_to_suse"`)

### Registry Transformations

The agent automatically handles registry path transformations:

| SUSE Registry | Upstream Equivalent |
|---------------|-------------------|
| `dp.apps.rancher.io/containers/ollama` | `ollama/ollama` |
| `dp.apps.rancher.io/containers/open-webui` | `ghcr.io/open-webui/open-webui` |
| `dp.apps.rancher.io/containers/open-webui-pipelines` | `ghcr.io/open-webui/pipelines` |

## Usage Examples

### 1. Basic Synchronization

```bash
# Quick dry run check
./sync-suse-versions.sh --dry-run

# Apply updates
./sync-suse-versions.sh
```

### 2. AI Demos Project Synchronization

```bash
# Use ai-demos specific configuration
./sync-suse-versions.sh --config ai-demos-sync-config.yaml --dry-run

# Apply with verbose logging
./sync-suse-versions.sh --config ai-demos-sync-config.yaml --verbose
```

### 3. Custom Configuration

```bash
# Create your own config file
cp suse-sync-config.yaml my-project-sync.yaml
# Edit my-project-sync.yaml for your project

# Run with custom config
./sync-suse-versions.sh --config my-project-sync.yaml --dry-run
```

### 4. Python Script Direct Usage

```bash
# Direct Python execution with options
python3 suse-app-collection-sync.py --config ai-demos-sync-config.yaml --dry-run --verbose

# Save output to file
python3 suse-app-collection-sync.py --config ai-demos-sync-config.yaml --dry-run > sync-preview.txt
```

## Output and Reporting

### Console Output

The agent provides colored console output showing:

- ✅ **Successful updates** with version changes
- ⚠️ **Warnings** for potential issues
- ❌ **Errors** with detailed explanations
- ℹ️ **Information** about operations

### Generated Files

- **`suse-sync.log`**: Detailed log file with all operations
- **`sync-summary-YYYYMMDD-HHMMSS.txt`**: Human-readable summary report
- **`*.backup-YYYYMMDD-HHMMSS`**: Backup files of modified charts

### Sample Report Output

```
================================================================================
SUSE Application Collection Synchronization Report
================================================================================
Generated: 2024-01-15 14:30:25
Mode: LIVE UPDATE

SUMMARY:
  Total charts processed: 6
  Successful updates: 4
  No changes needed: 2
  Failed updates: 0

DETAILED RESULTS:
--------------------------------------------------

✅ SUCCESS - ollama -> ai-compare-suse
  Changes made:
    • Updated ollama.image.tag: 0.11.3 -> 0.11.4

✅ SUCCESS - ollama -> ai-compare-opentelemetry
  Changes made:
    • Updated ollama.image.tag: 0.11.3 -> 0.11.4

VERSION SUMMARY:
------------------------------
  ollama.image: dp.apps.rancher.io/containers/ollama:0.11.4
  openWebui.image: dp.apps.rancher.io/containers/open-webui:0.6.18
```

## Advanced Configuration

### Chart-Specific Overrides

```yaml
chart_configurations:
  "charts/ai-compare-suse":
    preserve_suse_registry: true
    update_chart_version: true
    version_increment: "patch"
    additional_annotations:
      "suse.com/last-sync": "${timestamp}"

  "charts/ai-compare":
    force_upstream_registry: true
    registry_overrides:
      "ollama.image.repository": "ollama/ollama"
```

### Validation Settings

```yaml
validation:
  helm_template_check: true
  image_accessibility_check: false
  semver_validation: true
  required_values:
    - "ollama.image.repository"
    - "ollama.image.tag"
```

### Notification Integration

```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#ai-ops"
    mention_on_failure: true

  email:
    enabled: true
    recipients: ["team@example.com"]
```

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/sync-suse-versions.yml`:

```yaml
name: Sync SUSE Application Collection Versions

on:
  schedule:
    - cron: '0 9 * * 1'  # Monday 9 AM
  workflow_dispatch:

jobs:
  sync-versions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install Helm
        uses: azure/setup-helm@v3

      - name: Install dependencies
        run: pip install -r scripts/requirements.txt

      - name: Run synchronization
        run: |
          cd scripts
          ./sync-suse-versions.sh --config ai-demos-sync-config.yaml

      - name: Create Pull Request
        if: success()
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: sync SUSE Application Collection versions"
          body: "Automated update of container versions from SUSE Application Collection"
          branch: "sync/suse-versions"
```

### GitLab CI

Add to `.gitlab-ci.yml`:

```yaml
sync-suse-versions:
  stage: maintenance
  image: python:3.9
  before_script:
    - curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar -xz
    - mv linux-amd64/helm /usr/local/bin/
    - pip install -r scripts/requirements.txt
  script:
    - cd scripts
    - ./sync-suse-versions.sh --config ai-demos-sync-config.yaml
  rules:
    - if: $CI_PIPELINE_SOURCE == "schedule"
    - if: $CI_PIPELINE_SOURCE == "web"
  artifacts:
    reports:
      - reports/sync-reports/*.json
    paths:
      - "*.backup-*"
      - "sync-summary-*.txt"
```

## Troubleshooting

### Common Issues

1. **Helm not found:**
   ```bash
   # Install Helm
   curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar -xz
   sudo mv linux-amd64/helm /usr/local/bin/
   ```

2. **Python dependencies missing:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Registry access denied:**
   ```bash
   # Login to SUSE registry
   helm registry login dp.apps.rancher.io
   ```

4. **Chart not found:**
   ```bash
   # Verify chart exists
   helm show chart oci://dp.apps.rancher.io/charts/ollama
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Verbose output with debug information
./sync-suse-versions.sh --verbose --dry-run

# Direct Python with debug
python3 suse-app-collection-sync.py --verbose --dry-run
```

### Manual Chart Inspection

```bash
# Manually pull and inspect a chart
helm pull oci://dp.apps.rancher.io/charts/ollama --untar
cat ollama/values.yaml | grep -A 5 -B 5 image
```

## Customization for Other Projects

### 1. Create Project-Specific Configuration

```bash
cp suse-sync-config.yaml my-project-sync.yaml
```

### 2. Modify Chart Mappings

Edit `my-project-sync.yaml`:

```yaml
chart_syncs:
  - name: "my-app"
    source_chart: "oci://dp.apps.rancher.io/charts/some-chart"
    target_charts:
      - "charts/my-app-suse"
      - "charts/my-app-upstream"
    image_mappings:
      - source_path: "image"
        target_path: "myApp.image"
        registry_transform: null
```

### 3. Add New Registry Transformations

```yaml
global:
  registry_transforms:
    suse_to_upstream:
      "dp.apps.rancher.io/containers/my-app": "my-org/my-app"
    upstream_to_suse:
      "my-org/my-app": "dp.apps.rancher.io/containers/my-app"
```

### 4. Test Configuration

```bash
./sync-suse-versions.sh --config my-project-sync.yaml --dry-run --verbose
```

## Architecture

### Core Components

- **`suse-app-collection-sync.py`**: Main Python synchronization engine
- **`sync-suse-versions.sh`**: Bash wrapper with pre-flight checks
- **Configuration files**: YAML definitions for sync operations
- **`requirements.txt`**: Python dependencies

### Process Flow

1. **Load Configuration** → Parse YAML config and validate settings
2. **Pre-flight Checks** → Verify Helm, Python, and dependencies
3. **Pull Source Charts** → Download charts from SUSE Application Collection
4. **Extract Versions** → Parse values.yaml for image versions
5. **Transform Registries** → Apply registry path transformations
6. **Update Target Charts** → Modify target chart values.yaml files
7. **Validate Changes** → Run helm template validation
8. **Generate Reports** → Create summary and detailed reports

### Error Handling

- **Graceful Failures**: Continue processing other charts if one fails
- **Detailed Logging**: Comprehensive logs for debugging
- **Backup Creation**: Automatic backups before modifications
- **Rollback Support**: Easy restoration from backups

## Contributing

### Development Setup

```bash
# Clone and setup
git clone <repository>
cd scripts

# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pre-commit install
```

### Running Tests

```bash
# Run with dry-run to test functionality
./sync-suse-versions.sh --dry-run --verbose

# Test with different configurations
python3 suse-app-collection-sync.py --config test-config.yaml --dry-run
```

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings for functions
- Handle errors gracefully
- Log important operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review log files for error details
3. Test with `--dry-run --verbose` flags
4. Create an issue with configuration and error details

## Changelog

### v1.0.0
- Initial release with core synchronization functionality
- Support for SUSE Application Collection integration
- Registry transformation capabilities
- Comprehensive reporting and validation
- CI/CD integration examples
