# pylint: disable=duplicate-code, broad-exception-caught, too-many-statements, unused-argument, possibly-used-before-assignment
"""
Telemetry for chat completions served by Ollama through its OpenAI-compatible API.

The apps talk to Ollama over /v1 with the OpenAI SDK. OpenLIT's own OpenAI
instrumentor would label those calls as provider "openai", which is wrong for the
SUSE AI topology - the inference engine is Ollama. main.py therefore disables the
openai instrumentor and this wrapper owns the path, reporting provider "ollama"
and pricing the response against the local model entries in pricing.json.

Attribute names follow the OTel GenAI semantic conventions as shipped in
openlit >= 1.44 (SemanticConvention, gen_ai.provider.name, input/output tokens).
gen_ai.system is still emitted alongside gen_ai.provider.name so the same image
keeps working against older SUSE Observability releases.
"""

import logging
import time

from openlit.__helpers import general_tokens, get_chat_model_cost, handle_exception
from openlit.semcov import SemanticConvention
from opentelemetry.sdk.resources import TELEMETRY_SDK_NAME
from opentelemetry.trace import SpanKind, Status, StatusCode

from .suse_ai_metrics import _ensure_cost_histogram, _ensure_requests_counter

# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)

# Legacy attribute, kept for compatibility with pre-1.44 SUSE Observability.
GEN_AI_SYSTEM = "gen_ai.system"


def _is_ollama_endpoint(instance):
    """
    Returns True when the OpenAI client instance points at an Ollama server.
    """

    base_url = getattr(instance._client, "_base_url", None) if hasattr(instance, "_client") else None
    if not base_url:
        base_url = getattr(instance, "_base_url", None)

    base_url_str = str(base_url) if base_url else ""

    return "/v1" in base_url_str and (
        "ollama" in base_url_str.lower() or any(port in base_url_str for port in [":11434", ":8080", ":8000"])
    )


def chat_completions_create(
    gen_ai_endpoint, version, environment, application_name, tracer, pricing_info, trace_content, metrics, disable_metrics
):
    """
    Generates a telemetry wrapper for OpenAI chat completions served by Ollama.

    Args:
        gen_ai_endpoint: Endpoint identifier for logging and tracing.
        version: Version of the monitoring package.
        environment: Deployment environment (e.g., production, staging).
        application_name: Name of the application using the API.
        tracer: OpenTelemetry tracer for creating spans.
        pricing_info: Information used for calculating the cost of usage.
        trace_content: Flag indicating whether to trace the actual content.

    Returns:
        A function that wraps the chat completions create method to add telemetry.
    """

    def wrapper(wrapped, instance, args, kwargs):
        """
        Wraps the 'chat.completions.create' API call to add telemetry for Ollama.
        """

        # Anything not pointed at Ollama is left entirely alone.
        if not _is_ollama_endpoint(instance):
            return wrapped(*args, **kwargs)

        with tracer.start_as_current_span(gen_ai_endpoint, kind=SpanKind.CLIENT) as span:
            start_time = time.time()
            response = wrapped(*args, **kwargs)
            end_time = time.time()

            try:
                model = kwargs.get("model", "llama3.2")
                messages = kwargs.get("messages", [])

                prompt_content = ""
                for message in messages:
                    if isinstance(message, dict) and "content" in message:
                        prompt_content += message["content"] + " "

                input_tokens = general_tokens(prompt_content.strip())

                response_dict = response.dict() if hasattr(response, "dict") else response
                output_tokens = 0
                total_tokens = input_tokens
                completion_content = ""

                if response_dict and "choices" in response_dict and response_dict["choices"]:
                    completion_content = response_dict["choices"][0].get("message", {}).get("content", "") or ""

                # Ollama reports real usage on the OpenAI-compatible endpoint; fall
                # back to estimating from the completion text when it does not.
                if response_dict and response_dict.get("usage"):
                    usage = response_dict["usage"]
                    input_tokens = usage.get("prompt_tokens", input_tokens)
                    output_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
                else:
                    output_tokens = general_tokens(completion_content)
                    total_tokens = input_tokens + output_tokens

                cost = get_chat_model_cost(model, pricing_info, input_tokens, output_tokens)

                span.set_attribute(TELEMETRY_SDK_NAME, "openlit")
                span.set_attribute(SemanticConvention.GEN_AI_PROVIDER_NAME, SemanticConvention.GEN_AI_SYSTEM_OLLAMA)
                span.set_attribute(GEN_AI_SYSTEM, SemanticConvention.GEN_AI_SYSTEM_OLLAMA)
                span.set_attribute(SemanticConvention.GEN_AI_OPERATION, SemanticConvention.GEN_AI_OPERATION_TYPE_CHAT)
                span.set_attribute(SemanticConvention.GEN_AI_ENDPOINT, gen_ai_endpoint)
                span.set_attribute(SemanticConvention.GEN_AI_ENVIRONMENT, environment)
                span.set_attribute(SemanticConvention.GEN_AI_APPLICATION_NAME, application_name)
                span.set_attribute(SemanticConvention.GEN_AI_REQUEST_MODEL, model)
                span.set_attribute(SemanticConvention.GEN_AI_USAGE_INPUT_TOKENS, input_tokens)
                span.set_attribute(SemanticConvention.GEN_AI_USAGE_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(SemanticConvention.GEN_AI_USAGE_TOTAL_TOKENS, total_tokens)
                span.set_attribute(SemanticConvention.GEN_AI_USAGE_COST, cost)

                if response_dict and response_dict.get("id"):
                    span.set_attribute(SemanticConvention.GEN_AI_RESPONSE_ID, response_dict["id"])

                if trace_content:
                    span.set_attribute(SemanticConvention.GEN_AI_CONTENT_PROMPT_EVENT, prompt_content.strip())
                    span.set_attribute(SemanticConvention.GEN_AI_CONTENT_COMPLETION_EVENT, completion_content)

                span.set_status(Status(StatusCode.OK))

                if disable_metrics is False:
                    attributes = {
                        TELEMETRY_SDK_NAME: "openlit",
                        SemanticConvention.GEN_AI_APPLICATION_NAME: application_name,
                        SemanticConvention.GEN_AI_PROVIDER_NAME: SemanticConvention.GEN_AI_SYSTEM_OLLAMA,
                        GEN_AI_SYSTEM: SemanticConvention.GEN_AI_SYSTEM_OLLAMA,
                        SemanticConvention.GEN_AI_ENVIRONMENT: environment,
                        SemanticConvention.GEN_AI_OPERATION: SemanticConvention.GEN_AI_OPERATION_TYPE_CHAT,
                        SemanticConvention.GEN_AI_REQUEST_MODEL: model,
                    }

                    # openlit >= 1.44 replaced the genai_prompt_tokens /
                    # genai_completion_tokens counters with a single OTel-compliant
                    # gen_ai.client.token.usage histogram split by token type.
                    # gen_ai.total.requests is re-created here (see
                    # _ensure_requests_counter) because the SUSE AI extension
                    # requires the RequestsTotal meter to classify this app as
                    # GenAI and render token usage / cost charts.
                    _ensure_requests_counter().add(1, attributes)
                    _ensure_cost_histogram().record(cost, attributes)
                    metrics["genai_client_usage_tokens"].record(
                        input_tokens,
                        {**attributes, SemanticConvention.GEN_AI_TOKEN_TYPE: SemanticConvention.GEN_AI_TOKEN_TYPE_INPUT},
                    )
                    metrics["genai_client_usage_tokens"].record(
                        output_tokens,
                        {**attributes, SemanticConvention.GEN_AI_TOKEN_TYPE: SemanticConvention.GEN_AI_TOKEN_TYPE_OUTPUT},
                    )
                    metrics["genai_client_operation_duration"].record(end_time - start_time, attributes)
                    metrics["genai_cost"].record(cost, attributes)

                return response

            except Exception as e:
                handle_exception(span, e)
                logger.error("Error in trace creation: %s", e)
                return response

    return wrapper
