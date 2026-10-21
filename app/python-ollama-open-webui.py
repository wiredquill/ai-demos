import json
import logging
import os
import queue
import subprocess
import threading
import time
from typing import Any, Dict, List

import ollama  # Import at top level for OpenLit instrumentation
import openlit  # Import for @openlit.trace decorators
import requests
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server

from ollama_openai_client import OllamaOpenAIClient  # New OpenAI-pattern client

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
# --- End Logging Configuration ---

UI_PORT = int(os.getenv("UI_PORT", "7860"))
UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
UI_FILES = {"app.css", "app.js", "favicon.svg"}

# Levels the response_level pipeline applies; index is sent to the pipeline so labels match
PIPELINE_LEVELS = [
    {"name": "Default", "icon": "🎯", "modifier": ""},
    {
        "name": "Kid Mode",
        "icon": "🧒",
        "modifier": "Explain like I'm 5 years old using simple words, fun examples, and easy-to-understand concepts.",
    },
    {
        "name": "Young Scientist",
        "icon": "🔬",
        "modifier": "Explain like I'm 12 years old with some science details but keep it understandable and engaging.",
    },
    {
        "name": "College Student",
        "icon": "🎓",
        "modifier": "Explain like I'm a college student with technical context, examples, and deeper analysis.",
    },
    {
        "name": "Scientific",
        "icon": "⚗️",
        "modifier": "Give me the full scientific explanation with precise terminology, detailed mechanisms, and technical accuracy.",
    },
]

# Prefixes the response_level pipeline uses when it answers 200 but could not get a model response
PIPELINE_ERROR_PREFIXES = ("Pipeline processed the request", "Pipeline error:", "🔴 **Pipeline Service BROKEN**")

# --- OpenLit Observability Integration ---
try:
    import openlit

    OPENLIT_AVAILABLE = True
except ImportError:
    OPENLIT_AVAILABLE = False
    logger.warning("OpenLit not available - observability disabled")


# --- HTTP API Server for Observable Traffic ---
class ObservableAPIServer:
    """Flask-based HTTP API server for generating observable traffic patterns."""

    def __init__(self, chat_interface, port=8080):
        self.chat_interface = chat_interface
        self.port = port
        self.app = Flask(__name__)
        self.server = None
        self.server_thread = None
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP API routes for observable traffic."""

        @self.app.route("/healthz", methods=["GET", "OPTIONS"])
        def kubernetes_liveness():
            """Kubernetes liveness probe endpoint - fails when availability demo is active to ensure service shows as down."""
            import time

            # Check if availability demo is active via ConfigMap state
            try:
                (
                    is_demo_active,
                    demo_state,
                    config_value,
                ) = self.chat_interface._check_configmap_demo_state()
                if is_demo_active and demo_state == "ON":
                    logger.warning(
                        f"Kubernetes liveness check FAILED - Availability demo ACTIVE (ConfigMap broken: {config_value})"
                    )
                    # Make the entire service unresponsive for SUSE Observability
                    # Use a longer hang time to ensure persistent failure detection
                    time.sleep(300)  # Hang for 5 minutes to ensure sustained outage

                    # Should never reach here due to timeout
                    return (
                        jsonify(
                            {
                                "status": "DEMO_FAILURE",
                                "demo_state": demo_state,
                                "error": f"Service down - {config_value}",
                                "timestamp": time.time(),
                                "check_type": "liveness",
                            }
                        ),
                        503,
                    )
            except Exception as configmap_error:
                logger.debug(f"ConfigMap check failed (liveness continues): {configmap_error}")

            # Normal healthy response when demo is OFF
            logger.debug("Kubernetes liveness check - healthy")
            return (
                jsonify(
                    {
                        "status": "HEALTHY",
                        "timestamp": time.time(),
                        "check_type": "liveness",
                    }
                ),
                200,
            )

        @self.app.route("/health", methods=["GET", "OPTIONS"])
        def health_check():
            """Health check endpoint for observability - automatically fails when availability demo ConfigMap is in broken state."""
            import time  # Add time import at function top

            try:
                # First, check if SERVICE_HEALTH_FAILURE environment variable is explicitly set to true (for manual control)
                import os

                if os.getenv("SERVICE_HEALTH_FAILURE", "false").lower() == "true":
                    logger.error("Health check failed - SERVICE_HEALTH_FAILURE=true (manual override)")
                    return (
                        jsonify(
                            {
                                "status": "FAILING",
                                "error": "SERVICE_HEALTH_FAILURE=true",
                                "timestamp": time.time(),
                            }
                        ),
                        500,
                    )

                # Automatically check ConfigMap state for availability demo
                try:
                    (
                        is_demo_active,
                        demo_state,
                        config_value,
                    ) = self.chat_interface._check_configmap_demo_state()
                    if is_demo_active and demo_state == "ON":
                        logger.error(f"Health check failed - Availability demo ACTIVE (ConfigMap broken: {config_value})")

                        # Pure service down mode - always hang connection to simulate complete service failure
                        logger.warning("Availability demo ACTIVE - simulating complete service down (hanging connection)")

                        # Hang connection indefinitely to simulate service completely down
                        # This will cause monitoring systems to see connection timeouts/refused
                        time.sleep(300)  # Hang for 5 minutes to ensure sustained outage

                        # This should never be reached due to timeout, but return error if it somehow does
                        return (
                            jsonify(
                                {
                                    "status": "SERVICE_DOWN_SIMULATION",
                                    "error": f"Service completely unresponsive - {config_value}",
                                    "demo_state": demo_state,
                                    "timestamp": time.time(),
                                }
                            ),
                            503,  # Service Unavailable
                        )
                except Exception as configmap_error:
                    # If ConfigMap check fails, log but don't fail health check
                    logger.debug(f"ConfigMap check failed (health check continues): {configmap_error}")

                logger.info("Health check successful - service operational")
                return (
                    jsonify(
                        {
                            "status": "HEALTHY",
                            "timestamp": time.time(),
                            "uptime": time.time(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                logger.error(f"Health check endpoint error: {e}")
                return jsonify({"status": "ERROR", "error": str(e)}), 500

        @self.app.route("/api/test", methods=["GET", "OPTIONS"])
        def test_endpoint():
            """Simple test endpoint for debugging API routing."""
            logger.info("Test endpoint accessed successfully")
            return (
                jsonify(
                    {
                        "message": "API routing is working!",
                        "timestamp": time.time(),
                        "service_health_failure": getattr(self.chat_interface, "service_health_failure", False),
                    }
                ),
                200,
            )

        @self.app.route("/ask", methods=["GET", "POST", "OPTIONS"])
        def ask_endpoint():
            """GenAI ask endpoint for SUSE Observability detection - matches pattern from working GenAI apps."""
            logger.info("GenAI /ask endpoint called for SUSE Observability detection")

            try:
                # Use a simple test prompt to generate telemetry
                test_prompt = "Hello, this is a SUSE Observability GenAI detection test."

                # Generate telemetry through Ollama with OpenAI client pattern
                model = self.chat_interface.default_model()
                response = self.chat_interface.ollama_openai_client.ask_endpoint_handler(test_prompt, model)

                return jsonify(
                    {
                        "status": "success",
                        "genai_system": "ollama",
                        "model": model,
                        "response": (response[:100] + "..." if len(response) > 100 else response),
                        "application": "ai-compare-genai-app",
                        "framework": "flask-ollama-openlit",
                        "observability": "suse-observability-enabled",
                    }
                )
            except Exception as e:
                logger.error(f"GenAI /ask endpoint error: {e}")
                return jsonify(
                    {
                        "status": "success",  # Return success even on error for detection
                        "genai_system": "ollama",
                        "model": "llama3.2:latest",
                        "application": "ai-compare-genai-app",
                        "framework": "flask-ollama-openlit",
                        "observability": "suse-observability-enabled",
                        "note": "GenAI endpoint active for SUSE Observability detection",
                    }
                )

        @self.app.route("/api/status", methods=["GET", "OPTIONS"])
        def provider_status():
            """Provider status endpoint for React frontend."""
            logger.info("Provider status endpoint accessed")
            try:
                # Return current provider status in the format expected by React frontend
                return (
                    jsonify(
                        {
                            "providers": self.chat_interface.provider_status,
                            "timestamp": time.time(),
                        }
                    ),
                    200,
                )
            except Exception as e:
                logger.error(f"Provider status endpoint error: {e}")
                return (
                    jsonify({"error": str(e), "providers": {}, "timestamp": time.time()}),
                    500,
                )

        @self.app.route("/api/demo/status", methods=["GET", "OPTIONS"])
        def demo_status():
            """Demo status endpoint for React frontend."""
            logger.info("Demo status endpoint accessed")
            try:
                # Get real-time ConfigMap state for availability demo
                (
                    is_active,
                    state,
                    config_value,
                ) = self.chat_interface._check_configmap_demo_state()

                return (
                    jsonify(
                        {
                            "availability_demo": {
                                "is_active": is_active,
                                "config_value": config_value,
                                "last_toggled": getattr(
                                    self.chat_interface,
                                    "availability_demo_last_toggled",
                                    None,
                                ),
                            },
                            "data_leak_demo": {
                                "is_active": False,  # Data leak demo is always momentary
                                "last_triggered": getattr(
                                    self.chat_interface,
                                    "data_leak_last_triggered",
                                    None,
                                ),
                            },
                            "timestamp": time.time(),
                        }
                    ),
                    200,
                )
            except Exception as e:
                logger.error(f"Demo status endpoint error: {e}")
                return jsonify({"error": str(e), "timestamp": time.time()}), 500

        @self.app.route("/api/chat", methods=["POST", "OPTIONS"])
        def chat_completion():
            """Chat completion endpoint for frontend communication."""
            import time  # Add time import at function top

            try:
                # Check for manual service health failure via environment variable
                import os

                if os.getenv("SERVICE_HEALTH_FAILURE", "false").lower() == "true":
                    logger.error("Chat API failed - SERVICE_HEALTH_FAILURE=true (SUSE Observability pattern)")
                    return (
                        jsonify(
                            {
                                "error": "Service degraded - health check failure",
                                "status": "service_failure",
                                "timestamp": time.time(),
                            }
                        ),
                        500,
                    )

                # Check ConfigMap-based availability demo state
                try:
                    (
                        is_demo_active,
                        demo_state,
                        config_value,
                    ) = self.chat_interface._check_configmap_demo_state()
                    if is_demo_active and demo_state == "ON":
                        logger.error(f"Chat API failed - Availability demo ACTIVE (ConfigMap broken: {config_value})")

                        # Pure service down mode - always hang connection to simulate complete service failure
                        logger.warning(
                            "Availability demo ACTIVE - Chat API simulating complete service down (hanging connection)"
                        )

                        # Hang connection indefinitely to simulate service completely down
                        # This will cause monitoring systems to see connection timeouts/refused
                        time.sleep(300)  # Hang for 5 minutes to ensure sustained outage

                        # This should never be reached due to timeout, but return error if it somehow does
                        return (
                            jsonify(
                                {
                                    "error": f"Chat service completely unresponsive - {config_value}",
                                    "status": "chat_service_down_simulation",
                                    "demo_state": demo_state,
                                    "timestamp": time.time(),
                                }
                            ),
                            503,  # Service Unavailable
                        )
                except Exception as configmap_error:
                    logger.debug(f"ConfigMap check failed (chat API continues): {configmap_error}")

                data = request.get_json()
                if not data or "message" not in data:
                    logger.warning("Chat API - missing message in request")
                    return jsonify({"error": "Missing 'message' in request body"}), 400

                message = data["message"]
                model = data.get("model") or self.chat_interface.default_model()
                target = data.get("target")

                logger.info(f"Chat API request - message: '{message[:50]}...', model: {model}, target: {target or 'both'}")

                messages = [{"role": "user", "content": message}]

                # The UI asks for each side separately so the two panes fill in independently
                if target in ("direct", "pipeline"):
                    started = time.time()
                    if target == "direct":
                        content = self.chat_interface.chat_with_ollama(messages, model)
                        result = {
                            "ok": not content.startswith("Error communicating with Ollama"),
                            "route": "Direct Ollama",
                            "content": content,
                        }
                    else:
                        result = self.chat_interface.chat_via_pipeline(messages, model)
                    result.update(
                        {
                            "target": target,
                            "model": model,
                            "latency_ms": int((time.time() - started) * 1000),
                            "timestamp": time.time(),
                        }
                    )
                    return jsonify(result), 200

                # Ollama response
                logger.info(f"Requesting Ollama response from {self.chat_interface.ollama_base_url}")
                try:
                    ollama_response = self.chat_interface.chat_with_ollama(messages, model)
                    logger.info(f"Ollama response received: {ollama_response[:100]}...")
                except Exception as e:
                    logger.error(f"Ollama request failed: {e}")
                    ollama_response = f"Ollama Error: {str(e)}"

                # Open WebUI response
                logger.info(f"Requesting Open WebUI response from {self.chat_interface.open_webui_base_url}")
                try:
                    webui_response = self.chat_interface.chat_with_open_webui(messages, model)
                    logger.info(f"Open WebUI response received: {webui_response[:100]}...")
                except Exception as e:
                    logger.error(f"Open WebUI request failed: {e}")
                    webui_response = f"Open WebUI Error: {str(e)}"

                result = {
                    "ollama_response": ollama_response,
                    "webui_response": webui_response,
                    "status": "success",
                    "timestamp": time.time(),
                    "model": model,
                }

                logger.info("Chat API request completed successfully")
                return jsonify(result), 200

            except Exception as e:
                import traceback

                logger.error(f"Chat API endpoint error: {e}")
                logger.error(f"Chat API traceback: {traceback.format_exc()}")
                return (
                    jsonify(
                        {
                            "error": str(e),
                            "status": "error",
                            "timestamp": time.time(),
                            "details": "Check server logs for full traceback",
                        }
                    ),
                    500,
                )

        @self.app.route("/api/availability-demo/toggle", methods=["POST", "OPTIONS"])
        def toggle_availability_demo():
            """Toggle availability demo state."""
            try:
                message, status = self.chat_interface.run_availability_demo()
                is_active, _, config_value = self.chat_interface._check_configmap_demo_state()

                result = {
                    "message": message,
                    "status": status,
                    "service_failure_active": self.chat_interface.service_health_failure,
                    "is_active": is_active,
                    "config_value": config_value,
                    "timestamp": time.time(),
                }

                logger.info(f"Availability demo toggled - failure active: {self.chat_interface.service_health_failure}")
                return jsonify(result), 200

            except Exception as e:
                logger.error(f"Availability demo API error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 500

        @self.app.route("/api/data-leak-demo", methods=["POST", "OPTIONS"])
        def run_data_leak_demo():
            """Run data leak demo."""
            try:
                message, status = self.chat_interface.run_data_leak_demo()

                result = {
                    "message": message,
                    "status": status,
                    "data_types": ["credit_card", "ssn"],
                    "timestamp": time.time(),
                }

                logger.info("Data leak demo executed via API")
                return jsonify(result), 200

            except Exception as e:
                logger.error(f"Data leak demo API error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 500

        @self.app.route("/api/load-simulator/status", methods=["GET", "OPTIONS"])
        def load_simulator_status():
            """Get load simulator status."""
            try:
                sim = self.chat_interface.check_load_simulator_status()
                is_running = sim.get("running", False)

                return (
                    jsonify(
                        {
                            "status": "running" if is_running else "stopped",
                            "is_running": is_running,
                            "detail": sim.get("status"),
                            "request_count": getattr(self.chat_interface, "load_simulator_request_count", 0),
                            "last_request": getattr(self.chat_interface, "load_simulator_last_request", None),
                            "timestamp": time.time(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                logger.error(f"Load simulator status API error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 500

        @self.app.route("/api/load-simulator/start", methods=["POST", "OPTIONS"])
        def start_load_simulator():
            """Start load simulator."""
            try:
                success, message = self.chat_interface.start_load_simulator()

                return jsonify(
                    {
                        "message": message,
                        "status": "running" if success else "error",
                        "simulator_status": "running" if success else "error",
                        "timestamp": time.time(),
                    }
                ), (200 if success else 500)

            except Exception as e:
                logger.error(f"Start load simulator API error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 500

        @self.app.route("/api/load-simulator/stop", methods=["POST", "OPTIONS"])
        def stop_load_simulator():
            """Stop load simulator."""
            try:
                success, message = self.chat_interface.stop_load_simulator()

                return jsonify(
                    {
                        "message": message,
                        "status": "stopped" if success else "error",
                        "simulator_status": "stopped" if success else "error",
                        "timestamp": time.time(),
                    }
                ), (200 if success else 500)

            except Exception as e:
                logger.error(f"Stop load simulator API error: {e}")
                return jsonify({"error": str(e), "status": "error"}), 500

        @self.app.route("/api/models", methods=["GET", "OPTIONS"])
        def list_models():
            """Models installed on Ollama."""
            try:
                models = self.chat_interface.get_ollama_models()
                ok = bool(models) and "Error" not in models[0] and "No models" not in models[0]
                return jsonify({"models": models if ok else [], "error": None if ok else models[0]}), 200
            except Exception as e:
                logger.error(f"Models endpoint error: {e}")
                return jsonify({"models": [], "error": str(e)}), 500

        @self.app.route("/api/info", methods=["GET", "OPTIONS"])
        def app_info():
            """Static facts about this deployment for the UI header."""
            ci = self.chat_interface
            return (
                jsonify(
                    {
                        "namespace": os.getenv("KUBERNETES_NAMESPACE", ""),
                        "pod": os.getenv("K8S_POD_NAME") or os.getenv("HOSTNAME", ""),
                        "ollama_url": ci.ollama_base_url,
                        "pipelines_url": ci.pipelines_base_url,
                        "open_webui_url": ci.open_webui_base_url,
                        "observability_enabled": ci.observability_enabled,
                        "otlp_endpoint": os.getenv("OTLP_ENDPOINT", ""),
                        "levels": [{"name": lvl["name"], "icon": lvl["icon"]} for lvl in PIPELINE_LEVELS],
                    }
                ),
                200,
            )

        @self.app.route("/api/providers/refresh", methods=["POST", "OPTIONS"])
        def refresh_providers():
            """Re-check external provider reachability now."""
            try:
                self.chat_interface.update_all_provider_status()
                return jsonify({"providers": self.chat_interface.provider_status, "timestamp": time.time()}), 200
            except Exception as e:
                logger.error(f"Provider refresh error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/metrics", methods=["GET", "OPTIONS"])
        def get_metrics():
            """Get application metrics for monitoring."""
            try:
                import psutil

                metrics = {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent,
                    "service_health_failure": getattr(self.chat_interface, "service_health_failure", False),
                    "timestamp": time.time(),
                    "uptime": time.time(),
                }

                return jsonify(metrics), 200

            except Exception as e:
                logger.error(f"Metrics API error: {e}")
                return jsonify({"error": str(e)}), 500

        # Frontend serving routes
        @self.app.route("/", methods=["GET", "OPTIONS"])
        def serve_frontend():
            """Serve the main frontend HTML file."""
            try:
                return send_from_directory(UI_DIR, "index.html")
            except Exception as e:
                logger.error(f"Error serving frontend index: {e}")
                return f"Frontend error: {e}", 500

        @self.app.route("/<path:filename>", methods=["GET", "OPTIONS"])
        def serve_frontend_files(filename):
            """Serve frontend static files (CSS, JS, etc.)."""
            try:
                if filename in UI_FILES:
                    return send_from_directory(UI_DIR, filename)
                return "File not found", 404
            except Exception as e:
                logger.error(f"Error serving frontend file {filename}: {e}")
                return f"Frontend file error: {e}", 500

        # Add CORS headers to all responses
        @self.app.after_request
        def after_request(response):
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
            response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS")
            return response

    def start_server(self):
        """Start the HTTP API server in background thread."""
        try:
            # --- SUSE Observability: connected topology ---
            # Instrument the Flask app EXPLICITLY. openlit.init() already ran in
            # ChatInterface.__init__ (before this server object was built), and
            # its global Flask auto-instrumentor only patches apps constructed
            # AFTER init - so without this, /api/chat and /ask would never get
            # an incoming SERVER span. With one, the outbound requests calls in
            # chat_with_open_webui (pipelines/open-webui) and the ollama calls
            # nest under it, and the collector's topology exporter sees real
            # ai-compare -> pipelines / open-webui / ollama edges instead of
            # disconnected traces. Same explicit-instrumentation fix hr-assistant
            # made with FastAPIInstrumentor (2026-08-26).
            #
            # excluded_urls is matched with re.search against the full request URL
            # (scheme+host+path): "health" is a substring of both /health and
            # /healthz, so probes never create spans; /api/metrics and /static/
            # are excluded as noise. The real API endpoints (/api/chat, /ask,
            # /api/status, ...) stay instrumented.
            try:
                from opentelemetry.instrumentation.flask import FlaskInstrumentor

                FlaskInstrumentor.instrument_app(self.app, excluded_urls="health|/api/metrics|/static/")
                logger.info("FlaskInstrumentor enabled on Observable HTTP API server")
            except Exception as flask_instr_error:
                logger.warning(f"Could not enable FlaskInstrumentor: {flask_instr_error}")

            self.server = make_server("0.0.0.0", self.port, self.app, threaded=True)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            logger.info(f"Observable HTTP API server started on port {self.port}")

        except Exception as e:
            logger.error(f"Failed to start HTTP API server: {e}")

    def stop_server(self):
        """Stop the HTTP API server."""
        if self.server:
            self.server.shutdown()
            logger.info("Observable HTTP API server stopped")


class ChatInterface:
    """
    Application state and backend logic behind the HTTP API and web UI.
    """

    def __init__(self):
        self.config_path = "config.json"
        self.config = self.load_or_create_config()

        # Initialize availability demo state tracking
        self.availability_demo_last_check = 0
        self.availability_demo_auto_off_timer = None

        # Initialize provider status with pre-drawn boxes (default offline)
        # CRITICAL: Always guarantee all 9 providers are present from startup
        default_providers = {
            "OpenAI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "DeepSeek": {"country": "🇨🇳 China", "flag": "🇨🇳"},
            "Google Gemini": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Cohere": {"country": "🇨🇦 Canada", "flag": "🇨🇦"},
            "Mistral AI": {"country": "🇫🇷 France", "flag": "🇫🇷"},
            "Perplexity": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Together AI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Groq": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Hugging Face": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
        }

        self.provider_status = {}
        # Always initialize all 10 providers first
        for name, info in default_providers.items():
            self.provider_status[name] = {
                "status": "🔴",
                "response_time": "---ms",
                "country": info["country"],
                "flag": info["flag"],
                "status_code": "Loading",
            }

        # Override with any configured providers (but keep all 10)
        for name, provider_info in self.config.get("providers", {}).items():
            if name in self.provider_status:  # Only update if it's one of our 10
                if isinstance(provider_info, dict):
                    self.provider_status[name]["country"] = provider_info.get("country", self.provider_status[name]["country"])
                    self.provider_status[name]["flag"] = provider_info.get("flag", self.provider_status[name]["flag"])

        # --- MODIFIED: Load URLs from environment variables for K8s ---
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.open_webui_base_url = os.getenv("OPEN_WEBUI_BASE_URL")
        self.pipelines_base_url = os.getenv("PIPELINES_BASE_URL")
        self.pipeline_api_key = os.getenv("PIPELINE_API_KEY")

        # Initialize new OpenAI-pattern client for better OpenLit integration
        self.ollama_openai_client = OllamaOpenAIClient(self.ollama_base_url)

        # Configurable timeout settings optimized for SUSE security policies
        self.connection_timeout = int(os.getenv("CONNECTION_TIMEOUT", "5"))  # Increased for container networking stability
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "15"))  # Increased for model inference operations
        self.inference_timeout = int(os.getenv("INFERENCE_TIMEOUT", "45"))  # Increased for large model inference

        # Don't add Open WebUI to the provider status list - keep it separate for functionality

        if self.ollama_base_url.endswith("/"):
            self.ollama_base_url = self.ollama_base_url[:-1]

        self.ollama_models = []
        self.selected_model = ""

        # Open WebUI authentication
        self.open_webui_token = None

        # --- NEW: Model Config Management State ---
        self.model_config_value = os.getenv("MODEL_CONFIG", "models-latest")
        self.config_map_name = os.getenv("CONFIG_MAP_NAME", "ai-compare-config")
        self.config_map_namespace = os.getenv("CONFIG_MAP_NAMESPACE", "default")

        # --- NEW: Service Health Failure Simulation State ---
        self.service_health_failure = os.getenv("SERVICE_HEALTH_FAILURE", "false").lower() == "true"
        self.deployment_name = os.getenv("DEPLOYMENT_NAME", "ollama-chat-app")
        self.failure_env_var = "SERVICE_HEALTH_FAILURE"

        # --- NEW: Automation Runner State ---
        # Read automation settings from environment variables
        self.automation_enabled = os.getenv("AUTOMATION_ENABLED", "false").lower() == "true"
        self.automation_interval = int(os.getenv("AUTOMATION_INTERVAL", "30"))
        self.automation_send_messages = os.getenv("AUTOMATION_SEND_MESSAGES", "true").lower() == "true"

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

        self.availability_demo_last_toggled = None
        self.data_leak_last_triggered = None

        # --- OpenLit Observability Initialization ---
        self.observability_enabled = False
        self._initialize_observability()

        # --- HTTP API Server for Observable Traffic ---
        self.api_server = None
        self._initialize_api_server()

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

        # Check if observability is enabled
        dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"
        observability_enabled = os.getenv("OBSERVABILITY_ENABLED", "false").lower() == "true"

        if not observability_enabled and not dev_mode:
            logger.info(
                "OpenLit observability disabled (production default). Enable with OBSERVABILITY_ENABLED=true or DEV_MODE=true"
            )
            return

        try:
            # Import and use clean OpenLit initialization
            from openlit_init import initialize_openlit, patch_openlit

            if initialize_openlit():
                # Apply any custom patches
                patch_openlit()
                self.observability_enabled = True

                # Store enhanced observability settings for use in chat methods
                self.enhanced_observability = {
                    "token_tracking": os.getenv("TOKEN_TRACKING_ENABLED", "true").lower() == "true",
                    "cost_tracking": os.getenv("COST_TRACKING_ENABLED", "true").lower() == "true",
                    "model_metrics": os.getenv("MODEL_METRICS_ENABLED", "true").lower() == "true",
                    "trace_requests": os.getenv("TRACE_REQUESTS_ENABLED", "true").lower() == "true",
                    "collect_gpu_stats": os.getenv("COLLECT_GPU_STATS", "false").lower() == "true",
                }

                # Initialize GenAI tracer for manual instrumentation
                try:
                    from opentelemetry import trace

                    self.genai_tracer = trace.get_tracer("ollama-genai-sdk")
                    logger.info("✅ Enhanced GenAI telemetry tracer initialized")
                except Exception as tracer_error:
                    logger.warning(f"Could not initialize enhanced GenAI tracer: {tracer_error}")
                    self.genai_tracer = None
            else:
                logger.warning("OpenLit initialization failed - continuing without observability")

        except ImportError:
            logger.error("Failed to import openlit_init module - check implementation")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenLit observability: {e} - continuing without observability")

    def _initialize_api_server(self):
        """Initialize HTTP API server if enabled."""
        api_enabled = os.getenv("HTTP_API_ENABLED", "true").lower() == "true"
        api_port = int(os.getenv("HTTP_API_PORT", "8080"))

        if not api_enabled:
            logger.info("HTTP API server disabled via HTTP_API_ENABLED environment variable")
            return

        try:
            self.api_server = ObservableAPIServer(self, port=api_port)
            self.api_server.start_server()
            logger.info(f"HTTP API server initialized on port {api_port} for observable traffic generation")

        except Exception as e:
            logger.error(f"Failed to initialize HTTP API server: {e}")
            self.api_server = None

    def _read_demo_config(self, key: str) -> str:
        """Read configuration from mounted ConfigMap for demo purposes."""
        demo_config_path = os.getenv("DEMO_CONFIG_PATH", "/app/demo-config")
        config_file = os.path.join(demo_config_path, key)

        try:
            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    value = f.read().strip()
                    logger.info(f"Read demo config '{key}': {value}")
                    return value
            else:
                logger.warning(f"Demo config file not found: {config_file}")
                return None
        except Exception as e:
            logger.error(f"Failed to read demo config '{key}': {e}")
            return None

    def _simulate_configmap_failure(self) -> bool:
        """Create actual ConfigMap failure by changing the key that breaks the app."""
        try:
            import os
            import subprocess

            # Get namespace and ConfigMap name from environment or use defaults
            namespace = os.getenv("KUBERNETES_NAMESPACE", "ai-compare")
            configmap_name = os.getenv("DEMO_CONFIGMAP_NAME", "ai-compare-demo-config")

            # Verify ConfigMap exists
            try:
                result = subprocess.run(
                    [
                        "kubectl",
                        "get",
                        "configmap",
                        configmap_name,
                        "-n",
                        namespace,
                        "-o",
                        "name",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    logger.error(f"ConfigMap {configmap_name} not found in namespace {namespace}")
                    return False
                else:
                    logger.info(f"Found demo ConfigMap: {configmap_name}")
            except Exception as e:
                logger.error(f"Failed to verify ConfigMap: {e}")
                return False

            # Step 1: Remove the working key 'models-latest'
            logger.info(f"Removing working ConfigMap key 'models-latest' from {configmap_name}")
            result1 = subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "configmap",
                    configmap_name,
                    "-n",
                    namespace,
                    "--type=json",
                    '-p=[{"op": "remove", "path": "/data/models-latest"}]',
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            # Step 2: Add the broken key 'models_latest' (underscore breaks the app)
            logger.info(f"Adding broken ConfigMap key 'models_latest' to {configmap_name}")
            result2 = subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "configmap",
                    configmap_name,
                    "-n",
                    namespace,
                    "--type=json",
                    '-p=[{"op": "add", "path": "/data/models_latest", "value": "broken-model:invalid"}]',
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result1.returncode == 0 and result2.returncode == 0:
                logger.info("✅ ConfigMap manipulation successful - app should start failing!")
                logger.info(
                    '🔧 To fix externally: kubectl patch configmap <name> -n <namespace> --type=json -p=\'[{"op": "remove", "path": "/data/models_latest"}, {"op": "add", "path": "/data/models-latest", "value": "llama3.2:latest"}]\''
                )
                return True
            else:
                logger.error(f"ConfigMap patch failed: {result1.stderr} {result2.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("kubectl command timed out - ConfigMap manipulation failed")
            return False
        except Exception as e:
            logger.error(f"ConfigMap failure simulation error: {e}")
            return False

    def _check_configmap_demo_state(self) -> tuple:
        """Check current ConfigMap state to determine availability demo status.

        Probes, chat requests and the UI all ask for this, so the kubectl result is cached briefly.
        """
        cached = getattr(self, "_demo_state_cache", None)
        if cached and time.time() - cached[0] < 3:
            return cached[1]
        state = self._read_configmap_demo_state()
        self._demo_state_cache = (time.time(), state)
        return state

    def _read_configmap_demo_state(self) -> tuple:
        try:
            import json
            import os
            import subprocess

            # Get namespace and ConfigMap name from environment or use defaults
            namespace = os.getenv("KUBERNETES_NAMESPACE", "ai-compare")
            configmap_name = os.getenv("DEMO_CONFIGMAP_NAME", "ai-compare-demo-config")

            # Get ConfigMap data
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "configmap",
                    configmap_name,
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Could not read ConfigMap {configmap_name}: {result.stderr}")
                return False, "unknown", "ConfigMap not accessible"

            configmap_data = json.loads(result.stdout)
            data = configmap_data.get("data", {})

            # Check if demo is ON (broken key exists) or OFF (working key exists)
            if "models_latest" in data:
                # Demo is ON - broken configuration
                broken_value = data["models_latest"]
                return True, "ON", f"Broken config: {broken_value}"
            elif "models-latest" in data:
                # Demo is OFF - working configuration
                working_value = data["models-latest"]
                return False, "OFF", f"Working config: {working_value}"
            else:
                # Neither key exists - unknown state
                return False, "unknown", "No demo configuration found"

        except Exception as e:
            logger.error(f"Error checking ConfigMap demo state: {e}")
            return False, "error", f"Error: {str(e)}"

    def _start_auto_off_timer(self):
        """Start a 60-second timer to automatically turn off demo after ConfigMap is fixed."""

        def auto_off_worker():
            """Worker thread that waits 60 seconds then checks ConfigMap and turns off demo."""
            import time

            logger.info("Auto-off timer started - will check ConfigMap in 60 seconds")
            time.sleep(60)

            # Check if ConfigMap has been fixed (working key exists)
            is_demo_on, state, config_value = self._check_configmap_demo_state()

            if not is_demo_on and state == "OFF":
                # ConfigMap has been fixed, turn off internal demo state
                logger.info("Auto-off timer triggered - ConfigMap fixed, turning off demo")
                self.service_health_failure = False
                self.availability_demo_auto_off_timer = None
            else:
                logger.info(f"Auto-off timer expired but ConfigMap still broken ({state})")
                self.availability_demo_auto_off_timer = None

        # Cancel any existing timer
        if (
            hasattr(self, "availability_demo_auto_off_timer")
            and self.availability_demo_auto_off_timer
            and self.availability_demo_auto_off_timer.is_alive()
        ):
            logger.info("Canceling existing auto-off timer")

        # Start new timer
        self.availability_demo_auto_off_timer = threading.Thread(target=auto_off_worker, daemon=True)
        self.availability_demo_auto_off_timer.start()

    def _restore_configmap_health(self) -> bool:
        """Restore ConfigMap health by fixing the broken configuration."""
        try:
            import os
            import subprocess

            # Get namespace and ConfigMap name from environment or use defaults
            namespace = os.getenv("KUBERNETES_NAMESPACE", "ai-compare")
            configmap_name = os.getenv("DEMO_CONFIGMAP_NAME", "ai-compare-demo-config")

            # Verify ConfigMap exists
            try:
                result = subprocess.run(
                    [
                        "kubectl",
                        "get",
                        "configmap",
                        configmap_name,
                        "-n",
                        namespace,
                        "-o",
                        "name",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    logger.error(f"ConfigMap {configmap_name} not found in namespace {namespace}")
                    return False
                else:
                    logger.info(f"Found demo ConfigMap: {configmap_name}")
            except Exception as e:
                logger.error(f"Failed to verify ConfigMap: {e}")
                return False

            # Step 1: Remove the broken key 'models_latest'
            logger.info(f"Removing broken ConfigMap key 'models_latest' from {configmap_name}")
            result1 = subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "configmap",
                    configmap_name,
                    "-n",
                    namespace,
                    "--type=json",
                    '-p=[{"op": "remove", "path": "/data/models_latest"}]',
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            # Step 2: Restore the working key 'models-latest' from the chart's models-backup value,
            # since the charts ship different default models (tinyllama vs llama3.2)
            backup = subprocess.run(
                ["kubectl", "get", "configmap", configmap_name, "-n", namespace, "-o", "jsonpath={.data.models-backup}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            restore_value = backup.stdout.strip() if backup.returncode == 0 and backup.stdout.strip() else "llama3.2:latest"
            logger.info(f"Restoring working ConfigMap key 'models-latest'={restore_value} to {configmap_name}")
            patch = [{"op": "add", "path": "/data/models-latest", "value": restore_value}]
            result2 = subprocess.run(
                [
                    "kubectl",
                    "patch",
                    "configmap",
                    configmap_name,
                    "-n",
                    namespace,
                    "--type=json",
                    f"-p={json.dumps(patch)}",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result1.returncode == 0 and result2.returncode == 0:
                logger.info("✅ ConfigMap restoration successful - app should start working!")
                return True
            else:
                logger.error(f"ConfigMap restoration failed: {result1.stderr} {result2.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("kubectl command timed out - ConfigMap restoration failed")
            return False
        except Exception as e:
            logger.error(f"ConfigMap health restoration error: {e}")
            return False
            return False

    def default_model(self) -> str:
        """Model for callers that don't pick one: the demo ConfigMap's model, else the first installed model."""
        installed = self.ollama_models or self.get_ollama_models()
        installed = [m for m in installed if "Error" not in m and "No models" not in m]
        configured = self._read_demo_config("models-latest")
        if configured and configured in installed:
            return configured
        if installed:
            return installed[0]
        return configured or "llama3.2:latest"

    def get_ollama_models(self) -> List[str]:
        """Fetches the list of available models, checking ConfigMap config first for demo purposes."""
        logger.info(f"Attempting to fetch Ollama models from {self.ollama_base_url}/api/tags")

        # Check demo configuration first - if it's broken, fail immediately
        demo_models = self._read_demo_config("models-latest")
        if demo_models and ("broken-model" in demo_models or "invalid" in demo_models):
            logger.error(f"ConfigMap contains invalid model configuration: {demo_models}")
            raise Exception("ConfigMap model configuration is invalid - service failure simulation")

        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=self.connection_timeout)
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
        """Chat with Ollama using OpenAI client pattern with OpenLit automatic instrumentation."""
        try:
            logger.info(f"Chatting with Ollama model via OpenAI client: {model}")

            # Use the OpenAI client pattern with OpenLit automatic instrumentation
            response = self.ollama_openai_client.chat_with_ollama(messages, model)

            (
                logger.info(f"Ollama response received: {response[:100]}...")
                if len(response) > 100
                else logger.info(f"Ollama response: {response}")
            )
            return response

        except Exception as e:
            logger.error(f"Error in chat_with_ollama: {e}")
            return f"Error communicating with Ollama: {str(e)}"

    @staticmethod
    def _extract_content(response_data: dict) -> str:
        """Pull message content out of an OpenAI- or Ollama-shaped response."""
        if response_data.get("choices"):
            return response_data["choices"][0].get("message", {}).get("content", "")
        return response_data.get("message", {}).get("content", "")

    def chat_via_pipeline(self, messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
        """Runs a request through the response_level pipeline (or its fallbacks).

        Returns a dict with content, level name/icon, the route actually used and an ok flag.
        """
        # The level rotates every 30 seconds so consecutive demo questions show different styles
        level_index = int(time.time() / 30) % len(PIPELINE_LEVELS)
        level = PIPELINE_LEVELS[level_index]
        result = {"level": level["name"], "level_icon": level["icon"], "level_index": level_index}

        if self.service_health_failure:
            logger.warning("Service health failure detected: SERVICE_HEALTH_FAILURE=true")
            return {
                **result,
                "ok": False,
                "route": "Degraded",
                "content": "Service degraded: SERVICE_HEALTH_FAILURE=true. Turn the availability demo off to restore it.",
            }

        # Messages with the level modifier applied locally, for routes that bypass the pipeline
        modified_messages = [dict(m) for m in messages]
        if modified_messages and level["modifier"] and modified_messages[-1]["role"] == "user":
            modified_messages[-1]["content"] = f"{modified_messages[-1]['content']} {level['modifier']}"

        if self.pipelines_base_url:
            # The pipeline applies the level modifier itself, so send the original messages
            # plus the real Ollama model and the level we are labelling the response with
            payload = {
                "model": "response_level",
                "messages": messages,
                "stream": False,
                "max_tokens": 1000,
                "ollama_model": model,
                "response_level": level_index,
            }
            headers = {"Content-Type": "application/json"}
            if self.pipeline_api_key:
                headers["Authorization"] = f"Bearer {self.pipeline_api_key}"

            logger.info(f"Calling Pipelines service at {self.pipelines_base_url} with level: {level['name']}")
            try:
                response = requests.post(
                    f"{self.pipelines_base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.inference_timeout,
                )
                if response.status_code == 200:
                    content = self._extract_content(response.json())
                    # The pipeline reports its own failures as 200 responses with an error message
                    ok = bool(content) and not content.startswith(PIPELINE_ERROR_PREFIXES)
                    if not ok:
                        logger.warning(f"Pipelines service returned an error: {content[:200]}")
                    return {**result, "ok": ok, "route": "Pipelines Service", "content": content}
                logger.warning(
                    f"Pipelines service failed ({response.status_code}): {response.text[:200]}, falling back to direct Ollama"
                )
            except Exception as e:
                logger.warning(f"Pipelines service failed: {e}, falling back to direct Ollama")
        elif self.open_webui_base_url:
            headers = {"Content-Type": "application/json"}
            if self.open_webui_token:
                headers["Authorization"] = f"Bearer {self.open_webui_token}"

            logger.info(f"Calling Open WebUI with level: {level['name']}")
            try:
                response = requests.post(
                    f"{self.open_webui_base_url}/api/v1/chat/completions",
                    json={"model": model, "messages": modified_messages, "stream": False, "max_tokens": 1000},
                    headers=headers,
                    timeout=self.inference_timeout,
                )
                if response.status_code == 200:
                    content = self._extract_content(response.json())
                    return {**result, "ok": bool(content), "route": "Open WebUI", "content": content}
                logger.warning(f"Open WebUI failed ({response.status_code}), falling back to direct Ollama")
            except Exception as e:
                logger.warning(f"Open WebUI failed: {e}, falling back to direct Ollama")

        # Direct Ollama with the level modifier applied locally - still the pipeline behaviour
        logger.info(f"Using direct Ollama with pipeline level: {level['name']}")
        content = self.chat_with_ollama(modified_messages, model)
        return {
            **result,
            "ok": not content.startswith("Error communicating with Ollama"),
            "route": "Direct Ollama fallback",
            "content": content,
        }

    def chat_with_open_webui(self, messages: List[Dict[str, str]], model: str) -> str:
        """Pipeline response formatted with its level header (the format load-gen and logs expect)."""
        r = self.chat_via_pipeline(messages, model)
        return f"🔄 **Pipeline Mode**: {r['level_icon']} {r['level']} (via {r['route']})\n\n{r['content']}"

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

        # FIXED: Special timeout handling for problematic providers
        # DeepSeek and other Chinese services are often blocked, use very short timeout
        # ⚠️ IMPORTANT: DO NOT CHANGE THIS LOGIC - DeepSeek consistently causes 20s delays when blocked

        # Fast timeout for commonly blocked providers
        blocked_providers = [
            "DeepSeek",
            "OpenAI",
            "Cohere",
            "Mistral",
            "Perplexity",
            "Together",
            "Together AI",
            "Groq",
            "Hugging Face",
        ]
        blocked_domains = [
            "deepseek.com",
            "openai.com",
            "cohere.com",
            "mistral.ai",
            "perplexity.ai",
            "together.ai",
            "together.xyz",
            "groq.com",
            "huggingface.co",
        ]

        # Google Gemini gets normal timeout (it's usually allowed)
        if provider_name == "Google Gemini" or "google" in url.lower() or "gemini" in url.lower():
            provider_timeout = self.connection_timeout  # Normal timeout for Google
            logger.info(f"Using normal timeout ({self.connection_timeout}s) for allowed provider: {provider_name}")
        # Fast timeout for commonly blocked providers to prevent delays
        elif provider_name in blocked_providers or any(domain in url.lower() for domain in blocked_domains):
            provider_timeout = 1  # 1 second timeout for potentially blocked providers
            logger.info(f"Using fast timeout (1s) for potentially blocked provider: {provider_name}")
        else:
            provider_timeout = self.connection_timeout

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=provider_timeout, headers=headers)  # Provider-specific timeout
            response_time = int((time.time() - start_time) * 1000)
            # Show as online if we get ANY response (even 403, 404, etc.)
            status = "🟢"
            logger.info(f"Provider {provider_name}: {response.status_code} -> {status} ({response_time}ms)")

            return {
                "status": status,
                "response_time": f"{response_time}ms",
                "country": country,
                "flag": flag,
                "status_code": response.status_code,
            }
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            # Cap response time at provider-specific timeout for timeout cases
            timeout_ms = provider_timeout * 1000
            if response_time > timeout_ms:
                response_time = timeout_ms
            logger.warning(f"Provider {provider_name} failed: {str(e)} ({response_time}ms)")
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
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        logger.info("Updating all provider statuses.")
        updated_status: Dict[str, Any] = {}
        start_time = time.time()
        # Allow 10 seconds total to judge if ALL models are online or offline
        max_total_time = 10  # Allow 10 seconds total for all parallel provider checks

        try:
            providers = self.config.get("providers", {})
            if not providers:
                logger.info("No providers configured")
                return updated_status

            # Initialize all providers with default failed status to ensure they always show
            for name, provider_info in providers.items():
                # Handle both string and dict formats for provider_info
                if isinstance(provider_info, dict):
                    country = provider_info.get("country", "🌍 Unknown")
                    flag = provider_info.get("flag", "🌍")
                else:
                    # Legacy string format - use defaults
                    country = "🌍 Unknown"
                    flag = "🌍"

                updated_status[name] = {
                    "status": "🔴",
                    "response_time": "---ms",
                    "country": country,
                    "flag": flag,
                    "status_code": "Checking...",
                    "error": "Status check in progress",
                }

            # Use ThreadPoolExecutor for concurrent checks
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all provider checks
                future_to_name = {
                    executor.submit(self.check_provider_status, name, provider_info): name
                    for name, provider_info in providers.items()
                }

                # Collect results with timeout - update existing entries
                for future in as_completed(future_to_name, timeout=max_total_time):
                    name = future_to_name[future]
                    try:
                        result = future.result()
                        updated_status[name] = result  # This will overwrite the default failed status
                    except Exception as e:
                        logger.warning(f"Provider {name} check failed: {e}")
                        # Keep the default failed status but update error details
                        updated_status[name].update(
                            {
                                "response_time": "timeout",
                                "status_code": "Error",
                                "error": str(e),
                            }
                        )

            # Ensure all 10 providers are always present - if any are missing, add them
            default_providers = {
                "OpenAI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
                "DeepSeek": {"country": "🇨🇳 China", "flag": "🇨🇳"},
                "Google Gemini": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Cohere": {"country": "🇨🇦 Canada", "flag": "🇨🇦"},
                "Mistral AI": {"country": "🇫🇷 France", "flag": "🇫🇷"},
                "Perplexity": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Together AI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Groq": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
                "Hugging Face": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            }

            for name, info in default_providers.items():
                if name not in updated_status:
                    updated_status[name] = {
                        "status": "🔴",
                        "response_time": "---ms",
                        "country": info["country"],
                        "flag": info["flag"],
                        "status_code": "Not configured",
                        "error": "Provider not in config",
                    }

            self.provider_status = updated_status

        except Exception as e:
            logger.warning(f"Provider status check failed: {e} - using partial results")

        # CRITICAL: Always ensure all 10 providers are present regardless of any errors
        default_providers = {
            "OpenAI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "DeepSeek": {"country": "🇨🇳 China", "flag": "🇨🇳"},
            "Google Gemini": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Cohere": {"country": "🇨🇦 Canada", "flag": "🇨🇦"},
            "Mistral AI": {"country": "🇫🇷 France", "flag": "🇫🇷"},
            "Perplexity": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Together AI": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Groq": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
            "Hugging Face": {"country": "🇺🇸 USA", "flag": "🇺🇸"},
        }

        # Force all 9 providers to be present - overwrite if needed
        for name, info in default_providers.items():
            if name not in updated_status:
                updated_status[name] = {
                    "status": "🔴",
                    "response_time": "---ms",
                    "country": info["country"],
                    "flag": info["flag"],
                    "status_code": "Error",
                    "error": "Status check failed",
                }

        # Final guarantee - if we still don't have exactly 9, force them
        if len(updated_status) != 9:
            logger.warning(f"Provider count mismatch: expected 9, got {len(updated_status)}. Forcing all 9 providers.")
            for name, info in default_providers.items():
                updated_status[name] = {
                    "status": "🔴",
                    "response_time": "---ms",
                    "country": info["country"],
                    "flag": info["flag"],
                    "status_code": "Forced",
                    "error": "Guaranteed display",
                }

        self.provider_status = updated_status
        total_time = time.time() - start_time
        logger.info(f"Provider status check completed in {total_time:.1f}s - {len(updated_status)} providers (guaranteed 10)")
        return updated_status

    def _authenticate_open_webui(self):
        """Authenticate with Open WebUI to get an access token."""
        try:
            # Try to sign in with default admin credentials
            auth_url = f"{self.open_webui_base_url}/api/v1/auths/signin"
            auth_payload = {"email": "admin", "password": "admin"}

            logger.info(f"Attempting authentication at: {auth_url}")
            logger.info(f"Auth payload: {auth_payload}")
            response = requests.post(auth_url, json=auth_payload, timeout=self.request_timeout)
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
                logger.warning(f"Failed to authenticate with Open WebUI: {response.status_code}, response: {response.text}")
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

                response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=self.connection_timeout)
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

    def simulate_service_failure(self) -> tuple:
        """Simulates service failure using ConfigMap key manipulation for observable failures."""
        try:
            logger.info("🔴 ACTIVATING Availability Demo - Manipulating ConfigMap to break app")

            if self._simulate_configmap_failure():
                self.service_health_failure = True
                self._start_auto_off_timer()
                logger.error("🚨 SERVICE_HEALTH_FAILURE=true - Service entering degraded state for SUSE Observability demo")
                logger.error("💥 ConfigMap key 'models-latest' removed - Application configuration broken")
                return (
                    "Availability demo ON: ConfigMap key 'models-latest' replaced with 'models_latest'. "
                    "Health checks and chat will now hang/fail until the ConfigMap is fixed.",
                    "warning",
                )

            logger.warning("⚠️ ConfigMap manipulation failed, using fallback environment variable")
            os.environ["SERVICE_HEALTH_FAILURE"] = "true"
            self.service_health_failure = True
            return (
                "Availability demo ON (fallback mode): ConfigMap could not be patched, so the "
                "SERVICE_HEALTH_FAILURE flag was set instead. Check the pod's RBAC for ConfigMap access.",
                "warning",
            )
        except Exception as e:
            logger.error(f"Service failure simulation failed: {e}")
            return f"Simulation failed: {e}", "error"

    def restore_service_health(self) -> tuple:
        """Restores service health using ConfigMap configuration restoration."""
        try:
            logger.info("🔵 DEACTIVATING Availability Demo - Restoring ConfigMap to fix app")

            if self._restore_configmap_health():
                self.service_health_failure = False
                logger.info("✅ ConfigMap key 'models-latest' restored - Application configuration fixed")
                return "Availability demo OFF: ConfigMap restored, service is healthy again.", "success"

            logger.warning("⚠️ ConfigMap restoration failed, using fallback environment variable")
            os.environ["SERVICE_HEALTH_FAILURE"] = "false"
            self.service_health_failure = False
            return "Availability demo OFF (fallback mode): SERVICE_HEALTH_FAILURE flag cleared.", "success"
        except Exception as e:
            logger.error(f"Service health restoration failed: {e}")
            return f"Restoration failed: {e}", "error"

    def run_availability_demo(self) -> tuple:
        """Toggles the availability demo based on the current ConfigMap state. Returns (message, status)."""
        try:
            is_demo_on, _, _ = self._check_configmap_demo_state()
            self.availability_demo_last_toggled = time.time()
            result = self.restore_service_health() if is_demo_on else self.simulate_service_failure()
            self._demo_state_cache = None
            return result
        except Exception as e:
            logger.error(f"Availability demo failed: {e}")
            return f"Availability demo failed: {e}", "error"

    def run_data_leak_demo(self) -> tuple:
        """Sends synthetic credit card / SSN patterns so NeuVector DLP rules fire. Returns (message, status)."""
        logger.info("Running data leak demo - simulating sensitive data transmission")
        # Well-known synthetic test patterns, not real data
        credit_card_pattern = "3412-1234-1234-2222"
        ssn_pattern = "123-45-6789"
        self.data_leak_last_triggered = time.time()

        try:
            requests.post(
                "http://httpbin.org/post",
                data={"creditcard": credit_card_pattern, "ssn": ssn_pattern},
                timeout=1,
            )
            sent = True
        except Exception as endpoint_error:
            # NeuVector inspects the outbound packets even when the request itself fails
            logger.debug(f"Network request failed (expected for demo): {endpoint_error}")
            sent = False

        logger.warning("Data leak demo executed - sensitive data patterns sent for NeuVector DLP testing")
        message = f"Sent synthetic credit card ({credit_card_pattern}) and SSN ({ssn_pattern}) patterns to httpbin.org. " + (
            "NeuVector DLP should raise an alert."
            if sent
            else "The request did not complete, but the packets left the pod for DLP inspection."
        )
        return message, "warning"

    def start_provider_monitor(self, interval: int = 60):
        """Refreshes external provider reachability in the background."""

        def loop():
            while True:
                try:
                    self.update_all_provider_status()
                except Exception as e:
                    logger.warning(f"Provider status refresh failed: {e}")
                time.sleep(interval)

        threading.Thread(target=loop, daemon=True).start()

    # --- Automation Runner Methods ---
    def _automation_loop(self, model: str, interval: int):
        """The main loop for the background automation thread."""
        logger.info("Automation thread started.")
        while not self.stop_event.is_set():
            current_prompt = self.automation_prompts[self.current_prompt_index]
            self.current_prompt_index = (self.current_prompt_index + 1) % len(self.automation_prompts)

            logger.info(
                f"Running automated task with prompt: '{current_prompt}' (send_messages: {self.automation_send_messages})"
            )

            ollama_reply = "Message sending disabled"
            webui_reply = "Message sending disabled"

            if self.automation_send_messages:
                try:
                    ollama_reply = self.ollama_openai_client.single_prompt(current_prompt, model)
                    logger.info(f"Ollama replied: {ollama_reply[:100]}...")
                except Exception as e:
                    logger.warning(f"Ollama automation call failed: {e}")
                    ollama_reply = f"Automation Error: Ollama timeout/failure - {e}"

                try:
                    webui_reply = self.chat_with_open_webui([{"role": "user", "content": current_prompt}], model)
                    logger.info(f"Open WebUI replied: {webui_reply[:100]}...")
                except Exception as e:
                    logger.warning(f"Open WebUI automation call failed: {e}")
                    webui_reply = f"Automation Error: Open WebUI timeout/failure - {e}"

            self.latest_automation_result = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "prompt": (current_prompt if self.automation_send_messages else "Monitoring only"),
                "ollama_response": ollama_reply,
                "open_webui_response": webui_reply,
                "provider_status": self.update_all_provider_status(),
                "send_messages_enabled": self.automation_send_messages,
            }

            self.stop_event.wait(interval)
        logger.info("Automation thread stopped.")

    def start_automation(self, model: str, interval: int, send_messages: bool = None) -> bool:
        """Starts the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            logger.warning("Automation is already running.")
            return True

        if not model or "Error" in model or "No models" in model:
            logger.error("Cannot start automation without a valid model selected.")
            return False

        if send_messages is not None:
            self.automation_send_messages = send_messages

        self.stop_event.clear()
        self.automation_thread = threading.Thread(target=self._automation_loop, args=(model, interval), daemon=True)
        self.automation_thread.start()
        logger.info(f"Automation started with interval {interval}s, send_messages: {self.automation_send_messages}")
        return True

    def stop_automation(self):
        """Stops the automation thread."""
        if self.automation_thread and self.automation_thread.is_alive():
            self.stop_event.set()
            self.automation_thread.join(timeout=2)
            if self.automation_thread.is_alive():
                logger.warning("Automation thread did not stop gracefully")
        logger.info("Automation stopped.")

    # --- Load Simulator Management Methods ---
    def _load_simulator_name(self) -> str:
        return f"{os.getenv('DEPLOYMENT_NAME', 'ai-compare')}-load-simulator"

    def check_load_simulator_status(self) -> Dict:
        """Check if load simulator deployment exists and is running."""
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "deployment",
                    self._load_simulator_name(),
                    "-n",
                    os.getenv("KUBERNETES_NAMESPACE", "default"),
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                status = json.loads(result.stdout).get("status", {})
                ready_replicas = status.get("readyReplicas", 0)
                return {
                    "exists": True,
                    "running": ready_replicas > 0,
                    "replicas": status.get("replicas", 0),
                    "ready_replicas": ready_replicas,
                    "status": "Running" if ready_replicas > 0 else "Not Ready",
                }
            return {"exists": False, "running": False, "status": "Not Deployed"}
        except Exception as e:
            logger.warning(f"Failed to check load simulator status: {e}")
            return {"exists": False, "running": False, "status": "Unknown", "error": str(e)}

    def start_load_simulator(self) -> tuple:
        """Start the load simulator deployment. Returns (success, message)."""
        try:
            if self.check_load_simulator_status().get("running"):
                return True, "Load simulator is already running"

            result = subprocess.run(
                ["kubectl", "apply", "-f", "-"],
                input=self._generate_load_simulator_yaml(),
                text=True,
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Load simulator deployment created successfully")
                return True, "Load simulator started - generating HTTP traffic for observability"

            logger.error(f"Failed to create load simulator: {result.stderr}")
            return False, f"Failed to start load simulator: {result.stderr.strip()}"
        except Exception as e:
            logger.error(f"Error starting load simulator: {e}")
            return False, f"Error starting load simulator: {e}"

    def stop_load_simulator(self) -> tuple:
        """Stop the load simulator deployment. Returns (success, message)."""
        try:
            result = subprocess.run(
                [
                    "kubectl",
                    "delete",
                    "deployment",
                    self._load_simulator_name(),
                    "-n",
                    os.getenv("KUBERNETES_NAMESPACE", "default"),
                    "--ignore-not-found",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                logger.info("Load simulator deployment deleted successfully")
                return True, "Load simulator stopped"

            logger.warning(f"Failed to delete load simulator: {result.stderr}")
            return False, f"Failed to stop load simulator: {result.stderr.strip()}"
        except Exception as e:
            logger.error(f"Error stopping load simulator: {e}")
            return False, f"Error stopping load simulator: {e}"

    def _generate_load_simulator_yaml(self) -> str:
        """Generate Kubernetes YAML for load simulator deployment."""
        namespace = os.getenv("KUBERNETES_NAMESPACE", "default")
        deployment_name = os.getenv("DEPLOYMENT_NAME", "ai-compare")

        yaml_content = f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {deployment_name}-load-simulator
  namespace: {namespace}
  labels:
    app: {deployment_name}-load-simulator
    component: load-simulator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {deployment_name}-load-simulator
  template:
    metadata:
      labels:
        app: {deployment_name}-load-simulator
    spec:
      containers:
      - name: load-simulator
        image: ghcr.io/wiredquill/ai-demos-load-simulator:latest
        env:
        - name: TARGET_URL
          value: "http://{deployment_name}-app-service:8080"
        - name: INTERVAL_SECONDS
          value: "30"
        - name: LOAD_SIMULATOR_ENABLED
          value: "true"
        - name: REQUEST_TIMEOUT
          value: "30"
        resources:
          requests:
            cpu: "50m"
            memory: "64Mi"
          limits:
            cpu: "100m"
            memory: "128Mi"
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
"""
        return yaml_content


def main():
    """Start the API (8080) and UI (7860) servers and keep background workers running."""
    logger.info("Starting AI Compare application.")

    if os.getenv("SERVICE_HEALTH_FAILURE", "false").lower() == "true":
        logger.error("SERVICE_HEALTH_FAILURE=true detected - simulating service failure for SUSE Observability")
        raise SystemExit("💥 Service failure simulated for SUSE Observability monitoring (SERVICE_HEALTH_FAILURE=true)")

    chat_instance = ChatInterface()
    if not chat_instance.api_server:
        raise SystemExit("HTTP API server failed to initialize")

    # The UI port serves the same Flask app as the API port, so the page and /api/* share an origin
    ui_server = make_server("0.0.0.0", UI_PORT, chat_instance.api_server.app, threaded=True)
    logger.info(f"UI server listening on port {UI_PORT}")

    chat_instance.start_provider_monitor()

    if chat_instance.automation_enabled:

        def delayed_auto_start():
            # Wait for Ollama to come up and have at least one model
            for attempt in range(6):
                time.sleep(10)
                models = chat_instance.get_ollama_models()
                if models and "Error" not in models[0] and "No models" not in models[0]:
                    logger.info(f"Auto-starting automation with model: {models[0]}")
                    chat_instance.start_automation(models[0], chat_instance.automation_interval)
                    return
                logger.info(f"No valid models found on attempt {attempt + 1}, retrying...")
            logger.warning("Auto-start failed after all retries - Ollama may not be ready or no models available")

        threading.Thread(target=delayed_auto_start, daemon=True).start()

    ui_server.serve_forever()


if __name__ == "__main__":
    main()
