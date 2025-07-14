# Automated Pipeline Deployment

Complete automation of Open WebUI Pipeline integration for seamless educational demonstrations.

## 🎯 What Gets Automated

### ✅ **Automatic Deployment Features**

1. **📦 Pipeline Service Deployment**
   - Response Level Pipeline container with auto-cycle mode
   - Health checks configured for `/` endpoint  
   - Git-sync for automatic pipeline code deployment

2. **🔧 Auto-Configuration Job** 
   - Post-install Helm hook validates connectivity
   - Tests pipeline functionality end-to-end
   - Provides detailed setup instructions in logs

3. **📋 Configuration Management**
   - ConfigMaps with connection details
   - Environment variables for integration
   - JSON metadata for monitoring

4. **🎓 Educational Levels Ready**
   - 5 response complexity levels pre-configured
   - Auto-cycling through education levels
   - No manual setup required

## ⚙️ Configuration Options

### Helm Values Configuration

```yaml
pipelines:
  enabled: true                    # Enable pipeline service
  autoConfig:
    enabled: true                  # Enable auto-configuration  
    apiKey: "0p3n-w3bu!"          # Pipeline API key
    modelId: "response_level"      # Pipeline model identifier
    connectionName: "Response Level Pipeline"  # Display name
```

### Questions.yaml Options

When deploying via Rancher or other UI:

- **✅ Enable Open WebUI Pipelines**: Deploy pipeline service
- **✅ Auto-Configure Open WebUI Connection**: Automatic setup job
- **🔑 Pipeline API Key**: Customizable authentication key
- **🔄 Pipeline Mode**: Auto-cycle vs Manual level selection

## 🚀 Deployment Commands

### Quick Start (All Automation Enabled)

```bash
# Upstream version with full automation
helm install ai-demo charts/llm-comm-upstream -n upstream --create-namespace

# SUSE version with full automation  
helm install ai-demo charts/llm-comm-suse -n suse --create-namespace
```

### Custom Configuration

```bash
# Deploy with custom API key
helm install ai-demo charts/llm-comm-upstream \
  --set pipelines.autoConfig.apiKey="my-secure-key" \
  -n upstream --create-namespace

# Deploy without auto-configuration (manual setup)
helm install ai-demo charts/llm-comm-upstream \
  --set pipelines.autoConfig.enabled=false \
  -n upstream --create-namespace
```

## 📊 Monitoring Automation

### Check Auto-Configuration Job

```bash
# View job status
kubectl get jobs -n upstream -l app.kubernetes.io/component=pipeline-configurator

# View configuration logs
kubectl logs -n upstream -l app.kubernetes.io/component=pipeline-configurator

# Check job completion
kubectl describe job -n upstream -l app.kubernetes.io/component=pipeline-configurator
```

### Verify Pipeline Connectivity

```bash
# Test pipeline service directly
kubectl exec -n upstream $(kubectl get pods -l app=pipelines -o jsonpath='{.items[0].metadata.name}') -- \
  curl -s http://localhost:9099/

# Test from Open WebUI pod
kubectl exec -n upstream $(kubectl get pods -l app=open-webui -o jsonpath='{.items[0].metadata.name}') -- \
  curl -s http://pipelines-service:9099/
```

### View Configuration Details

```bash
# Check pipeline configuration ConfigMap
kubectl get configmap -n upstream -l app.kubernetes.io/component=pipeline-config -o yaml

# View pipeline setup script
kubectl get configmap -n upstream -o jsonpath='{.data.pipeline-setup\.sh}' | sh
```

## 🐛 Troubleshooting Automation

### Auto-Configuration Job Fails

```bash
# Check job pod logs
kubectl logs -n upstream $(kubectl get pods -l job-name -o jsonpath='{.items[0].metadata.name}')

# Restart configuration job
kubectl delete job -n upstream -l app.kubernetes.io/component=pipeline-configurator
helm upgrade ai-demo charts/llm-comm-upstream -n upstream
```

### Pipeline Service Not Ready

```bash
# Check pipeline pod status
kubectl get pods -n upstream -l app=pipelines

# View pipeline startup logs  
kubectl logs -n upstream -l app=pipelines -f

# Verify git-sync init container
kubectl logs -n upstream -l app=pipelines -c git-sync
```

### Open WebUI Connection Issues

```bash
# Test Open WebUI API
kubectl exec -n upstream $(kubectl get pods -l app=open-webui -o jsonpath='{.items[0].metadata.name}') -- \
  curl -s http://localhost:8080/api/v1/models

# Check Open WebUI logs for pipeline errors
kubectl logs -n upstream -l app=open-webui | grep -i pipeline
```

## 🎓 Education Level Verification

### Test Response Level Cycling

```bash
# Send test request to pipeline
kubectl exec -n upstream $(kubectl get pods -l app=pipelines -o jsonpath='{.items[0].metadata.name}') -- \
  curl -s -X POST http://localhost:9099/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "response_level",
    "messages": [{"role": "user", "content": "Why is the sky blue?"}],
    "stream": false
  }'
```

### Expected Response Levels

1. **Default**: Standard AI responses
2. **Kid Mode**: "Explain like I'm 5 years old using simple words and fun examples"
3. **Young Scientist**: "Explain like I'm 12 years old with science details but understandable"  
4. **College Student**: "Explain with technical context, examples, and deeper analysis"
5. **Scientific**: "Full scientific explanation with precise terminology and technical accuracy"

## 🔄 Updating Pipeline Configuration

### Modify Auto-Configuration Settings

```bash
# Update API key
helm upgrade ai-demo charts/llm-comm-upstream \
  --set pipelines.autoConfig.apiKey="new-api-key" \
  -n upstream

# Disable auto-configuration
helm upgrade ai-demo charts/llm-comm-upstream \
  --set pipelines.autoConfig.enabled=false \
  -n upstream  

# Change pipeline mode to manual
helm upgrade ai-demo charts/llm-comm-upstream \
  --set pipelines.config.pipelineMode="manual" \
  -n upstream
```

### Re-run Configuration Job

```bash
# Delete existing job and trigger new one
kubectl delete job -n upstream -l app.kubernetes.io/component=pipeline-configurator
helm upgrade ai-demo charts/llm-comm-upstream -n upstream --reuse-values
```

## 🎯 Success Indicators

### ✅ Fully Automated Deployment

- **Pipeline pod**: Running (1/1 Ready)
- **Configuration job**: Completed successfully  
- **Pipeline API**: Responding on port 9099
- **Response levels**: All 5 levels loaded
- **Auto-cycle mode**: Active and cycling
- **Integration logs**: No errors in Open WebUI

### 📋 Manual Steps Eliminated

- ❌ No manual Open WebUI admin configuration required
- ❌ No manual API key setup needed
- ❌ No manual model enabling required  
- ❌ No manual connection testing needed
- ✅ **Zero-touch educational demonstration deployment**

The automation ensures consistent, reliable pipeline deployment for educational environments!