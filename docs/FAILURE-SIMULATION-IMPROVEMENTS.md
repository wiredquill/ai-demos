# Model Configuration Failure Simulation - Analysis & Improvements

## Current Approach Issues

### 1. UI Default Values Problem
- **Issue**: The UI input field shows `"models_latest"` (with underscore) but the working configuration should be `"models-latest"` (with hyphen)
- **Impact**: Causes confusion where the UI shows incorrect initial value
- **Fix**: Updated line 1167 in `/app/python-ollama-open-webui.py` to use correct default value

### 2. Current Failure Simulation Method
The existing approach uses ConfigMap value changes to simulate failures:
- Uses environment variable `MODEL_CONFIG` from ConfigMap
- Python app checks if `MODEL_CONFIG != "models-latest"`
- When broken, shows error message in chat responses
- Updates ConfigMap using kubectl commands

### 3. Problems with Current Approach
- **Artificial Logic**: The failure is simulated through application logic rather than real service failure
- **Limited Observability**: Only shows as broken chat responses, not actual service health degradation
- **Poor User Experience**: Users see pipeline errors in chat rather than system-level service failures
- **Not Realistic**: Real-world failures would affect service health, not just response content

## Improved Approach: Environment Variable Deployment Patching

### Benefits of the New Approach
1. **Realistic Failure Simulation**: Uses `kubectl patch` to change deployment environment variables
2. **Actual Service Impact**: Service health status changes to "DEVIATING" state
3. **Better Observability**: SUSE Observability can detect deployment changes and correlate with health degradation
4. **System-Level Changes**: Changes are visible at the infrastructure level, not just application level

### Implementation Details

#### New Environment Variables Added
```yaml
# Service health failure simulation
- name: SERVICE_HEALTH_FAILURE
  value: "false"
- name: DEPLOYMENT_NAME
  value: "ollama-chat-app"
```

#### New Methods Added

1. **Service Health Check**
   - `get_service_health_status()`: Returns service health status with color coding
   - Checks for simulated failures, configuration issues, and service connectivity
   - Returns status: HEALTHY, DEGRADED, DEVIATING, or UNKNOWN

2. **Deployment Patching**
   - `simulate_service_failure()`: Patches deployment to set `SERVICE_HEALTH_FAILURE="true"`
   - `restore_service_health()`: Patches deployment to set `SERVICE_HEALTH_FAILURE="false"`
   - `_patch_deployment_env_var()`: Core kubectl patch functionality with rollout monitoring

3. **Enhanced UI Components**
   - Service Health Simulation modal with clear explanations
   - System Status display showing service health alongside provider status
   - New buttons: "🚨 Simulate Service Failure" and "🩹 Restore Service Health"

#### kubectl Patch Implementation
```python
def _patch_deployment_env_var(self, env_var_name: str, env_var_value: str) -> bool:
    """Patches deployment environment variable using kubectl."""
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "chat-app",
                            "env": [
                                {
                                    "name": env_var_name,
                                    "value": env_var_value
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }
    
    cmd = [
        "kubectl", "patch", "deployment", self.deployment_name,
        "-n", self.config_map_namespace,
        "--type", "strategic",
        "--patch", json.dumps(patch)
    ]
```

### Comparison: Old vs New Approach

| Aspect | Old Approach (ConfigMap) | New Approach (Deployment Patch) |
|--------|--------------------------|----------------------------------|
| **Failure Type** | Application logic check | Environment variable change |
| **Visibility** | Chat response errors | Service health status change |
| **Observability** | ConfigMap change events | Deployment change + health state |
| **Realism** | Artificial pipeline logic | Actual service configuration |
| **Recovery** | Update ConfigMap value | Patch environment variable |
| **Impact** | Chat responses only | System-wide service health |
| **Detection** | Manual chat testing | Automated health monitoring |

### Usage Instructions

#### Simulate Service Failure
1. Click "🚨 Simulate Service Failure" button
2. Confirm in the Service Health Simulation modal
3. System patches deployment with `SERVICE_HEALTH_FAILURE="true"`
4. Service health status changes to "DEVIATING"
5. SUSE Observability detects the deployment change and health degradation

#### Restore Service Health
1. Click "🩹 Restore Service Health" button
2. System patches deployment with `SERVICE_HEALTH_FAILURE="false"`
3. Service health status returns to "HEALTHY"
4. SUSE Observability tracks the recovery

### SUSE Observability Integration

The new approach provides better integration with SUSE Observability:

1. **Deployment Change Detection**: Observability can track kubectl patch operations
2. **Service Health Correlation**: Health status changes can be correlated with deployment modifications
3. **Timeline Visibility**: Clear timeline of when failure was introduced and resolved
4. **Alerting Capabilities**: Health state "DEVIATING" can trigger alerts
5. **Root Cause Analysis**: Deployment changes provide clear root cause for service degradation

### Files Modified

1. `/app/python-ollama-open-webui.py`:
   - Fixed UI default value (line 1167)
   - Added service health state management
   - Added deployment patching methods
   - Enhanced provider status display with service health
   - Added new UI components and event handlers

2. `/charts/ai-compare/templates/32-deployment-llm-chat.yaml`:
   - Added `SERVICE_HEALTH_FAILURE` environment variable
   - Added `DEPLOYMENT_NAME` environment variable

3. `/charts/ai-compare-suse/templates/32-deployment-llm-chat.yaml`:
   - Added same environment variables for SUSE variant

### Backward Compatibility

The improvements maintain backward compatibility:
- Old ConfigMap-based failure simulation still works
- Both failure types are displayed in service health status
- Existing UI components remain functional
- No breaking changes to existing functionality

This enhanced approach provides a more realistic and observable failure simulation that better demonstrates SUSE Observability's capabilities for detecting and correlating infrastructure changes with service health issues.