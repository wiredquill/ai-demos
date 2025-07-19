# AI Compare

Welcome to AI Compare! This comprehensive demonstration shows the differences between direct AI model access and pipeline-enhanced responses. The project highlights building, deploying, and managing AI applications on SUSE's cloud-native platform with configuration change detection for SUSE Observability demos.

Follow along with these demos to see how SUSE provides an end-to-end solution for accelerating your AI initiatives, from infrastructure provisioning to application security and observability.

## Demos

Click on a demo below for detailed steps and key takeaways.

1.  [**Demo 1: Accelerating AI with Rancher and GPUs**](./demo-1.md)
    * *Highlights: Provisioning GPU-accelerated infrastructure for AI workloads with Rancher.*

2.  [**Demo 2: Deploying the SUSE AI Stack: Multiple Methods**](./demo-2.md)
    * *Highlights: Demonstrating flexible application deployment using the Rancher UI, Helm, and a GitOps approach with Fleet.*

3.  [**Demo 3: Monitoring AI with SUSE Observability**](./demo-3.md)
    * *Highlights: Gaining deep insights into GPU utilization and API token consumption to manage performance and cost.*

4.  [**Demo 4: Building Trustworthy AI on a Secure Foundation**](./demo-4.md)
    * *Highlights: Using SUSE NeuVector to scan for vulnerabilities and automatically profile application behavior before deployment.*

5.  [**Demo 5: Zero-Trust Security for AI Applications**](./demo-5.md)
    * *Highlights: Securing all internal and external network traffic for a running AI application with NeuVector's zero-trust model.*

## Development and Advanced Configuration

This section provides details on advanced configuration options and how to set up a development environment for the LLM Chat application.

### LLM Chat Development Mode

For rapid iteration and development, you can enable a special development mode for the LLM Chat application. This mode allows you to SSH into the running application pod and perform `git pull` operations to update the code without rebuilding and redeploying the container image.

**Features:**
-   **SSH Access:** Gain direct shell access to the application container.
-   **Persistent Code Storage:** Application code is stored on a Persistent Volume, allowing changes to persist across pod restarts.
-   **On-the-fly Code Updates:** Update the application code by simply running `git pull` inside the container.

**How to Use:**

1.  **Build the Development Docker Image:**
    The development mode requires a specialized Docker image that includes SSH capabilities. This image is built via a dedicated GitHub Actions workflow.
    *   Navigate to the "Actions" tab in your GitHub repository.
    *   Select the workflow named "Build, Push, and Update K8s Manifests (upstream & SUSE)".
    *   On the left sidebar, click on "build-push-dev" (or similar name if changed).
    *   Manually trigger this workflow. This will build the `app/Dockerfile.dev` image and push it to your GitHub Container Registry (GHCR) with a `-dev` tag (e.g., `ghcr.io/wiredquill/ai-demos-dev:latest-dev`). This step is typically only needed once, or when `app/Dockerfile.dev` itself is modified.

2.  **Deploy the Helm Chart in Development Mode:**
    When deploying the `ai-compare` or `ai-compare-suse` Helm chart, enable the development mode by setting `llmChat.devMode.enabled` to `true`. You can also customize other development-specific settings.

    **Example Helm Command:**
    ```bash
    helm upgrade --install my-dev-release charts/ai-compare \
      --set llmChat.devMode.enabled=true \
      --set llmChat.devMode.image.repository=ghcr.io/wiredquill/ai-demos-dev \
      --set llmChat.devMode.image.tag=latest-dev \
      --set llmChat.devMode.persistence.enabled=true \
      --set llmChat.devMode.gitRepo=https://github.com/wiredquill/ai-demos.git \
      --set llmChat.devMode.gitBranch=openweb-ui-dev # Replace with your development branch
    ```
    *   **`llmChat.devMode.enabled`**: Set to `true` to activate development mode.
    *   **`llmChat.devMode.image.repository`**: The repository for your development image (default: `ghcr.io/wiredquill/ai-demos-dev`).
    *   **`llmChat.devMode.image.tag`**: The tag for your development image (default: `latest-dev`).
    *   **`llmChat.devMode.persistence.enabled`**: Set to `true` to enable persistent storage for the application code.
    *   **`llmChat.devMode.persistence.size`**: The size of the Persistent Volume Claim (e.g., `1Gi`, `5Gi`).
    *   **`llmChat.devMode.persistence.storageClassName`**: (Optional) Specify a storage class name for the PVC. Leave empty to use the default.
    *   **`llmChat.devMode.gitRepo`**: The Git repository URL to clone for the initial code (default: `https://github.com/wiredquill/ai-demos.git`).
    *   **`llmChat.devMode.gitBranch`**: The Git branch to checkout for the initial code (default: `main`).

3.  **Access the Pod via SSH:**
    Once the Helm chart is deployed and the LLM Chat pod is running, the service will expose port 22 for SSH access.
    *   You can use `kubectl port-forward` to forward the SSH port to your local machine (e.g., `kubectl port-forward service/ollama-chat-app-service 2222:22`).
    *   Then, SSH into the pod: `ssh root@localhost -p 2222`.
    *   The default password for the `root` user is `suse`.
    *   Inside the pod, navigate to the `/app` directory. You can now perform `git pull` to fetch the latest code changes from your development branch.

### Ollama Model Persistence

By default, Ollama models are stored in an `emptyDir` volume, meaning they are lost if the pod restarts. You can enable persistent storage for Ollama models to avoid re-downloading them.

**How to Use:**

When deploying the `ai-compare` or `ai-compare-suse` Helm chart, enable Ollama persistence by setting `ollama.persistence.enabled` to `true`.

**Example Helm Command:**
```bash
helm upgrade --install my-release charts/ai-compare \
  --set ollama.persistence.enabled=true \
  --set ollama.persistence.size=50Gi \
  --set ollama.persistence.storageClassName=my-storage-class # Optional
```
*   **`ollama.persistence.enabled`**: Set to `true` to enable persistent storage for Ollama models.
*   **`ollama.persistence.size`**: The size of the Persistent Volume Claim for Ollama models (e.g., `10Gi`, `50Gi`).
*   **`ollama.persistence.storageClassName`**: (Optional) Specify a storage class name for the PVC. Leave empty to use the default.