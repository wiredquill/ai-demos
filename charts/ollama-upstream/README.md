# Ollama Upstream Wrapper Chart

This is a wrapper chart for the upstream community Ollama Helm chart with custom configuration options via `questions.yaml`.

## Overview

This chart wraps the popular [otwld/ollama-helm](https://github.com/otwld/ollama-helm) chart and adds a comprehensive `questions.yaml` interface for easy configuration through Rancher UI or other Helm UI tools.

## Repository Information

- **Upstream Chart**: `ollama` from `https://helm.otwld.com/`
- **Chart Version**: ^0.4.0
- **Image**: `ollama/ollama` (official Docker Hub image)

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
# Basic installation
helm install my-ollama ai-demos/ollama-upstream --namespace ollama --create-namespace

# With custom values
helm install my-ollama ai-demos/ollama-upstream \
  --namespace ollama \
  --create-namespace \
  --set ollama.gpu.enabled=true \
  --set ollama.persistence.size=100Gi
```

### Install with Questions (Rancher UI)

This chart includes a comprehensive `questions.yaml` that provides an intuitive UI in Rancher for configuring:

- **Service Configuration**: Service type, ports
- **Resource Configuration**: CPU/memory requests and limits
- **GPU Configuration**: GPU support, type, and count
- **Storage Configuration**: Persistence, size, storage class
- **Model Configuration**: Auto-download models, pull policies
- **Networking**: Ingress, hostname, TLS
- **Security**: Non-root execution, read-only filesystem
- **Observability**: Monitoring, logging levels

## Configuration Groups

### Service Configuration
- Service type (ClusterIP, NodePort, LoadBalancer)
- Port configuration

### Resource Configuration
- Memory: 2Gi request, 8Gi limit (default)
- CPU: 1000m request, 4000m limit (default)

### GPU Configuration
- GPU support toggle
- GPU type selection (nvidia, amd, intel)
- GPU count (1-8)

### Storage Configuration
- Persistent storage toggle
- Storage size (default: 50Gi)
- Storage class selection

### Model Configuration
- Auto-download model list
- Model pull policy

### Networking
- Ingress configuration
- Hostname and TLS settings

### Security
- Non-root execution
- Read-only root filesystem

### Observability
- Prometheus monitoring
- ServiceMonitor creation
- Log level configuration

## Dependencies

This chart automatically downloads and manages the upstream Ollama chart dependency. The dependency is defined in `Chart.yaml`:

```yaml
dependencies:
  - name: ollama
    version: "^0.4.0"
    repository: "https://helm.otwld.com/"
```

## Updating Dependencies

```bash
# Update chart dependencies
helm dependency update charts/ollama-upstream

# List dependencies
helm dependency list charts/ollama-upstream
```

## Values

All values are passed through to the upstream `ollama` chart under the `ollama` key. See `values.yaml` for available configuration options.

## Support

This is a community wrapper chart. For issues with the underlying Ollama functionality, please refer to:
- [Ollama official repository](https://github.com/ollama/ollama)
- [Upstream Helm chart](https://github.com/otwld/ollama-helm)

For issues with this wrapper chart, please file an issue in this repository.
