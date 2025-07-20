# AI Model Caching Solutions

This document outlines various approaches to cache AI models to avoid downloading large models (600MB+) on every cluster deployment.

## 🚀 Solution 1: Pre-built Docker Image (IMPLEMENTED)

**Status**: ✅ Implemented  
**Speed**: Fastest (~30 seconds vs ~5 minutes)  
**Maintenance**: Low

### How it works:
- Custom Docker image with TinyLlama model pre-installed
- No initContainer downloads needed
- Models are ready immediately on pod start

### Build Process:
```bash
# Image built automatically by GitHub Actions
docker build -f app/Dockerfile.ollama-tinyllama -t ghcr.io/suse-technical-marketing/ollama-tinyllama:latest .
```

### Benefits:
- ✅ **Instant startup** - no model download wait
- ✅ **Reliable** - no network dependency during deployment
- ✅ **Simple** - standard Docker image pull
- ✅ **Version controlled** - model version tied to image tag

### Drawbacks:
- ❌ **Image size** - larger Docker image (~1.2GB vs 600MB)
- ❌ **Model updates** - requires rebuilding image for new models

---

## 🏗️ Solution 2: Harbor OCI Registry (AVAILABLE)

**Status**: 🟡 Available for Harbor v2.5+  
**Speed**: Fast (~1-2 minutes)  
**Maintenance**: Medium

### Prerequisites:
- Harbor v2.5+ with OCI artifact support
- ORAS CLI tool for pushing models

### Setup:
```bash
# 1. Configure Harbor project for AI models
# 2. Push model as OCI artifact
oras push harbor.yourdomain.com/ai-models/tinyllama:latest \
  ~/.ollama/models/blobs/* \
  --annotation "ai.model.type=ollama"

# 3. Configure Ollama to pull from Harbor
export OLLAMA_MODELS_REGISTRY="harbor.yourdomain.com/ai-models"
```

### Benefits:
- ✅ **Centralized** - all models in one registry
- ✅ **Versioning** - proper model version management
- ✅ **Access control** - Harbor RBAC for models
- ✅ **Replication** - Harbor multi-region support

### Drawbacks:
- ❌ **Harbor dependency** - requires Harbor v2.5+
- ❌ **Complexity** - additional OCI artifact management
- ❌ **Network dependency** - still downloads during deployment

---

## 💾 Solution 3: Persistent Shared Storage (AVAILABLE)

**Status**: 🟡 Available with NFS/EFS  
**Speed**: Medium (~2-3 minutes)  
**Maintenance**: High

### Setup:
```yaml
# Enable in values.yaml
ollama:
  modelCache:
    sharedStorage:
      enabled: true
      storageClassName: "nfs-client"
```

### Benefits:
- ✅ **Persistent** - survives cluster rebuilds
- ✅ **Shared** - multiple deployments use same cache
- ✅ **Cost effective** - reuse existing NFS

### Drawbacks:
- ❌ **NFS dependency** - requires shared storage setup
- ❌ **Performance** - network storage latency
- ❌ **Complexity** - PVC lifecycle management

---

## 🎯 Recommendation

**Use Solution 1 (Pre-built Image)** for:
- ✅ Demo environments
- ✅ Fixed model requirements
- ✅ Fastest deployment times
- ✅ Simplest maintenance

**Use Solution 2 (Harbor)** for:
- ✅ Production environments
- ✅ Multiple model versions
- ✅ Existing Harbor infrastructure
- ✅ Model governance requirements

**Use Solution 3 (Shared Storage)** for:
- ✅ Dynamic model loading
- ✅ Large model collections
- ✅ Development environments
- ✅ Cost optimization

## Configuration

### Current Implementation (Solution 1):
```yaml
# charts/ai-compare/values.yaml
ollama:
  image:
    repository: ghcr.io/suse-technical-marketing/ollama-tinyllama
    tag: "latest"
  modelCache:
    prebuiltImage: true  # Default: use pre-built image
```

### Alternative Configurations:
```yaml
# Harbor OCI Registry
ollama:
  modelCache:
    harbor:
      enabled: true
      registry: "harbor.example.com"
      project: "ai-models"

# Shared Storage
ollama:
  modelCache:
    sharedStorage:
      enabled: true
      storageClassName: "nfs-client"
```