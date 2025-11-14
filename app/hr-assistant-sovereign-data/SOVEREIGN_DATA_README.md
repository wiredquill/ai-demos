# HR Assistant - Sovereign Data Edition

## Overview

The HR Assistant Sovereign Data Edition is an advanced extension of the SUSE AI HR Assistant that includes comprehensive regional data sovereignty compliance capabilities. This application intelligently manages HR inquiries while enforcing local data protection laws and compliance requirements based on deployment region and country.

## Key Features

### 1. Regional Deployment Configuration
- **Three Global Regions**: Americas, EMEA (Europe, Middle East, Africa), and ASIA-Pac
- **Dynamic Country Selection**: Region-specific country lists with relevant data protection laws
- **Automatic Compliance Detection**: System automatically identifies when data sovereignty requirements apply

### 2. Data Sovereignty Compliance

#### Supported Regions

**Americas:**
- Canada, United States, Mexico, Brazil, Argentina, Chile, Colombia, Peru

**EMEA:**
- European Countries (with strict GDPR compliance): UK, Spain, Germany, France, Italy, Netherlands, Belgium, Poland, Sweden, Norway, Denmark, Finland, Austria, Ireland, Portugal, Greece, Czech Republic, Hungary, Romania, Bulgaria, Croatia, Slovenia, Slovakia, Luxembourg, Malta, Cyprus, Lithuania, Latvia, Estonia
- Middle Eastern & African Countries: UAE, Saudi Arabia, Israel, South Africa, Egypt, Nigeria, Kenya

**ASIA-Pac:**
- Australia, New Zealand, Japan, South Korea, China, India, Singapore, Malaysia, Thailand, Indonesia, Vietnam, Philippines, Taiwan, Hong Kong

#### Countries Requiring Data Sovereignty Acknowledgment

All EU Member States have strict data sovereignty requirements under GDPR and national implementations:

- **UK**: UK Data Protection Act 2018 + retained GDPR
- **Spain**: GDPR + LSSI-CE (Spanish Integrated Services Law)
- **Germany**: GDPR + TMG + NetzDG with BfDI (Federal Data Protection Authority) oversight
- **France**: GDPR + CNIL (National Commission for Data Protection)
- **Italy**: GDPR + Italian Data Protection Code with Garante oversight
- **Netherlands**: GDPR + Dutch Data Protection Act with AP oversight
- **Belgium**: GDPR + Belgian Data Protection Authority oversight
- **Poland**: GDPR + UODO (Polish Data Protection Authority)
- **Sweden**: GDPR + Datainspektionen (Swedish DPA)
- **Norway**: GDPR equivalent + Norwegian Personal Data Act
- **Denmark**: GDPR + Danish Data Protection Authority
- **Finland**: GDPR + Tietosuojavaltuutettu (Finnish DPA)
- **Austria**: GDPR + Austrian Data Protection Authority
- **Ireland**: GDPR + Irish Data Protection Commission
- **Portugal**: GDPR + Portuguese Data Protection Commission
- **Greece**: GDPR + Greek Data Protection Authority
- **Czech Republic**: GDPR + Czech Data Protection Authority
- **Hungary**: GDPR + Hungarian Data Protection Authority
- **Romania**: GDPR + Romanian Data Protection Authority
- **Bulgaria**: GDPR + Bulgarian Data Protection Commission
- **Croatia**: GDPR + Croatian Data Protection Authority
- **Slovenia**: GDPR + Slovenian Data Protection Authority
- **Slovakia**: GDPR + Slovak Data Protection Authority
- **Luxembourg**: GDPR + Luxembourg Data Protection Commission
- **Malta**: GDPR + Maltese Information and Data Protection Commissioner
- **Cyprus**: GDPR + Cyprus Data Protection Authority
- **Lithuania**: GDPR + Lithuanian Data Protection Authority
- **Latvia**: GDPR + Latvian Data Protection Authority
- **Estonia**: GDPR + Estonian Data Protection Inspectorate

### 3. Intelligent Compliance Workflow

1. **Deployment Region Selection**: Administrator selects the region during deployment
2. **Country Selection**: Administrator selects the specific country
3. **Compliance Check**: System automatically detects if the country requires data sovereignty compliance
4. **Acknowledgment Requirement**: For countries with sovereignty requirements, administrator must acknowledge "Adhere to local data laws"
5. **Runtime Enforcement**: Application includes compliance notices in all responses

### 4. API Endpoints

#### Root Endpoint
```
GET /
```
Returns deployment status including region, country, and compliance status.

**Example Response:**
```json
{
  "Status": "Ready",
  "Application": "HR Assistant - Sovereign Data Edition",
  "Deployment": {
    "region": "emea",
    "country": "Germany",
    "complianceEnabled": true
  }
}
```

#### Sovereign Data Information
```
GET /sovereign-data-info
```
Returns detailed information about data sovereignty requirements for the deployment.

**Example Response:**
```json
{
  "region": "emea",
  "country": "Germany",
  "requiresSovereigntyCompliance": true,
  "dataLaws": ["GDPR", "TMG", "NetzDG"],
  "sovereigntyDetails": "Germany has stringent data protection laws...",
  "complianceAcknowledged": true
}
```

#### HR Assistant Query
```
GET /ask
```
Main endpoint for HR queries. Responses include compliance context.

**Example Response:**
```json
{
  "answer": "Professional HR response...",
  "complianceContext": {
    "deploymentRegion": "emea",
    "deploymentCountry": "Germany",
    "sovereigntyCompliant": true
  },
  "sovereignDataCompliance": {
    "enabled": true,
    "acknowledged": true
  }
}
```

## Deployment Configuration

### Helm Installation

#### Basic Installation (Americas/No Sovereignty Requirements)
```bash
helm install my-release charts/hr-assistant-sovereign-data
```

#### European Deployment (with GDPR Compliance)
```bash
helm install my-release charts/hr-assistant-sovereign-data \
  --set deployment.region=emea \
  --set deployment.country=Germany \
  --set deployment.acknowledgeDataSovereignty=true \
  --set ollama.enabled=true
```

#### ASIA-Pac Deployment
```bash
helm install my-release charts/hr-assistant-sovereign-data \
  --set deployment.region=asia-pac \
  --set deployment.country=Singapore \
  --set ollama.enabled=true
```

### Rancher UI Configuration

When deploying via Rancher UI:

1. **Select Region**: Choose from Americas, EMEA, or ASIA-Pac
2. **Select Country**: Choose from the list filtered by region
3. **Data Sovereignty Acknowledgment**:
   - For EU countries: Checkbox is **pre-checked** and **required**
   - For other countries: Not shown (compliance not required)
4. **Acknowledge and Deploy**: Confirm compliance acknowledgment and deploy

### Environment Variables

The application accepts the following environment variables:

```bash
DEPLOYMENT_REGION=emea                           # Region: americas, emea, asia-pac
DEPLOYMENT_COUNTRY=Germany                       # Country within region
ACKNOWLEDGE_DATA_SOVEREIGNTY=true                # Compliance acknowledgment
APP_NAME=HRAssistant                            # Application mode
MODEL=llama3.2:1b                               # LLM model
OLLAMA_ENDPOINT=http://ollama:11434             # Ollama service
OTLP_ENDPOINT=http://collector:4318             # OpenTelemetry collector
COLLECT_GPU_STATS=false                         # GPU metrics collection
```

## Compliance Context in Responses

### European Deployment Example

When deployed in an EU country, responses include data sovereignty compliance information:

```
📋 Data Sovereignty Compliance Notice:
Deployment Country: Germany
Applicable Data Protection Laws: GDPR, TMG, NetzDG
Details: Germany has stringent data protection laws including GDPR, TMG (Telemediengesetz), and NetzDG. Data must be processed in compliance with German data protection authority (BfDI) requirements.
✓ Compliance Acknowledged: true
```

### Non-Compliant Deployment Warning

If compliance is required but not acknowledged:

```
⚠️ WARNING: Data Sovereignty Compliance Not Acknowledged
```

## Architecture

```
FastAPI Server
├── Sovereign Data Compliance Configuration
│   ├── Region Management
│   ├── Country Registry
│   └── Compliance Rules
│
├── HR Assistant Applications
│   ├── Simple HR Assistant (Conversational)
│   ├── HR Policy Database (Structured Queries)
│   └── Employee Handbook (RAG-based)
│
├── Compliance Enforcement
│   ├── Automatic Region/Country Detection
│   ├── Sovereignty Requirement Checking
│   ├── Compliance Notice Generation
│   └── Audit Logging
│
└── Integration
    ├── Ollama LLM
    ├── OpenTelemetry Observability
    └── Kubernetes ConfigMaps
```

## Configuration Files

### regions.json
Defines available regions and their associated countries.

```json
{
  "regions": [
    {
      "id": "americas",
      "name": "Americas",
      "countries": ["Canada", "United States", ...]
    },
    ...
  ]
}
```

### countries.json
Comprehensive country registry with data sovereignty details.

```json
{
  "countries": {
    "Germany": {
      "region": "emea",
      "requiresSovereigntyCompliance": true,
      "dataLaws": ["GDPR", "TMG", "NetzDG"],
      "sovereigntyDetails": "..."
    },
    ...
  }
}
```

## Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DEPLOYMENT_REGION=americas
export DEPLOYMENT_COUNTRY="United States"
export ACKNOWLEDGE_DATA_SOVEREIGNTY=true
export OLLAMA_ENDPOINT=http://localhost:11434
export OTLP_ENDPOINT=http://localhost:4318
export APP_NAME=HRAssistant

# Run application
python main.py
```

### Testing Compliance Features

```bash
# Test with EU deployment (compliance required)
curl -X GET http://localhost:8000/sovereign-data-info \
  -H "DEPLOYMENT_REGION: emea" \
  -H "DEPLOYMENT_COUNTRY: Germany"

# Test with Americas deployment (no compliance required)
curl -X GET http://localhost:8000/sovereign-data-info \
  -H "DEPLOYMENT_REGION: americas" \
  -H "DEPLOYMENT_COUNTRY: United States"
```

## Audit and Logging

The application automatically logs:

1. **Deployment Configuration**: Region, country, and compliance status
2. **Compliance Checks**: Whether data sovereignty requirements apply
3. **Acknowledgments**: Confirmation of compliance acknowledgment
4. **HR Interactions**: All HR queries include compliance context
5. **OpenTelemetry Traces**: Full observability with region/country context

## Compliance Verification

### Quick Status Check
```bash
# Check if deployment is compliant
kubectl exec deployment/my-release-hr-assistant -- curl localhost:8000/sovereign-data-info
```

### Audit Trail
All interactions include compliance context in OpenTelemetry traces for audit purposes.

## Support and Documentation

For detailed information about:
- **GDPR Compliance**: See individual country details in countries.json
- **Regional Regulations**: Refer to country configuration for applicable laws
- **Deployment Best Practices**: See CLAUDE.md for SUSE-specific guidance
- **HR Assistant Features**: See the original hr-assistant documentation

## Key Differences from Standard HR Assistant

| Feature | Standard HR Assistant | Sovereign Data Edition |
|---------|----------------------|------------------------|
| Regional Awareness | No | Yes (3 regions) |
| Country Selection | No | Yes (50+ countries) |
| Compliance Requirements | No | Yes (GDPR, etc.) |
| Data Sovereignty Notices | No | Yes (automatic) |
| Audit Logging | Basic | Enhanced with compliance context |
| Configuration | Static | Dynamic per deployment |

## Security Considerations

1. **Data Residency**: Ensure Ollama and data stores are in compliant regions
2. **Network Policies**: Implement egress controls for EU deployments
3. **Encryption**: Enable TLS for all communications
4. **RBAC**: Restrict access to ConfigMaps containing sovereignty configuration
5. **Audit**: Monitor access to /sovereign-data-info endpoint

## Version History

- **v1.0.0** (Initial Release): Full region/country support, GDPR compliance framework, dynamic configuration, API endpoints

## Contact

For questions about sovereign data compliance features, refer to the SUSE AI team or your regional data protection officer.
