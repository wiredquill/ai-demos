# Installation Guide: NVIDIA Datacenter GPU Manager (DCGM)

This guide details how to install and configure the NVIDIA Datacenter GPU Manager (DCGM).
We need the NVIDIA DCGM driver to export GPU data to SUSE Observability.

## Install NVIDIA Datacenter GPU Manager (DCGM)


1. Set variable to current CUDA version
```
CUDA_VERSION=$(nvidia-smi | sed -E -n 's/.*CUDA Version: ([0-9]+)[.].*/\1/p')
```

2. Install DCGM with zypper

```
sudo zypper install --no-confirm \
                      --recommends \
                      datacenter-gpu-manager-4-cuda${CUDA_VERSION}
```
3. Enable Service

```
systemctl --now enable nvidia-dcgm
```

4. Verify Service is running

```
systemctl status nvidia-dcgm
```

![Status](/assets/systemctl-status-nvidia-dcgm-result.png)


5. Enable DCGMI Health

```
dcgmi health -s a
```

6. View current modules in dcgmi and verify `Core`, `NvSwitch` and `Health` are enabled

```
dcgmi modules -l
```

![DCGMI](/assets/dcgmi-modules-results.png)