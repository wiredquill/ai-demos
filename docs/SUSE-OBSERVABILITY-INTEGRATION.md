# SUSE Observability OpenTelemetry Integration Guide

This guide explains how to enable OpenTelemetry observability for an existing Python application to appear in SUSE Observability's GenAI Applications section with full metrics, traces, and LLM system detection.

## Overview

This implementation demonstrates integrating a Python AI application with SUSE Observability using OpenTelemetry and OpenLit for comprehensive GenAI observability. The application will appear in:

- **GenAI Applications** section with full metrics
- **LLM Systems** with Ollama detection  
- **OpenTelemetry** service monitoring

## Prerequisites

- Kubernetes cluster with SUSE Observability deployed
- OpenTelemetry collector endpoint available
- Python application making AI/LLM calls

## Step 1: Python Dependencies

Add OpenTelemetry libraries to your `requirements.txt`:

```txt
# Core dependencies
requests
flask
ollama

# OpenTelemetry dependencies
openlit>=1.28.0
opentelemetry-api
opentelemetry-sdk
```

## Step 2: Python Application Changes

### A. Import Required Libraries

```python
import os
import logging
try:
    import openlit
    OPENLIT_AVAILABLE = True
except ImportError:
    OPENLIT_AVAILABLE = False

logger = logging.getLogger(__name__)
```

### B. Initialize OpenTelemetry Observability

Add this initialization method to your application class:

```python
def _initialize_observability(self):
    """Initialize OpenLit observability if enabled and available."""
    if not OPENLIT_AVAILABLE:
        logger.warning("OpenLit not available - observability disabled")
        return
        
    # Read configuration from environment variables
    otlp_endpoint = os.getenv("OTLP_ENDPOINT")
    collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false").lower() == "true"
    observability_enabled = os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"
    
    if not observability_enabled or not otlp_endpoint:
        logger.info("Observability disabled or endpoint not configured")
        return
        
    logger.info(f"Initializing OpenLit observability with endpoint: {otlp_endpoint}")
    
    # Set OpenTelemetry service name environment variables BEFORE OpenLit initialization
    # This is critical for SUSE Observability GenAI service detection
    os.environ["OTEL_SERVICE_NAME"] = "your-genai-app-name"
    os.environ["OTEL_SERVICE_NAMESPACE"] = "your-namespace"
    os.environ["OTEL_SERVICE_VERSION"] = "1.0.0"
    
    # Set GenAI-specific resource attributes for SUSE Observability detection
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = (
        "service.name=your-genai-app-name,"
        "service.namespace=your-namespace,"
        "service.version=1.0.0,"
        "gen_ai.system=ollama,"  # or openai, claude, etc.
        "gen_ai.operation.name=chat,"
        "gen_ai.request.model=your-model-name,"
        "gen_ai.application.name=your-app,"
        "gen.ai.environment=default,"
        "gen_ai_app=true,"  # CRITICAL: Required for GenAI Apps section
        "openlit=dev-ai,"
        "ai.model.provider=meta,"  # or openai, anthropic, etc.
        "ai.workload.type=inference"
    )
    
    # Pre-import AI libraries for OpenLit auto-instrumentation
    try:
        import ollama  # or import openai, etc.
        logger.info("Pre-imported AI library for OpenLit instrumentation")
    except ImportError:
        logger.warning("Could not import AI library for instrumentation")
    
    # Initialize OpenLit with configuration
    try:
        openlit.init(
            otlp_endpoint=otlp_endpoint,
            collect_gpu_stats=collect_gpu_stats
        )
        logger.info(f"✅ OpenLit observability initialized successfully")
        logger.info(f"Endpoint: {otlp_endpoint}, GPU Stats: {collect_gpu_stats}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenLit observability: {e}")
```

### C. Call Initialization in Your Application

```python
class YourApplication:
    def __init__(self):
        # Initialize observability EARLY in startup
        self._initialize_observability()
        
        # Rest of your application initialization...
```

## Step 3: Kubernetes Deployment Configuration

### A. Environment Variables

Add these environment variables to your Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: your-genai-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: your-app:latest
        env:
        # OpenTelemetry Configuration
        - name: OBSERVABILITY_ENABLED
          value: "true"
        - name: OTLP_ENDPOINT
          value: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
        - name: COLLECT_GPU_STATS
          value: "true"  # Set to false if no GPU available
        
        # Optional: Enhanced GenAI observability features
        - name: TOKEN_TRACKING_ENABLED
          value: "true"
        - name: COST_TRACKING_ENABLED
          value: "true"
        - name: MODEL_METRICS_ENABLED
          value: "true"
        - name: TRACE_REQUESTS_ENABLED
          value: "true"
```

### B. Pod Labels for GenAI Detection

Add these labels to your pod template:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: your-genai-app
spec:
  template:
    metadata:
      labels:
        # SUSE Observability GenAI Detection Labels
        app.kubernetes.io/name: genai-observability-demo
        genai: your-app-name
        observability.suse.com/genai-workload: chat-completion
        suse-ai/component: genai-app
        suse-ai/tier: application
```

## Step 4: Kubernetes Service Configuration

Create a service to expose your application:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: your-genai-app-service
  labels:
    app: your-genai-app
spec:
  selector:
    app: your-genai-app
  ports:
  - name: app
    port: 8080
    targetPort: 8080
  type: ClusterIP
```

## Step 5: RBAC Configuration (if using Kubernetes integration)

If your application needs to read Kubernetes resources:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: genai-service-account
  namespace: your-namespace
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: genai-reader
rules:
- apiGroups: [""]
  resources: ["pods", "services", "configmaps"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: genai-reader-binding
subjects:
- kind: ServiceAccount
  name: genai-service-account
  namespace: your-namespace
roleRef:
  kind: ClusterRole
  name: genai-reader
  apiGroup: rbac.authorization.k8s.io
```

## Step 6: Helm Chart Integration (Optional)

If using Helm, add observability configuration to your `values.yaml`:

```yaml
observability:
  enabled: true
  otlpEndpoint: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
  collectGpuStats: true
  # Enhanced GenAI observability settings
  tokenTracking: true
  costTracking: true
  modelMetrics: true
  traceRequests: true
```

And template it in your deployment:

```yaml
env:
- name: OBSERVABILITY_ENABLED
  value: {{ .Values.observability.enabled | quote }}
- name: OTLP_ENDPOINT
  value: {{ .Values.observability.otlpEndpoint | quote }}
- name: COLLECT_GPU_STATS
  value: {{ .Values.observability.collectGpuStats | quote }}
```

## Expected Results in SUSE Observability

After deployment, you should see:

### 1. GenAI Applications Section
- Service name: `your-genai-app-name`
- Type: `otel service`
- Labels include: `gen_ai_app`, `gen.ai.environment:default`, `openlit:dev-ai`

### 2. OpenTelemetry Section
- Service instance with all resource attributes
- Kubernetes integration labels
- Pod, deployment, and node information

### 3. Traces and Spans
- **GenAI spans**: `gen_ai.chat.completions` with semantic attributes
- **LLM system spans**: Auto-instrumented AI library calls
- **HTTP spans**: Network calls to AI services
- **Token/cost metrics**: Usage and performance data

### 4. LLM Systems (if applicable)
- `ollama (genai.system.ollama)` or equivalent for your AI provider
- Model usage and performance metrics

## Troubleshooting

### Common Issues

1. **Service not appearing in GenAI Apps**:
   - Verify `gen_ai_app=true` in resource attributes
   - Check that `OTEL_SERVICE_NAME` is set before OpenLit initialization
   - Ensure pod has correct labels

2. **No traces/metrics**:
   - Confirm `OTLP_ENDPOINT` is accessible from pods
   - Check OpenLit initialization logs
   - Verify AI library (ollama, openai, etc.) is imported before OpenLit

3. **LLM Systems not detected**:
   - Ensure AI library auto-instrumentation is working
   - Check for `gen_ai.system` attributes in spans
   - Verify actual AI API calls are being made

### Verification Steps

1. **Check pod logs**:
```bash
kubectl logs -n your-namespace your-pod-name | grep -i "openlit\|observability"
```

2. **Verify environment variables**:
```bash
kubectl exec -n your-namespace your-pod-name -- env | grep OTEL
```

3. **Test connectivity to collector**:
```bash
kubectl exec -n your-namespace your-pod-name -- curl -I http://opentelemetry-collector.suse-observability.svc.cluster.local:4318/v1/traces
```

## Additional Features

### GPU Statistics (Optional)
If running on GPU-enabled nodes:

```yaml
env:
- name: COLLECT_GPU_STATS
  value: "true"
```

### Automation for Continuous Telemetry (Optional)
To generate continuous AI traffic for testing:

```yaml
env:
- name: AUTOMATION_ENABLED
  value: "true"
- name: AUTOMATION_INTERVAL
  value: "30"  # seconds
```

## Security Considerations

- Use proper RBAC permissions
- Avoid logging sensitive data in telemetry
- Configure appropriate retention policies
- Use network policies to restrict collector access

## Performance Impact

- OpenLit adds minimal overhead (~1-2% CPU)
- Memory usage increases by ~50-100MB
- Network traffic for telemetry data
- Consider sampling for high-traffic applications

## Conclusion

This integration provides comprehensive observability for AI applications in SUSE Observability with minimal code changes. The key is proper resource attribute configuration and ensuring OpenLit can auto-instrument your AI library calls.

For questions or issues, check the OpenLit documentation and SUSE Observability GenAI integration guides.