Demo 5: Zero-Trust Security for AI Applications
Goal: Showcase how SUSE NeuVector enforces a zero-trust security model for a running AI workload, providing deep network visibility and protection for both internal and external traffic.

Key Steps:

In the NeuVector UI, ensure the AI application group is in Monitor or Protect Mode.

Navigate to the "Network Activity" view to see a live map of all network connections.

View Internal Traffic: Point out the legitimate "east-west" traffic between the internal components of the AI application (e.g., connections from a web frontend to a backend inference service).

View External Traffic: Explicitly highlight the allowed "egress" traffic from the application to external AI model APIs (e.g., OpenAI, Anthropic, Hugging Face).

Simulate an Attack: Attempt an unauthorized connection from one of the containers (e.g., curl to a malicious website or an unapproved API).

Show the violation being logged and, in Protect Mode, actively blocked by NeuVector.

What to Look For:

The clear, visual map of all network traffic, with a distinct view of internal vs. external connections.

How NeuVector's allow-list model secures both inter-service communication and external API access.

Real-time threat detection and prevention that stops unauthorized data exfiltration or communication.