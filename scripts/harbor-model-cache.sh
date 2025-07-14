#!/bin/bash
# Harbor AI Model Caching Script
# Harbor v2.5+ supports OCI artifacts for AI models

# Configure Harbor as OCI registry for models
HARBOR_HOST="your-harbor.domain.com"
HARBOR_PROJECT="ai-models"
MODEL_NAME="tinyllama"
MODEL_TAG="latest"

# 1. Configure Ollama to use Harbor as model registry
export OLLAMA_MODELS_REGISTRY="$HARBOR_HOST/$HARBOR_PROJECT"

# 2. Push model to Harbor (one-time setup)
echo "Pushing model to Harbor..."
ollama serve &
sleep 5
ollama pull tinyllama:latest
# Use oras tool to push model as OCI artifact
oras push $HARBOR_HOST/$HARBOR_PROJECT/$MODEL_NAME:$MODEL_TAG \
  ~/.ollama/models/blobs/* \
  --annotation "ai.model.type=ollama" \
  --annotation "ai.model.size=600MB"

# 3. Configure Kubernetes to pull from Harbor
echo "Model cached in Harbor at: $HARBOR_HOST/$HARBOR_PROJECT/$MODEL_NAME:$MODEL_TAG"