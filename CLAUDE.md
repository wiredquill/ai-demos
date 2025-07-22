# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is AI Compare - a comprehensive demonstration of AI response comparison that shows differences between direct model access and pipeline-enhanced responses. The project demonstrates building, deploying, and managing AI applications on SUSE's cloud-native platform, with configuration change detection capabilities for SUSE Observability demonstrations.

## Architecture

**Multi-Container AI Stack:**
- **Ollama**: Local LLM inference server (runs models like tinyllama)
- **Open WebUI**: Web interface for LLM interactions with pipeline support
- **AI Compare Chat**: Custom Python/Gradio chat application that compares responses from direct Ollama vs pipeline-enhanced Open WebUI

**Deployment Options:**
- **SUSE variant**: Uses SUSE BCI (Base Container Images) with zypper package manager
- **Upstream variant**: Uses standard Debian-based Python images with apt

**Key Integrations:**
- **Fleet GitOps**: Automated deployment via Rancher Fleet
- **GPU Support**: NVIDIA GPU acceleration with runtime class configuration
- **Observability**: Integration with SUSE Observability for monitoring

## Development Commands

### Container Builds
```bash
# Build upstream variant (from repo root)
docker build -f app/Dockerfile.upstream -t ai-compare:upstream .

# Build SUSE variant (from repo root)
docker build -f app/Dockerfile.suse -t ai-compare:suse .
```

### Application Development
```bash
# Install Python dependencies
pip install -r app/requirements.txt

# Run the chat application locally
cd app && python python-ollama-open-webui.py
```

### Helm Chart Operations
```bash
# Install SUSE variant
helm install my-release charts/ai-compare-suse

# Install upstream variant  
helm install my-release charts/ai-compare

# Install with GPU support
helm install my-release charts/ai-compare-suse \
  --set ollama.gpu.enabled=true \
  --set ollama.hardware.type=nvidia

# Enable development mode with SSH access
helm install my-release charts/ai-compare \
  --set llmChat.devMode.enabled=true \
  --set llmChat.devMode.persistence.enabled=true

# Enable OpenTelemetry observability with SUSE Observability
helm install my-release charts/ai-compare-suse \
  --set llmChat.observability.enabled=true \
  --set llmChat.observability.otlpEndpoint="http://opentelemetry-collector.suse-observability.svc.cluster.local:4318" \
  --set llmChat.observability.collectGpuStats=true

# Enable optional NGINX frontend for End User UI and HTTP traffic generation
helm install my-release charts/ai-compare \
  --set frontend.enabled=true

# Enable frontend with SUSE Application Collection NGINX (for SUSE variant)
helm install my-release charts/ai-compare-suse \
  --set frontend.enabled=true

# Complete observability setup with frontend enabled
helm install my-release charts/ai-compare-suse \
  --set frontend.enabled=true \
  --set llmChat.observability.enabled=true \
  --set llmChat.observability.otlpEndpoint="http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
```

### Fleet GitOps Deployment
```bash
# Deploy Fleet resources
kubectl apply -f fleet/fleet.yaml

# Target clusters with labels
kubectl label cluster my-cluster needs-llm-suse=true    # For SUSE variant
kubectl label cluster my-cluster needs-llm=true        # For upstream variant
```

## Key Configuration

**Environment Variables (LLM Chat App):**
- `OLLAMA_BASE_URL`: Ollama service endpoint
- `OPEN_WEBUI_BASE_URL`: Open WebUI service endpoint  
- `AUTOMATION_ENABLED`: Enable automated testing loop
- `AUTOMATION_PROMPT`: Default prompt for automation
- `AUTOMATION_INTERVAL`: Automation interval in seconds
- `OBSERVABILITY_ENABLED`: Enable OpenTelemetry observability via OpenLit
- `OTLP_ENDPOINT`: OpenTelemetry collector endpoint for SUSE Observability
- `COLLECT_GPU_STATS`: Enable GPU statistics collection
- `KUBERNETES_NAMESPACE`: Kubernetes namespace for ConfigMap manipulation
- `DEMO_CONFIGMAP_NAME`: ConfigMap name for availability demo
- `CONNECTION_TIMEOUT`: Network connection timeout (optimized for SUSE security policies)
- `REQUEST_TIMEOUT`: HTTP request timeout (optimized for SUSE security policies)
- `INFERENCE_TIMEOUT`: LLM inference timeout

**Helm Values Structure:**
- `ollama.*`: Ollama deployment configuration
- `openWebui.*`: Open WebUI configuration
- `llmChat.*`: Chat application configuration
- `llmChat.observability.*`: OpenTelemetry observability configuration
- `*.persistence.enabled`: Enable persistent storage
- `ollama.gpu.enabled`: Enable GPU acceleration
- `frontend.enabled`: Enable optional NGINX frontend with End User UI
- `demo.availability.*`: ConfigMap-based availability demo configuration

## Availability Demo & Observability

### ConfigMap-Based Service Failure Simulation

The application includes a sophisticated availability demo that creates **real** observable failures for SUSE Observability monitoring:

**How It Works:**
1. **ON Toggle**: Manipulates Kubernetes ConfigMap to break application configuration
   - Removes working config key `models-latest`
   - Adds broken config key `models_latest` (underscore breaks lookup)
   - Application starts returning HTTP 500 errors
   - Health checks fail with real error conditions

2. **OFF Toggle**: Restores Kubernetes ConfigMap to fix application
   - Removes broken config key `models_latest`
   - Restores working config key `models-latest` with valid values
   - Application resumes normal HTTP 200 operations
   - Health checks return to healthy status

**Observable Patterns for SUSE Observability:**
- HTTP error rate spike (0% → 50%+)
- Health check endpoint failures (`/health` returns HTTP 500)
- Configuration error logs and alerts
- Service degradation patterns
- Recovery patterns when toggled OFF

**External Kubernetes Fixing During Demos:**
```bash
# View current ConfigMap state
kubectl get configmap <release-name>-demo-config -n <namespace> -o yaml

# Fix the broken app externally (during demo)
kubectl patch configmap <release-name>-demo-config -n <namespace> --type=json -p='[
  {"op": "remove", "path": "/data/models_latest"},
  {"op": "add", "path": "/data/models-latest", "value": "tinyllama:latest,llama2:latest"}
]'

# Break the app externally (alternative demo approach)
kubectl patch configmap <release-name>-demo-config -n <namespace> --type=json -p='[
  {"op": "remove", "path": "/data/models-latest"},
  {"op": "add", "path": "/data/models_latest", "value": "broken-model:invalid"}
]'
```

**Demo Integration:**
- Frontend toggle button shows real-time ON/OFF state
- Button reflects actual ConfigMap manipulation results
- Works in both Gradio UI and optional NGINX frontend
- Requires `kubectl` access from pod for ConfigMap manipulation
- Falls back to environment variables if ConfigMap access unavailable

### Data Leak Demo (NeuVector Integration)

Second demo button simulates sensitive data transmission:
- Sends actual credit card and SSN patterns to external endpoints
- Triggers NeuVector DLP (Data Loss Prevention) detection
- Generates observable security alerts
- Enhanced visual feedback with dramatic color changes

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd.yaml`) automatically:
1. Builds both upstream and SUSE Docker images
2. Pushes to GitHub Container Registry (ghcr.io)
3. Tags with both commit SHA and `latest`
4. Updates Helm chart values (currently commented out)

**Manual Triggers:**
- Push to `main` branch with changes to `app/`, `charts/`, or workflow files
- Manual workflow dispatch

## Key Implementation Details

**ConfigMap Manipulation Methods:**
- `_simulate_configmap_failure()`: Uses kubectl to break ConfigMap
- `_restore_configmap_health()`: Uses kubectl to fix ConfigMap
- Requires proper RBAC permissions for ConfigMap manipulation
- Environment variables provide namespace and ConfigMap names

**Frontend Integration:**
- HTTP API endpoints: `/api/availability-demo/toggle`, `/api/data-leak-demo`
- Real-time button state management
- Visual feedback with color-coded states (ON=red, OFF=green)
- Tooltip guidance for external Kubernetes fixing

**Network Timeout Optimizations:**
- CONNECTION_TIMEOUT: 5s (down from 30s)
- REQUEST_TIMEOUT: 8s (down from 30s) 
- INFERENCE_TIMEOUT: 30s (down from 120s)
- Optimized for SUSE security network policies

**Container Security Features:**
- SUSE BCI (Base Container Images) for enterprise hardening
- SUSE Application Collection NGINX for frontend
- Read-only root filesystem, non-root execution
- Capability dropping for minimal attack surface

## Development Mode

Special development setup allows SSH access to running pods for rapid iteration:
1. Enable `llmChat.devMode.enabled=true` in Helm values
2. Application code persisted on PVC for git pulls inside container
3. SSH access on port 22 (default password: `suse`)
4. Port forward: `kubectl port-forward service/chat-service 2222:22`

## File Structure Notes

- `app/`: Contains the Python chat application and Dockerfiles
- `charts/`: Helm charts for both SUSE and upstream variants
  - `**/templates/60-configmap-demo.yaml`: Availability demo ConfigMap templates
  - `**/templates/42-configmap-frontend-nginx.yaml`: NGINX frontend configuration
  - `**/templates/43-configmap-frontend-content.yaml`: Frontend static content
- `frontend/`: Optional NGINX-based End User Interface
  - `index.html`: Main frontend application
  - `script.js`: JavaScript client with availability demo toggle
  - `style.css`: Enhanced UI styles with demo button states
- `fleet/`: Fleet GitOps configuration
- `install/`: Documentation for infrastructure setup
- `demo-*.md`: Step-by-step demo guides
- `assets/`: Screenshots and documentation images