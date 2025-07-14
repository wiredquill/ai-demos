Demo 2: Deploying the SUSE AI Stack: Multiple Methods
Goal: Showcase the flexibility of deploying a complete, pre-configured AI application stack using various methods available through Rancher.

2.1: Installing from the Rancher UI
Goal: Highlight the simplicity of a one-click deployment from the Rancher Application Catalog.

Key Steps:

In the Rancher UI, navigate to the "Apps & Marketplace" or "App Catalog" section.

Search for and select a pre-built AI application or stack.

Review the configuration options and deploy the application with a single click.

Show the deployed resources in the Rancher dashboard.

What to Look For:

The speed and ease of getting a full AI stack running for experimentation or development.

2.2: Installing with Helm
Goal: Demonstrate how to automate the deployment for CI/CD integration using the standard Helm package manager.

Key Steps:

Show a values.yaml file used to configure the AI stack's Helm chart.

From a command line with kubectl and helm access, run a helm install command to deploy the application.

Switch back to the Rancher UI to show the application appearing as it's being deployed.

What to Look For:

How developers and operations teams can use familiar tools to manage the AI application lifecycle.

The repeatability and consistency provided by Helm-based deployments.

2.3: Installing with Fleet (GitOps)
Goal: Showcase a GitOps approach to managing the AI stack, ensuring consistency and declarative configuration across multiple clusters.

Key Steps:

Show a Git repository containing the Kubernetes manifests or Helm chart for the AI stack.

In the Rancher UI, navigate to the "Continuous Delivery" (Fleet) section.

Show the GitRepo resource pointing to the application repository and targeting one or more clusters.

Make a change in the Git repository (e.g., update an image tag) and commit it.

Watch as Fleet automatically detects the change and rolls out the update to the target cluster(s).

What to Look For:

The "single source of truth" for application configuration being the Git repository.

The automated, auditable, and scalable nature of GitOps for managing AI infrastructure.