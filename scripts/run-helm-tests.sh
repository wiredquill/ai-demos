#!/bin/bash

# Helm Chart Test Runner for AI Compare
# Usage: ./scripts/run-helm-tests.sh [chart-name] [namespace]

set -e

CHART_NAME="${1:-ai-compare}"
NAMESPACE="${2:-ai-compare-test}"
CHART_PATH="charts/$CHART_NAME"

echo "========================================"
echo "🧪 AI Compare Helm Chart Test Runner"
echo "========================================"
echo "Chart: $CHART_NAME"
echo "Namespace: $NAMESPACE"
echo "Chart Path: $CHART_PATH"
echo ""

# Check if chart exists
if [ ! -d "$CHART_PATH" ]; then
    echo "❌ Chart not found: $CHART_PATH"
    echo "Available charts:"
    ls -1 charts/
    exit 1
fi

# Create namespace if it doesn't exist
echo "📦 Creating namespace if needed..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Lint the chart first
echo "🔍 Linting Helm chart..."
helm lint "$CHART_PATH"

# Validate template rendering
echo "🔧 Validating template rendering..."
helm template "$CHART_NAME" "$CHART_PATH" --namespace "$NAMESPACE" > /dev/null
echo "✅ Template validation passed"

# Install or upgrade the chart
echo "🚀 Installing/upgrading chart..."
if helm status "$CHART_NAME" -n "$NAMESPACE" > /dev/null 2>&1; then
    echo "Upgrading existing release..."
    helm upgrade "$CHART_NAME" "$CHART_PATH" --namespace "$NAMESPACE" --wait --timeout 10m
else
    echo "Installing new release..."
    helm install "$CHART_NAME" "$CHART_PATH" --namespace "$NAMESPACE" --wait --timeout 10m
fi

# Wait for pods to be ready
echo "⏳ Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod --all -n "$NAMESPACE" --timeout=300s

# Run Helm tests
echo "🧪 Running Helm tests..."
helm test "$CHART_NAME" -n "$NAMESPACE" --logs

# Show test results
echo ""
echo "📊 Test Results Summary:"
kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/managed-by=Helm" --show-labels

echo ""
echo "✅ All tests completed successfully!"
echo ""
echo "🧹 To cleanup test environment:"
echo "   helm uninstall $CHART_NAME -n $NAMESPACE"
echo "   kubectl delete namespace $NAMESPACE"