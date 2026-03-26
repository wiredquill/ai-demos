"""
Ollama client for LLM inference with OpenLit instrumentation.
Uses the ollama library directly to produce gen_ai.system=ollama spans
which are required for SUSE Observability GenAI LLM System view.
"""

import logging
import os
from typing import Dict, List

import ollama
import openlit

logger = logging.getLogger(__name__)


class OllamaOpenAIClient:
    def __init__(self, ollama_url: str = None):
        """Initialize Ollama client."""
        self.ollama_url = ollama_url or os.getenv("OLLAMA_ENDPOINT", "http://ollama-service:11434")
        self.client = ollama.Client(host=self.ollama_url)  # type: ignore[attr-defined]

    @openlit.trace
    def chat_with_ollama(self, messages: List[Dict[str, str]], model: str = "llama3.2:latest") -> str:
        """Chat with Ollama using the ollama library with OpenLit tracing."""
        try:
            logger.info(f"Chatting with Ollama model: {model}")
            response = self.client.chat(
                model=model,
                messages=messages,
            )
            # OpenLit's instrumentation wrapper may return a dict instead of ChatResponse
            if isinstance(response, dict):
                response_content = response.get("message", {}).get("content", "")
                total_tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
            else:
                response_content = response.message.content
                total_tokens = getattr(response, "eval_count", 0) + getattr(response, "prompt_eval_count", 0)
            if total_tokens:
                logger.info(f"GenAI cost tracking - Tokens: {total_tokens}")

            return response_content
        except Exception as e:
            logger.error(f"Error in chat_with_ollama: {e}")
            return f"Error communicating with Ollama: {str(e)}"

    @openlit.trace
    def single_prompt(self, prompt: str, model: str = "llama3.2:latest") -> str:
        """Single prompt with OpenLit tracing."""
        try:
            messages = [{"role": "user", "content": prompt}]
            return self.chat_with_ollama(messages, model)
        except Exception as e:
            logger.error(f"Error in single_prompt: {e}")
            return f"Error: {str(e)}"

    @openlit.trace
    def ask_endpoint_handler(self, prompt: str = "Why is the sky blue?", model: str = "llama3.2:latest") -> str:
        """Handle /ask endpoint requests with OpenLit tracing."""
        try:
            logger.info("GenAI /ask endpoint called for SUSE Observability detection")
            response = self.single_prompt(prompt, model)
            return response
        except Exception as e:
            logger.error(f"Error in ask_endpoint_handler: {e}")
            return f"GenAI endpoint error: {str(e)}"
