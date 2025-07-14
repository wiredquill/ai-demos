Demo 1: Accelerating AI with Rancher and GPUs
Goal: Demonstrate the ease of provisioning and managing GPU-accelerated infrastructure for AI workloads using Rancher.

Key Steps:

Log in to the Rancher management console.

Navigate to the target Kubernetes cluster.

Show the cluster's node configuration, highlighting the presence of GPU-enabled nodes.

Deploy a sample AI/ML workload (e.g., a Jupyter Notebook or a TensorFlow training job) that specifically requests GPU resources.

Verify from the command line or Rancher UI that the pod is successfully scheduled on a GPU node and has access to the GPU.

What to Look For:

The simplicity of the Rancher UI for managing complex, GPU-enabled clusters.

How Kubernetes, managed by Rancher, seamlessly handles the scheduling of pods onto specialized GPU hardware.

The pod specification (pod.yaml) clearly requesting a nvidia.com/gpu resource.