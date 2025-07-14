# Configuration Guide: SUSE AI Observability Plugin

This guide details how to configure the SUSE AI Observability Plugin.

# Prerequisites

- Rancher Cluster
- SUSE Observabiity installed on a dedicated downstream cluster
- Downstream Cluster with GPU
    - GPU drivers enabled in the OS
    - Nvidia datacenter-gpu-manager installed
    - Nvidia Kubernetes GPU Operator installed
- DNS entry 
    - Observability
    - Otel-collector

# Installation of SUSE AI Observability Plugin


## Installing the Observability Agent


First, install the CLI for StackState if you haven’t already. To do this, go to the WebUI for SUSE Observability and select “CLI” from the left menu. The command with the API token will be created for you:

## Install SUSE AI Observability Extension

```
vi gen-ai-values.yaml
```

# genai-values.yaml

```
global:
  imagePullSecrets:
  - application-collection 
serverUrl: https://SUSE_OBSERVABILITY_API_URL
apiKey: SUSE_OBSERVABILITY_API_KEY
tokenType: SUSE_OBSERVABILITY_API_TOKEN_TYPE
apiToken: SUSE_OBSERVABILITY_TOKEN
clusterName: OBSERVED_SERVER_NAME
```

![Welcome](/assets/detials-for-genai-values.png)

helm upgrade --install --namespace suse-observability -f gen-ai-values.yaml genai-observability oci://dp.apps.rancher.io/charts/suse-ai-observability-extension --version 1.0.1

![Welcome](/assets/gen-ai-values.png)

## Create Secret for Opentelemtry Agent


```
kubectl create secret generic open-telemetry-collector --namespace suse-observability --from-literal=API_KEY='<from>'
```

```
helm upgrade --install opentelemetry-collector oci://dp.apps.rancher.io/charts/opentelemetry-collector --version 0.127.2 -f otel-values.yaml -n suse-observability
```

## Activating the Rancher UI Observability extension

First, install the CLI for StackState if you haven’t already. To do this, go to the WebUI for SUSE Observability and select “CLI” from the left menu. The command with the API token will be created for you:
