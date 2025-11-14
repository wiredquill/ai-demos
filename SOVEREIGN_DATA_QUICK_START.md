# HR Assistant - Sovereign Data Edition: Quick Start Guide

## 📋 Table of Contents
- [Installation](#installation)
- [Deployment Examples](#deployment-examples)
- [Testing](#testing)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites
```bash
# Kubernetes cluster with Helm 3+
kubectl version
helm version

# Access to SUSE Application Collection (for Ollama)
helm repo add suse https://dp.apps.rancher.io/charts
helm repo update
```

### Add/Update Helm Repository
```bash
# If using a custom registry
helm repo add ai-demos [your-registry-url]
helm repo update
```

## Deployment Examples

### 1️⃣ Quick Deploy (Americas - No Compliance Required)

```bash
helm install my-hr-assistant charts/hr-assistant-sovereign-data \
  --namespace ai \
  --create-namespace \
  --set ollama.enabled=true
```

**What happens:**
- Region: Americas
- Country: United States
- Compliance: Not required
- Takes ~3-5 minutes to start

### 2️⃣ Europe Deployment (GDPR Compliant)

```bash
helm install my-hr-assistant charts/hr-assistant-sovereign-data \
  --namespace ai-eu \
  --create-namespace \
  --set deployment.region=emea \
  --set deployment.country=Germany \
  --set deployment.acknowledgeDataSovereignty=true \
  --set ollama.enabled=true \
  --set ollama.gpu.enabled=true
```

**What happens:**
- Region: EMEA
- Country: Germany
- Compliance: Required and acknowledged ✅
- All responses include GDPR/German law notices
- GPU acceleration enabled (if available)

### 3️⃣ Asia-Pacific Deployment

```bash
helm install my-hr-assistant charts/hr-assistant-sovereign-data \
  --namespace ai-apac \
  --create-namespace \
  --set deployment.region=asia-pac \
  --set deployment.country=Singapore \
  --set ollama.enabled=true
```

**What happens:**
- Region: ASIA-Pac
- Country: Singapore
- Compliance: Not required
- Local data protection laws referenced

### 4️⃣ Via Rancher UI

1. Go to **Cluster > Apps > Installed Apps**
2. Click **Install from Helm Repository**
3. Search for `hr-assistant-sovereign-data`
4. Click **Install**
5. Fill in deployment details:
   - **Region**: Select from dropdown (Americas, EMEA, ASIA-Pac)
   - **Country**: Select filtered list
   - **Compliance**: Auto-checked for EU (required)
6. Click **Deploy**

## Deployment Variations

### European Countries (All Require Compliance)
```bash
# Spain with GDPR
helm install hr-es charts/hr-assistant-sovereign-data \
  --set deployment.region=emea \
  --set deployment.country=Spain \
  --set deployment.acknowledgeDataSovereignty=true

# France with CNIL compliance
helm install hr-fr charts/hr-assistant-sovereign-data \
  --set deployment.region=emea \
  --set deployment.country=France \
  --set deployment.acknowledgeDataSovereignty=true

# UK with post-Brexit GDPR
helm install hr-uk charts/hr-assistant-sovereign-data \
  --set deployment.region=emea \
  --set deployment.country=UK \
  --set deployment.acknowledgeDataSovereignty=true
```

### Americas Countries (No Compliance Pre-Check)
```bash
# Canada with PIPEDA
helm install hr-ca charts/hr-assistant-sovereign-data \
  --set deployment.region=americas \
  --set deployment.country=Canada

# Brazil with LGPD
helm install hr-br charts/hr-assistant-sovereign-data \
  --set deployment.region=americas \
  --set deployment.country=Brazil

# Mexico
helm install hr-mx charts/hr-assistant-sovereign-data \
  --set deployment.region=americas \
  --set deployment.country=Mexico
```

### ASIA-Pac Countries (Regional Laws)
```bash
# Australia
helm install hr-au charts/hr-assistant-sovereign-data \
  --set deployment.region=asia-pac \
  --set deployment.country=Australia

# Japan with APPI
helm install hr-jp charts/hr-assistant-sovereign-data \
  --set deployment.region=asia-pac \
  --set deployment.country=Japan

# India with DPDP Act
helm install hr-in charts/hr-assistant-sovereign-data \
  --set deployment.region=asia-pac \
  --set deployment.country=India
```

## Testing

### Test 1: Verify Deployment Status

```bash
# Check pod status
kubectl get pods -n ai

# Check if ready
kubectl get deployment my-hr-assistant -n ai

# View logs
kubectl logs -f deployment/my-hr-assistant-hr-assistant -n ai
```

### Test 2: Check Compliance Configuration

```bash
# Get sovereign data info
kubectl exec -it deployment/my-hr-assistant-hr-assistant -n ai -- \
  curl localhost:8000/sovereign-data-info | jq

# Expected output for EU:
{
  "region": "emea",
  "country": "Germany",
  "requiresSovereigntyCompliance": true,
  "dataLaws": ["GDPR", "TMG", "NetzDG"],
  "sovereigntyDetails": "...",
  "complianceAcknowledged": true
}
```

### Test 3: Query HR Assistant

```bash
# Get a response (should include compliance notice)
kubectl exec -it deployment/my-hr-assistant-hr-assistant -n ai -- \
  curl localhost:8000/ask | jq

# For EU deployment, response will include:
# "📋 Data Sovereignty Compliance Notice:
#  Deployment Country: Germany
#  Applicable Data Protection Laws: GDPR, TMG, NetzDG"
```

### Test 4: Port Forward and Test Locally

```bash
# Forward port
kubectl port-forward -n ai deployment/my-hr-assistant-hr-assistant 8000:8000

# In another terminal, test endpoints:
curl http://localhost:8000/
curl http://localhost:8000/sovereign-data-info
curl http://localhost:8000/ask
```

### Test 5: Verify ConfigMap

```bash
# Check ConfigMap was created
kubectl get configmap -n ai | grep sovereign

# View countries configuration
kubectl get configmap my-hr-assistant-sovereign-data-config -n ai -o yaml

# Verify Germany is in countries list
kubectl get configmap my-hr-assistant-sovereign-data-config -n ai \
  -o jsonpath='{.data.countries\.json}' | jq '.countries.Germany'
```

## Verification

### ✅ Deployment Checklist

- [ ] **Pods Running**
  ```bash
  kubectl get pods -n ai
  # All pods show "Running" status
  ```

- [ ] **Compliance Configuration Loaded**
  ```bash
  kubectl logs deployment/my-hr-assistant-hr-assistant -n ai | grep "DEPLOYMENT"
  # Shows DEPLOYMENT_REGION and DEPLOYMENT_COUNTRY
  ```

- [ ] **ConfigMap Created**
  ```bash
  kubectl get configmap -n ai my-hr-assistant-sovereign-data-config
  # Should exist and have data
  ```

- [ ] **API Endpoints Responding**
  ```bash
  kubectl port-forward -n ai deployment/my-hr-assistant-hr-assistant 8000:8000 &
  curl http://localhost:8000/
  # Should return: {"Status": "Ready", ...}
  ```

- [ ] **Compliance Info Available**
  ```bash
  curl http://localhost:8000/sovereign-data-info | jq .
  # Should show region, country, compliance requirements
  ```

- [ ] **EU Deployments Show Notices**
  ```bash
  curl http://localhost:8000/ask | grep "Data Sovereignty"
  # Should include compliance notice (for EU)
  ```

### Regional Verification Matrix

| Region | Test Command | Expected Result |
|--------|--------------|-----------------|
| **Americas** | `curl /sovereign-data-info \| jq .requiresSovereigntyCompliance` | `false` |
| **EU** | `curl /sovereign-data-info \| jq .requiresSovereigntyCompliance` | `true` |
| **ASIA-Pac** | `curl /sovereign-data-info \| jq .requiresSovereigntyCompliance` | `false` |
| **Americas** | `curl /ask \| grep "Compliance Notice"` | No notice |
| **EU** | `curl /ask \| grep "Compliance Notice"` | Has notice |
| **ASIA-Pac** | `curl /ask \| grep "Compliance Notice"` | No notice |

## Troubleshooting

### Issue: Pod not starting

```bash
# Check events
kubectl describe pod my-hr-assistant-hr-assistant-xxxx -n ai

# Check logs
kubectl logs deployment/my-hr-assistant-hr-assistant -n ai

# Common causes:
# - Image pull failed
# - Insufficient resources
# - ConfigMap not created
```

### Issue: Compliance info not loading

```bash
# Check ConfigMap exists
kubectl get configmap my-hr-assistant-sovereign-data-config -n ai

# Check if mounted correctly
kubectl exec -it deployment/my-hr-assistant-hr-assistant -n ai -- \
  ls -la /app/countries.json

# Check file is readable
kubectl exec -it deployment/my-hr-assistant-hr-assistant -n ai -- \
  cat /app/countries.json | head -20
```

### Issue: Wrong region/country after upgrade

```bash
# Check current values
kubectl get deployment my-hr-assistant-hr-assistant -n ai -o yaml | grep DEPLOYMENT_

# Get values used in release
helm get values my-hr-assistant -n ai

# Upgrade with correct values
helm upgrade my-hr-assistant charts/hr-assistant-sovereign-data \
  -n ai \
  --set deployment.region=emea \
  --set deployment.country=Germany \
  --set deployment.acknowledgeDataSovereignty=true
```

### Issue: Compliance notice missing (for EU)

```bash
# Check environment variables set
kubectl exec deployment/my-hr-assistant-hr-assistant -n ai -- env | grep DEPLOYMENT

# Check if compliance acknowledgment is true
kubectl exec deployment/my-hr-assistant-hr-assistant -n ai -- env | grep ACKNOWLEDGE

# Verify country configuration
kubectl exec deployment/my-hr-assistant-hr-assistant -n ai -- \
  curl localhost:8000/sovereign-data-info | jq .
```

### Issue: ConfigMap has old data

```bash
# Delete ConfigMap
kubectl delete configmap my-hr-assistant-sovereign-data-config -n ai

# Redeploy
helm upgrade --force my-hr-assistant charts/hr-assistant-sovereign-data -n ai

# Or scale down and up to force pod restart
kubectl scale deployment my-hr-assistant-hr-assistant -n ai --replicas=0
kubectl scale deployment my-hr-assistant-hr-assistant -n ai --replicas=1
```

## Common Operations

### List All Supported Countries

```bash
# Get all available countries
kubectl get configmap my-hr-assistant-sovereign-data-config -n ai \
  -o jsonpath='{.data.countries\.json}' | jq '.countries | keys'

# Get EU countries only (requiresSovereigntyCompliance: true)
kubectl get configmap my-hr-assistant-sovereign-data-config -n ai \
  -o jsonpath='{.data.countries\.json}' | \
  jq '.countries | to_entries | map(select(.value.requiresSovereigntyCompliance == true)) | map(.key)'
```

### Change Deployment Region/Country

```bash
# Change from USA to Germany
helm upgrade my-hr-assistant charts/hr-assistant-sovereign-data \
  -n ai \
  --set deployment.region=emea \
  --set deployment.country=Germany \
  --set deployment.acknowledgeDataSovereignty=true

# Verify change
kubectl exec deployment/my-hr-assistant-hr-assistant -n ai -- \
  curl localhost:8000/sovereign-data-info | jq .country
```

### Enable GPU for European Deployment

```bash
helm install my-hr-assistant charts/hr-assistant-sovereign-data \
  -n ai-gpu \
  --create-namespace \
  --set deployment.region=emea \
  --set deployment.country=Germany \
  --set deployment.acknowledgeDataSovereignty=true \
  --set ollama.enabled=true \
  --set ollama.gpu.enabled=true \
  --set ollama.gpu.type=nvidia
```

### Scale Replicas

```bash
# Scale to 3 replicas
kubectl scale deployment my-hr-assistant-hr-assistant -n ai --replicas=3

# Check replicas
kubectl get deployment my-hr-assistant-hr-assistant -n ai
```

## Next Steps

1. **Test Your Deployment**: Run the verification checklist above
2. **Customize for Your Region**: Adjust resource limits as needed
3. **Enable Observability**: Connect to OpenTelemetry collector
4. **Configure Ingress**: Set up external access
5. **Monitor Compliance**: Track compliance notices in logs

## Support

- See `SOVEREIGN_DATA_README.md` for detailed documentation
- Check `HR_ASSISTANT_SOVEREIGN_DATA_OVERVIEW.md` for architecture
- Review `SOVEREIGN_DATA_IMPLEMENTATION_SUMMARY.md` for what was built
- Consult country-specific details in ConfigMap

---

**Quick Start v1.0** | Nov 14, 2024
