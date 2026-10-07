# pylint: disable=duplicate-code, broad-exception-caught, too-many-statements, unused-argument, possibly-used-before-assignment
"""
Telemetry for chat completions served by vLLM's OpenAI-compatible router.

Same shape as patch/openlit_ollama.py (the apps talk to vLLM over /v1 with the
OpenAI SDK, and OpenLIT's own openai instrumentor would mislabel the provider
as "openai"), but gated on LLM_PROVIDER=vllm (an explicit env var the
hr-assistant-vllm chart sets) instead of URL/port sniffing — vLLM's router
has no fixed port convention to detect the way Ollama's :11434 does.

"vllm" is used as a literal gen_ai.provider.name value rather than an
openlit.semcov.SemanticConvention constant: openlit's vLLM support targets the
in-process `vllm.LLM()` Python API, not this OpenAI-compatible HTTP path, so
there is no guaranteed GEN_AI_SYSTEM_VLLM constant to import across openlit
versions. The collector's transform/infer-providers pipeline matches on the
resource attribute's string value, not on which constant produced it, so this
is equivalent.
"""

import logging
import os
import time

from openlit.__helpers import general_tokens, get_chat_model_cost, handle_exception
from openlit.semcov import SemanticConvention
from opentelemetry.sdk.resources import TELEMETRY_SDK_NAME
from opentelemetry.trace import SpanKind, Status, StatusCode

from .suse_ai_metrics import _ensure_cost_histogram, _ensure_requests_counter

logger = logging.getLogger(__name__)

GEN_AI_SYSTEM = "gen_ai.system"
VLLM_PROVIDER = "vllm"


def _is_vllm_endpoint(instance):
    """True when LLM_PROVIDER=vllm — set by the hr-assistant-vllm chart on
    every app pod. Simpler and more robust than sniffing the router's base
    URL/port, which (unlike Ollama's fixed :11434) has no fixed convention.
    """

    return os.getenv("LLM_PROVIDER") == "vllm"


def chat_completions_create(
    gen_ai_endpoint, version, environment, application_name, tracer, pricing_info, trace_content, metrics, disable_metrics
):
    """
    Generates a telemetry wrapper for OpenAI chat completions served by vLLM.
    """

    def wrapper(wrapped, instance, args, kwargs):
        """
        Wraps the 'chat.completions.create' API call to add telemetry for vLLM.
        """

        # Anything not pointed at vLLM is left entirely alone.
        if not _is_vllm_endpoint(instance):
            return wrapped(*args, **kwargs)

        with tracer.start_as_current_span(gen_ai_endpoint, kind=SpanKind.CLIENT) as span:
            start_time = time.time()
            response = wrapped(*args, **kwargs)
            end_time = time.time()

            try:
                model = kwargs.get("model", "unknown")
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

                # vLLM's OpenAI-compatible endpoint always reports real usage;
                # fall back to estimating from the completion text if it does not.
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
                span.set_attribute(SemanticConvention.GEN_AI_PROVIDER_NAME, VLLM_PROVIDER)
                span.set_attribute(GEN_AI_SYSTEM, VLLM_PROVIDER)
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
                        SemanticConvention.GEN_AI_PROVIDER_NAME: VLLM_PROVIDER,
                        GEN_AI_SYSTEM: VLLM_PROVIDER,
                        SemanticConvention.GEN_AI_ENVIRONMENT: environment,
                        SemanticConvention.GEN_AI_OPERATION: SemanticConvention.GEN_AI_OPERATION_TYPE_CHAT,
                        SemanticConvention.GEN_AI_REQUEST_MODEL: model,
                    }

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
