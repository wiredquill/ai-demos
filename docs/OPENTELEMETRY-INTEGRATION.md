# Adding OpenTelemetry to Your Application

This guide shows how simple it is to add comprehensive OpenTelemetry observability to your Python application using OpenLIT.

## Overview

OpenLIT provides OpenTelemetry-native observability for LLM applications with automatic instrumentation for popular AI frameworks and GPU monitoring capabilities.

## Step 1: Add Dependency

Add OpenLIT to your requirements:

```txt
# requirements.txt
openlit
```

## Step 2: Initialize in Your Application

Add 3 lines of code to your Python application:

```python
# Import OpenLIT
try:
    import openlit
    OPENLIT_AVAILABLE = True
except ImportError:
    OPENLIT_AVAILABLE = False

class YourApplication:
    def __init__(self):
        # Initialize observability
        self._initialize_observability()
    
    def _initialize_observability(self):
        """Initialize OpenLIT observability if enabled and available."""
        if not OPENLIT_AVAILABLE:
            return
            
        # Read configuration from environment variables
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false").lower() == "true"
        observability_enabled = os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"
        
        if not observability_enabled or not otlp_endpoint:
            return
            
        try:
            # Initialize OpenLIT with configuration
            openlit.init(
                otlp_endpoint=otlp_endpoint,
                collect_gpu_stats=collect_gpu_stats
            )
            logger.info(f"OpenLIT observability initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenLIT observability: {e}")
```

## Step 3: Configure Environment Variables

Set these environment variables in your deployment:

```yaml
env:
  - name: OBSERVABILITY_ENABLED
    value: "true"
  - name: OTLP_ENDPOINT
    value: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
  - name: COLLECT_GPU_STATS
    value: "true"  # Set to false if no GPU available
```

## That's It! 🎉

With these minimal changes, your application now automatically tracks:

- **LLM Requests & Responses** - Token counts, latency, model usage
- **HTTP Requests** - API calls and response times  
- **GPU Statistics** - GPU utilization, memory usage (if enabled)
- **Error Tracking** - Failures and exceptions
- **Performance Metrics** - Request duration, throughput

## What Gets Automatically Instrumented

OpenLIT automatically instruments popular frameworks:
- **Ollama** - Local LLM inference
- **OpenAI** - API calls to OpenAI models
- **Requests** - HTTP client library
- **Gradio** - Web UI frameworks
- **LangChain** - LLM application frameworks
- **And many more...**

## Example Output

Once running, you'll see logs like:
```
2025-07-19 15:27:38 - INFO - OpenLIT observability initialized successfully. 
Endpoint: http://opentelemetry-collector.suse-observability.svc.cluster.local:4318, GPU Stats: True
```

## Advanced Configuration

For production deployments, consider:

```python
# More detailed configuration
openlit.init(
    otlp_endpoint="http://your-collector:4318",
    collect_gpu_stats=True,
    # Additional OpenTelemetry configuration can be added here
)
```

## Helm Chart Integration

If using Helm, add observability configuration to your values:

```yaml
observability:
  enabled: true
  otlpEndpoint: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
  collectGpuStats: true
```

## Verification

Check your SUSE Observability dashboard to see:
- LLM request traces
- Token usage metrics  
- GPU utilization graphs
- Application performance data

**Total Integration Time: ~5 minutes** ⚡