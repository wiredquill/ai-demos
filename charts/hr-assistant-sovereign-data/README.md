# HR Assistant - Sovereign Data Edition

## Overview

**HR Assistant - Sovereign Data Edition** is an intelligent employee support system powered by advanced AI models. It provides instant access to HR policies, employee handbook information, and policy database queries with complete transparency through direct model response comparison. This specialized edition includes comprehensive data sovereignty compliance features designed for global deployments across different regions and countries.

## 🌍 Regional Data Sovereignty

This chart includes built-in data protection features specifically designed for global deployments:

### 🔒 Data Sovereignty & Compliance
- **GDPR Compliance**: Automatic GDPR enforcement for EU deployments
- **Regional Requirements**: Data residency regulations and local data protection laws
- **Automatic Detection**: Intelligent region and country-based compliance identification
- **Policy Application**: Configurable data protection policies per deployment location

### 🗺️ Supported Regions

#### 🌎 Americas
- United States, Canada, Mexico, Brazil, Chile, Colombia, Argentina, Peru
- **Compliance**: Standard data protection practices

#### 🌍 EMEA (Europe, Middle East, Africa)
- 27 EU Member States, UK, Norway, plus Switzerland, Turkey, Russia, Ukraine, Israel
- **Compliance**: GDPR + national data protection laws enforced automatically

#### 🌏 ASIA-PAC (Asia-Pacific)
- Australia, China, India, Indonesia, Japan, Malaysia, New Zealand, Philippines, Singapore, South Korea, Thailand, Vietnam, Pakistan, Bangladesh
- **Compliance**: Regional data protection requirements

## 🏗️ Architecture Components

This chart deploys a complete HR Assistant stack with multiple components:

### 🦙 Ollama - Local LLM Server
- **Purpose**: Local large language model inference for HR queries
- **Technology**: Open-source LLM runtime
- **Models**: TinyLlama, Llama2, and custom models
- **Features**: GPU acceleration, model caching, API access

### 📚 Employee Handbook Service
- **Purpose**: Searchable employee handbook and HR policies
- **Technology**: FastAPI backend with full-text search
- **Features**: Policy database queries, document indexing

### 📋 HR Policy Database
- **Purpose**: Comprehensive HR policy information system
- **Technology**: Database backend with policy templates
- **Features**: Policy templates, compliance rules, documentation

### 🐍 HR Assistant Chat - Custom Comparison App
- **Purpose**: Side-by-side HR query response comparison
- **Technology**: Python + Gradio web framework
- **Features**: Direct Ollama vs enhanced responses, automation
- **Monitoring**: OpenTelemetry observability integration

## ✨ Key Features

### 🌐 **Global Deployment Ready**
- Multi-region configuration (Americas, EMEA, ASIA-Pac)
- Country-specific compliance settings
- Automatic data protection policy application

### 📜 **Data Sovereignty Compliance**
- GDPR enforcement for EU countries
- National data protection law compliance
- Data residency requirements enforcement
- Compliance acknowledgment and tracking

### 🔄 **Response Comparison**
- Side-by-side comparison of direct model responses vs enhanced responses
- Real-time response analysis and metrics
- Educational demonstrations with different response levels

### 🚀 **Easy Deployment**
- One-click installation via Rancher Apps & Marketplace
- Region-based configuration wizard
- Automatic compliance policy application
- GPU acceleration support with NVIDIA runtime

### 📊 **Observability Ready**
- OpenTelemetry integration with SUSE Observability
- Request tracing and token usage monitoring
- Performance metrics and compliance auditing
- GPU statistics collection and monitoring

### ⚙️ **Automation**
- Automated testing and response generation
- Configurable prompt rotation and scheduling
- Background traffic generation for monitoring demos
- Compliance verification automation

## 🚀 Quick Start

1. **Install from Rancher Apps & Marketplace**
   - Navigate to Apps & Marketplace
   - Search for "HR Assistant - Sovereign Data Edition"
   - Click Install

2. **Configure Regional Settings**
   - Select deployment region (Americas, EMEA, or ASIA-Pac)
   - Choose specific country
   - Accept data sovereignty compliance requirements (if applicable)

3. **Basic Configuration**
   - Choose your deployment namespace
   - Enable GPU support if available
   - Configure storage preferences
   - Set observability endpoints

4. **Access the Application**
   - HR Assistant Chat: `http://<cluster-ip>:<node-port>`
   - Employee Handbook: `http://<cluster-ip>:<handbook-port>`
   - Ollama API: `http://<cluster-ip>:<ollama-port>`

## 📋 Prerequisites

- **Kubernetes Cluster**: v1.24+
- **Storage**: Persistent volumes for model caching (recommended)
- **GPU Support**: NVIDIA GPU Operator (optional but recommended)
- **Memory**: 4GB+ available for model loading
- **CPU**: 2+ cores recommended
- **Internet**: For initial model downloads

## ⚙️ Configuration Options

### Regional Settings
- **Deployment Region**: Choose from Americas, EMEA, or ASIA-Pac
- **Deployment Country**: Auto-filtered by selected region
- **Compliance Acknowledgment**: Required for countries with GDPR/data sovereignty laws

### Basic Settings
- **Namespace**: Target deployment namespace
- **Model Selection**: Choose from available LLM models
- **Service Types**: NodePort, ClusterIP, or LoadBalancer
- **Resource Limits**: CPU and memory allocation

### Advanced Settings (Optional)
- **GPU Acceleration**: Enable NVIDIA GPU support
- **Persistent Storage**: Model caching and data persistence
- **Observability**: OpenTelemetry and SUSE Observability integration
- **Automation**: Background testing and monitoring configurations

## 🔒 Compliance Features

### GDPR Countries (EU)
When deploying to EU member states (Austria, Belgium, Bulgaria, Croatia, Cyprus, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Poland, Portugal, Romania, Slovakia, Slovenia, Spain, Sweden) or UK and Norway:

- Automatic GDPR compliance detection
- Data residency enforcement
- National data protection law compliance
- Compliance acknowledgment requirement
- Policy application option (automatic or manual)

### Non-EU Countries
Deployments to non-EU regions proceed with standard data protection practices without additional compliance requirements.

## 🎯 Use Cases

- **HR Support System**: Employee policy and handbook queries
- **Global HR Operations**: Multi-region HR service deployment
- **Compliance Training**: Data sovereignty and compliance demonstrations
- **Development & Testing**: AI/ML demonstrations with compliance focus
- **Educational Platform**: Teaching data protection and regional compliance

## 📚 Documentation

- **Configuration Guide**: Detailed setup and configuration instructions
- **Compliance Guide**: GDPR and data sovereignty compliance details
- **Troubleshooting**: Common issues and solutions
- **Best Practices**: Deployment and operational best practices

## 🔧 Support

For issues, questions, or feature requests, please refer to:
- **Documentation**: [SUSE AI Products](https://www.suse.com/products/ai/)
- **GitHub**: [SUSE AI Demos](https://github.com/wiredquill/ai-demos)

## 📄 License

This chart is part of the SUSE AI Demos project. Refer to the repository for license information.

## 🙏 Acknowledgments

Built with contributions from the SUSE AI Team and the open-source community. Uses:
- [Ollama](https://ollama.ai/) - Local LLM inference
- [OpenTelemetry](https://opentelemetry.io/) - Observability framework
- [SUSE BCI](https://documentation.suse.com/bci/) - Container base images

---

**Version**: 1.2.20
**Updated**: November 14, 2025
**Maintainer**: SUSE AI Team
