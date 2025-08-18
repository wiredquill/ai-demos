# Ollama Wrapper Charts

This repository provides two wrapper charts for Ollama deployment with comprehensive `questions.yaml` interfaces for easy configuration through Rancher UI and other Helm UI tools.

## Overview

We've created wrapper charts for both upstream community and enterprise SUSE Application Collection versions of Ollama:

### 1. Ollama Upstream (`ollama-upstream`)
- **Base Chart**: Community `otwld/ollama-helm`
- **Repository**: `https://helm.otwld.com/`
- **Image**: `ollama/ollama` (Docker Hub)
- **Focus**: Community features, standard configurations

### 2. Ollama SUSE (`ollama-suse`)
- **Base Chart**: SUSE Application Collection Ollama
- **Repository**: `oci://dp.apps.rancher.io/charts`
- **Image**: `registry.suse.com/bci/ollama` (SUSE BCI)
- **Focus**: Enterprise features, security hardening, compliance

## Quick Start

### Repository Setup

```bash
# Add this repository (replace with your actual repo URL)
helm repo add ai-demos https://your-repo.example.com/charts
helm repo update
```

### Basic Installations

#### Upstream Community Version
```bash
helm install my-ollama ai-demos/ollama-upstream \
  --namespace ollama \
  --create-namespace
```

#### SUSE Enterprise Version
```bash
# First, authenticate with SUSE Application Collection
helm registry login dp.apps.rancher.io/charts \
  -u <your_email> \
  -p <your_application_collection_token>

# Install enterprise version
helm install my-ollama ai-demos/ollama-suse \
  --namespace suse-ai \
  --create-namespace
```

## Configuration Comparison

| Feature | Upstream | SUSE Enterprise |
|---------|----------|-----------------|
| **Base Resources** | 2Gi RAM, 1 CPU | 4Gi RAM, 2 CPU |
| **Storage Default** | 50Gi | 100Gi |
| **Storage Class** | Default | `suse-csi` |
| **Security** | Basic | Hardened (SELinux, Pod Security) |
| **Monitoring** | Optional | Enabled by default |
| **Compliance** | None | Built-in SUSE compliance |
| **Support** | Community | Enterprise SUSE support |

## Questions.yaml Features

Both charts include comprehensive UI configuration through `questions.yaml`:

### Common Configuration Groups

#### Service Configuration
- Service type (ClusterIP, NodePort, LoadBalancer)
- Port configuration

#### Resource Configuration
- CPU/Memory requests and limits
- Enterprise vs community sizing defaults

#### GPU Configuration
- GPU enable/disable toggle
- GPU vendor selection
- GPU count (1-8 upstream, 1-16 SUSE)

#### Storage Configuration
- Persistence enable/disable
- Storage size configuration
- Storage class selection
- Backup configuration (SUSE only)

#### Model Configuration
- Auto-download model lists
- Model pull policies
- Model registry configuration (SUSE)
- Model validation (SUSE only)

#### Networking
- Ingress configuration
- Hostname and TLS settings
- Certificate manager selection (SUSE)

#### Security
- Non-root execution
- Read-only filesystem
- SELinux enforcement (SUSE only)
- Pod Security Standards (SUSE only)
- Network policies (SUSE only)

#### Observability
- Monitoring enable/disable
- Log level configuration
- Audit logging (SUSE only)
- Structured logging (SUSE only)

### SUSE-Specific Features

#### Enterprise Configuration
- Authentication requirements
- Compliance feature toggles
- Support level selection (community/enterprise/premium)

#### Advanced Security
- Seccomp profile selection
- SELinux enforcement
- Network policy isolation
- Pod Security Standards enforcement

#### Data Protection
- Automated backup scheduling
- Backup retention policies
- Disaster recovery configuration

#### SUSE Integration
- System registry for air-gapped environments
- SUSE Observability platform integration
- Enterprise dashboard templates
- SUSE-certified GPU drivers

## Advanced Configurations

### GPU-Enabled Deployment

#### Upstream with NVIDIA GPU
```bash
helm install gpu-ollama ai-demos/ollama-upstream \
  --set ollama.gpu.enabled=true \
  --set ollama.gpu.type=nvidia \
  --set ollama.gpu.number=2 \
  --set ollama.resources.limits.memory=16Gi
```

#### SUSE Enterprise with GPU
```bash
helm install gpu-ollama ai-demos/ollama-suse \
  --set ollama.gpu.enabled=true \
  --set ollama.gpu.vendor=nvidia \
  --set ollama.gpu.resources.limits=2 \
  --set ollama.resources.limits.memory=32Gi
```

### High-Availability Enterprise Deployment
```bash
helm install ha-ollama ai-demos/ollama-suse \
  --set ollama.compliance.enabled=true \
  --set ollama.security.selinux.enabled=true \
  --set ollama.monitoring.enabled=true \
  --set ollama.backup.enabled=true \
  --set ollama.backup.schedule="0 2 * * *" \
  --set ollama.persistence.size=500Gi \
  --set ollama.networkPolicy.enabled=true
```

### Air-Gapped SUSE Deployment
```bash
helm install airgap-ollama ai-demos/ollama-suse \
  --set global.cattle.systemDefaultRegistry=internal-registry.company.com \
  --set ollama.models.registry.url=internal-registry.company.com/suse-models \
  --set ollama.models.registry.auth.enabled=true \
  --set ollama.image.repository=internal-registry.company.com/suse/ollama
```

## Model Management

### Auto-Download Models

#### Upstream
```yaml
ollama:
  models:
    autoDownload:
      - "tinyllama:latest"
      - "llama2:7b"
      - "codellama:latest"
```

#### SUSE Enterprise
```yaml
ollama:
  models:
    registry:
      url: "registry.suse.com"
      auth:
        enabled: true
    autoDownload:
      - "enterprise-llama:latest"
      - "suse-codegen:latest"
    validation:
      enabled: true
```

## Monitoring and Observability

### Upstream Monitoring
```bash
helm install monitored-ollama ai-demos/ollama-upstream \
  --set ollama.monitoring.enabled=true \
  --set ollama.monitoring.serviceMonitor.enabled=true \
  --set ollama.logging.level=debug
```

### SUSE Enterprise Observability
```bash
helm install observed-ollama ai-demos/ollama-suse \
  --set ollama.monitoring.enabled=true \
  --set ollama.monitoring.prometheus.enabled=true \
  --set ollama.monitoring.grafana.dashboard=true \
  --set ollama.monitoring.alerts.enabled=true \
  --set ollama.logging.format=json \
  --set ollama.logging.audit.enabled=true
```

## Troubleshooting

### Dependency Issues
```bash
# Update chart dependencies
helm dependency update charts/ollama-upstream
helm dependency update charts/ollama-suse

# Check dependency status
helm dependency list charts/ollama-upstream
```

### SUSE Registry Authentication
```bash
# Test registry access
helm registry login dp.apps.rancher.io/charts

# Pull chart manually
helm pull oci://dp.apps.rancher.io/charts/ollama --version 1.16.0
```

### Values Validation
```bash
# Dry-run with debug
helm install test-ollama ai-demos/ollama-upstream --dry-run --debug

# Validate specific values
helm template test-ollama ai-demos/ollama-suse \
  --set ollama.gpu.enabled=true \
  --debug
```

## Chart Development

### Adding New Questions
1. Edit `questions.yaml` in the appropriate chart directory
2. Follow the existing group structure
3. Use conditional `show_if` for dependent fields
4. Test with Rancher UI or equivalent

### Updating Dependencies
```bash
# Update to newer upstream versions
# Edit Chart.yaml dependency version
helm dependency update charts/ollama-upstream

# Repackage
helm package charts/ollama-upstream
```

### Testing Changes
```bash
# Lint charts
helm lint charts/ollama-upstream
helm lint charts/ollama-suse

# Template validation
helm template test charts/ollama-upstream
helm template test charts/ollama-suse

# Dry-run installation
helm install test ./ollama-upstream-0.1.0.tgz --dry-run
```

## Support

### Community Support (Upstream)
- [Ollama Community](https://github.com/ollama/ollama)
- [Upstream Helm Chart](https://github.com/otwld/ollama-helm)

### Enterprise Support (SUSE)
- SUSE Support Portal
- [SUSE Application Collection Documentation](https://docs.apps.rancher.io/)
- Your assigned SUSE support representative

### Wrapper Chart Issues
File issues in this repository for problems specific to our wrapper charts and `questions.yaml` configurations.
