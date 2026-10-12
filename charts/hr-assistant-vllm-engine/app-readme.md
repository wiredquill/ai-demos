# HR Assistant (vLLM): vLLM serving engine

SUSE vLLM serving engine (GPU) for the HR Assistant. Serves the model over the OpenAI API; the router component in front of it discovers it by label.

Part of the **hr-assistant-vllm** SUSE AI Factory blueprint, which deploys each of its eight pods as a separate component. Install all eight into the same namespace (the blueprint does this for you).
