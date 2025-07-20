# AI Demos Collection

A comprehensive collection of AI demonstration applications showcasing modern cloud-native AI workloads on SUSE's enterprise platform. This repository demonstrates end-to-end AI application deployment, security, observability, and management using SUSE's complete AI stack.

## 🚀 Overview

This collection provides practical demonstrations of:

- **AI Application Deployment**: Multiple deployment methods (Rancher UI, Helm, GitOps with Fleet)
- **GPU Acceleration**: Leveraging NVIDIA GPUs for AI workloads with SUSE's cloud-native platform
- **Pipeline Processing**: Advanced AI response processing with configurable pipeline levels
- **Security & Compliance**: Zero-trust security with SUSE NeuVector, including DLP monitoring
- **Observability**: Deep insights into GPU utilization, API consumption, and application performance
- **DevOps Integration**: CI/CD pipelines, automated testing, and development workflows

## 📦 Applications

### AI Compare App

The flagship application that demonstrates the power of AI pipeline processing by comparing responses from direct model access versus pipeline-enhanced responses.

**Key Features:**
- **Direct LLM Access**: Connect to local Ollama models (tinyllama, etc.)
- **Pipeline Processing**: Enhanced responses through Open WebUI pipelines with multiple sophistication levels
- **Real-time Comparison**: Side-by-side comparison of direct vs pipeline-enhanced responses
- **Provider Status Monitoring**: Live status checking of major AI providers (OpenAI, Anthropic, Google, etc.)
- **Security Demos**: Built-in demonstrations for SUSE NeuVector DLP monitoring
- **Observability**: OpenTelemetry integration with SUSE Observability for comprehensive monitoring

**Architecture:**
- **Ollama**: Local LLM inference server
- **Open WebUI**: Web interface with pipeline support
- **Pipelines Service**: Response enhancement processing
- **AI Compare App**: Custom Gradio-based comparison interface

## 🛠️ Quick Start

### Prerequisites

- Kubernetes cluster with GPU support (optional but recommended)
- Helm 3.x
- kubectl configured for your cluster

### Installation Methods

#### Method 1: Rancher UI (Recommended)

1. Access your Rancher cluster management interface
2. Navigate to Apps & Marketplace
3. Search for "AI Compare" 
4. Select either:
   - `ai-compare`: Upstream version (Debian-based)
   - `ai-compare-suse`: SUSE version (SUSE BCI-based)
5. Configure values and deploy

#### Method 2: Helm CLI

**SUSE Version (Recommended):**
```bash
# Add the repository (if using a Helm repo)
helm repo add ai-demos https://your-repo-url.com
helm repo update

# Install with basic configuration
helm install my-ai-demo charts/ai-compare-suse

# Install with GPU acceleration
helm install my-ai-demo charts/ai-compare-suse \
  --set ollama.gpu.enabled=true \
  --set ollama.hardware.type=nvidia

# Install with observability
helm install my-ai-demo charts/ai-compare-suse \
  --set llmChat.observability.enabled=true \
  --set llmChat.observability.otlpEndpoint="http://your-otlp-collector:4318"
```

**Upstream Version:**
```bash
helm install my-ai-demo charts/ai-compare
```

#### Method 3: GitOps with Fleet

```bash
# Deploy Fleet configuration
kubectl apply -f fleet/fleet.yaml

# Label target clusters
kubectl label cluster my-cluster needs-llm-suse=true    # For SUSE variant
kubectl label cluster my-cluster needs-llm=true        # For upstream variant
```

### Accessing the Application

After deployment, access the AI Compare interface:

```bash
# Port forward to access locally
kubectl port-forward svc/my-ai-demo-app-service 7860:7860

# Open browser to http://localhost:7860
```

## 🔧 Configuration

### GPU Support

Enable GPU acceleration for improved performance:

```yaml
ollama:
  gpu:
    enabled: true
  hardware:
    type: nvidia  # or amd, intel
```

### Observability Integration

Enable comprehensive monitoring with SUSE Observability:

```yaml
llmChat:
  observability:
    enabled: true
    otlpEndpoint: "http://opentelemetry-collector.suse-observability.svc.cluster.local:4318"
    collectGpuStats: true
```

### Development Mode

For rapid development and iteration:

```yaml
llmChat:
  devMode:
    enabled: true
    persistence:
      enabled: true
      size: 5Gi
    gitRepo: "https://github.com/your-org/ai-demos.git"
    gitBranch: "development"
```

**SSH Access:**
```bash
kubectl port-forward service/my-ai-demo-app-service 2222:22
ssh root@localhost -p 2222  # password: suse
```

## 🔒 Security Demonstrations

### Data Leak Prevention (DLP)

The AI Compare app includes built-in security demonstrations for SUSE NeuVector:

**Data Leak Demo:**
- **Dual Data Type Transmission**: Single button sends both credit card and Social Security Number data
- **Credit Card Pattern**: `3412-1234-1234-2222`
- **SSN Pattern**: `123-45-6789`
- **Clean UI**: Shows simple popup message "⚠️ Attempting to send sensitive data"
- **NeuVector Integration**: Triggers DLP monitoring and alerting for multiple data types
- **Comprehensive Detection**: Demonstrates advanced data loss prevention capabilities

**Availability Demo:**
- Tests external connectivity and network policies
- Validates security posture and network segmentation

### Zero-Trust Security

When deployed with NeuVector:
- Automatic security policy generation
- Runtime threat detection
- Network segmentation enforcement
- Vulnerability scanning and compliance reporting

## 📊 Observability & Monitoring

### GPU Metrics
- Real-time GPU utilization tracking
- Memory usage and temperature monitoring
- Performance bottleneck identification

### Application Metrics
- API token consumption tracking
- Response time analysis
- Pipeline processing performance
- Error rate and success metrics

### Infrastructure Monitoring
- Kubernetes resource utilization
- Network traffic analysis
- Storage and persistent volume metrics

## 🎯 Demonstration Scenarios

Follow these guided demonstrations to explore different aspects of the AI platform:

1. **[Demo 1: Accelerating AI with Rancher and GPUs](./demo-1.md)**
   - GPU infrastructure provisioning
   - Performance optimization techniques

2. **[Demo 2: Deploying the SUSE AI Stack](./demo-2.md)**
   - Multiple deployment methodologies
   - Rancher UI, Helm, and GitOps approaches

3. **[Demo 3: Monitoring AI with SUSE Observability](./demo-3.md)**
   - GPU utilization insights
   - Cost management and optimization

4. **[Demo 4: Building Trustworthy AI](./demo-4.md)**
   - Vulnerability scanning with NeuVector
   - Security policy automation

5. **[Demo 5: Zero-Trust Security for AI](./demo-5.md)**
   - Network security enforcement
   - Runtime threat protection

## 🔄 Development & CI/CD

### Automated Building

GitHub Actions workflows automatically:
- Build both upstream and SUSE Docker images
- Push to GitHub Container Registry (ghcr.io)
- Update Helm chart image tags
- Run comprehensive test suites

### Testing Framework

Comprehensive testing includes:
- Python unit tests with pytest
- Helm chart validation tests
- Integration testing for all components
- Security validation with test policies

### Development Workflow

```bash
# Local development setup
cd app
pip install -r requirements.txt
python python-ollama-open-webui.py

# Container development
docker build -f Dockerfile.suse -t ai-compare:suse .
docker run -p 7860:7860 ai-compare:suse
```

## 📁 Repository Structure

```
ai-demos/
├── app/                          # AI Compare application source
│   ├── python-ollama-open-webui.py  # Main application
│   ├── Dockerfile.suse              # SUSE BCI-based image
│   ├── Dockerfile.upstream          # Debian-based image
│   └── requirements.txt             # Python dependencies
├── charts/                       # Helm charts
│   ├── ai-compare/                  # Upstream chart
│   └── ai-compare-suse/             # SUSE-optimized chart
├── fleet/                        # GitOps deployment configs
├── pipelines/                    # AI pipeline configurations
├── install/                      # Infrastructure setup guides
├── docs/                         # Technical documentation
└── scripts/                      # Automation and utility scripts
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite
5. Submit a pull request

### Development Environment

```bash
# Setup development environment
git clone https://github.com/your-org/ai-demos.git
cd ai-demos
pip install -r app/requirements.txt
pip install -r app/test-requirements.txt

# Run tests
cd app && pytest
helm test my-release
```

## 📜 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Open an issue in this repository
- Check the [documentation](./docs/) for technical details
- Review the [installation guides](./install/) for setup assistance

---

**Powered by SUSE's Cloud-Native AI Platform**

This demonstration showcases SUSE's complete solution for enterprise AI workloads, from infrastructure provisioning to application security and observability.