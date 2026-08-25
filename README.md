# AI Demos Collection

**Enterprise AI applications and demonstrations for SUSE's cloud-native platform**

This repository is scoped to the applications this project actively develops:
**AI Compare** and **HR Assistant** (including the sovereign-data variant). Their
source code lives under `app/`, `frontend/`, `frontend-react/`, and `pipelines/`,
and their deployable Helm charts under `charts/`.

Standalone/shared Helm charts (ollama, open-webui, ollama-suse, ollama-upstream,
ollama-webui-upstream, rancher-ai-ollama, rancher-ai-vllm, stable-diffusion,
genai-observability-demo, etc.) have moved to the dedicated charts repository
**`wiredquill/helm-charts`** (GitHub Pages catalog, installable via Rancher).

---

## 📋 Table of Contents

- [🎯 Repository Overview](#-repository-overview)
- [🚀 AI Compare Application](#-ai-compare-application)
- [📖 Available Demonstrations](#-available-demonstrations)
- [🛠️ Quick Start](#️-quick-start)
- [📁 Repository Structure](#-repository-structure)
- [🔧 Advanced Configuration](#-advanced-configuration)
- [🤝 Contributing](#-contributing)

---

## 🎯 Repository Overview

This repository provides a curated collection of enterprise-ready AI applications and comprehensive demonstration materials organized into three main categories:

### **1. 🤖 AI Applications** (source in this repo)
Production Helm charts for the apps actively developed here:

- **AI Compare** - AI response comparison tool with security and observability demonstrations
  - `ai-compare-suse`: Enterprise SUSE BCI-based edition
  - `ai-compare`: Upstream community edition
  - `ai-compare-opentelemetry`: Advanced GenAI observability edition with token/cost tracking
- **HR Assistant** - RAG-based HR assistant
  - `hr-assistant`: Full stack with OpenTelemetry, Qdrant/OpenSearch retrieval
  - `hr-assistant-sovereign-data`: Sovereign-data variant

> Standalone Ollama / Open WebUI / Rancher AI / Stable Diffusion charts now live in `wiredquill/helm-charts`.

**Key Application Features:**
- **Security Demonstrations**: Built-in NeuVector DLP testing with dual data type transmission
- **Enterprise Integration**: OpenTelemetry observability, GPU acceleration, persistent storage
- **Multi-Deployment Options**: Rancher UI, Helm CLI, GitOps with Fleet
- **Flexible Architecture**: Direct model access or pipeline-enhanced processing

### **2. 📋 Platform Demonstrations**
Guided demonstrations covering the complete AI application lifecycle:
- **Infrastructure**: GPU provisioning and management with Rancher
- **Deployment**: Multiple deployment methodologies for AI workloads
- **Observability**: AI-specific monitoring with SUSE Observability
- **Security**: Container security and runtime protection with NeuVector
- **Zero-Trust**: Network security and policy enforcement

### **3. 🏗️ Enterprise Infrastructure**
Complete deployment automation and configurations:
- **Helm Charts**: Production-ready charts for all applications with SUSE and upstream variants
- **GitOps**: Fleet-based continuous deployment configurations
- **Observability**: Pre-configured monitoring and alerting
- **Security**: NeuVector policy automation and DLP configurations

### **📦 Available Charts**

| Chart Name | Version | Description | Variants |
|------------|---------|-------------|----------|
| `ai-compare-suse` | 0.1.x | Enterprise AI comparison app (SUSE BCI) | Production |
| `ai-compare` | 0.1.x | AI comparison app (Upstream) | Community |
| `ai-compare-opentelemetry` | 0.1.x | Enhanced GenAI observability edition | Advanced |
| `ollama-suse` | 0.1.x | LLM inference server (SUSE) | Enterprise |
| `ollama-upstream` | 0.1.x | LLM inference server (Upstream) | Community |

**Adding New Applications:**
This repository is designed to grow as a catalog of AI applications. To add new applications, package them as Helm charts and submit via pull request following the existing chart structure.

---

## 🚀 AI Compare Application

### **Core Functionality**
The flagship AI Compare application provides real-time comparison between:

- **🤖 Direct Ollama**: Local LLM inference (TinyLlama, Llama2, custom models)
- **🌐 Pipeline-Enhanced**: Processed responses through Open WebUI pipelines with educational levels:
  - 👶 Kid-friendly explanations
  - 🎓 Student-level responses
  - ⚗️ Scientific detailed analysis

### **Built-in Security Demonstrations**

#### **🔒 Data Leak Prevention (DLP) Demo**
- **Dual Data Transmission**: Single button sends both credit card and SSN data
- **Credit Card**: `3412-1234-1234-2222`
- **Social Security Number**: `123-45-6789`
- **NeuVector Integration**: Triggers real-time DLP monitoring and alerting
- **Clean Interface**: Simple popup showing "⚠️ Attempting to send sensitive data"

#### **🌐 Availability Demo**
- **External Connectivity**: Tests connection to https://suse.com
- **Network Policy Validation**: Demonstrates network segmentation capabilities
- **Security Monitoring**: Validates outbound connection policies

### **Enterprise Features**
- **📊 Real-time Observability**: OpenTelemetry integration with SUSE Observability
- **🖥️ GPU Acceleration**: NVIDIA GPU support with runtime configuration
- **💾 Persistent Storage**: Model caching and configuration persistence
- **🔄 Automation**: Background testing and response comparison
- **👥 Provider Monitoring**: Live status of major AI providers (OpenAI, Anthropic, Google, etc.)

---

## 📖 Available Demonstrations

### **Platform Demonstrations (Guided Walkthroughs)**

| Demo | Focus Area | Duration | Key Takeaways |
|------|------------|----------|---------------|
| **[Demo 1: Accelerating AI with Rancher and GPUs](./demo-1.md)** | Infrastructure | 15 min | GPU provisioning, cluster management, hardware optimization |
| **[Demo 2: Deploying the SUSE AI Stack](./demo-2.md)** | Deployment | 20 min | Rancher UI, Helm CLI, GitOps deployment methods |
| **[Demo 3: Monitoring AI with SUSE Observability](./demo-3.md)** | Observability | 15 min | GPU metrics, cost tracking, performance optimization |
| **[Demo 4: Building Trustworthy AI](./demo-4.md)** | Security | 20 min | Container scanning, vulnerability management, policy automation |
| **[Demo 5: Zero-Trust Security for AI](./demo-5.md)** | Network Security | 15 min | Runtime protection, network policies, threat detection |

### **Interactive Application Demos (Built-in)**

| Demo | Trigger | Data Transmitted | NeuVector Detection |
|------|---------|------------------|-------------------|
| **🔒 Data Leak Demo** | Single Button | Credit Card + SSN | Multi-pattern DLP alerts |
| **🌐 Availability Demo** | Single Button | HTTPS Request | Network policy validation |

---

## 🛠️ Quick Start

### **Prerequisites**
- Kubernetes cluster (RKE2 recommended)
- Helm 3.x
- kubectl configured
- Optional: GPU nodes with NVIDIA drivers

### **Adding the Repository**

#### **Option 1: Rancher UI (ClusterRepo)**
Add this repository to Rancher's Apps & Marketplace by creating a ClusterRepo resource:

1. Navigate to **Cluster → More Resources → Catalog (catalog.cattle.io) → ClusterRepos**
2. Click **Create from YAML**
3. Apply the following configuration:

```yaml
apiVersion: catalog.cattle.io/v1
kind: ClusterRepo
metadata:
  name: ai-demos
spec:
  url: https://wiredquill.github.io/ai-demos
```

4. Click **Create** - Charts will appear in Apps & Marketplace within 1-2 minutes

#### **Option 2: Helm Repository**
```bash
# Add the Helm repository
helm repo add ai-demos https://wiredquill.github.io/ai-demos

# Update repository index
helm repo update

# Search available charts
helm search repo ai-demos

# Install a chart
helm install my-release ai-demos/ai-compare-suse
```

### **Deployment Options**

#### **Option 1: Rancher Apps & Marketplace (Recommended)**
1. Open Rancher cluster management interface
2. Navigate to **Apps & Marketplace**
3. Search for "AI Compare"
4. Select variant:
   - `ai-compare-suse`: Enterprise SUSE edition
   - `ai-compare`: Upstream community edition
5. Configure and deploy

#### **Option 2: Helm CLI**
```bash
# SUSE Enterprise Edition
helm install ai-demo charts/ai-compare-suse \
  --set ollama.gpu.enabled=true \
  --set aiCompare.observability.enabled=true

# Upstream Community Edition
helm install ai-demo charts/ai-compare
```

#### **Option 3: GitOps with Fleet**
```bash
# Deploy Fleet configuration
kubectl apply -f fleet/fleet.yaml

# Label target clusters
kubectl label cluster my-cluster needs-llm-suse=true
```

### **Access the Application**
```bash
# Port forward to access locally
kubectl port-forward svc/ai-demo-app-service 7860:7860

# Open browser to http://localhost:7860
```

---

## 📁 Repository Structure

```
ai-demos/
├── 📱 app/                           # AI Compare application source
│   ├── python-ollama-open-webui.py     # Main Gradio application
│   ├── Dockerfile.suse                 # SUSE BCI-based container
│   ├── Dockerfile.upstream             # Debian-based container
│   ├── requirements.txt                # Python dependencies
│   └── tests/                          # Application test suite
├── 📦 charts/                        # Production Helm charts
│   ├── ai-compare/                     # Upstream community chart
│   └── ai-compare-suse/               # SUSE enterprise chart
├── 📋 Demo Guides/                   # Step-by-step demonstrations
│   ├── demo-1.md                       # GPU infrastructure with Rancher
│   ├── demo-2.md                       # Multi-method deployment
│   ├── demo-3.md                       # SUSE Observability monitoring
│   ├── demo-4.md                       # Container security with NeuVector
│   └── demo-5.md                       # Zero-trust network security
├── 🚀 fleet/                         # GitOps deployment automation
│   ├── fleet.yaml                      # Fleet configuration
│   └── gpu-operator/                   # GPU operator automation
├── 🔧 install/                       # Infrastructure setup guides
│   ├── README.md                       # Installation overview
│   ├── Install-GPU-Operator.md        # GPU infrastructure setup
│   ├── Enable-SUSE-AI-Observability.md # Monitoring configuration
│   └── Install-NVIDIA-drivers.md      # Driver installation guide
├── 🔄 pipelines/                     # AI pipeline configurations
│   ├── response_level_pipeline.py     # Educational response processing
│   └── pipeline_config.yaml           # Pipeline configuration
├── 📊 docs/                          # Technical documentation
│   ├── OPENTELEMETRY-INTEGRATION.md   # Observability setup
│   ├── AUTOMATED-DEPLOYMENT.md        # CI/CD configuration
│   └── AI-MODEL-CACHING.md           # Model caching strategies
├── 🖼️ assets/                        # Screenshots and documentation images
└── 🔨 scripts/                       # Automation and utility scripts
```

---

## 🔧 Advanced Configuration

### **GPU Acceleration**
```yaml
ollama:
  gpu:
    enabled: true
  hardware:
    type: nvidia
```

### **Enterprise Observability**
```yaml
aiCompare:
  observability:
    enabled: true
    otlpEndpoint: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
    collectGpuStats: true
```

### **Security Integration**
```yaml
neuvector:
  enabled: true
  dlpPolicies: true
  securityDemos: true
```

### **Development Mode**
```yaml
aiCompare:
  devMode:
    enabled: true
    persistence:
      enabled: true
    gitRepo: "https://github.com/your-org/ai-demos.git"
```

---

## 🤝 Contributing

This repository welcomes contributions of new AI applications, improved demonstrations, and enhanced documentation.

### **Adding New AI Applications to the Catalog**

To add a new AI application to the repository:

1. **Create Helm Chart Structure**
   ```bash
   # Create chart directory following naming convention
   mkdir -p charts/your-app-name-suse
   mkdir -p charts/your-app-name  # for upstream variant
   ```

2. **Package Your Application**
   - Follow existing chart patterns (see `charts/ai-compare-suse` as reference)
   - Include both SUSE BCI and upstream variants when possible
   - Add comprehensive values.yaml with documentation
   - Include README.md explaining application purpose and configuration

3. **Test Your Chart**
   ```bash
   # Lint the chart
   helm lint charts/your-app-name-suse

   # Test deployment
   helm install test-release charts/your-app-name-suse
   helm test test-release
   ```

4. **Submit Pull Request**
   - Charts are automatically packaged and published to gh-pages branch via CI/CD
   - Include demo documentation if applicable
   - Update main README.md to list your application in the catalog table

### **General Contributions**

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-app` or `git checkout -b feature/improved-demo`
3. **Make your changes**: Add new applications, demos, or improvements
4. **Test thoroughly**: Ensure all changes work in both SUSE and upstream environments
5. **Submit a pull request**: Include clear description of changes and testing performed

### **Development Environment**
```bash
# Setup local development
git clone https://github.com/wiredquill/ai-demos.git
cd ai-demos

# For application development
cd app
pip install -r requirements.txt
python python-ollama-open-webui.py

# For chart development
helm lint charts/your-chart-name
helm install test charts/your-chart-name --dry-run --debug

# Run tests
pytest tests/
helm test my-release
```

### **Chart Packaging and Publishing**

Charts are automatically packaged and published via GitHub Actions:
- Commits to `main` trigger automatic chart packaging
- Charts are published to gh-pages branch
- Rancher ClusterRepo and Helm repository automatically pick up updates
- Manual packaging: See `.github/workflows/` for CI/CD pipeline details

---

## 📜 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **📖 Documentation**: Check the [docs/](./docs/) directory for detailed technical guides
- **🛠️ Installation Help**: Review [install/README.md](./install/README.md) for setup assistance
- **🐛 Issues**: Open an issue in this repository for bug reports or feature requests
- **💬 Discussions**: Use GitHub Discussions for questions and community support

---

**Powered by SUSE's Enterprise Cloud-Native AI Platform**

*Complete demonstrations of enterprise AI workloads from infrastructure provisioning to application security and observability.*
