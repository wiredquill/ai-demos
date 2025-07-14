# Installation Guide: NVIDIA Drivers

This guide provides a concise set of instructions to configure a SUSE Linux Enterprise Server (SLES) 15 SP6 or openSUSE Leap 15.6 machine with an NVIDIA GPU as a node in a Rancher-managed Kubernetes cluster and enable GPU workloads.

## 1. System Requirements

Before you begin, ensure you have the following:

* **Host System:** A machine with a clean installation of either SLES 15 SP6 (fully registered and patched) or openSUSE Leap 15.6 (fully updated).
* **NVIDIA GPU:** A compatible NVIDIA GPU. The modern G06 driver supports a wide range of cards, including but not limited to:
    * **Data Center GPUs:** A100, H100, L40S, etc.
    * **RTX Series:** RTX 6000 Ada, RTX 50-series (5090), RTX 40-series (4090, 4080), RTX 30-series (3090, 3080).

## 2. Host Preparation: Install NVIDIA Drivers

Choose one of the two methods below to install the NVIDIA drivers. The SUSE-provided method is recommended for official support, while the upstream NVIDIA method can be useful for newer drivers or to resolve dependency conflicts.

---

### Method A (Recommended): Use SUSE-Provided Repositories

This method uses the official SUSE module and the NVIDIA CUDA repository.

1.  **Add Driver Repositories:** Add the appropriate SUSE module for your distribution if you did not select the NVIDIA Modules during the initial install.

    * **For SLES 15 SP6:**
        ```bash
        # Add the NVIDIA Compute Module for SLES
        sudo SUSEConnect -p sle-module-NVIDIA-compute/15/x86_64
        ```

    * **For openSUSE Leap 15.6:**
        ```bash
        # Add the openSUSE community repository for NVIDIA drivers
        sudo zypper addrepo https://download.nvidia.com/opensuse/leap/15.6/ nvidia
        ```

    * **For BOTH Distributions:** Add the official NVIDIA CUDA repository.
        ```bash
        sudo zypper addrepo https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/cuda-sles15.repo
        sudo zypper refresh
        ```

---

### Method B (Alternative): Use Upstream NVIDIA Repositories

This method uses the official NVIDIA repositories for all components, which can help resolve version conflicts.

1.  **Add Driver Repositories:** Add the appropriate NVIDIA repositories for your specific SUSE distribution.

    * **For SLES 15 SP6:**
        ```bash
        # Add the official NVIDIA repository for SLES drivers and utils
        sudo zypper addrepo  https://download.nvidia.com/suse/sle15sp6/ nvidia
        sudo zypper refresh
        sudo zypper in nvidia-driver-G06-kmp-default
        ```

    * Reboot!

    * **For BOTH Distributions:** Add the official NVIDIA CUDA repository.
        ```bash
        sudo zypper addrepo https://developer.download.nvidia.com/compute/cuda/repos/sles15/x86_64/cuda-sles15.repo
        sudo zypper refresh
        ```

---

### Continue Installation (For Both Methods)

After adding repositories using either Method A or B, complete the installation with the following steps.

1. Uninstall the current drivers (Trust me, this solve most driver issues...)

    ```bash
    sudo zypper rm *nvidia*
    ```

2.  **Install NVIDIA Drivers and CUDA Toolkit:** Install the `cuda` package, which will pull in the correct, version-matched drivers as dependencies from the repositories you added.

    ```bash
    sudo zypper refresh
    sudo zypper install --auto-agree-with-licenses cuda
    ```

3.  **Reboot System:** A reboot is required to load the new NVIDIA kernel module.

    ```bash
    sudo reboot
    ```

4.  **Verify Driver Installation:** After rebooting, confirm the driver is working by running `nvidia-smi`. The command should now successfully display your GPU information without any errors.

    ```bash
    nvidia-smi
    ```
    ![Welcome](/assets/nvidia-smi.png)

    > **Troubleshooting: Driver Mismatch Error**
    > If you still see the `Failed to initialize NVML: Driver/library version mismatch` error after rebooting, it means the old kernel module is still loaded or there's a package conflict. A more robust solution is to fully remove the driver packages and then reinstall them.
    > ```bash
    > # 1. Remove the main cuda package; zypper will handle removing the old driver dependencies.
    > sudo zypper remove cuda
    > 
    > # 2. Reinstall cuda, which will pull in the correct, matching driver packages.
    > sudo zypper install --auto-agree-with-licenses cuda
    > 
    > # 3. Reboot again to load the correct module.
    > sudo reboot
    > ```