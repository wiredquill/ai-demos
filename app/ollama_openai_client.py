"""
OpenAI client pattern for Ollama following Ravan's implementation.
Uses OpenAI SDK with Ollama's OpenAI-compatible API endpoint.
"""

import logging
import os
from typing import Dict, List

import openlit
from openai import OpenAI

logger = logging.getLogger(__name__)


class OllamaOpenAIClient:
    def __init__(self, ollama_url: str = None):
        """Initialize OpenAI client for Ollama."""
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_ENDPOINT", "http://ollama-service:11434"
        )
        self.client = OpenAI(
            base_url=f"{self.ollama_url}/v1",
            api_key="ollama",  # required, but unused
        )

    @openlit.trace
    def chat_with_ollama(
        self, messages: List[Dict[str, str]], model: str = "llama3.2:latest"
    ) -> str:
        """Chat with Ollama using OpenAI client pattern with OpenLit tracing."""
        try:
            logger.info(f"Chatting with Ollama model: {model}")
            completion = self.client.chat.completions.create(
                model=model,
                messages=messages,
            )
            response_content = completion.choices[0].message.content

            # Log cost information (OpenLit handles the telemetry automatically)
            if hasattr(completion, "usage") and completion.usage:
                total_tokens = getattr(completion.usage, "total_tokens", 0)
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
    def ask_endpoint_handler(
        self, prompt: str = "Why is the sky blue?", model: str = "llama3.2:latest"
    ) -> str:
        """Handle /ask endpoint requests with OpenLit tracing."""
        try:
            logger.info("GenAI /ask endpoint called for SUSE Observability detection")
            response = self.single_prompt(prompt, model)
            return response
        except Exception as e:
            logger.error(f"Error in ask_endpoint_handler: {e}")
            return f"GenAI endpoint error: {str(e)}"
