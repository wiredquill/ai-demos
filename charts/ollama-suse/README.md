# Ollama SUSE Application Collection Wrapper Chart

This is a wrapper chart for the SUSE Application Collection Ollama Helm chart with enterprise-focused configuration options via `questions.yaml`.

## Overview

This chart wraps the enterprise Ollama chart from SUSE Application Collection and adds a comprehensive `questions.yaml` interface optimized for enterprise deployments with enhanced security, compliance, and observability features.

## Repository Information

- **Upstream Chart**: `ollama` from `oci://dp.apps.rancher.io/charts`
- **Chart Version**: ^1.0.0
- **Image**: `registry.suse.com/bci/ollama` (SUSE BCI)
- **Support**: Enterprise support available through SUSE

## Prerequisites

### Authentication

Before installation, authenticate with the SUSE Application Collection registry:

```bash
# Obtain your Application Collection token from SUSE
helm registry login dp.apps.rancher.io/charts \
  -u <your_email> \
  -p <your_application_collection_token>
```

### SUSE AI Namespace

Create a dedicated namespace for SUSE AI workloads:

```bash
kubectl create namespace suse-ai
kubectl label namespace suse-ai suse.com/ai=enabled
```

## Installation

### Add Repository

```bash
# Add this repository
helm repo add ai-demos https://your-repo.example.com/charts

# Update repositories
helm repo update
```

### Install Chart

```bash
# Basic enterprise installation
helm install my-ollama ai-demos/ollama-suse \
  --namespace suse-ai \
  --create-namespace

# Enterprise installation with GPU and monitoring
helm install my-ollama ai-demos/ollama-suse \
  --namespace suse-ai \
  --create-namespace \
  --set ollama.gpu.enabled=true \
  --set ollama.monitoring.enabled=true \
  --set ollama.security.selinux.enabled=true
```

### Air-Gapped Installation

For air-gapped environments, configure the system registry:

```bash
helm install my-ollama ai-demos/ollama-suse \
  --namespace suse-ai \
  --set global.cattle.systemDefaultRegistry=your-registry.com \
  --set ollama.models.registry.url=your-registry.com/suse-models
```

## Enterprise Features

### SUSE Configuration
- **Authentication**: Enterprise authentication integration
- **Compliance**: SUSE compliance features enabled by default
- **Support Levels**: Community, Enterprise, Premium support tiers

### Enhanced Security
- **SELinux**: Enabled by default for SUSE security
- **Pod Security Standards**: Restricted profile enforced
- **Network Policies**: Traffic isolation enabled
- **Read-only Root FS**: Hardened container configuration
- **Seccomp Profiles**: Runtime security enforcement

### Enterprise Resource Sizing
- **Memory**: 4Gi request, 16Gi limit (enterprise defaults)
- **CPU**: 2000m request, 8000m limit (enterprise defaults)
- **Storage**: 100Gi default with SUSE CSI storage class

### SUSE Observability Integration
- **Prometheus**: Enterprise metrics collection
- **Grafana**: SUSE dashboard templates
- **Alerting**: Enterprise alerting rules
- **Audit Logging**: Compliance audit trails
- **Structured Logging**: JSON format for log aggregation

### Data Protection
- **Automated Backup**: Integration with SUSE backup tools
- **Retention Policies**: Configurable backup retention
- **Model Validation**: Cryptographic signature verification

## Configuration Groups

### SUSE Configuration
- System registry for air-gapped environments
- Authentication and compliance settings
- Support level configuration

### Security (Enhanced)
- SELinux enforcement
- Pod Security Standards
- Network policies
- Seccomp profiles
- Read-only filesystem

### GPU Configuration (SUSE Certified)
- SUSE-certified GPU vendors
- Driver version management
- Enterprise GPU allocation (up to 16 GPUs)

### Storage (Enterprise)
- SUSE CSI storage class integration
- Automated backup configuration
- Enterprise storage sizing

### Model Management
- SUSE model registry integration
- Model signature validation
- Enterprise model auto-download

### Observability (SUSE Integrated)
- SUSE Observability platform integration
- Enterprise dashboard templates
- Compliance audit logging
- Structured logging with JSON format

### Data Protection
- Automated backup scheduling
- Backup retention policies
- Disaster recovery configuration

## Air-Gapped Deployment

For air-gapped environments, this chart supports:

1. **System Registry Override**:
   ```yaml
   global:
     cattle:
       systemDefaultRegistry: "your-internal-registry.com"
   ```

2. **Model Registry Configuration**:
   ```yaml
   ollama:
     models:
       registry:
         url: "your-internal-registry.com/suse-models"
         auth:
           enabled: true
   ```

3. **Image Override**:
   ```yaml
   ollama:
     image:
       repository: "your-internal-registry.com/suse/ollama"
   ```

## Dependencies

This chart uses OCI-based dependencies from SUSE Application Collection:

```yaml
dependencies:
  - name: ollama
    version: "^1.0.0"
    repository: "oci://dp.apps.rancher.io/charts"
```

## Updating Dependencies

```bash
# Update chart dependencies (requires authentication)
helm dependency update charts/ollama-suse

# List dependencies
helm dependency list charts/ollama-suse
```

## Enterprise Support

This chart provides enterprise-grade Ollama deployment with:

- **SUSE Support**: Enterprise support through SUSE channels
- **Security Hardening**: SUSE security best practices
- **Compliance**: Built-in compliance features
- **Observability**: Integration with SUSE Observability platform
- **Performance**: Enterprise-optimized resource configurations

## Values

All values are passed through to the SUSE Application Collection `ollama` chart under the `ollama` key. Enterprise defaults are pre-configured for production deployments.

## Support

For enterprise support and issues:
- **SUSE Support**: Contact your SUSE support representative
- **Application Collection**: [SUSE Application Collection Documentation](https://docs.apps.rancher.io/)
- **Wrapper Chart Issues**: File issues in this repository

For community support:
- [SUSE Community](https://www.suse.com/communities/)
- [Rancher Community](https://rancher.com/community)
