# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the SUSE AI Demo Showcase - a comprehensive demonstration of building, deploying, and managing AI applications on SUSE's cloud-native platform. The project showcases an end-to-end solution for AI workloads including infrastructure provisioning, application deployment, and observability.

## Architecture

**Multi-Container AI Stack:**
- **Ollama**: Local LLM inference server (runs models like tinyllama)
- **Open WebUI**: Web interface for LLM interactions
- **LLM Chat**: Custom Python/Gradio chat application that aggregates responses from both Ollama and Open WebUI

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
docker build -f app/Dockerfile.upstream -t suse-ai-demo:upstream .

# Build SUSE variant (from repo root)
docker build -f app/Dockerfile.suse -t suse-ai-demo:suse .
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
helm install my-release charts/llm-comm-suse

# Install upstream variant  
helm install my-release charts/llm-comm-upstream

# Install with GPU support
helm install my-release charts/llm-comm-suse \
  --set ollama.gpu.enabled=true \
  --set ollama.hardware.type=nvidia

# Enable development mode with SSH access
helm install my-release charts/llm-comm-upstream \
  --set llmChat.devMode.enabled=true \
  --set llmChat.devMode.persistence.enabled=true
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

**Helm Values Structure:**
- `ollama.*`: Ollama deployment configuration
- `openWebui.*`: Open WebUI configuration
- `llmChat.*`: Chat application configuration
- `*.persistence.enabled`: Enable persistent storage
- `ollama.gpu.enabled`: Enable GPU acceleration

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd.yaml`) automatically:
1. Builds both upstream and SUSE Docker images
2. Pushes to GitHub Container Registry (ghcr.io)
3. Tags with both commit SHA and `latest`
4. Updates Helm chart values (currently commented out)

**Manual Triggers:**
- Push to `main` branch with changes to `app/`, `charts/`, or workflow files
- Manual workflow dispatch

## Development Mode

Special development setup allows SSH access to running pods for rapid iteration:
1. Enable `llmChat.devMode.enabled=true` in Helm values
2. Application code persisted on PVC for git pulls inside container
3. SSH access on port 22 (default password: `suse`)
4. Port forward: `kubectl port-forward service/chat-service 2222:22`

## File Structure Notes

- `app/`: Contains the Python chat application and Dockerfiles
- `charts/`: Helm charts for both SUSE and upstream variants
- `fleet/`: Fleet GitOps configuration
- `install/`: Documentation for infrastructure setup
- `demo-*.md`: Step-by-step demo guides
- `assets/`: Screenshots and documentation images