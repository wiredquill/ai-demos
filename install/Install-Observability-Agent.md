# Installation Guide: SUSE Observability Agent

This guide details how to install the SUSE Observability Agent.

## Add the SUSE Observability Agent Repository in the UI

`name` = 
`https://charts.rancher.com/server-charts/prime/suse-observability`

![Welcome](/assets/add-suse-observability-repo.png)

Install the SUSE AI Observability Agent

![Welcome](/assets/stackpack-install-credentials.png)



In the Terminal 

```
helm repo add suse-observability https://charts.rancher.com/server-charts/prime/suse-observability
helm repo update
```

![Welcome](/assets/install-observability-agent-ai-cluster.png)
