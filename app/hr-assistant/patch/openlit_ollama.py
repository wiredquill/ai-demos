# pylint: disable=duplicate-code, broad-exception-caught, too-many-statements, unused-argument, possibly-used-before-assignment
"""
Module for monitoring Ollama API calls.
"""

import logging

from openlit.__helpers import general_tokens, get_chat_model_cost, get_embed_model_cost, handle_exception
from openlit.semcov import SemanticConvetion
from opentelemetry.sdk.resources import TELEMETRY_SDK_NAME
from opentelemetry.trace import SpanKind, Status, StatusCode

# Initialize logger for logging potential issues and operations
logger = logging.getLogger(__name__)


def embed(
    gen_ai_endpoint, version, environment, application_name, tracer, pricing_info, trace_content, metrics, disable_metrics
):
    """
    Generates a telemetry wrapper for embed to collect metrics.

    Args:
        gen_ai_endpoint: Endpoint identifier for logging and tracing.
        version: Version of the monitoring package.
        environment: Deployment environment (e.g., production, staging).
        application_name: Name of the application using the Ollama API.
        tracer: OpenTelemetry tracer for creating spans.
        pricing_info: Information used for calculating the cost of Ollama usage.
        trace_content: Flag indicating whether to trace the actual content.

    Returns:
        A function that wraps the embed method to add telemetry.
    """

    def wrapper(wrapped, instance, args, kwargs):
        """
        Wraps the 'embed' API call to add telemetry.

        This collects metrics such as execution time, cost, and token usage, and handles errors
        gracefully, adding details to the trace for observability.

        Args:
            wrapped: The original 'embed' method to be wrapped.
            instance: The instance of the class where the original method is defined.
            args: Positional arguments for the 'embed' method.
            kwargs: Keyword arguments for the 'embed' method.

        Returns:
            The response from the original 'embed' method.
        """

        with tracer.start_as_current_span(gen_ai_endpoint, kind=SpanKind.CLIENT) as span:
            response = wrapped(*args, **kwargs)

            try:
                input = kwargs.get("input", "")
                if isinstance(input, list):
                    prompt_tokens = sum([general_tokens(i) for i in input])
                else:
                    prompt_tokens = general_tokens(input)
                # Calculate cost of the operation
                cost = get_embed_model_cost(kwargs.get("model", "mistral-embed"), pricing_info, prompt_tokens)
                # Set Span attributes
                span.set_attribute(TELEMETRY_SDK_NAME, "openlit")
                span.set_attribute(SemanticConvetion.GEN_AI_SYSTEM, SemanticConvetion.GEN_AI_SYSTEM_OLLAMA)
                span.set_attribute(SemanticConvetion.GEN_AI_TYPE, SemanticConvetion.GEN_AI_TYPE_EMBEDDING)
                span.set_attribute(SemanticConvetion.GEN_AI_ENDPOINT, gen_ai_endpoint)
                span.set_attribute(SemanticConvetion.GEN_AI_ENVIRONMENT, environment)
                span.set_attribute(SemanticConvetion.GEN_AI_APPLICATION_NAME, application_name)
                span.set_attribute(SemanticConvetion.GEN_AI_REQUEST_MODEL, kwargs.get("model", "llama3"))
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_PROMPT_TOKENS, prompt_tokens)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_TOTAL_TOKENS, prompt_tokens)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_COST, cost)
                if trace_content:
                    span.add_event(
                        name=SemanticConvetion.GEN_AI_CONTENT_PROMPT_EVENT,
                        attributes={
                            SemanticConvetion.GEN_AI_CONTENT_PROMPT: kwargs.get("prompt", ""),
                        },
                    )

                span.set_status(Status(StatusCode.OK))

                if disable_metrics is False:
                    attributes = {
                        TELEMETRY_SDK_NAME: "openlit",
                        SemanticConvetion.GEN_AI_APPLICATION_NAME: application_name,
                        SemanticConvetion.GEN_AI_SYSTEM: SemanticConvetion.GEN_AI_SYSTEM_OLLAMA,
                        SemanticConvetion.GEN_AI_ENVIRONMENT: environment,
                        SemanticConvetion.GEN_AI_TYPE: SemanticConvetion.GEN_AI_TYPE_EMBEDDING,
                        SemanticConvetion.GEN_AI_REQUEST_MODEL: kwargs.get("model", "llama3"),
                    }

                    metrics["genai_requests"].add(1, attributes)
                    metrics["genai_total_tokens"].add(prompt_tokens, attributes)
                    metrics["genai_prompt_tokens"].add(prompt_tokens, attributes)
                    metrics["genai_cost"].record(cost, attributes)

                # Return original response
                return response

            except Exception as e:
                handle_exception(span, e)
                logger.error("Error in trace creation: %s", e)

                # Return original response
                return response

    return wrapper


def chat_completions_create(
    gen_ai_endpoint, version, environment, application_name, tracer, pricing_info, trace_content, metrics, disable_metrics
):
    """
    Generates a telemetry wrapper for OpenAI chat completions when using Ollama endpoint.

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
        # Check if this is an Ollama endpoint by looking at the base_url
        base_url = getattr(instance._client, "_base_url", None) if hasattr(instance, "_client") else None
        if not base_url:
            base_url = getattr(instance, "_base_url", None)

        # Convert base_url to string if it's not already
        base_url_str = str(base_url) if base_url else ""

        # Only apply Ollama telemetry if this is pointing to an Ollama endpoint
        is_ollama_endpoint = "/v1" in base_url_str and (
            "ollama" in base_url_str.lower() or any(port in base_url_str for port in [":11434", ":8080", ":8000"])
        )

        if not is_ollama_endpoint:
            # If this is not an Ollama endpoint, just call the original function without telemetry
            return wrapped(*args, **kwargs)

        # Only create span and telemetry for Ollama endpoints
        with tracer.start_as_current_span(gen_ai_endpoint, kind=SpanKind.CLIENT) as span:
            response = wrapped(*args, **kwargs)

            try:
                # Extract request data
                model = kwargs.get("model", "llama3.2")
                messages = kwargs.get("messages", [])

                # Calculate tokens
                prompt_content = ""
                for message in messages:
                    if isinstance(message, dict) and "content" in message:
                        prompt_content += message["content"] + " "

                prompt_tokens = general_tokens(prompt_content.strip())

                # Get completion tokens from response
                response_dict = response.dict() if hasattr(response, "dict") else response
                completion_tokens = 0
                total_tokens = prompt_tokens

                if response_dict and "usage" in response_dict:
                    completion_tokens = response_dict["usage"].get("completion_tokens", 0)
                    total_tokens = response_dict["usage"].get("total_tokens", prompt_tokens)
                elif response_dict and "choices" in response_dict and response_dict["choices"]:
                    # Estimate completion tokens from response content
                    completion_content = response_dict["choices"][0].get("message", {}).get("content", "")
                    completion_tokens = general_tokens(completion_content)
                    total_tokens = prompt_tokens + completion_tokens

                # Calculate cost using Ollama model pricing
                cost = get_chat_model_cost(model, pricing_info, prompt_tokens, completion_tokens)

                # Set Span attributes for OpenAI (with Ollama backend pricing)
                span.set_attribute(TELEMETRY_SDK_NAME, "openlit")
                span.set_attribute(SemanticConvetion.GEN_AI_SYSTEM, SemanticConvetion.GEN_AI_SYSTEM_OPENAI)
                span.set_attribute(SemanticConvetion.GEN_AI_TYPE, SemanticConvetion.GEN_AI_TYPE_CHAT)
                span.set_attribute(SemanticConvetion.GEN_AI_ENDPOINT, gen_ai_endpoint)
                span.set_attribute(SemanticConvetion.GEN_AI_ENVIRONMENT, environment)
                span.set_attribute(SemanticConvetion.GEN_AI_APPLICATION_NAME, application_name)
                span.set_attribute(SemanticConvetion.GEN_AI_REQUEST_MODEL, model)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_PROMPT_TOKENS, prompt_tokens)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_COMPLETION_TOKENS, completion_tokens)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_TOTAL_TOKENS, total_tokens)
                span.set_attribute(SemanticConvetion.GEN_AI_USAGE_COST, cost)

                if trace_content:
                    span.add_event(
                        name=SemanticConvetion.GEN_AI_CONTENT_PROMPT_EVENT,
                        attributes={
                            SemanticConvetion.GEN_AI_CONTENT_PROMPT: prompt_content.strip(),
                        },
                    )

                    if response_dict and "choices" in response_dict and response_dict["choices"]:
                        completion_content = response_dict["choices"][0].get("message", {}).get("content", "")
                        span.add_event(
                            name=SemanticConvetion.GEN_AI_CONTENT_COMPLETION_EVENT,
                            attributes={
                                SemanticConvetion.GEN_AI_CONTENT_COMPLETION: completion_content,
                            },
                        )

                span.set_status(Status(StatusCode.OK))

                if disable_metrics is False:
                    attributes = {
                        TELEMETRY_SDK_NAME: "openlit",
                        SemanticConvetion.GEN_AI_APPLICATION_NAME: application_name,
                        SemanticConvetion.GEN_AI_SYSTEM: SemanticConvetion.GEN_AI_SYSTEM_OPENAI,
                        SemanticConvetion.GEN_AI_ENVIRONMENT: environment,
                        SemanticConvetion.GEN_AI_TYPE: SemanticConvetion.GEN_AI_TYPE_CHAT,
                        SemanticConvetion.GEN_AI_REQUEST_MODEL: model,
                    }

                    metrics["genai_requests"].add(1, attributes)
                    metrics["genai_total_tokens"].add(total_tokens, attributes)
                    metrics["genai_prompt_tokens"].add(prompt_tokens, attributes)
                    metrics["genai_completion_tokens"].add(completion_tokens, attributes)
                    metrics["genai_cost"].record(cost, attributes)

                return response

            except Exception as e:
                handle_exception(span, e)
                logger.error("Error in trace creation: %s", e)
                return response

    return wrapper
