
# Installation Guide: NVIDIA GPU Operator

The GPU Operator is best installed via a `HelmChart` resource managed by Fleet or directly with Helm. The key is to provide the correct `containerd` paths for RKE2 and disable the operator's own driver installation, as you have already installed it on the host.

This Helm chart enables the NVIDIA dcgm staticts to be read by SUSE Observability AI Plug-in  

Here is an example `HelmChart` manifest to deploy via Fleet.

```yaml
# Save as gpu-operator-chart.yaml
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata: 
  name: gpu-operator
  namespace: kube-system # Deploys the chart resource into kube-system
spec:
  repo: https://helm.ngc.nvidia.com/nvidia
  chart: gpu-operator
  targetNamespace: gpu-operator # Installs the operator into its own namespace
  createNamespace: true
  valuesContent: |-
    # GPU Operator component settings
    driver:
      enabled: false # Important: Do not let the operator manage the driver
    devicePlugin:
      enabled: true
    dcgm:
      enabled: true
    dcgmExporter:
      enabled: true
    nodeStatusExporter:
      enabled: true
    # Environment-specific settings for RKE2/K3s
    toolkit:
      env:
      - name: CONTAINERD_CONFIG
        value: /var/lib/rancher/rke2/agent/etc/containerd/config.toml
      - name: CONTAINERD_SOCKET
        value: /run/k3s/containerd/containerd.sock
```

Apply this manifest to your cluster:

```bash
kubectl apply -f gpu-operator-chart.yaml
```

You can Watch the deployment via the Rancher Console

![Welcome](/assets/gpu-operator-rancher-deploy.gif)


## 5. Verify the GPU Operator Installation

1.  **Check the Operator Pods:** Ensure all pods in the `gpu-operator` namespace are `Running` or `Completed`.

    ```bash
    kubectl get pods -n gpu-operator
    ```

    ![Welcome](/assets/kubectl-verify-gpu-operator.png)

2.  **Run a Test Pod:** Deploy a simple test pod that requests a GPU resource and runs `nvidia-smi`.

    ```yaml
    # Save as gpu-test.yaml
    apiVersion: v1
    kind: Pod
    metadata:
      name: nvidia-smi-test
    spec:
      runtimeClassName: nvidia
      restartPolicy: OnFailure
      containers:
      - name: gpu-test-container
        image: nvidia/cuda:12.1.0-base-ubuntu22.04
        command: ["nvidia-smi"]
        resources:
          limits:
            nvidia.com/gpu: 1
    ```

3.  **Apply and Check Logs:**

    ```bash
    kubectl apply -f gpu-test.yaml
    # Wait for the pod to complete
    kubectl logs nvidia-smi-test
    ```

If the logs show the `nvidia-smi` output, your installation is successful.

  ![Welcome](/assets/kubectl-logs-nvidia-smi-test.png)

4.  Delete the pod

    ```bash
    kubectl delete -f gpu-test.yaml
    # Wait for the pod to complete
    ```
