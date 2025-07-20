import json
import logging
import os
import queue
import subprocess
import threading
import time
from typing import Any, Dict, List

import gradio as gr
import requests

# Build trigger comment - pipeline model fix deployment

# --- OpenLit Observability Integration ---
try:
    import openlit

    OPENLIT_AVAILABLE = True
except ImportError:
    OPENLIT_AVAILABLE = False
    logger.warning("OpenLit not available - observability disabled")

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# --- End Logging Configuration ---


class ChatInterface:
    """
    Manages the application state and logic for the Gradio chat interface.
    """

    def __init__(self):
        self.config_path = "config.json"
        self.config = self.load_or_create_config()

        # Initialize provider status with pre-drawn boxes (default offline)
        self.provider_status = {}
        for name, provider_info in self.config.get("providers", {}).items():
            if isinstance(provider_info, str):
                country = "🌍 Unknown"
                flag = "🌍"
            else:
                country = provider_info.get("country", "🌍 Unknown")
                flag = provider_info.get("flag", "🌍")

            self.provider_status[name] = {
                "status": "🔴",
                "response_time": "---ms",
                "country": country,
                "flag": flag,
                "status_code": "Loading",
            }

        # --- MODIFIED: Load URLs from environment variables for K8s ---
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.open_webui_base_url = os.getenv("OPEN_WEBUI_BASE_URL")
        self.pipelines_base_url = os.getenv("PIPELINES_BASE_URL")
        self.pipeline_api_key = os.getenv("PIPELINE_API_KEY")

        # Don't add Open WebUI to the provider status list - keep it separate for functionality

        if self.ollama_base_url.endswith("/"):
            self.ollama_base_url = self.ollama_base_url[:-1]

        self.ollama_models = []
        self.selected_model = ""

        # Open WebUI authentication
        self.open_webui_token = None

        # --- NEW: Model Config Management State ---
        self.model_config_value = os.getenv("MODEL_CONFIG", "models-latest")
        self.config_map_name = os.getenv("CONFIG_MAP_NAME", "llm-chat-config")
        self.config_map_namespace = os.getenv("CONFIG_MAP_NAMESPACE", "default")

        # --- NEW: Service Health Failure Simulation State ---
        self.service_health_failure = (
            os.getenv("SERVICE_HEALTH_FAILURE", "false").lower() == "true"
        )
        self.deployment_name = os.getenv("DEPLOYMENT_NAME", "ollama-chat-app")
        self.failure_env_var = "SERVICE_HEALTH_FAILURE"

        # --- NEW: Automation Runner State ---
        # Read automation settings from environment variables
        self.automation_enabled = (
            os.getenv("AUTOMATION_ENABLED", "false").lower() == "true"
        )
        self.automation_interval = int(os.getenv("AUTOMATION_INTERVAL", "30"))
        self.automation_send_messages = (
            os.getenv("AUTOMATION_SEND_MESSAGES", "true").lower() == "true"
        )

        # Built-in rotating prompts for automation
        self.automation_prompts = [
            "Why is the sky blue?",
            "Why is the sky blue? Explain like I'm 5 years old.",
            "Why is the sky blue? Explain like I'm 12 years old.",
            "Why is the sky blue? Explain like I'm a college student.",
            "Why is the sky blue? Give me the scientific explanation.",
        ]
        self.current_prompt_index = 0

        # Thread management for the runner
        self.automation_thread = None
        self.stop_event = threading.Event()
        self.results_queue = queue.Queue()
        self.latest_automation_result = None

        # --- OpenLit Observability Initialization ---
        self._initialize_observability()

        logger.info(
            f"ChatInterface initialized. Ollama URL: {self.ollama_base_url}, Open WebUI URL: {self.open_webui_base_url}, Pipelines URL: {self.pipelines_base_url}, Pipeline API Key: {'***' if self.pipeline_api_key else 'None'}"
        )
        if self.automation_enabled:
            logger.info(
                f"Automation enabled with interval {self.automation_interval}s and {len(self.automation_prompts)} rotating prompts"
            )

        # Authenticate with Open WebUI if available
        if self.open_webui_base_url:
            self._authenticate_open_webui()

    def load_or_create_config(self) -> Dict:
        """Loads configuration from config.json, or creates it with defaults if it doesn't exist."""
        default_config = {
            "providers": {
                "OpenAI": {
                    "url": "https://help.openai.com",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
                "Claude (Anthropic)": {
                    "url": "https://anthropic.com",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
                "DeepSeek": {
                    "url": "https://api.deepseek.com",
                    "country": "🇨🇳 China",
                    "flag": "🇨🇳",
                },
                "Google Gemini": {
                    "url": "https://ai.google.dev",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
                "Cohere": {
                    "url": "https://cohere.com",
                    "country": "🇨🇦 Canada",
                    "flag": "🇨🇦",
                },
                "Mistral AI": {
                    "url": "https://mistral.ai",
                    "country": "🇫🇷 France",
                    "flag": "🇫🇷",
                },
                "Perplexity": {
                    "url": "https://www.perplexity.ai",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
                "Together AI": {
                    "url": "https://together.ai",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
                "Groq": {"url": "https://groq.com", "country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Hugging Face": {
                    "url": "https://huggingface.co",
                    "country": "🇺🇸 USA",
                    "flag": "🇺🇸",
                },
            }
        }

        # In K8s, the config is mounted at /app/config.json
        if os.path.exists(self.config_path):
            logger.info(f"Loading configuration from {self.config_path}")
            with open(self.config_path, "r") as f:
                try:
                    config_data = json.load(f)
                    config_data.setdefault("providers", default_config["providers"])
                    return config_data
                except json.JSONDecodeError:
                    logger.error("Error decoding config.json, using default config.")
                    return default_config
        else:
            logger.info(f"Creating default configuration file at {self.config_path}")
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config

    def _initialize_observability(self):
        """Initialize OpenLit observability if enabled and available."""
        if not OPENLIT_AVAILABLE:
            logger.info("OpenLit not available - skipping observability initialization")
            return

        # Read observability configuration from environment variables
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false").lower() == "true"
        observability_enabled = (
            os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"
        )

        if not observability_enabled:
            logger.info(
                "Observability disabled via OBSERVABILITY_ENABLED environment variable"
            )
            return

        if not otlp_endpoint:
            logger.warning("OTLP_ENDPOINT not configured - observability disabled")
            return

        try:
            # Initialize OpenLit with configuration
            openlit.init(
                otlp_endpoint=otlp_endpoint, collect_gpu_stats=collect_gpu_stats
            )
            logger.info(
                f"OpenLit observability initialized successfully. Endpoint: {otlp_endpoint}, GPU Stats: {collect_gpu_stats}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenLit observability: {e}")

    def get_ollama_models(self) -> List[str]:
        """Fetches the list of available models from the Ollama /api/tags endpoint."""
        logger.info(
            f"Attempting to fetch Ollama models from {self.ollama_base_url}/api/tags"
        )
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            if not models:
                logger.warning("No Ollama models found at the endpoint.")
                return ["No models found at Ollama endpoint."]
            logger.info(f"Successfully fetched Ollama models: {models}")
            self.ollama_models = models
            return models
        except Exception as e:
            logger.error(f"Error fetching Ollama models: {str(e)}")
            return ["Connection Error - Is Ollama running?"]

    def chat_with_ollama(self, messages: List[Dict[str, str]], model: str) -> str:
        """Sends a conversation history to the Ollama /api/chat endpoint."""
        logger.info(f"Attempting to chat with Ollama model: {model}")
        try:
            payload = {"model": model, "messages": messages, "stream": False}
            response = requests.post(
                f"{self.ollama_base_url}/api/chat", json=payload, timeout=120
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("message", {}).get(
                "content", "Error: Unexpected response format from Ollama."
            )
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"

    def chat_with_open_webui(self, messages: List[Dict[str, str]], model: str) -> str:
        """Sends a conversation history with pipeline-modified prompts for response level cycling."""
        # Educational levels that the pipeline cycles through
        pipeline_levels = [
            {"name": "🎯 Default", "modifier": ""},
            {
                "name": "🧒 Kid Mode",
                "modifier": "Explain like I'm 5 years old using simple words, fun examples, and easy-to-understand concepts.",
            },
            {
                "name": "🔬 Young Scientist",
                "modifier": "Explain like I'm 12 years old with some science details but keep it understandable and engaging.",
            },
            {
                "name": "🎓 College Student",
                "modifier": "Explain like I'm a college student with technical context, examples, and deeper analysis.",
            },
            {
                "name": "⚗️ Scientific",
                "modifier": "Give me the full scientific explanation with precise terminology, detailed mechanisms, and technical accuracy.",
            },
        ]

        # Calculate which level to use (cycling every 30 seconds)
        import time

        level_index = int(time.time() / 30) % len(pipeline_levels)
        current_level = pipeline_levels[level_index]

        # Apply pipeline level modification to the message
        modified_messages = messages.copy()
        if modified_messages and current_level["modifier"]:
            last_message = modified_messages[-1]
            if last_message["role"] == "user":
                modified_messages[-1] = {
                    "role": "user",
                    "content": f"{last_message['content']} {current_level['modifier']}",
                }

        # Check if service is in failure state (like co-worker's approach)
        if self.service_health_failure:
            logger.warning(
                f"Service health failure detected: SERVICE_HEALTH_FAILURE=true"
            )
            broken_response = f"🔴 **SERVICE DEGRADED**: Health failure detected!\n\n"
            broken_response += f"❌ Service Status: DEVIATING\n"
            broken_response += f"🔧 Cause: SERVICE_HEALTH_FAILURE=true\n\n"
            broken_response += (
                f"💡 Service cannot process requests while in degraded state.\n"
            )
            broken_response += f"⚠️ This demonstrates SUSE Observability's ability to detect configuration changes and service health degradation.\n\n"
            broken_response += f"🔄 To fix: Use 'Restore Service Health' in the Service Health Simulation modal."
            return broken_response

        # Try Pipelines service first if available, otherwise fall back to Open WebUI
        if self.pipelines_base_url:
            # Use dedicated Pipelines service for enhanced processing
            api_url = f"{self.pipelines_base_url}/v1/chat/completions"
            # Use the response_level pipeline which handles the educational level modifications
            payload = {
                "model": "response_level",
                "messages": modified_messages,
                "stream": False,
                "max_tokens": 1000,
            }

            # Add authentication header for pipeline service
            headers = {"Content-Type": "application/json"}
            if self.pipeline_api_key:
                headers["Authorization"] = f"Bearer {self.pipeline_api_key}"

            logger.info(
                f"Attempting Pipelines service with pipeline level: {current_level['name']}"
            )
            logger.info(
                f"Using pipeline API key: {'***' if self.pipeline_api_key else 'None'}"
            )
            logger.info(f"Request URL: {api_url}")
            logger.info(f"Headers: {dict(headers)}")
            try:
                response = requests.post(
                    api_url, json=payload, headers=headers, timeout=120
                )
                logger.info(f"Initial response status: {response.status_code}")
                if response.status_code == 200:
                    response_data = response.json()
                    # Handle OpenAI-compatible response format
                    if "choices" in response_data and response_data["choices"]:
                        content = (
                            response_data["choices"][0]
                            .get("message", {})
                            .get(
                                "content",
                                "Error: Unexpected response format from Open WebUI.",
                            )
                        )
                    else:
                        # Fallback to Ollama format
                        content = response_data.get("message", {}).get(
                            "content",
                            "Error: Unexpected response format from Open WebUI.",
                        )

                    # Add pipeline level header to the response - this IS the pipeline working
                    formatted_response = f"🔄 **Pipeline Mode**: {current_level['name']} (via Pipelines Service)\n\n{content}"
                    logger.info(
                        f"Pipelines service response successful with level: {current_level['name']}"
                    )
                    return formatted_response
                else:
                    logger.warning(
                        f"Pipelines service failed ({response.status_code}), response: {response.text[:200]}, falling back to Open WebUI or direct Ollama"
                    )
            except Exception as e:
                logger.warning(
                    f"Pipelines service failed: {str(e)}, falling back to direct Ollama"
                )
        elif self.open_webui_base_url:
            # Try Open WebUI as secondary option
            api_url = f"{self.open_webui_base_url}/api/v1/chat/completions"
            payload = {
                "model": model,
                "messages": modified_messages,
                "stream": False,
                "max_tokens": 1000,
            }

            headers = {"Content-Type": "application/json"}
            if self.open_webui_token:
                headers["Authorization"] = f"Bearer {self.open_webui_token}"

            logger.info(
                f"Attempting Open WebUI fallback with pipeline level: {current_level['name']}"
            )
            try:
                response = requests.post(
                    api_url, json=payload, headers=headers, timeout=120
                )
                if response.status_code == 200:
                    response_data = response.json()
                    if "choices" in response_data and response_data["choices"]:
                        content = (
                            response_data["choices"][0]
                            .get("message", {})
                            .get(
                                "content",
                                "Error: Unexpected response format from Open WebUI.",
                            )
                        )
                    else:
                        content = response_data.get("message", {}).get(
                            "content",
                            "Error: Unexpected response format from Open WebUI.",
                        )

                    formatted_response = f"🔄 **Pipeline Mode**: {current_level['name']} (via Open WebUI Fallback)\n\n{content}"
                    logger.info(
                        f"Open WebUI fallback response successful with level: {current_level['name']}"
                    )
                    return formatted_response
                else:
                    logger.warning(
                        f"Open WebUI fallback failed ({response.status_code}), falling back to direct Ollama"
                    )
            except Exception as e:
                logger.warning(
                    f"Open WebUI fallback failed: {str(e)}, falling back to direct Ollama"
                )
        else:
            logger.info(
                "No Pipelines or Open WebUI URL configured, using direct Ollama"
            )

        # Fallback to direct Ollama with pipeline-modified prompt - this is STILL pipeline working!
        logger.info(f"Using direct Ollama with pipeline level: {current_level['name']}")
        ollama_response = self.chat_with_ollama(modified_messages, model)

        # Add pipeline level header - this is still pipeline functionality
        formatted_response = f"🔄 **Pipeline Mode**: {current_level['name']} (via Direct Ollama)\n\n{ollama_response}"
        return formatted_response

    def check_provider_status(self, provider_name: str, provider_info) -> dict:
        """Checks the status of a single provider and returns detailed info."""
        import time

        start_time = time.time()

        # Handle both old string format and new dict format
        if isinstance(provider_info, str):
            url = provider_info
            country = "🌍 Unknown"
            flag = "🌍"
        else:
            url = provider_info.get("url", provider_info)
            country = provider_info.get("country", "🌍 Unknown")
            flag = provider_info.get("flag", "🌍")

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=3, headers=headers)  # 3-second timeout
            response_time = int((time.time() - start_time) * 1000)
            # Show as online if we get ANY response (even 403, 404, etc.)
            status = "🟢"
            logger.info(
                f"Provider {provider_name}: {response.status_code} -> {status} ({response_time}ms)"
            )

            return {
                "status": status,
                "response_time": f"{response_time}ms",
                "country": country,
                "flag": flag,
                "status_code": response.status_code,
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            # Cap response time at 3000ms for timeout cases
            if response_time > 3000:
                response_time = 3000
            logger.warning(
                f"Provider {provider_name} failed: {str(e)} ({response_time}ms)"
            )
            return {
                "status": "🔴",
                "response_time": f"{response_time}ms",
                "country": country,
                "flag": flag,
                "status_code": "Error",
                "error": str(e),
            }

    def update_all_provider_status(self) -> Dict:
        """Updates all provider statuses and returns the status dictionary."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        logger.info("Updating all provider statuses.")
        updated_status = {}
        start_time = time.time()
        max_total_time = 15  # Maximum total time for all providers

        try:
            providers = self.config.get("providers", {})
            if not providers:
                logger.info("No providers configured")
                return updated_status

            # Use ThreadPoolExecutor for concurrent checks
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all provider checks
                future_to_name = {
                    executor.submit(
                        self.check_provider_status, name, provider_info
                    ): name
                    for name, provider_info in providers.items()
                }

                # Collect results with timeout
                for future in as_completed(future_to_name, timeout=max_total_time):
                    name = future_to_name[future]
                    try:
                        result = future.result()
                        updated_status[name] = result
                    except Exception as e:
                        logger.warning(f"Provider {name} check failed: {e}")
                        updated_status[name] = {
                            "status": "🔴",
                            "response_time": "timeout",
                            "country": "🌍 Unknown",
                            "flag": "🌍",
                            "status_code": "Error",
                            "error": str(e),
                        }

            self.provider_status = updated_status

        except Exception as e:
            logger.warning(f"Provider status check failed: {e} - using partial results")
            self.provider_status = updated_status

        total_time = time.time() - start_time
        logger.info(f"Provider status check completed in {total_time:.1f}s")
        return updated_status

    def _authenticate_open_webui(self):
        """Authenticate with Open WebUI to get an access token."""
        try:
            # Try to sign in with default admin credentials
            auth_url = f"{self.open_webui_base_url}/api/v1/auths/signin"
            auth_payload = {"email": "admin", "password": "admin"}

            logger.info(f"Attempting authentication at: {auth_url}")
            logger.info(f"Auth payload: {auth_payload}")
            response = requests.post(auth_url, json=auth_payload, timeout=10)
            logger.info(f"Auth response status: {response.status_code}")
            logger.info(f"Auth response content: {response.text[:500]}")

            if response.status_code == 200:
                auth_data = response.json()
                self.open_webui_token = auth_data.get("token")
                logger.info(
                    f"Successfully authenticated with Open WebUI, token length: {len(self.open_webui_token) if self.open_webui_token else 0}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to authenticate with Open WebUI: {response.status_code}, response: {response.text}"
                )
                return False
        except Exception as e:
            logger.warning(f"Open WebUI authentication failed: {str(e)}")
            return False

    def get_service_health_status(self) -> dict:
        """Check overall service health and return status information."""
        try:
            # Check if service health failure is simulated
            if self.service_health_failure:
                return {
                    "status": "DEVIATING",
                    "color": "#dc3545",
                    "message": "Service health degraded due to configuration failure",
                    "details": "SERVICE_HEALTH_FAILURE environment variable is set to 'true'",
                }

            # Check if model config is broken (legacy failure simulation)
            if self.model_config_value != "models-latest":
                return {
                    "status": "DEVIATING",
                    "color": "#ffa726",
                    "message": "Pipeline configuration error detected",
                    "details": f"MODEL_CONFIG is '{self.model_config_value}' instead of 'models-latest'",
                }

            # Check basic service connectivity
            try:
                import requests

                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    return {
                        "status": "HEALTHY",
                        "color": "#28a745",
                        "message": "All services operating normally",
                        "details": "Ollama service responsive and configuration valid",
                    }
                else:
                    return {
                        "status": "DEGRADED",
                        "color": "#ffa726",
                        "message": "Ollama service not responding properly",
                        "details": f"HTTP {response.status_code} from Ollama API",
                    }
            except Exception as e:
                return {
                    "status": "DEGRADED",
                    "color": "#ffa726",
                    "message": "Cannot connect to Ollama service",
                    "details": str(e),
                }
        except Exception as e:
            return {
                "status": "UNKNOWN",
                "color": "#6c757d",
                "message": "Unable to determine service health",
                "details": str(e),
            }

    def get_provider_status_html(self) -> str:
        """Generates compact provider cards with flags and status, plus service health."""
        # Get service health status
        health_status = self.get_service_health_status()

        # Calculate statistics
        total_providers = len(self.provider_status)
        online_count = sum(
            1
            for info in self.provider_status.values()
            if isinstance(info, dict) and info.get("status") == "🟢"
        )
        offline_count = total_providers - online_count

        # Calculate average response time
        response_times = []
        for info in self.provider_status.values():
            if isinstance(info, dict) and "response_time" in info:
                try:
                    rt_str = info["response_time"]
                    if "ms" in rt_str and rt_str != "---ms":
                        rt = int(rt_str.replace("ms", ""))
                        response_times.append(rt)
                except:
                    pass
        avg_rt = int(sum(response_times) / len(response_times)) if response_times else 0

        html_content = f"""
        <div style='background: linear-gradient(135deg, #0c322c 0%, #1a4a3a 100%); padding: 15px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);'>
            <h3 style='color: #30ba78; margin: 0 0 15px 0; font-size: 16px; text-align: center; font-weight: 600;'>🌐 System Status</h3>
            
            <!-- Service Health Status -->
            <div style='background: rgba(255,255,255,0.05); border-radius: 12px; padding: 12px; margin-bottom: 15px; border-left: 4px solid {health_status["color"]};'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <div style='color: {health_status["color"]}; font-weight: 700; font-size: 14px;'>🏥 Service Health: {health_status["status"]}</div>
                        <div style='color: #ffffff; font-size: 11px; opacity: 0.9; margin-top: 2px;'>{health_status["message"]}</div>
                    </div>
                    <div style='color: {health_status["color"]}; font-size: 20px;'>
                        {"🟢" if health_status["status"] == "HEALTHY" else "🔴" if health_status["status"] == "DEVIATING" else "🟡"}
                    </div>
                </div>
            </div>
            
            <!-- Model Provider List -->
            <div style='margin-bottom: 15px;'>
        """

        for name, info in sorted(self.provider_status.items()):
            if isinstance(info, dict):
                status = info.get("status", "🔴")
                flag = info.get("flag", "🌍")
                response_time = info.get("response_time", "---ms")

                html_content += f"""
                <div style='display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 4px; background: rgba(255,255,255,0.05); border-radius: 12px; border-left: 3px solid {"#28a745" if status == "🟢" else "#dc3545"};'>
                    <div style='display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0;'>
                        <span style='font-size: 14px; width: 18px; text-align: center; flex-shrink: 0;'>{flag}</span>
                        <span style='color: #ffffff; font-size: 12px; font-weight: 500; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{name}</span>
                    </div>
                    <div style='display: flex; align-items: center; gap: 8px; flex-shrink: 0; min-width: 80px;'>
                        <span style='font-size: 14px; width: 16px; text-align: center;'>{status}</span>
                        <span style='color: #a0a0a0; font-size: 10px; text-align: right; min-width: 45px; font-family: monospace;'>{response_time}</span>
                    </div>
                </div>
                """
            else:
                # Fallback for old format
                html_content += f"""
                <div style='display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; margin-bottom: 4px; background: rgba(255,255,255,0.05); border-radius: 12px;'>
                    <span style='color: #ffffff; font-size: 12px; font-weight: 500;'>{name}</span>
                    <span style='font-size: 14px;'>{info}</span>
                </div>
                """

        html_content += f"""
            </div>
            
            <!-- Compact Statistics -->
            <div style='background: linear-gradient(135deg, rgba(48, 186, 120, 0.1) 0%, rgba(48, 186, 120, 0.05) 100%); border: 1px solid rgba(48, 186, 120, 0.2); border-radius: 12px; padding: 12px; text-align: center;'>
                <div style='display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 11px;'>
                    <div style='text-align: center;'>
                        <div style='color: #28a745; font-weight: 700; font-size: 16px;'>{online_count}</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Online</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: #dc3545; font-weight: 700; font-size: 16px;'>{offline_count}</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Offline</div>
                    </div>
                    <div style='text-align: center;'>
                        <div style='color: #ffc107; font-weight: 700; font-size: 16px;'>{avg_rt}ms</div>
                        <div style='color: #ffffff; opacity: 0.8; font-size: 9px;'>Avg RT</div>
                    </div>
                </div>
            </div>
        </div>
        """

        return html_content

    def simulate_service_failure(self) -> tuple:
        """Simulates service failure using kubectl patch (like co-worker's approach)."""
        try:
            logger.info("Simulating service failure using kubectl patch")

            # Use kubectl patch to change environment variable - exactly like your co-worker's pattern
            cmd = [
                "kubectl",
                "patch",
                "deployment",
                self.deployment_name,
                "-n",
                self.config_map_namespace,
                "--type=json",
                f'-p=[{{"op": "replace", "path": "/spec/template/spec/containers/0/env/0/value", "value": "true"}}]',
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Deployment patch successful: {result.stdout}")

            # Update local state
            self.service_health_failure = True

            message = f"🚨 Service failure simulated! Deployment '{self.deployment_name}' patched with SERVICE_HEALTH_FAILURE=true. SUSE Observability should detect configuration change and service degradation."

            return gr.Column(visible=False), message, "warning"

        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl patch failed: {e.stderr}")
            return (
                gr.Column(visible=True),
                f"❌ kubectl patch failed: {e.stderr}",
                "error",
            )
        except Exception as e:
            logger.error(f"Service failure simulation failed: {e}")
            return gr.Column(visible=True), f"❌ Simulation failed: {str(e)}", "error"

    def restore_service_health(self) -> tuple:
        """Restores service health using kubectl patch."""
        try:
            logger.info("Restoring service health using kubectl patch")

            # Patch deployment back to healthy state
            cmd = [
                "kubectl",
                "patch",
                "deployment",
                self.deployment_name,
                "-n",
                self.config_map_namespace,
                "--type=json",
                f'-p=[{{"op": "replace", "path": "/spec/template/spec/containers/0/env/0/value", "value": "false"}}]',
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Deployment restore successful: {result.stdout}")

            # Update local state
            self.service_health_failure = False

            message = f"✅ Service health restored! Deployment '{self.deployment_name}' patched back to SERVICE_HEALTH_FAILURE=false. SUSE Observability should detect recovery."

            return gr.Column(visible=False), message, "success"

        except subprocess.CalledProcessError as e:
            logger.error(f"kubectl patch failed: {e.stderr}")
            return (
                gr.Column(visible=True),
                f"❌ kubectl patch failed: {e.stderr}",
                "error",
            )
        except Exception as e:
            logger.error(f"Service health restoration failed: {e}")
            return gr.Column(visible=True), f"❌ Restoration failed: {str(e)}", "error"

    def run_availability_demo(self) -> tuple:
        """Runs availability demo by testing external connectivity (SUSE security demo pattern)."""
        try:
            logger.info("Running availability demo - testing external connectivity")

            # Use requests library instead of curl (available in container)
            import requests

            response = requests.head("https://suse.com", timeout=3)

            if response.status_code in [200, 301, 302]:  # Accept success and redirects
                headers_text = "\n".join(
                    [f"{k}: {v}" for k, v in response.headers.items()][:10]
                )
                if response.status_code == 301:
                    message = f"✅ Availability Demo: Successfully connected to https://suse.com (redirected to {response.headers.get('Location', 'unknown')})\n\nResponse Headers:\n{headers_text}..."
                else:
                    message = f"✅ Availability Demo: Successfully connected to https://suse.com\n\nResponse Headers:\n{headers_text}..."
                status = "success"
            else:
                message = f"⚠️ Availability Demo: Connection returned status {response.status_code}"
                status = "warning"

            logger.info(f"Availability demo completed with status: {status}")
            return gr.Column(visible=False), message, status

        except requests.exceptions.Timeout:
            logger.error("Availability demo timed out")
            return (
                gr.Column(visible=True),
                "❌ Availability Demo: Connection timed out after 5 seconds",
                "error",
            )
        except Exception as e:
            logger.error(f"Availability demo failed: {e}")
            return (
                gr.Column(visible=True),
                f"❌ Availability Demo failed: {str(e)}",
                "error",
            )

    def run_data_leak_demo(self) -> tuple:
        """Runs data leak demo by sending credit card data (SUSE security demo pattern)."""
        try:
            logger.info(
                "Running data leak demo - simulating sensitive data transmission"
            )

            # Use requests library with credit card data similar to the security demo script
            credit_card_pattern = "3412-1234-1234-2222"
            import requests

            data = {"creditcard": credit_card_pattern}
            response = requests.post("http://example.com", data=data, timeout=3)

            # Always report this as a security concern regardless of HTTP response
            message = f"🔒 Data Leak Demo: Transmitted credit card {credit_card_pattern} to http://example.com\n\n"
            message += f"⚠️ SECURITY ALERT: This demonstrates data loss prevention (DLP) monitoring.\n"
            message += f"SUSE NeuVector should detect and alert on this sensitive data transmission.\n\n"

            try:
                message += f"HTTP Response Status: {response.status_code}\n"
                if response.text:
                    message += f"Response: {response.text[:300]}..."
            except:
                message += "Connection completed - response processing skipped"

            logger.warning(
                f"Data leak demo executed - credit card data sent for DLP testing"
            )
            return gr.Column(visible=False), message, "warning"

        except requests.exceptions.Timeout:
            logger.error("Data leak demo timed out")
            # Still report as successful for DLP demo purposes
            message = f"🔒 Data Leak Demo: Attempted to transmit credit card {credit_card_pattern} to http://example.com\n\n"
            message += f"⚠️ Connection timed out, but this demonstrates DLP monitoring capabilities.\n"
            message += f"SUSE NeuVector should still detect the sensitive data transmission attempt."
            return gr.Column(visible=False), message, "warning"
        except Exception as e:
            logger.error(f"Data leak demo failed: {e}")
            return (
                gr.Column(visible=True),
                f"❌ Data Leak Demo failed: {str(e)}",
                "error",
            )

    def refresh_providers(self) -> gr.HTML:
        """Manually refreshes provider statuses and returns the HTML."""
        logger.info("Manual provider refresh triggered.")
        self.update_all_provider_status()
        return gr.HTML(value=self.get_provider_status_html())

    def refresh_ollama_models(self) -> gr.Dropdown:
        """Refreshes the dropdown with models from Ollama."""
        logger.info("Refreshing Ollama models dropdown.")
        self.ollama_models = self.get_ollama_models()
        current_value = (
            self.selected_model
            if self.selected_model in self.ollama_models
            else (
                self.ollama_models[0]
                if self.ollama_models and "Error" not in self.ollama_models[0]
                else ""
            )
        )
        self.selected_model = current_value
        return gr.Dropdown(
            choices=self.ollama_models,
            label="🤖 Ollama Model",
            value=current_value,
            allow_custom_value=True,
        )

    # --- NEW: Automation Runner Methods ---
    def _automation_loop(self, model: str, interval: int):
        """The main loop for the background automation thread."""
        logger.info("Automation thread started.")
        while not self.stop_event.is_set():
            # Get the current prompt and rotate to next
            current_prompt = self.automation_prompts[self.current_prompt_index]
            self.current_prompt_index = (self.current_prompt_index + 1) % len(
                self.automation_prompts
            )

            logger.info(
                f"Running automated task with prompt: '{current_prompt}' (send_messages: {self.automation_send_messages})"
            )

            # Initialize response variables
            ollama_reply = "Message sending disabled"
            webui_reply = "Message sending disabled"

            # Send messages to models only if enabled
            if self.automation_send_messages:
                # 1. Send to Ollama
                logger.info("About to call Ollama...")
                ollama_reply = self.chat_with_ollama(
                    [{"role": "user", "content": current_prompt}], model
                )
                logger.info(f"Ollama replied: {ollama_reply[:100]}...")

                # 2. Send to Open WebUI
                logger.info("About to call Open WebUI...")
                webui_reply = self.chat_with_open_webui(
                    [{"role": "user", "content": current_prompt}], model
                )
                logger.info(f"Open WebUI replied: {webui_reply[:100]}...")
            else:
                logger.info(
                    "Skipping message sending - automation_send_messages is disabled"
                )

            # 3. Always check providers (this is the ping/monitoring functionality)
            logger.info("About to check provider statuses...")
            provider_statuses = self.update_all_provider_status()
            logger.info("Provider status check completed")

            # Create result package
            logger.info("Creating automation result package...")
            result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "prompt": (
                    current_prompt
                    if self.automation_send_messages
                    else "Monitoring only"
                ),
                "ollama_response": ollama_reply,
                "open_webui_response": webui_reply,
                "provider_status": provider_statuses,
                "send_messages_enabled": self.automation_send_messages,
            }
            # Store latest result and put in queue for the UI to pick up
            self.latest_automation_result = result
            self.results_queue.put(result)
            logger.info("Automation result stored in queue successfully")

            # Wait for the next interval
            self.stop_event.wait(interval)
        logger.info("Automation thread stopped.")

    def start_automation(self, model: str, interval: int, send_messages: bool = None):
        """Starts the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            logger.warning("Automation is already running.")
            running_status = "<div style='text-align: center; color: #4CAF50; padding: 10px; background: rgba(76, 175, 80, 0.1); border-radius: 8px; margin: 10px 0;'>▶️ Automation is running - Automated testing in progress</div>"
            return (
                gr.Button(interactive=False),
                gr.Button(interactive=True),
                gr.HTML(value=running_status),
            )

        if not model or "Error" in model or "No models" in model:
            logger.error("Cannot start automation without a valid model selected.")
            stopped_status = "<div style='text-align: center; color: #f44336; padding: 10px; background: rgba(244, 67, 54, 0.1); border-radius: 8px; margin: 10px 0;'>❌ Cannot start automation - No valid model selected</div>"
            return (
                gr.Button(interactive=True),
                gr.Button(interactive=False),
                gr.HTML(value=stopped_status),
            )

        # Update send messages setting if provided
        if send_messages is not None:
            self.automation_send_messages = send_messages
            logger.info(f"Automation send messages setting updated to: {send_messages}")

        self.stop_event.clear()
        self.automation_thread = threading.Thread(
            target=self._automation_loop, args=(model, interval), daemon=True
        )
        self.automation_thread.start()
        logger.info(
            f"Automation started with interval {interval}s, send_messages: {self.automation_send_messages}"
        )
        # UI update to show it's running
        running_status = "<div style='text-align: center; color: #4CAF50; padding: 10px; background: rgba(76, 175, 80, 0.1); border-radius: 8px; margin: 10px 0;'>▶️ Automation is running - Automated testing in progress</div>"
        return (
            gr.Button(interactive=False),
            gr.Button(interactive=True),
            gr.HTML(value=running_status),
        )

    def stop_automation(self):
        """Stops the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            self.stop_event.set()
            # Wait a short time for thread to finish gracefully
            self.automation_thread.join(timeout=2)
            if self.automation_thread.is_alive():
                logger.warning("Automation thread did not stop gracefully")
            else:
                logger.info("Automation thread stopped successfully")
        logger.info("Automation stopping.")
        stopped_status = "<div style='text-align: center; color: #ffa726; padding: 10px; background: rgba(255, 167, 38, 0.1); border-radius: 8px; margin: 10px 0;'>⏹️ Automation stopped - Click Start to begin automated testing</div>"
        return (
            gr.Button(interactive=True),
            gr.Button(interactive=False),
            gr.HTML(value=stopped_status),
        )

    def format_automation_results_html(self, result):
        """Formats automation results as readable HTML."""
        if not result:
            return "<div style='text-align: center; color: #888; padding: 20px;'>No automation results yet...</div>"

        # Truncate responses for display
        def truncate_text(text, max_length=150):
            if len(text) > max_length:
                return text[:max_length] + "..."
            return text

        ollama_response = truncate_text(result.get("ollama_response", "N/A"))
        webui_response = truncate_text(result.get("open_webui_response", "N/A"))

        html = f"""
        <div style='background: rgba(0,0,0,0.3); border-radius: 10px; padding: 15px; margin: 10px 0;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <span style='color: #73ba25; font-weight: 600; font-size: 0.9em;'>🕐 {result.get('timestamp', 'N/A')}</span>
                <span style='color: #888; font-size: 0.8em;'>{'Messages Enabled' if result.get('send_messages_enabled', False) else 'Monitoring Only'}</span>
            </div>
            
            <div style='margin-bottom: 12px;'>
                <div style='color: #fff; font-weight: 500; margin-bottom: 5px;'>❓ Test Question:</div>
                <div style='background: rgba(115,186,37,0.1); padding: 8px; border-radius: 6px; color: #e0e0e0; font-size: 0.9em;'>
                    {result.get('prompt', 'N/A')}
                </div>
            </div>
            
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px;'>
                <div style='background: rgba(76,175,80,0.1); padding: 10px; border-radius: 6px; border-left: 3px solid #4CAF50;'>
                    <div style='color: #4CAF50; font-weight: 600; font-size: 0.8em; margin-bottom: 5px;'>🤖 OLLAMA RESPONSE</div>
                    <div style='color: #e0e0e0; font-size: 0.8em; line-height: 1.4;'>{ollama_response}</div>
                </div>
                
                <div style='background: rgba(33,150,243,0.1); padding: 10px; border-radius: 6px; border-left: 3px solid #2196F3;'>
                    <div style='color: #2196F3; font-weight: 600; font-size: 0.8em; margin-bottom: 5px;'>🌐 OPEN WEBUI RESPONSE</div>
                    <div style='color: #e0e0e0; font-size: 0.8em; line-height: 1.4;'>{webui_response}</div>
                </div>
            </div>
        </div>
        """
        return html


def create_interface():
    logger.info("Creating Gradio interface.")
    chat_instance = ChatInterface()

    css = """
    .gradio-container { 
        background: linear-gradient(135deg, #0a2f26 0%, #0c322c 50%, #0f3a2f 100%); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
        color: #efefef; 
        min-height: 100vh;
        height: 100vh;
        overflow-y: auto;
    }
    .main-header { 
        background: linear-gradient(135deg, #30ba78 0%, #28a745 100%); 
        border: 1px solid #30ba78; 
        border-radius: 15px; 
        box-shadow: 0 8px 32px rgba(48, 186, 120, 0.3); 
        padding: 25px; 
        margin-bottom: 25px; 
    }
    .control-panel, .chat-container { 
        background: rgba(255, 255, 255, 0.9); 
        border: 1px solid rgba(48, 186, 120, 0.2); 
        border-radius: 15px; 
        padding: 20px; 
        backdrop-filter: blur(10px);
    }
    h1, h2, h3, h4 { color: #ffffff; font-weight: 600; }
    .gr-button { 
        background: #73ba25; 
        color: #ffffff; 
        border: none; 
        border-radius: 6px; 
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.3); 
        font-weight: 600; 
        transition: all 0.3s ease;
    }
    .gr-button:hover { 
        background: #5a9e1c; 
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(115, 186, 37, 0.4);
    }
    .refresh-btn { 
        background: linear-gradient(135deg, #2453ff 0%, #4f75ff 100%); 
    } 
    .refresh-btn:hover { 
        background: linear-gradient(135deg, #4f75ff 0%, #6c8cff 100%); 
    }
    .stop-btn { 
        background: linear-gradient(135deg, #dc3545 0%, #e04f5e 100%); 
    } 
    .stop-btn:hover { 
        background: linear-gradient(135deg, #e04f5e 0%, #e8606f 100%); 
    }
    .gr-textbox { 
        background: #ffffff; 
        border: 2px solid #73ba25; 
        border-radius: 8px; 
        color: #000000;
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.2);
    }
    .gr-textbox:focus { 
        border-color: #73ba25; 
        box-shadow: 0 0 12px rgba(115, 186, 37, 0.4); 
        background: #ffffff;
    }
    .gr-textbox textarea, .gr-textbox input {
        background: #ffffff !important;
        color: #000000 !important;
        font-size: 14px;
        line-height: 1.5;
    }
    .gr-textbox textarea::placeholder, .gr-textbox input::placeholder {
        color: #666666 !important;
        font-style: italic;
    }
    .gr-dropdown { 
        background: #ffffff; 
        border: 2px solid #73ba25; 
        border-radius: 8px; 
        box-shadow: 0 2px 8px rgba(115, 186, 37, 0.2);
    }
    .gr-dropdown:focus-within {
        border-color: #73ba25;
        box-shadow: 0 0 12px rgba(115, 186, 37, 0.4);
    }
    .gr-group {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.08) 100%);
        border: 2px solid rgba(48, 186, 120, 0.2);
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(15px);
        position: relative;
        overflow: hidden;
    }
    .gr-group::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(48, 186, 120, 0.5), transparent);
    }
    /* Modern AI Response boxes with consistent rounded styling */
    .ollama-response .gr-textbox,
    .ollama-response .gr-textbox textarea {
        background: linear-gradient(145deg, #e8f5e8 0%, #f1f8e9 100%) !important;
        border: 2px solid #4CAF50 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(76, 175, 80, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
        position: relative;
        overflow: hidden;
        height: clamp(200px, 40vh, 600px) !important;
        max-height: 60vh !important;
    }
    .ollama-response .gr-textbox::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #4CAF50, transparent);
        z-index: 1;
    }
    .ollama-response .gr-textbox textarea {
        background: transparent !important;
        color: #1b5e20 !important;
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.6 !important;
        font-size: 14px !important;
        letter-spacing: 0.2px;
        font-weight: 400;
        padding: 16px !important;
        border: none !important;
        resize: none !important;
        height: 100% !important;
        min-height: 200px !important;
    }
    .webui-response .gr-textbox,
    .webui-response .gr-textbox textarea {
        background: linear-gradient(145deg, #e3f2fd 0%, #f3f9ff 100%) !important;
        border: 2px solid #2196F3 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(33, 150, 243, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.6) !important;
        position: relative;
        overflow: hidden;
        height: clamp(200px, 40vh, 600px) !important;
        max-height: 60vh !important;
    }
    .webui-response .gr-textbox::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #2196F3, transparent);
        z-index: 1;
    }
    .webui-response .gr-textbox textarea {
        background: transparent !important;
        color: #0d47a1 !important;
        font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        line-height: 1.6 !important;
        font-size: 14px !important;
        letter-spacing: 0.2px;
        font-weight: 400;
        padding: 16px !important;
        border: none !important;
        resize: none !important;
        height: 100% !important;
        min-height: 200px !important;
    }
    /* Consistent rounded styling for all other textboxes */
    .gr-textbox {
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    /* Fix white backgrounds around response boxes - keep everything else as original grey */
    div[style*="background-color: white"], div[style*="background-color: #fff"], div[style*="background: white"] {
        background: inherit !important;
    }
    /* Target specific containers that might have white backgrounds around response boxes */
    .ollama-response > div, .webui-response > div {
        background: inherit !important;
    }
    /* Target the container wrapping the response textboxes */
    .ollama-response, .webui-response {
        background: inherit !important;
    }
    /* Target Gradio form and container elements around response boxes */
    .ollama-response .gr-form, .webui-response .gr-form,
    .ollama-response .gr-box, .webui-response .gr-box {
        background: inherit !important;
    }
    /* Fix white background around input box only - aggressive targeting all potential containers */
    .input-box .gr-form, .input-box .gr-box, .input-box > div, 
    .input-box .gr-textbox, .input-box div[data-testid="textbox"] {
        background: rgba(255, 255, 255, 0.05) !important;
    }
    /* Target all nested divs inside input-box */
    .input-box > div > div, .input-box .gr-form > div, .input-box div div {
        background: rgba(255, 255, 255, 0.05) !important;
    }
    /* Ultra-aggressive targeting for any white background elements in input-box */
    .input-box *, .input-box *[style*="background"], .input-box *[style*="background-color"] {
        background: rgba(255, 255, 255, 0.05) !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    /* Specific targeting for Gradio wrapper elements */
    .input-box .gr-padded, .input-box .gr-compact, .input-box .wrap {
        background: rgba(255, 255, 255, 0.05) !important;
    }
    /* Force override for any element that might still show white in input box area */
    .input-box [style*="background-color: white"], 
    .input-box [style*="background-color: #fff"], 
    .input-box [style*="background-color: #ffffff"],
    .input-box [style*="background: white"],
    .input-box [style*="background: #fff"],
    .input-box [style*="background: #ffffff"] {
        background: rgba(255, 255, 255, 0.05) !important;
        background-color: rgba(255, 255, 255, 0.05) !important;
    }
    .gr-button {
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
    }
    .gr-button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important;
    }
    .send-button {
        background: linear-gradient(135deg, #30ba78 0%, #28a745 100%) !important;
        border: none !important;
        color: white !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        padding: 12px 20px !important;
        min-height: 48px !important;
        border-radius: 12px !important;
    }
    .input-box .gr-textbox {
        border: 2px solid rgba(115, 186, 37, 0.3) !important;
        border-radius: 15px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        transition: all 0.3s ease !important;
    }
    .input-box .gr-textbox:focus-within {
        border-color: #73ba25 !important;
        box-shadow: 0 0 0 3px rgba(115, 186, 37, 0.1) !important;
    }
    .gr-dropdown {
        border-radius: 12px !important;
    }
    """

    with gr.Blocks(css=css, title="AI Compare") as interface:
        # Simple header without complex graphics
        gr.HTML(
            """
        <div style='text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #0c322c 0%, #1a4a3a 100%); border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);'>
            <h1 style='color: #30ba78; margin: 0; font-size: 1.8em; font-weight: 600;'>AI Compare</h1>
            <p style='color: #ffffff; margin: 10px 0 0 0; opacity: 0.8; font-size: 1em;'>Compare AI responses: Direct Ollama vs Open WebUI</p>
        </div>
        """
        )

        with gr.Row():
            # LEFT PANEL - Compact Provider Status (30%)
            with gr.Column(scale=3):
                # Initialize with pre-drawn provider status boxes
                initial_status_html = chat_instance.get_provider_status_html()
                provider_status_html = gr.HTML(value=initial_status_html)
                # Removed refresh button per UI feedback
                # SUSE Security Demo buttons (direct action)
                availability_demo_btn = gr.Button(
                    "🌐 Availability Demo", variant="secondary", size="sm"
                )
                data_leak_demo_btn = gr.Button(
                    "🔒 Data Leak Demo", variant="secondary", size="sm"
                )
                demo_help_btn = gr.Button(
                    "❓ Demo Help", variant="secondary", size="sm"
                )
                
                # Demo status message display moved here from modal
                with gr.Row():
                    with gr.Column():
                        demo_status_msg = gr.HTML(value="", visible=False)

            # CENTER PANEL - Chat Interface in Grouped Container (70%)
            with gr.Column(scale=7):
                with gr.Group():
                    # Header with automation controls and config
                    gr.HTML(
                        """
                    <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px; background: linear-gradient(135deg, rgba(115, 186, 37, 0.1) 0%, rgba(115, 186, 37, 0.05) 100%); border-radius: 10px; border: 1px solid rgba(115, 186, 37, 0.2);'>
                        <h2 style='color: #73ba25; margin: 0; font-size: 1.3em; font-weight: 600;'>🔄 AI Response Comparison</h2>
                    </div>
                    """
                    )

                    # Automation and Config Controls Row
                    with gr.Row():
                        with gr.Column(scale=2):
                            # Always show automation buttons, even if automation is disabled in environment
                            with gr.Row():
                                start_auto_btn = gr.Button(
                                    "▶️ Start Automation",
                                    variant="primary",
                                    size="sm",
                                    interactive=True,
                                )
                                stop_auto_btn = gr.Button(
                                    "⏹️ Stop Automation",
                                    variant="secondary",
                                    size="sm",
                                    interactive=False,
                                )
                        with gr.Column(scale=1):
                            config_btn = gr.Button("⚙️ Config", size="sm")

                    # Input section with beautiful styling
                    with gr.Row():
                        with gr.Column():
                            gr.HTML(
                                """
                            <div style='background: linear-gradient(135deg, rgba(115, 186, 37, 0.1) 0%, rgba(115, 186, 37, 0.05) 100%); border: 1px solid rgba(115, 186, 37, 0.2); border-radius: 12px; padding: 12px; margin: 10px 0;'>
                                <h4 style='color: #73ba25; margin: 0 0 8px 0; font-size: 1.1em; font-weight: 600;'>💭 Ask Your Question</h4>
                                <p style='color: #ffffff; margin: 0; font-size: 0.9em; opacity: 0.8;'>Compare responses from Direct Ollama and Open WebUI</p>
                            </div>
                            """
                            )
                            with gr.Row():
                                with gr.Column(scale=5):
                                    msg_input = gr.Textbox(
                                        label="",
                                        placeholder="Type your question here to compare AI responses...",
                                        lines=2,
                                        show_label=False,
                                        container=True,
                                        elem_classes="input-box",
                                    )
                                with gr.Column(scale=1, min_width=80):
                                    send_btn = gr.Button(
                                        "Send ❯",
                                        variant="primary",
                                        size="lg",
                                        elem_classes="send-button",
                                    )

                    # Response comparison panels with enhanced styling
                    with gr.Row():
                        with gr.Column():
                            gr.HTML(
                                """
                            <div style='background: linear-gradient(135deg, #1e3a2e 0%, #2d5a3d 100%); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #4CAF50; box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);'>
                                <h4 style='text-align: center; color: #4CAF50; margin: 0; font-size: 1.1em; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.3);'>🤖 Direct Ollama Response</h4>
                                <p style='text-align: center; color: #a5d6a7; margin: 5px 0 0 0; font-size: 0.85em; opacity: 0.9;'>Local AI Model • Direct Connection</p>
                            </div>
                            """
                            )
                            ollama_output = gr.Textbox(
                                label="",
                                lines=12,
                                show_label=False,
                                interactive=False,
                                placeholder="Direct Ollama response will appear here...",
                                container=True,
                                elem_classes="ollama-response",
                            )

                        with gr.Column():
                            gr.HTML(
                                """
                            <div style='background: linear-gradient(135deg, #1a2f3a 0%, #2d4a5a 100%); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #2196F3; box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);'>
                                <h4 style='text-align: center; color: #2196F3; margin: 0; font-size: 1.1em; font-weight: 700; text-shadow: 0 1px 2px rgba(0,0,0,0.3);'>🌐 Open WebUI Response</h4>
                                <p style='text-align: center; color: #90caf9; margin: 5px 0 0 0; font-size: 0.85em; opacity: 0.9;'>Web Interface • Enhanced Features</p>
                            </div>
                            """
                            )
                            webui_output = gr.Textbox(
                                label="",
                                lines=12,
                                show_label=False,
                                interactive=False,
                                placeholder="Open WebUI response will appear here...",
                                container=True,
                                elem_classes="webui-response",
                            )

                    clear_btn = gr.Button("🗑️ Clear All", variant="secondary", size="sm")

                    # Automation status display - always show
                    with gr.Row():
                        automation_status = gr.HTML(
                            value="<div style='text-align: center; color: #ffa726; padding: 10px; background: rgba(255, 167, 38, 0.1); border-radius: 8px; margin: 10px 0;'>⏹️ Automation stopped - Click Start to begin automated testing</div>"
                        )
                        # Removed manual refresh button per UI feedback

        # Configuration Modal (initially hidden)
        with gr.Column(visible=False) as config_panel:
            with gr.Row():
                gr.HTML(
                    "<h3 style='color: #73ba25; text-align: center;'>⚙️ Configuration</h3>"
                )
                close_config_btn = gr.Button(
                    "✕", variant="secondary", size="sm", elem_classes="close-btn"
                )

            # Model selection
            model_dropdown = gr.Dropdown(
                choices=["Loading..."],
                label="🤖 Active Model",
                value="",
                allow_custom_value=True,
            )

            # Automation settings - always available for button handlers
            gr.HTML(
                "<h4 style='color: #73ba25; margin: 15px 0 10px 0;'>🤖 Automation Settings</h4>"
            )

            with gr.Row():
                automation_interval_input = gr.Number(
                    label="Interval (seconds)",
                    value=chat_instance.automation_interval,
                    precision=0,
                    minimum=5,
                    maximum=300,
                )
                automation_send_messages_input = gr.Checkbox(
                    label="Send test messages to models",
                    value=chat_instance.automation_send_messages,
                    info="When enabled, sends test questions to Ollama and Open WebUI",
                )

            with gr.Row():
                automation_provider_test_input = gr.Checkbox(
                    label="Enable Model Provider Status test",
                    value=True,
                    info="When enabled, regularly tests connectivity to model providers and updates status",
                )

            # Automation controls and results moved to main screen for better UX

        # Demo Help Modal (initially hidden)
        with gr.Column(visible=False) as demo_help_modal:
            with gr.Row():
                gr.HTML(
                    "<h3 style='color: #73ba25; text-align: center;'>🔒 SUSE Security Demos</h3>"
                )
                close_demo_help_btn = gr.Button(
                    "✕", variant="secondary", size="sm", elem_classes="close-btn"
                )

            gr.HTML(
                """
            <div style='background: rgba(255, 255, 255, 0.95); border: 1px solid rgba(220, 53, 69, 0.3); border-radius: 8px; padding: 12px; margin: 10px 0;'>
                <p style='color: #d32f2f; margin: 0; font-size: 0.9em; font-weight: 600;'>
                    🔒 <strong>SUSE Security Demonstration:</strong> These demos simulate real security scenarios that 
                    SUSE NeuVector and SUSE Observability can detect and alert on.
                </p>
            </div>
            """
            )

            gr.HTML(
                """
            <div style='background: rgba(255, 255, 255, 0.95); border: 1px solid rgba(115, 186, 37, 0.3); border-radius: 8px; padding: 12px; margin: 10px 0;'>
                <p style='color: #2e7d32; margin: 0 0 8px 0; font-weight: 700;'>🔍 Security Demo Scenarios:</p>
                <ul style='color: #1b5e20; margin: 0; font-size: 0.85em; padding-left: 20px; font-weight: 500;'>
                    <li><strong>Availability Demo:</strong> Tests external connectivity to https://suse.com (network policy monitoring)</li>
                    <li><strong>Data Leak Demo:</strong> Transmits credit card data to simulate data loss prevention (DLP) detection</li>
                    <li><strong>Security Monitoring:</strong> SUSE NeuVector should detect and alert on sensitive data transmission</li>
                    <li><strong>Observability:</strong> Network traffic and security events are monitored by SUSE security stack</li>
                </ul>
            </div>
            """
            )

        # Demo status message now defined in left panel

        # --- Event Handlers ---

        def handle_send_message(message: str, model: str):
            if not message.strip():
                return "", "", ""
            if not model or any(err in model for err in ["Error", "No models"]):
                error_msg = "⚠️ Please select a valid Ollama model first."
                return error_msg, error_msg, ""

            # Show "Thinking..." in both outputs
            yield "🤔 Thinking...", "🤔 Thinking...", ""

            messages_for_api = [{"role": "user", "content": message}]

            ollama_reply = chat_instance.chat_with_ollama(messages_for_api, model)
            open_webui_reply = chat_instance.chat_with_open_webui(
                messages_for_api, model
            )

            yield ollama_reply, open_webui_reply, ""

        def show_config_panel():
            """Show the configuration panel."""
            return gr.Column(visible=True)

        def hide_config_panel():
            """Hide the configuration panel."""
            return gr.Column(visible=False)

        def show_demo_help_modal():
            """Show the demo help modal."""
            return gr.Column(visible=True)

        def hide_demo_help_modal():
            """Hide the demo help modal."""
            return gr.Column(visible=False)

        def run_availability_demo():
            """Run availability demo directly."""
            _, message, status = chat_instance.run_availability_demo()

            # Create status message HTML based on status with better contrast
            if status == "success":
                status_html = f"<div style='color: #1b5e20; background: rgba(76, 175, 80, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #4CAF50; font-weight: 500;'>{message}</div>"
            elif status == "warning":
                status_html = f"<div style='color: #e65100; background: rgba(255, 167, 38, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #ffa726; font-weight: 500;'>{message}</div>"
            else:
                status_html = f"<div style='color: #c62828; background: rgba(244, 67, 54, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #f44336; font-weight: 500;'>{message}</div>"

            return status_html, gr.HTML(visible=True)

        def run_data_leak_demo():
            """Run data leak demo directly."""
            _, message, status = chat_instance.run_data_leak_demo()

            # Create status message HTML based on status with better contrast
            if status == "success":
                status_html = f"<div style='color: #1b5e20; background: rgba(76, 175, 80, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #4CAF50; font-weight: 500;'>{message}</div>"
            elif status == "warning":
                status_html = f"<div style='color: #e65100; background: rgba(255, 167, 38, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #ffa726; font-weight: 500;'>{message}</div>"
            else:
                status_html = f"<div style='color: #c62828; background: rgba(244, 67, 54, 0.15); padding: 12px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #f44336; font-weight: 500;'>{message}</div>"

            return status_html, gr.HTML(visible=True)

        send_btn.click(
            handle_send_message,
            inputs=[msg_input, model_dropdown],
            outputs=[ollama_output, webui_output, msg_input],
        )
        msg_input.submit(
            handle_send_message,
            inputs=[msg_input, model_dropdown],
            outputs=[ollama_output, webui_output, msg_input],
        )
        clear_btn.click(
            lambda: ("", "", ""), outputs=[ollama_output, webui_output, msg_input]
        )

        # Removed refresh button per UI feedback - no click handler needed
        config_btn.click(show_config_panel, outputs=[config_panel])
        close_config_btn.click(hide_config_panel, outputs=[config_panel])

        # Security demo modal handlers
        availability_demo_btn.click(
            run_availability_demo, outputs=[demo_status_msg, demo_status_msg]
        )
        data_leak_demo_btn.click(
            run_data_leak_demo, outputs=[demo_status_msg, demo_status_msg]
        )
        demo_help_btn.click(
            show_demo_help_modal, outputs=[demo_help_modal]
        )
        close_demo_help_btn.click(
            hide_demo_help_modal, outputs=[demo_help_modal]
        )

        def initial_load():
            """Loads initial data when the UI starts."""
            chat_instance.update_all_provider_status()
            status_html = chat_instance.get_provider_status_html()
            models_dd = chat_instance.refresh_ollama_models()

            # Check if automation is already running and update button states
            if chat_instance.automation_enabled:
                if (
                    chat_instance.automation_thread
                    and chat_instance.automation_thread.is_alive()
                ):
                    # Automation is running - update UI to reflect this
                    running_status = "<div style='text-align: center; color: #4CAF50; padding: 10px; background: rgba(76, 175, 80, 0.1); border-radius: 8px; margin: 10px 0;'>▶️ Automation is running - Automated testing in progress</div>"
                    return (
                        status_html,
                        models_dd,
                        gr.Button(interactive=False),
                        gr.Button(interactive=True),
                        gr.HTML(value=running_status),
                    )
                else:
                    # Automation is not running
                    stopped_status = "<div style='text-align: center; color: #ffa726; padding: 10px; background: rgba(255, 167, 38, 0.1); border-radius: 8px; margin: 10px 0;'>⏹️ Automation stopped - Click Start to begin automated testing</div>"
                    return (
                        status_html,
                        models_dd,
                        gr.Button(interactive=True),
                        gr.Button(interactive=False),
                        gr.HTML(value=stopped_status),
                    )
            else:
                return status_html, models_dd

        if chat_instance.automation_enabled:
            interface.load(
                initial_load,
                outputs=[
                    provider_status_html,
                    model_dropdown,
                    start_auto_btn,
                    stop_auto_btn,
                    automation_status,
                ],
            )
        else:
            interface.load(initial_load, outputs=[provider_status_html, model_dropdown])

        # Add a simple auto-refresh for provider status every 10 seconds
        def refresh_provider_status():
            """Refresh provider status display."""
            chat_instance.update_all_provider_status()
            return gr.HTML(value=chat_instance.get_provider_status_html())

        # Only set up UI refresh mechanism - no background pinging unless automation is running
        logger.info(
            "UI refresh mechanism ready - background processes controlled by automation state"
        )

        # --- Automation Event Handlers - Always available ---
        start_auto_btn.click(
            chat_instance.start_automation,
            inputs=[
                model_dropdown,
                automation_interval_input,
                automation_send_messages_input,
            ],
            outputs=[start_auto_btn, stop_auto_btn, automation_status],
        )
        stop_auto_btn.click(
            chat_instance.stop_automation,
            outputs=[start_auto_btn, stop_auto_btn, automation_status],
        )

        # Update main UI with automation results
        def update_ui_from_queue():
            """Updates main UI elements with automation test questions and responses."""
            logger.info("🔄 UI update_ui_from_queue called - checking results queue")
            logger.info(f"Queue size: {chat_instance.results_queue.qsize()}")
            logger.info(
                f"Latest result available: {chat_instance.latest_automation_result is not None}"
            )

            try:
                latest_result = chat_instance.results_queue.get_nowait()
                logger.info(
                    f"✅ Found new automation result: {latest_result.get('timestamp', 'unknown time')}"
                )

                # Extract data from automation result
                question = latest_result.get("prompt", "")
                ollama_response = latest_result.get("ollama_response", "")
                webui_response = latest_result.get("open_webui_response", "")
                timestamp = latest_result.get("timestamp", "")

                # Update the main UI elements
                question_with_timestamp = (
                    f"🤖 Automation Test [{timestamp}]: {question}"
                )
                status_html = chat_instance.get_provider_status_html()

                logger.info("🎨 Updating main UI with automation data")
                return (
                    question_with_timestamp,
                    ollama_response,
                    webui_response,
                    status_html,
                )

            except queue.Empty:
                # No new results, keep current display
                logger.info("📭 No new results in queue")
                status_html = chat_instance.get_provider_status_html()
                return (
                    gr.Textbox(),
                    gr.Textbox(),
                    gr.Textbox(),
                    gr.HTML(value=status_html),
                )

        # Connect manual refresh button to update main UI
        def manual_refresh_clicked():
            logger.info("🖱️ MANUAL REFRESH BUTTON CLICKED!")
            logger.info(f"🔍 Queue size: {chat_instance.results_queue.qsize()}")
            logger.info(
                f"🔍 Automation running: {chat_instance.automation_thread and chat_instance.automation_thread.is_alive()}"
            )
            result = update_ui_from_queue()
            logger.info("🔄 Manual refresh completed")
            return result

        # Removed manual refresh button per UI feedback - no click handler needed

        # Add a Python-based auto-refresh as fallback
        def auto_refresh_fallback():
            """Fallback Python-based auto-refresh when automation is running."""
            if (
                chat_instance.automation_thread
                and chat_instance.automation_thread.is_alive()
            ):
                logger.info("🔄 Python auto-refresh fallback triggered")
                return update_ui_from_queue()
            else:
                # Return current state if automation is not running
                status_html = chat_instance.get_provider_status_html()
                return (
                    gr.Textbox(),
                    gr.Textbox(),
                    gr.Textbox(),
                    gr.HTML(value=status_html),
                )

        # Set up Python-based auto-refresh every 6 seconds
        gr.HTML(
            """
        <div id="python-auto-refresh-trigger" style="display: none;"></div>
        <script>
        // Trigger Python auto-refresh
        setInterval(() => {
            const trigger = document.getElementById('python-auto-refresh-trigger');
            if (trigger) {
                trigger.click();
            }
        }, 6000);
        </script>
        """
        )

        # Create hidden button for Python auto-refresh
        python_auto_refresh_btn = gr.Button(
            "", elem_id="python-auto-refresh-trigger", visible=False
        )
        python_auto_refresh_btn.click(
            auto_refresh_fallback,
            outputs=[msg_input, ollama_output, webui_output, provider_status_html],
        )

        # Create a simple demo of manual refresh to test JavaScript
        demo_refresh_btn = gr.Button(
            "🔄 DEMO Refresh (For Testing)",
            size="sm",
            visible=True,
            elem_id="demo-refresh-btn",
        )
        demo_refresh_btn.click(
            lambda: "Demo button clicked successfully!",
            outputs=gr.Textbox(visible=False),
        )

        # Use a more robust JavaScript approach with multiple strategies
        # Always available for debugging auto-refresh issues
        gr.HTML(
            """
                <script>
                // Auto-refresh solution with multiple strategies
                let refreshInterval;
                let refreshAttempts = 0;
                const maxRefreshAttempts = 5;
                
                function findAndClickRefreshButton() {
                    console.log('=== Auto-refresh attempt ===');
                    
                    // Strategy 1: Find by ID
                    let refreshButton = document.getElementById('automation-refresh-btn');
                    if (refreshButton && refreshButton.style.display !== 'none') {
                        console.log('✅ Found refresh button by ID');
                        refreshButton.click();
                        refreshAttempts = 0;
                        return true;
                    }
                    
                    // Strategy 2: Find by text content
                    const allButtons = document.querySelectorAll('button');
                    for (let btn of allButtons) {
                        if (btn.textContent.includes('🔄 Refresh') && btn.style.display !== 'none') {
                            console.log('✅ Found refresh button by text');
                            btn.click();
                            refreshAttempts = 0;
                            return true;
                        }
                    }
                    
                    // Strategy 3: Try to trigger Gradio event directly 
                    try {
                        const gradioApp = document.querySelector('.gradio-container');
                        if (gradioApp) {
                            const event = new CustomEvent('gradio:refresh', {
                                detail: { component: 'automation-refresh' }
                            });
                            gradioApp.dispatchEvent(event);
                            console.log('✅ Triggered Gradio refresh event');
                            return true;
                        }
                    } catch (e) {
                        console.log('⚠️ Gradio event trigger failed:', e);
                    }
                    
                    refreshAttempts++;
                    console.log(`❌ Refresh attempt ${refreshAttempts}/${maxRefreshAttempts} failed`);
                    
                    // Stop trying after max attempts
                    if (refreshAttempts >= maxRefreshAttempts) {
                        console.log('❌ Stopping auto-refresh after max attempts');
                        clearInterval(refreshInterval);
                    }
                    
                    return false;
                }
                
                // Start auto-refresh after page loads
                setTimeout(() => {
                    console.log('🚀 Starting auto-refresh system');
                    refreshInterval = setInterval(findAndClickRefreshButton, 5000);
                }, 5000);
                
                // Also listen for manual refresh clicks to reset counter
                document.addEventListener('click', (e) => {
                    if (e.target.textContent.includes('🔄 Refresh')) {
                        console.log('👆 Manual refresh clicked - resetting counter');
                        refreshAttempts = 0;
                    }
                });
                
                // JavaScript-based CSS fix for white background around input box
                function fixWhiteBackground() {
                    console.log('🎨 Applying JavaScript CSS fix for white background');
                    
                    // Create a more aggressive CSS style
                    const style = document.createElement('style');
                    style.textContent = `
                        /* Ultra-aggressive JavaScript CSS injection to fix white background */
                        .input-box * {
                            background: rgba(255, 255, 255, 0.05) !important;
                            background-color: rgba(255, 255, 255, 0.05) !important;
                        }
                        
                        /* Target specific Gradio containers that might have white backgrounds */
                        .input-box .gr-form,
                        .input-box .gr-box,
                        .input-box .gr-padded,
                        .input-box .gr-compact,
                        .input-box .wrap,
                        .input-box > div,
                        .input-box > div > div,
                        .input-box div div {
                            background: rgba(255, 255, 255, 0.05) !important;
                            background-color: rgba(255, 255, 255, 0.05) !important;
                        }
                        
                        /* Force override any inline styles */
                        .input-box *[style*="background"] {
                            background: rgba(255, 255, 255, 0.05) !important;
                            background-color: rgba(255, 255, 255, 0.05) !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    // Also directly modify any elements with white backgrounds
                    const whiteElements = document.querySelectorAll('.input-box *');
                    whiteElements.forEach(el => {
                        const computedStyle = window.getComputedStyle(el);
                        if (computedStyle.backgroundColor === 'rgb(255, 255, 255)' || 
                            computedStyle.backgroundColor === 'white' ||
                            computedStyle.backgroundColor === '#ffffff') {
                            el.style.setProperty('background', 'rgba(255, 255, 255, 0.05)', 'important');
                            el.style.setProperty('background-color', 'rgba(255, 255, 255, 0.05)', 'important');
                            console.log('🎨 Fixed white background on element:', el);
                        }
                    });
                }
                
                // Apply CSS fix after page loads and periodically reapply
                setTimeout(fixWhiteBackground, 2000);
                setTimeout(fixWhiteBackground, 5000);
                setInterval(fixWhiteBackground, 10000); // Reapply every 10 seconds
                </script>
                """
        )
        logger.info(
            "Auto-refresh setup - using ultra-simple JavaScript with full debugging"
        )

        # Auto-refresh every 5 seconds when automation is running
        # Removed periodic refresh - provider status updates are handled by automation loop

        # Auto-start automation in background thread (delayed start with retry logic)
        if chat_instance.automation_enabled:

            def delayed_auto_start():
                import time

                # Wait for interface and services to fully load
                time.sleep(10)

                # Retry logic for Ollama readiness
                max_retries = 6
                retry_delay = 10

                for attempt in range(max_retries):
                    try:
                        logger.info(
                            f"Auto-start attempt {attempt + 1}/{max_retries} - checking for Ollama models..."
                        )
                        models = chat_instance.get_ollama_models()
                        if models and len(models) > 0 and "Error" not in models[0]:
                            model = models[0]
                            logger.info(f"Auto-starting automation with model: {model}")
                            chat_instance.start_automation(
                                model, chat_instance.automation_interval
                            )
                            return
                        else:
                            logger.info(
                                f"No valid models found on attempt {attempt + 1}, retrying in {retry_delay}s..."
                            )
                    except Exception as e:
                        logger.warning(f"Auto-start attempt {attempt + 1} failed: {e}")

                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)

                logger.warning(
                    "Auto-start failed after all retries - Ollama may not be ready or no models available"
                )

            # Start auto-start in background thread
            import threading

            auto_start_thread = threading.Thread(target=delayed_auto_start, daemon=True)
            auto_start_thread.start()

    return interface


if __name__ == "__main__":
    logger.info("Starting Chat Interface application.")
    app_interface = create_interface()
    # In K8s, we bind to 0.0.0.0 to be accessible from outside the container
    app_interface.launch(server_name="0.0.0.0", server_port=7860, show_error=True)
# Added a comment to trigger a new build
