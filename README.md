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

## 🧩 SUSE AI Factory Blueprints

The `catalog/blueprints/` directory holds SUSE AI Factory **Blueprints** for the
demos. A Blueprint (`ai-factory.suse.com/v1alpha1`, cluster-scoped, on the
Rancher management cluster) lists Helm charts as **components**. When you edit or
deploy a blueprint, the AI Factory UI shows each component together with the
install form from its chart's `questions.yaml`. An **AIWorkload** then deploys
the components to a downstream cluster as Fleet bundles.

### hr-assistant-vllm 1.5.0: SUSE charts plus the app pods

The infrastructure components are SUSE's own charts, so the AI Factory UI shows
the real chart name and version, just as `simple-chatbot-with-rag` does. SUSE's
`vllm` and `opensearch` charts ship no install form, so
`scripts/package-aif-suse-charts.sh` republishes them to `wiredquill-ai-demos`,
keeping SUSE's name and version and adding the `questions.yaml` from
`catalog/charts/<chart>/`. For `vllm` it also applies
`catalog/charts/vllm/form-friendly-values.patch`. The patch:
- makes the form's Storage Class (`Default` = the cluster default) and Shared NFS
  Model Cache switch work. Upstream, an empty storage class disables dynamic
  provisioning, and shared storage switches on whenever the key exists.
- points `HF_HOME` at the NFS cache when it's enabled. Upstream mounts the cache
  but keeps downloading into the per-install PVC.
- sets `app.kubernetes.io/managed-by: Helm` on the engine and router Deployments'
  and Services' own labels. The cluster rewrites upstream's lowercase `helm`, so
  Fleet reported the vllm bundle as Modified. Selectors and pod labels keep `helm`,
  because selectors are immutable and changing them would make upgrades fail. The version list for those two
therefore shows only the versions republished there. Each of the four app pods has its own small chart
with its own `questions.yaml`. Those charts vendor `charts/hr-assistant-vllm`
(alias `hr`) and switch on only their own workload:

| Component | Repo / version | Release | Pods |
|---|---|---|---|
| `vllm` | wiredquill-ai-demos 0.1.10 (SUSE chart + form) | `vllm` | engine (GPU) + router (`vllm-router-service`) |
| `qdrant` | suse-ai-registry 1.19.0 | `qdrant` | Qdrant (`qdrant:6333`) |
| `opensearch` | wiredquill-ai-demos 3.8.0 (SUSE chart + form) | `opensearch` | OpenSearch (`opensearch-cluster-master:9200`) |
| `hr-assistant-vllm-policy-db` | wiredquill-ai-demos 0.1.1 | `hr-policy-db` | HR Policy DB + dashboard (NodePort 30081) |
| `hr-assistant-vllm-handbook` | wiredquill-ai-demos 0.1.1 | `employee-handbook` | Employee Handbook |
| `hr-assistant-vllm-app` | wiredquill-ai-demos 0.1.1 | `hr-assistant` | HR Assistant |
| `hr-assistant-vllm-load-gen` | wiredquill-ai-demos 0.1.1 | `load-gen` | load generator + health-check emitter |

That's seven components and eight pods. SUSE's `vllm` chart provides both the
engine and the router, and a blueprint can list each `chartName` only once.

Install everything into **one namespace**. The release names are pinned because the
app forms default to the SUSE charts' Service names (`vllm-router-service`,
`qdrant`, `opensearch-cluster-master`). The app components share
`fullnameOverride: hr-assistant-vllm`, so they reach each other as
`hr-assistant-vllm-<app>`. If the `vllm` component serves a different model,
select the same **Model served by vLLM** in the three app forms.

The all-in-one `hr-assistant-vllm` chart is unchanged for Rancher Apps installs.

### Installing a blueprint on a cluster with SUSE AI Factory

**Prerequisites**
- A Rancher management cluster with SUSE AI Factory installed (the `aif-operator`
  and the AI Factory UI extension).
- A downstream target cluster with:
  - an NVIDIA GPU and the GPU operator;
  - a default StorageClass;
  - the shared SUSE AI collector (`charts/ai-observability-collector`, Service
    `opentelemetry-collector` in namespace `observability`);
  - pull secrets named `application-collection` and `suse-registry` in the target
    namespace, or set `hr.imagePullSecrets` in each form.

**1. Publish the charts to the git ClusterRepo AI Factory reads.** Rancher's git
catalog indexes only a root `index.yaml` plus packaged `.tgz` files on the tracked
branch (`aif/hr-assistant-vllm`):
```bash
git checkout main && git pull
mkdir -p /tmp/aif && rm -f /tmp/aif/*.tgz
for c in charts/hr-assistant-vllm charts/hr-assistant-vllm-*/; do
  helm package "$c" --dependency-update -d /tmp/aif
done
# SUSE vllm + opensearch with install forms (needs: helm registry login dp.apps.rancher.io)
scripts/package-aif-suse-charts.sh /tmp/aif
git checkout aif/hr-assistant-vllm
cp /tmp/aif/*.tgz .
helm repo index . --url https://github.com/wiredquill/ai-demos
git add index.yaml hr-assistant-vllm*.tgz vllm-*.tgz opensearch-*.tgz
git commit -s -m "chore(aif): publish hr-assistant-vllm component charts"
git push origin aif/hr-assistant-vllm
```

**2. Register the ClusterRepo** (once per management cluster):
```yaml
apiVersion: catalog.cattle.io/v1
kind: ClusterRepo
metadata:
  name: wiredquill-ai-demos   # blueprints reference this as chartRepo
spec:
  gitRepo: https://github.com/wiredquill/ai-demos
  gitBranch: aif/hr-assistant-vllm
```
```bash
kubectl apply -f clusterrepo.yaml
# after a push, force a refresh and confirm the new commit was picked up
kubectl patch clusterrepo wiredquill-ai-demos --type=merge -p "{\"spec\":{\"forceUpdate\":\"$(date -u +%FT%TZ)\"}}"
kubectl get clusterrepo wiredquill-ai-demos -o jsonpath='{.status.commit}'
```
The operator fetches charts from git ClusterRepos at deploy time, which needs
`Settings.spec.rancherCatalog` set (a Rancher token in a secret). On vimes, use
`url: https://rancher.cattle-system` and `insecureSkipVerify: true`.

**3. Check that a component's form will render.** This is the endpoint the wizard
calls; the response must include a top-level `questions` array:
```bash
curl -sk -H "Authorization: Bearer $TOKEN" \
  "https://<rancher>/v1/catalog.cattle.io.clusterrepos/wiredquill-ai-demos?link=info&chartName=hr-assistant-vllm-policy-db&version=0.1.1" \
  | jq '.questions | length'
```

**4. Create the blueprint** on the management cluster:
```bash
kubectl apply -f catalog/blueprints/hr-assistant-vllm-1-5-0.yaml
kubectl get blueprints.ai-factory.suse.com -l ai-factory.suse.com/blueprint-name=hr-assistant-vllm
```

**5. Deploy it.** In Rancher, go to **AI Factory → Blueprints → SUSE AI HR
Assistant (vLLM) 1.5.0 → Deploy**. Pick the target cluster and a namespace that
nothing else uses, then review each component (the `vllm` component holds the
model and HF token).
To deploy from YAML instead, use an AIWorkload. `componentValues` is keyed by
chart name, and values sit under `hr:`:
```yaml
apiVersion: ai-factory.suse.com/v1alpha1
kind: AIWorkload
metadata:
  name: hr-assistant-vllm
  namespace: aif-operator
spec:
  displayName: HR Assistant (vLLM)
  deployStrategy: FleetBundle        # required for Blueprint sources
  source:
    sourceType: Blueprint
    blueprint:
      name: hr-assistant-vllm
      version: "1.5.0"
  targetClusters:
    - c-m-xxxxxxxx                   # Rancher cluster ID, not the display name
  targetNamespace: hr-assistant-vllm
  componentValues:
    - componentName: hr-assistant-vllm-policy-db
      values:
        hr:
          service:
            nodePort: 30082          # if 30081 is taken on the cluster
```

**6. Verify** on the target cluster. Expect eight pods (vLLM engine and router,
qdrant, opensearch-cluster-master, and the four `hr-assistant-vllm-*` apps):
```bash
kubectl get pods -n hr-assistant-vllm
kubectl logs -n hr-assistant-vllm deploy/hr-assistant-vllm-load-gen -c load-gen --tail=5
```

> **Gotchas** (all hit in practice)
> - `deployStrategy` must be `FleetBundle`. With the default `Helm`, a
>   Blueprint-sourced workload creates nothing and stays `Pending`.
> - `targetClusters` takes the Rancher cluster ID (`c-m-…`). Look it up with
>   `kubectl get clusters.fleet.cattle.io -A -o custom-columns=NAME:.metadata.name,ID:.metadata.labels.management\\.cattle\\.io/cluster-name`.
> - A `Degraded` phase with the bundle in a `Modified` loop is Fleet re-patching
>   `app.kubernetes.io/managed-by` labels. It's cosmetic; the pods run fine.
> - The engine downloads the model on first start (~15 GB for Qwen2.5-7B). Until
>   it's ready, the app pods answer `/ask` with errors.
> - The engine reserves 90% of GPU memory. If another vLLM engine already holds the
>   GPU (for example a leftover all-in-one install), it fails with `Free memory on
>   device … is less than desired GPU memory utilization`.
> - On Rancher-provisioned clusters, the AIWorkload can show `Degraded` even when
>   every bundle is Ready. The operator tracks the target under both its cluster ID
>   (`c-m-…`, which stays Pending) and its Fleet name (which shows Running). Check
>   the Fleet bundles and the pods instead.
> - The first engine start downloads the model unless the Shared NFS Model Cache
>   already holds it. An interrupted Hugging Face download makes the engine exit
>   once, and the restart resumes the download.
> - Editing a blueprint in the UI saves a new blueprint version with every value
>   baked in, secrets such as `hf_token` included. It takes the next patch version
>   (e.g. 1.4.2 → 1.4.3), so publish repository versions with a minor bump to avoid
>   overwriting a UI-saved one. Blueprints are readable across
>   the whole management cluster.

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
