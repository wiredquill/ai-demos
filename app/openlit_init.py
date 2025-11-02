"""
OpenLit initialization module following ravan/llm-experiments pattern.
Provides clean OpenTelemetry and pricing integration for Ollama costing.
"""

import logging
import os

import openlit

logger = logging.getLogger(__name__)


def setup_ollama_environment():
    """Setup Ollama environment variables before OpenLit init."""
    ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_ENDPOINT", "http://ollama-service:11434"))

    # Set standard Ollama environment variables
    os.environ["OLLAMA_SERVER_URL"] = ollama_url
    os.environ["OLLAMA_HOST"] = ollama_url

    # Set API key if provided
    ollama_api_key = os.getenv("OLLAMA_API_KEY", "")
    if ollama_api_key:
        os.environ["OLLAMA_API_KEY"] = ollama_api_key

    logger.info(f"Ollama environment setup: {ollama_url}")


def initialize_openlit():
    """Initialize OpenLit with proper pricing.json integration."""
    try:
        # Setup Ollama environment first
        setup_ollama_environment()

        # Get configuration from environment
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        app_name = os.getenv("APP_NAME", "ai-compare")
        collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false").lower() == "true"

        if not otlp_endpoint:
            logger.warning("No OTLP_ENDPOINT configured, skipping OpenLit initialization")
            return False

        logger.info(f"Initializing OpenLit for {app_name}")
        logger.info(f"OTLP Endpoint: {otlp_endpoint}")
        logger.info(f"GPU Stats: {collect_gpu_stats}")

        # Initialize OpenLit with pricing.json file and metrics enabled
        openlit.init(
            otlp_endpoint=otlp_endpoint,
            disable_batch=True,
            trace_content=True,
            application_name=app_name,
            pricing_json="./pricing.json",  # Key change: use file path like reference
            collect_gpu_stats=collect_gpu_stats,
            disable_metrics=False,  # Ensure metrics are enabled for GenAI Apps dashboard
        )

        logger.info("✅ OpenLit initialized successfully with pricing.json")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize OpenLit: {e}")
        return False


def get_model_pricing(model_name):
    """Get pricing information for a model from pricing.json."""
    try:
        import json
        import os

        # Try to read pricing.json from app directory
        pricing_path = "./pricing.json"
        if not os.path.exists(pricing_path):
            pricing_path = "/app/pricing.json"

        if os.path.exists(pricing_path):
            with open(pricing_path, "r") as f:
                pricing_data = json.load(f)

            # Look for the model in chat pricing
            chat_pricing = pricing_data.get("chat", {})

            # Try different model name variations
            model_variations = [
                model_name,
                model_name.replace(":latest", ""),
                model_name.replace(":latest", ":latest"),
            ]

            for variation in model_variations:
                if variation in chat_pricing:
                    model_pricing = chat_pricing[variation]
                    return {
                        "input_cost_per_token": model_pricing.get("promptPrice", 0.00005),
                        "output_cost_per_token": model_pricing.get("completionPrice", 0.0001),
                        "cost_per_request": 0.001,  # Standard request cost
                    }

        # Default pricing for Ollama models if not found
        logger.warning(f"Pricing not found for model {model_name}, using defaults")
        return {
            "input_cost_per_token": 0.00005,  # Default for local models
            "output_cost_per_token": 0.0001,
            "cost_per_request": 0.001,
        }

    except Exception as e:
        logger.error(f"Error reading pricing data: {e}")
        return {
            "input_cost_per_token": 0.00005,
            "output_cost_per_token": 0.0001,
            "cost_per_request": 0.001,
        }


def patch_openlit():
    """Apply any custom OpenLit patches if needed."""
    # Placeholder for custom patches following reference pattern
    pass
