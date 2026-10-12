# HR Assistant (vLLM): vLLM router

SUSE vLLM router: the OpenAI-compatible entry point (Service vllm-router-service when installed as release vllm). Discovers the engine pods in the namespace by label.

Part of the **hr-assistant-vllm** SUSE AI Factory blueprint, which deploys each of its eight pods as a separate component. Install all eight into the same namespace (the blueprint does this for you).
