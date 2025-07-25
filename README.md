# AI Demos Collection

**Comprehensive enterprise AI demonstrations showcasing SUSE's complete cloud-native AI platform**

This repository provides end-to-end demonstrations of AI application deployment, security, observability, and management using SUSE's enterprise-grade cloud-native stack. Perfect for sales demonstrations, technical evaluations, and hands-on learning.

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

This repository contains a complete collection of AI demonstration materials organized into three main categories:

### **1. 🤖 AI Compare Application**
A production-ready AI response comparison tool that demonstrates:
- **Direct vs Pipeline-Enhanced AI Responses**: Side-by-side comparison of local LLM responses vs processed responses
- **Security Demonstrations**: Built-in NeuVector DLP testing with dual data type transmission
- **Enterprise Integration**: OpenTelemetry observability, GPU acceleration, persistent storage
- **Multi-Deployment Options**: Rancher UI, Helm CLI, GitOps with Fleet

### **2. 📋 Platform Demonstrations** 
Guided demonstrations covering:
- **Infrastructure**: GPU provisioning and management with Rancher
- **Deployment**: Multiple deployment methodologies for AI workloads
- **Observability**: AI-specific monitoring with SUSE Observability
- **Security**: Container security and runtime protection with NeuVector
- **Zero-Trust**: Network security and policy enforcement

### **3. 🏗️ Enterprise Infrastructure**
Complete deployment automation including:
- **Helm Charts**: Production-ready charts for both upstream and SUSE variants
- **GitOps**: Fleet-based continuous deployment configurations
- **Observability**: Pre-configured monitoring and alerting
- **Security**: NeuVector policy automation and DLP configurations

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

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/new-demo`
3. **Make your changes**: Add new demos or improve existing ones
4. **Test thoroughly**: Ensure all demos work in both SUSE and upstream environments
5. **Submit a pull request**: Include clear description of changes

### **Development Environment**
```bash
# Setup local development
git clone https://github.com/your-org/ai-demos.git
cd ai-demos/app
pip install -r requirements.txt
python python-ollama-open-webui.py

# Run tests
pytest tests/
helm test my-release
```

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