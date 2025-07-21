#!/bin/bash
# SUSE Observability ConfigMap-based Availability Demo Script
# This script demonstrates how to trigger observable failures for SUSE Observability monitoring

set -e

NAMESPACE="${1:-ai-compare}"
RELEASE_NAME="${2:-my-release}"

echo "🎯 SUSE Observability ConfigMap-based Availability Demo"
echo "Namespace: ${NAMESPACE}"
echo "Release: ${RELEASE_NAME}"
echo ""

# Function to get current ConfigMap status
get_configmap_status() {
    echo "📊 Current ConfigMap status:"
    kubectl get configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} -o yaml | grep -E "models-latest|models_latest" || true
    echo ""
}

# Function to check service health via API
check_service_health() {
    echo "🏥 Checking service health via API..."
    kubectl port-forward -n ${NAMESPACE} service/${RELEASE_NAME}-app-service 8080:8080 &
    PF_PID=$!
    sleep 3
    
    curl -s http://localhost:8080/health | jq . || echo "Health check failed"
    
    kill $PF_PID 2>/dev/null || true
    echo ""
}

# Function to simulate failure by changing ConfigMap key
simulate_failure() {
    echo "💥 Simulating service failure by breaking ConfigMap..."
    echo "Changing 'models-latest' key to 'models_latest' (invalid key)"
    
    # Get current configmap
    kubectl get configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} -o yaml > /tmp/configmap-backup.yaml
    
    # Create broken configmap (change key name)
    kubectl get configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} -o yaml | \
        sed 's/models-latest:/models_latest:/' | \
        sed 's/tinyllama:latest/broken-model:invalid/' | \
        kubectl apply -f -
    
    echo "✅ ConfigMap key changed - service should start failing within 30 seconds"
    echo "🔍 Monitor SUSE Observability for:"
    echo "   - HTTP 500 error rate spikes"
    echo "   - /health endpoint failures"  
    echo "   - ConfigMap read errors in logs"
    echo "   - Service degradation alerts"
    echo ""
}

# Function to restore service health
restore_health() {
    echo "✅ Restoring service health by fixing ConfigMap..."
    
    if [ -f "/tmp/configmap-backup.yaml" ]; then
        kubectl apply -f /tmp/configmap-backup.yaml
        rm -f /tmp/configmap-backup.yaml
        echo "✅ ConfigMap restored from backup"
    else
        # Manual restore
        kubectl patch configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} --type='json' -p='[
            {"op": "remove", "path": "/data/models_latest"},
            {"op": "add", "path": "/data/models-latest", "value": "tinyllama:latest,llama2:latest"}
        ]' 2>/dev/null || {
            echo "⚠️  Manual patch failed, restoring via template..."
            kubectl get configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} -o yaml | \
                sed 's/models_latest:/models-latest:/' | \
                sed 's/broken-model:invalid/tinyllama:latest/' | \
                kubectl apply -f -
        }
    fi
    
    echo "✅ Service should recover within 30 seconds"
    echo "🔍 Monitor SUSE Observability for:"
    echo "   - Error rate returning to 0%"
    echo "   - /health endpoint returning 200"
    echo "   - Recovery patterns in metrics"
    echo ""
}

# Function to generate continuous HTTP traffic for observability
generate_traffic() {
    echo "🌐 Generating continuous HTTP traffic for observability monitoring..."
    kubectl port-forward -n ${NAMESPACE} service/${RELEASE_NAME}-app-service 8080:8080 &
    PF_PID=$!
    sleep 3
    
    echo "Sending 20 requests over 60 seconds..."
    for i in {1..20}; do
        echo "Request $i/20:"
        curl -s -X POST http://localhost:8080/api/chat \
            -H "Content-Type: application/json" \
            -d '{"message": "Hello, how are you?", "model": "tinyllama:latest"}' \
            | jq -r '.status // .error' || echo "Request failed"
        
        sleep 3
    done
    
    kill $PF_PID 2>/dev/null || true
    echo "✅ Traffic generation completed"
    echo ""
}

# Function to show SUSE Observability monitoring commands
show_monitoring_commands() {
    echo "📊 SUSE Observability Monitoring Commands:"
    echo ""
    echo "# Check pod logs for errors"
    echo "kubectl logs -n ${NAMESPACE} deployment/${RELEASE_NAME}-app -f"
    echo ""
    echo "# Monitor health endpoint"
    echo "watch -n 5 'kubectl exec -n ${NAMESPACE} deployment/${RELEASE_NAME}-app -- curl -s http://localhost:8080/health'"
    echo ""
    echo "# Check ConfigMap status"
    echo "kubectl get configmap ${RELEASE_NAME}-demo-config -n ${NAMESPACE} -o yaml"
    echo ""
    echo "# Port forward for direct API access"
    echo "kubectl port-forward -n ${NAMESPACE} service/${RELEASE_NAME}-app-service 8080:8080"
    echo ""
}

# Main execution
case "${3:-demo}" in
    "status")
        get_configmap_status
        check_service_health
        ;;
    "fail")
        get_configmap_status
        simulate_failure
        get_configmap_status
        ;;
    "restore")
        restore_health
        get_configmap_status
        ;;
    "traffic")
        generate_traffic
        ;;
    "monitor")
        show_monitoring_commands
        ;;
    "demo"|*)
        echo "🚀 Running complete availability demo cycle..."
        echo ""
        
        echo "1️⃣ Initial status check..."
        get_configmap_status
        
        echo "2️⃣ Generating baseline traffic (30 seconds)..."
        generate_traffic &
        sleep 30
        
        echo "3️⃣ Simulating service failure..."
        simulate_failure
        
        echo "4️⃣ Waiting 60 seconds for SUSE Observability to detect failure..."
        sleep 60
        
        echo "5️⃣ Restoring service health..."
        restore_health
        
        echo "6️⃣ Waiting 60 seconds for SUSE Observability to detect recovery..."
        sleep 60
        
        echo "7️⃣ Final status check..."
        get_configmap_status
        
        echo "✅ Demo completed!"
        echo ""
        show_monitoring_commands
        ;;
esac

echo "🎯 Demo script completed. Check SUSE Observability dashboard for failure patterns!"