# Claude Code Session Transfer - AI Compare Project

## Current State (as of commit 12f25e90)
- **Project**: AI Compare - LLM response comparison with SUSE Observability integration
- **Latest commit**: `12f25e90` - Fix 404 errors, improve UI/UX, and add proper toggle functionality
- **Chart versions**: 0.1.178
- **Status**: All major issues have been fixed and committed

## Recent Major Fixes Completed

### 1. 404 Errors - SOLVED ✅
**Root Cause**: Service only exposed port 7860 (Gradio), NGINX tried to proxy to port 8080
**Fix**: Updated service templates to expose BOTH ports:
- `charts/ai-compare/templates/42-service-llm-chat.yaml`
- `charts/ai-compare-suse/templates/42-service-llm-chat.yaml`
- Now exposes: port 7860 (Gradio UI) + port 8080 (HTTP API server)

### 2. Python App UI Improvements - SOLVED ✅
**Changes in**: `app/python-ollama-open-webui.py`
- **Status Display**: Moved from bottom to TOP of interface (line ~1815)
- **Availability Demo**: Now proper ON/OFF toggle with colored states
- **Data Leak Demo**: Added visual feedback (🔥 Processing...)
- **Button Management**: Fixed click handlers and return values

### 3. Frontend API Routing - SOLVED ✅
**Fixed**: All frontend API calls now use correct `/api/` prefix
- `frontend/script.js`: Updated API endpoints
- `charts/ai-compare/templates/43-configmap-frontend-content.yaml`: ConfigMap version updated

### 4. ConfigMap-Based Availability Demo - IMPLEMENTED ✅
**Features**:
- Real kubectl ConfigMap manipulation for authentic K8s failures
- External fixing capability during demos
- Environment variables for namespace/ConfigMap detection
- Demo ConfigMap templates added to both chart variants

## Current Architecture

### Service Configuration
```yaml
# Both chart variants now expose:
ports:
  - port: 7860    # Gradio UI
    name: gradio
  - port: 8080    # HTTP API server  
    name: http-api
```

### NGINX Routing (Frontend)
```
/ -> Static frontend content
/api/* -> Proxy to port 8080 (HTTP API server)
/health -> Direct proxy to port 8080
```

### Flask HTTP API Server (Port 8080)
```
/health -> Health check endpoint
/api/chat -> Chat completion endpoint
/api/data-leak-demo -> Data leak demo
/api/availability-demo/toggle -> Availability toggle
/api/test -> Debug endpoint
```

## Outstanding Items

### Ready for Testing
- **Local Docker builds**: Need to set up for faster iteration
- **Service validation**: Test that 404 errors are resolved
- **UI/UX validation**: Verify status display visibility and button feedback

### Known Issues (User Reported)
- Web frontend still showing 404 errors (should be fixed with latest service config)
- Need to verify data leak button feedback is now visible every time
- Availability demo should now show proper ON/OFF states

## Next Steps for New Session
1. **Test local Docker builds**: `docker buildx build --platform linux/amd64 -f app/Dockerfile.suse -t ai-compare-suse:local-test .`
2. **Validate fixes**: Deploy latest charts (0.1.178) and test frontend
3. **Debug any remaining issues**: Use enhanced logging and /api/test endpoint

## File Locations of Recent Changes
- `app/python-ollama-open-webui.py`: Main application with UI improvements
- `charts/*/templates/42-service-llm-chat.yaml`: Service port configuration  
- `charts/*/templates/60-configmap-demo.yaml`: Demo configuration
- `frontend/script.js`: Frontend API routing fixes
- `CLAUDE.md`: Comprehensive project documentation

## Key Environment Variables
```bash
KUBERNETES_NAMESPACE=<namespace>
DEMO_CONFIGMAP_NAME=<release-name>-demo-config  
HTTP_API_ENABLED=true
HTTP_API_PORT=8080
```

## Deployment Commands
```bash
# Install with frontend enabled
helm install my-release charts/ai-compare-suse \
  --set frontend.enabled=true \
  --set llmChat.observability.enabled=true

# External ConfigMap fixing during demos
kubectl patch configmap <name>-demo-config -n <namespace> --type=json \
  -p='[{"op": "remove", "path": "/data/models_latest"}, 
       {"op": "add", "path": "/data/models-latest", "value": "tinyllama:latest,llama2:latest"}]'
```

---
Generated: $(date)
Commit: 12f25e90
User: Need to move to new machine with Docker/kubectl for faster local testing