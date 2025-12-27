# Stable Diffusion Helm Chart

Deploy Stable Diffusion with your choice of UI (ComfyUI, Automatic1111, or InvokeAI) on Kubernetes with GPU acceleration, flexible storage options, and network share support.

## Features

- **Multiple UI Options**: Choose between ComfyUI, Automatic1111, or InvokeAI
- **GPU Acceleration**: NVIDIA GPU support with CPU fallback
- **Flexible Storage**: Separate persistent volumes for models and outputs
- **Network Shares**: NFS/SMB support for easy file access
- **Auto Model Download**: Automatically download Stable Diffusion v1.5 on first startup
- **Rancher Integration**: Easy deployment via Rancher Fleet with questions.yaml

## Quick Start

### Install with ComfyUI (Default)

```bash
helm install sd charts/stable-diffusion \
  --set gpu.enabled=true \
  --set storage.models.enabled=true \
  --set storage.outputs.enabled=true
```

### Install with Automatic1111

```bash
helm install sd charts/stable-diffusion \
  --set uiVariant=automatic1111 \
  --set gpu.enabled=true
```

### Install with InvokeAI

```bash
helm install sd charts/stable-diffusion \
  --set uiVariant=invokeai \
  --set gpu.enabled=true
```

### Install with Example Values Files

Pre-configured values files for common scenarios:

```bash
# ComfyUI with GPU and basic storage
helm install sd charts/stable-diffusion -f values-comfyui-gpu.yaml

# Automatic1111 in CPU-only mode
helm install sd charts/stable-diffusion -f values-automatic1111-cpu.yaml

# InvokeAI with Ingress and TLS
helm install sd charts/stable-diffusion -f values-invokeai-ingress.yaml

# Production setup with SMB share
helm install sd charts/stable-diffusion -f values-production-smb.yaml -n stable-diffusion
```

## UI Variants

### ComfyUI
- **Best for**: Advanced users who want node-based workflows
- **Port**: 8188
- **Features**: Visual workflow editor, custom nodes, advanced control
- **Default NodePort**: 31800

### Automatic1111
- **Best for**: Traditional users who want a familiar interface
- **Port**: 7860
- **Features**: Extensive extensions, stable, well-documented
- **Default NodePort**: 31801

### InvokeAI
- **Best for**: Users who want a modern, polished interface
- **Port**: 9090
- **Features**: Clean UI, canvas editor, good balance of features
- **Default NodePort**: 31802

## Storage Configuration

### Model Storage
Store model checkpoints, LoRAs, VAEs, and embeddings:

```bash
helm install sd charts/stable-diffusion \
  --set storage.models.enabled=true \
  --set storage.models.size=50Gi \
  --set storage.models.storageClassName=fast-ssd
```

**Recommended size**: 50Gi (each model is 2-10GB)

### Output Storage
Store generated images:

```bash
helm install sd charts/stable-diffusion \
  --set storage.outputs.enabled=true \
  --set storage.outputs.size=100Gi
```

**Recommended size**: 100Gi (images accumulate quickly)

### Network Share (NFS)

Access your generated images from any machine on your network:

```bash
helm install sd charts/stable-diffusion \
  --set storage.shared.enabled=true \
  --set storage.shared.type=nfs \
  --set storage.shared.nfs.server=192.168.1.100 \
  --set storage.shared.nfs.path=/mnt/ai-outputs \
  --set storage.shared.linkToOutputs=true
```

This will:
- Mount your NFS share at `/shared`
- Symlink `/outputs` to `/shared/outputs` (if `linkToOutputs=true`)
- Save all generated images directly to your NFS server

### Network Share (SMB/CIFS)

Use Windows/Samba shares for file access:

**Step 1**: Create a secret with SMB credentials:
```bash
kubectl create secret generic smb-credentials \
  --from-literal=username=myuser \
  --from-literal=password=mypassword \
  -n stable-diffusion
```

**Step 2**: Install with SMB share:
```bash
helm install sd charts/stable-diffusion \
  --set storage.shared.enabled=true \
  --set storage.shared.type=smb \
  --set storage.shared.smb.server="//192.168.1.100/ai-outputs" \
  --set storage.shared.smb.secretName=smb-credentials \
  --set storage.shared.linkToOutputs=true
```

## GPU Configuration

### NVIDIA GPU (Recommended)

```bash
helm install sd charts/stable-diffusion \
  --set gpu.enabled=true \
  --set gpu.count=1 \
  --set gpu.type=nvidia
```

**Requirements**:
- NVIDIA GPU drivers installed on nodes
- NVIDIA GPU Operator or device plugin deployed
- Node labeled with GPU capability

### CPU-Only Mode

```bash
helm install sd charts/stable-diffusion \
  --set gpu.enabled=false
```

**Note**: Image generation will be significantly slower on CPU (minutes vs seconds).

## Networking

### NodePort (Default)
Simple external access via node IP:

```bash
helm install sd charts/stable-diffusion \
  --set comfyui.service.type=NodePort \
  --set comfyui.service.nodePort=31800
```

Access at: `http://<node-ip>:31800`

### LoadBalancer
Cloud load balancer (AWS/GCP/Azure):

```bash
helm install sd charts/stable-diffusion \
  --set comfyui.service.type=LoadBalancer
```

### ClusterIP (with Ingress)
Internal access only, use with ingress:

```bash
helm install sd charts/stable-diffusion \
  --set comfyui.service.type=ClusterIP
```

## Advanced Configuration

### Custom Models

Download custom models on startup:

```yaml
initModels:
  enabled: true
  models:
    - url: "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
      filename: "sd_v1-5.safetensors"
    - url: "https://civitai.com/api/download/models/12345"
      filename: "custom-model.safetensors"
```

### Resource Limits

**GPU Mode** (lighter footprint):
```yaml
resources:
  gpuOptimized:
    requests:
      cpu: "2"
      memory: "8Gi"
    limits:
      cpu: "4"
      memory: "16Gi"
```

**CPU Mode** (higher requirements):
```yaml
resources:
  cpuOnly:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
```

### Authentication

Enable basic auth (ComfyUI/Automatic1111):

```yaml
comfyui:
  auth:
    enabled: true
    username: "admin"
    password: "secure-password"
```

### Observability

Enable OpenTelemetry metrics:

```bash
helm install sd charts/stable-diffusion \
  --set observability.enabled=true \
  --set observability.otlpEndpoint="http://otel-collector:4318" \
  --set observability.collectGpuStats=true
```

## Complete Example: Production Deployment

```bash
# Create namespace
kubectl create namespace stable-diffusion

# Create SMB credentials (if using SMB)
kubectl create secret generic smb-credentials \
  --from-literal=username=myuser \
  --from-literal=password=mypassword \
  -n stable-diffusion

# Install with all features
helm install sd charts/stable-diffusion \
  --namespace stable-diffusion \
  --set uiVariant=comfyui \
  --set gpu.enabled=true \
  --set gpu.count=1 \
  --set storage.models.enabled=true \
  --set storage.models.size=50Gi \
  --set storage.outputs.enabled=true \
  --set storage.outputs.size=100Gi \
  --set storage.shared.enabled=true \
  --set storage.shared.type=nfs \
  --set storage.shared.nfs.server=192.168.1.100 \
  --set storage.shared.nfs.path=/mnt/ai-outputs \
  --set storage.shared.linkToOutputs=true \
  --set comfyui.service.type=LoadBalancer \
  --set initModels.enabled=true
```

## Rancher Fleet Deployment

1. **Navigate to Rancher UI** → Continuous Delivery → Git Repos
2. **Add Repository**: Point to this Git repository
3. **Deploy Chart**: Select `charts/stable-diffusion`
4. **Configure via UI**: Use the questions.yaml form to configure:
   - UI variant (ComfyUI/Automatic1111/InvokeAI)
   - GPU settings
   - Storage options (models, outputs, shared)
   - Network share (NFS/SMB)
   - Service type (ClusterIP/NodePort/LoadBalancer)
   - Resource limits

## Accessing Your Deployment

### Find Your Service

```bash
kubectl get svc -n stable-diffusion
```

### NodePort Access

```bash
# Get node IP
kubectl get nodes -o wide

# Access UI
# ComfyUI: http://<node-ip>:31800
# Automatic1111: http://<node-ip>:31801
# InvokeAI: http://<node-ip>:31802
```

### LoadBalancer Access

```bash
# Get external IP
kubectl get svc -n stable-diffusion

# Access UI
# http://<external-ip>:<port>
```

### Port Forward (for testing)

```bash
kubectl port-forward -n stable-diffusion svc/sd-stable-diffusion 8188:8188

# Access at http://localhost:8188
```

## Troubleshooting

### Pod not starting (GPU)

Check GPU availability:
```bash
kubectl describe node <node-name> | grep nvidia.com/gpu
```

Verify GPU operator:
```bash
kubectl get pods -n gpu-operator
```

### Storage issues

Check PVC status:
```bash
kubectl get pvc -n stable-diffusion
```

Describe PVC for details:
```bash
kubectl describe pvc -n stable-diffusion
```

### NFS/SMB mount issues

Check pod logs:
```bash
kubectl logs -n stable-diffusion <pod-name>
```

Verify NFS server accessibility:
```bash
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside pod:
mount -t nfs <nfs-server>:<path> /mnt
```

### Model download failures

Check init container logs:
```bash
kubectl logs -n stable-diffusion <pod-name> -c download-models
```

## Uninstall

```bash
helm uninstall sd -n stable-diffusion

# Optionally delete PVCs (this will delete your models and outputs!)
kubectl delete pvc -n stable-diffusion --all
```

## Values Reference

See [`values.yaml`](values.yaml) for complete configuration options.

### Key Configuration Sections

- `uiVariant`: UI selection (comfyui/automatic1111/invokeai)
- `gpu.*`: GPU configuration
- `storage.models.*`: Model storage configuration
- `storage.outputs.*`: Output storage configuration
- `storage.shared.*`: Network share configuration (NFS/SMB)
- `resources.*`: CPU/memory limits
- `initModels.*`: Auto-download models
- `observability.*`: Metrics and monitoring

## Requirements

- Kubernetes 1.20+
- Helm 3.0+
- For GPU: NVIDIA GPU Operator or device plugin
- For NFS: NFS client support on nodes
- For SMB: SMB CSI driver (if using SMB shares)

## Support

For issues, questions, or contributions:
- GitHub: https://github.com/wiredquill/ai-demos
- Issues: https://github.com/wiredquill/ai-demos/issues

## License

See repository LICENSE file.
