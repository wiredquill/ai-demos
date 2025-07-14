# Harbor Model Caching for AI Workloads

This document explains how the SUSE AI Demo implements intelligent model caching using SUSE Private Registry (Harbor) to dramatically reduce deployment times and bandwidth usage.

## Overview

**Problem**: AI models like TinyLlama are 600MB+ and must be downloaded from the internet on every fresh deployment, causing:
- Slow deployment times (5-10 minutes)  
- High bandwidth usage
- Potential download failures
- Poor user experience

**Solution**: Harbor OCI Registry Model Caching automatically caches models as OCI artifacts, enabling:
- Fast deployments (30 seconds after first cache)
- Bandwidth savings (90%+ reduction)
- Reliable deployments (no external dependencies after caching)
- Shared model cache across multiple clusters

## How It Works

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Ollama Pod    │───▶│  Harbor Registry │◀───│  Internet       │
│   (Init Container)   │    │  (Cache)         │    │  (Ollama Models)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
       │                         │                        │
       │ 1. Check Harbor         │ 2. Model cached?      │ 3. Download
       │ 2. Pull if cached       │ 3. Store for future   │    if needed
       │ 3. Download+Push if not │ 4. Fast retrieval     │
```

### Workflow

1. **Deployment Starts**
   - Helm chart creates Ollama deployment with Harbor caching enabled
   - Init container `harbor-model-cache` runs before main Ollama container

2. **Fast Path (Model Already Cached)**
   ```bash
   # Init container checks Harbor first
   ollama pull registry.example.com/ai-models/tinyllama:latest
   # ✅ Model found in cache - deployment completes in 30 seconds
   ```

3. **Slow Path (First Time - Model Not Cached)**
   ```bash
   # Harbor cache miss - download from internet
   ollama pull tinyllama:latest                              # Download from internet (600MB, 5-10 min)
   ollama tag tinyllama:latest registry.example.com/ai-models/tinyllama:latest
   ollama push registry.example.com/ai-models/tinyllama:latest  # Cache in Harbor for future use
   # ⚠️ First deployment slow, all future deployments fast
   ```

4. **Future Deployments**
   - All subsequent deployments use Harbor cache (fast path)
   - 90%+ time reduction (5-10 minutes → 30 seconds)

## Configuration

### Harbor Setup

1. **Create Harbor Project**
   ```
   Project Name: ai-models
   Access Level: Public (for anonymous access) or Private (with credentials)
   ```

2. **Helm Configuration**
   ```yaml
   ollama:
     modelCache:
       harbor:
         enabled: true
         registry: "registry.example.com"    # Your Harbor hostname
         project: "ai-models"                # Project created above
         username: ""                        # Optional for public projects
         password: ""                        # Optional for public projects
   ```

### Rancher UI Configuration

Navigate to the Helm chart installation and configure:

- **Model Caching** → Enable SUSE Private Registry (Harbor) Caching: `true`
- **SUSE Private Registry URL**: `registry.example.com` (no https://)
- **Harbor Project Name**: `ai-models`
- **Username/Password**: Only needed for private projects

### Verification

Check Harbor project after first deployment:
```
Harbor Project: ai-models
Artifacts:
├── tinyllama:latest (600MB OCI artifact)
└── metadata and layers
```

## Implementation Details

### Harbor Secret Creation

When Harbor credentials are provided, the chart creates a Kubernetes secret:

```yaml
# File: templates/15-secret-harbor-registry.yaml
apiVersion: v1
kind: Secret
metadata:
  name: {release-name}-harbor-registry
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: {base64-encoded-docker-config}
```

### Init Container Logic

The `harbor-model-cache` init container implements the caching logic:

```yaml
# File: templates/30-deployment-ollama.yaml
initContainers:
- name: harbor-model-cache
  image: ollama/ollama:0.6.8
  command: ["/bin/sh"]
  args: 
    - -c
    - |
      # 1. Try Harbor cache first (fast path)
      if ollama pull "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/tinyllama:latest"; then
        echo "✅ Using Harbor cache - fast deployment!"
      else
        # 2. Download from internet and cache (slow path, one-time)
        echo "⚠️ Downloading from internet - first time setup"
        ollama pull tinyllama:latest
        ollama tag tinyllama:latest "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/tinyllama:latest"
        ollama push "${HARBOR_REGISTRY}/${HARBOR_PROJECT}/tinyllama:latest"
        echo "✅ Cached in Harbor - future deployments will be fast!"
      fi
```

### Volume Mounts

- **Model Storage**: `/root/.ollama` (persistent or emptyDir)
- **Harbor Config**: `/root/.docker/config.json` (registry credentials)

## Monitoring and Troubleshooting

### Check Init Container Logs

```bash
# View Harbor caching logs
kubectl logs -n {namespace} {pod-name} -c harbor-model-cache

# Look for these messages:
# ✅ SUCCESS: Model found in Harbor cache
# ⚠️ Model not found in Harbor cache, downloading from internet
# ✅ SUCCESS: Model cached in Harbor
```

### Common Issues

1. **Authentication Failures**
   ```
   Error: authentication required
   Solution: Check Harbor username/password in values.yaml
   ```

2. **Network Connectivity**
   ```
   Error: connection timeout to registry.example.com
   Solution: Verify Harbor URL and network policies
   ```

3. **Harbor Project Not Found**
   ```
   Error: project "ai-models" not found
   Solution: Create the project in Harbor UI first
   ```

4. **Disk Space**
   ```
   Error: no space left on device
   Solution: Ensure Harbor has sufficient storage for 600MB+ models
   ```

### Performance Metrics

| Scenario | Time | Bandwidth | Description |
|----------|------|-----------|-------------|
| First deployment (no cache) | 5-10 min | 600MB | Downloads from internet, caches in Harbor |
| Cached deployment | 30-60 sec | ~10MB | Pulls from Harbor cache |
| Multiple deployments | 30-60 sec each | ~10MB each | All use Harbor cache |

## Benefits

- **90%+ Time Reduction**: 5-10 minutes → 30 seconds
- **Bandwidth Savings**: 600MB → 10MB per deployment
- **Reliability**: No external dependencies after caching
- **Multi-Cluster**: Share cache across multiple environments
- **Automatic**: Works transparently with existing workflows

## Future Enhancements

- Support for multiple model types (Llama2, CodeLlama, etc.)
- Configurable model selection through Helm values
- Harbor garbage collection policies for old model versions
- Model signing and verification for security
- Metrics and monitoring for cache hit/miss rates