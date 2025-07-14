# Pipeline Integration Guide

This guide explains how to configure and use the Open WebUI Pipeline integration with response level cycling.

## 🚀 Pipeline Status

✅ **Pipeline Service Running**: `pipelines-service:9099`  
✅ **Response Level Pipeline Loaded**: Auto-cycle mode enabled  
✅ **Health Checks Passing**: Using `/` endpoint  
✅ **5 Education Levels Available**: Default, Kid Mode, Young Scientist, College, Scientific  

## 📋 Configuration Steps

### 1. Open WebUI Admin Configuration

1. **Access Open WebUI**: Navigate to your Open WebUI instance
2. **Admin Panel**: Go to Admin Panel → Settings → Connections
3. **Add Pipeline Connection**: Click the `+` button to add a new connection
4. **Configure Pipeline**:
   - **API URL**: `http://pipelines-service:9099`
   - **API Key**: `0p3n-w3bu!` (default Open WebUI pipelines key)
   - **Name**: `Response Level Pipeline`

### 2. Enable Pipeline in Models

1. **Models Section**: Go to Admin Panel → Models
2. **Add Pipeline Model**: The `response_level` model should appear
3. **Enable Model**: Make sure it's enabled for users

### 3. Using the Pipeline

The pipeline automatically cycles through 5 response complexity levels:

1. **Default**: Standard AI responses
2. **Kid Mode**: "Explain like I'm 5 years old using simple words and fun examples"
3. **Young Scientist**: "Explain like I'm 12 years old with science details but understandable"
4. **College Student**: "Explain with technical context, examples, and deeper analysis"
5. **Scientific**: "Full scientific explanation with precise terminology and technical accuracy"

## 🔧 Technical Details

### Pipeline Architecture

```
User Message → Pipeline (Level Modifier) → LLM Backend → Response
```

### API Endpoints

- **Health Check**: `GET http://pipelines-service:9099/`
- **Chat Completions**: `POST http://pipelines-service:9099/v1/chat/completions`
- **Models**: `GET http://pipelines-service:9099/v1/models`

### Example API Request

```bash
curl -X POST http://pipelines-service:9099/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "response_level",
    "messages": [
      {"role": "user", "content": "Why is the sky blue?"}
    ]
  }'
```

## 🐛 Troubleshooting

### Pipeline Pod Not Ready
- **Issue**: Health checks failing
- **Solution**: Ensure health check uses `/` endpoint not `/health`

### Pipeline Not Loading
- **Issue**: Git sync fails to clone repository
- **Solution**: Check git repository URL and branch in values.yaml

### Open WebUI Can't Connect
- **Issue**: Connection refused to pipelines-service
- **Solution**: Verify service exists and pods are running:
```bash
kubectl get svc pipelines-service -n upstream
kubectl get pods -l app=pipelines -n upstream
```

### Authentication Errors
- **Issue**: "Not authenticated" errors
- **Solution**: Configure API key in Open WebUI connections

## 📊 Monitoring

### Check Pipeline Logs
```bash
kubectl logs -n upstream -l app=pipelines -f
```

### Test Pipeline Connectivity
```bash
kubectl exec -n upstream $(kubectl get pods -l app=open-webui -o jsonpath='{.items[0].metadata.name}') -- curl -s http://pipelines-service:9099/
```

### Verify Pipeline Loading
```bash
kubectl logs -n upstream -l app=pipelines | grep -E "(Pipeline|Loaded|Available)"
```

## 🎯 Expected Behavior

When working correctly, you should see:

1. **Pipeline startup logs** showing response level pipeline loaded
2. **Open WebUI connection** showing pipelines-service as available
3. **Response modification** where questions get complexity level instructions added
4. **Auto-cycling** through the 5 education levels on subsequent requests

The pipeline enhances educational demonstrations by showing how AI can adapt responses for different audience levels automatically.