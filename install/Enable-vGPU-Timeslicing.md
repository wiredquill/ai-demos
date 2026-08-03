# Configuring NVIDIA vGPU Time-Slicing in a Rancher-Managed Cluster

This guide details how to configure the NVIDIA GPU Operator to enable "virtual GPUs" (vGPUs) via time-slicing on an existing, Rancher-managed Kubernetes cluster. Time-slicing allows a single physical NVIDIA GPU to be shared by multiple pods, which is ideal for running multiple, less-intensive workloads, maximizing resource utilization, and demonstrating GPU sharing.

> **Fleet automation:** If you use Fleet GitOps, the time-slicing config is already automated in this repo under `fleet/gpu-operator/` — the HelmChart CR (`gpu-operator.yaml`, pinned to GPU Operator v26.3.3) references a `time-slicing-config` ConfigMap (`time-slicing-config.yaml`) that slices each GPU into 8 replicas and sets `DEVICE_LIST_STRATEGY=cdi-annotations`. Deploy the `fleet/gpu-operator/` directory to a fleet-managed cluster and time-slicing is configured end-to-end. The manual steps below remain for clusters not using Fleet.

## Prerequisites

This guide assumes you have already completed the following setup:

- **A Running Kubernetes Cluster:** Your cluster is operational and managed by Rancher.
- **NVIDIA GPU Node:** At least one node in your cluster has a physical NVIDIA GPU.
- **NVIDIA GPU Operator:** The NVIDIA GPU Operator is already successfully installed in the `gpu-operator` namespace. Recommended: v26.3.3 or newer.
- **Rancher Management:** Your cluster is imported into and managed by your Rancher instance.
- **`kubectl` Access:** Your `kubectl` command-line tool is configured to communicate with your cluster.

## Step 1: Establish a Baseline

Before enabling time-slicing, let's verify the current state of the GPU resources.

1.  **Check GPU Operator Health:**
    Ensure all operator pods are `Running` or `Completed`. This is critical for the `ClusterPolicy` to be available.
    ```bash
    kubectl get pods -n gpu-operator
    ```
    ![Results](/assets/kubectl-gpu-operator-results.png)

2.  **Check Allocatable GPUs:**
    Check how many GPUs are currently advertised by your node. For a single GPU, this should be `1`.
    ```bash
    kubectl describe nodes | grep nvidia.com/gpu
    ```
    *Expected output for a single GPU node:*
    ```
    nvidia.com/gpu:               1
    nvidia.com/gpu:               1
    ```

## Step 2: Define the Time-Slicing Configuration

We will create a Kubernetes `ConfigMap` that defines how we want to slice up the GPU.

1.  Create a file named `time-slicing-config.yaml`. This configuration tells the operator to slice each physical GPU into **4** virtual replicas. You can change the `replicas` value to suit your needs (e.g., 2, 8, etc.).

    ```yaml
    # time-slicing-config.yaml
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: time-slicing-config
      namespace: gpu-operator
    data:
      any: |-
        version: v1
        sharing:
          timeSlicing:
            resources:
            - name: nvidia.com/gpu
              replicas: 4
    ```

2.  Apply the `ConfigMap` to your cluster:
    ```bash
    kubectl apply -f time-slicing-config.yaml
    ```

## Step 3: Activate Time-Slicing in the GPU Operator

Now we instruct the GPU Operator to use the `ConfigMap` we just created.

1.  **Find Your `ClusterPolicy` Name:** The operator's default policy name can vary. Find the correct name with this command:
    ```bash
    kubectl get clusterpolicies -n gpu-operator
    ```
    Look at the `NAME` column. Common names are `cluster-policy` or `gpu-cluster-policy`.

2.  **Patch the `ClusterPolicy`:**
    Use the name you discovered in the command below. This command patches the policy to activate the device plugin configuration from our `ConfigMap`.

    > **Note:** Replace `cluster-policy` in the command below if your policy has a different name.

    ```bash
    # IMPORTANT: Replace 'cluster-policy' if your policy has a different name!
    kubectl patch clusterpolicy/cluster-policy -n gpu-operator --type merge \
      --patch '{"spec": {"devicePlugin": {"config": {"name": "time-slicing-config", "default": "any"}}}}'
    ```
    A success message should confirm the resource was patched. The `nvidia-device-plugin` pod will automatically restart to apply the new configuration.

## Step 4: Verify and Demonstrate vGPU in Rancher

> **Known rke2/k3s issue (fixed in fleet config):** on rke2/k3s clusters the GPU Operator chart's *default* toolkit config points at `/run/containerd` and `/etc/containerd`, which are NOT where rke2's containerd lives. Symptoms: `nvidia-container-toolkit-daemonset` CrashLoopBackOff and pods failing with `unresolvable CDI devices management.nvidia.com/gpu=GPU-...`. Two fixes are required:
> 1. **Toolkit socket paths** (rke2): set `toolkit.env.CONTAINERD_CONFIG=/var/lib/rancher/rke2/agent/etc/containerd/config.toml` and `CONTAINERD_SOCKET=/run/k3s/containerd/containerd.sock` (already in `fleet/gpu-operator/gpu-operator.yaml`).
> 2. **CDI device list strategy** (time-slicing on containerd): set `devicePlugin.env.DEVICE_LIST_STRATEGY=cdi-annotations`. The chart default `volume-mounts` makes the runtime fall back to the `management.nvidia.com/gpu` CDI spec (which only contains the `all` device), so time-sliced GPU pods fail with `unresolvable CDI devices`. With `cdi-annotations`, kubelet injects `cdi.k8s.io/k8s.device-plugin.nvidia.com/gpu=GPU-...` annotations and containerd resolves the device from the correct spec.
>
> Verify after enabling: `kubectl get nodes -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}'` should show the replica count (e.g. `8`).

### Verify the Configuration

1.  **Check for New vGPU Resources:**
    After a minute, run the verification command again.
    ```bash
    kubectl describe nodes | grep nvidia.com/gpu
    ```
    *The output should now show your new replica count (e.g., `4`), confirming that your single physical GPU is now advertising multiple virtual GPUs.*
    ```
    nvidia.com/gpu:               4
    nvidia.com/gpu:               4
    ```

### Demonstrate with a Workload

Now, let's deploy multiple pods to prove the sharing works, using the Rancher UI.

1.  Navigate to your cluster in the **Rancher UI**.
2.  Go to **Workload > Deployments** and click **Create**.
3.  **General Tab:**
    - Give the Deployment a **Name** (e.g., `gpu-test-workload`).
    - Set the **Replicas** to **4** (or the number you configured).
4.  **Container Tab:**
    - Set the **Image** to a CUDA-enabled image, for example: `nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04`.
5.  **Resources Tab:**
    - Click **Add Resource**.
    - In the **Resource Type** dropdown, select `nvidia.com/gpu`.
    - Set the **Request** and **Limit** for that resource to `1`.
6.  Click **Create**.

Within moments, you will see all 4 pods of your deployment in a `Running` state. Each pod has successfully requested `1` `nvidia.com/gpu` resource, and Kubernetes has scheduled all of them onto the same physical GPU, proving that your vGPU time-slicing configuration is working perfectly.
