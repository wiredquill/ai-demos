#!/bin/bash

# AI Compare Diagnostic Script
echo "🔍 AI Compare Service Diagnostic"
echo "================================="

# Check if pods are running
echo -e "\n1️⃣ Pod Status:"
kubectl get pods -n ai-compare -l app.kubernetes.io/name=ai-compare-opentelemetry

# Check deployment status  
echo -e "\n2️⃣ Deployment Status:"
kubectl get deployment -n ai-compare

# Check service configuration
echo -e "\n3️⃣ Service Configuration:"
kubectl get service -n ai-compare

# Check recent logs for automation activity
echo -e "\n4️⃣ Recent Logs (last 50 lines):"
kubectl logs -n ai-compare deployment/ai-compare-ai-compare-opentelemetry-app --tail=50 | grep -E "(automation|observability|openlit|otel)" -i

# Check environment variables in running pod
echo -e "\n5️⃣ OpenTelemetry Environment Variables:"
kubectl exec -n ai-compare deployment/ai-compare-ai-compare-opentelemetry-app -- env | grep -E "(OTEL_|OBSERVABILITY|AUTOMATION)" | sort

# Check health endpoint
echo -e "\n6️⃣ Health Check:"
kubectl exec -n ai-compare deployment/ai-compare-ai-compare-opentelemetry-app -- curl -s http://localhost:8080/health | jq .

echo -e "\n✅ Diagnostic Complete"