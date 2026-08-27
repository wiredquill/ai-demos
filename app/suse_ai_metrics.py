"""
SUSE AI StackPack acceptance-gate metrics for ai-compare.

openlit >= 1.44 dropped the gen_ai.total.requests counter, but the SUSE AI
StackPack's extension uses the RequestsTotal meter (with GenAi* attributes) as
its acceptance gate for "this is a GenAI application" - without it, no token
usage or cost charts are produced for the app, even though openlit still
tracks cost/tokens correctly as span attributes. Re-created here (once) rather
than duplicated per call path.

SUSE's cost binding also reads gen_ai.client.operation.cost specifically
(gen_ai_client_operation_cost_USD_* in StackState). openlit's own cost metric
("genai_cost") uses a different name, and its native ollama instrumentor
never records it as a metric (cost is only ever set as a gen_ai.usage.cost
span attribute), so record it here explicitly.

Same pattern as hr-assistant's app/hr-assistant/patch/suse_ai_metrics.py
(the verified-working fix that made hr-assistant's token/cost charts and
SUSE AI view go green, 2026-08-26).
"""

from openlit.semcov import SemanticConvention
from opentelemetry import metrics as otel_metrics

_requests_counter = None
_cost_histogram = None


def _ensure_requests_counter():
    """Return the gen_ai.total.requests counter, created lazily."""
    global _requests_counter
    if _requests_counter is None:
        meter = otel_metrics.get_meter("ai-compare.telemetry", version="0.1.0")
        _requests_counter = meter.create_counter(
            name="gen_ai.total.requests",
            description="Number of requests",
            unit="{request}",
        )
    return _requests_counter


def _ensure_cost_histogram():
    """Return the gen_ai.client.operation.cost histogram, created lazily."""
    global _cost_histogram
    if _cost_histogram is None:
        meter = otel_metrics.get_meter("ai-compare.telemetry", version="0.1.0")
        _cost_histogram = meter.create_histogram(
            name="gen_ai.client.operation.cost",
            description="Cost of GenAI operations in USD",
            unit="USD",
        )
    return _cost_histogram


def record_suse_ai_metrics(application_name, environment, provider, model, cost):
    """Bump the SUSE AI acceptance-gate counter and cost histogram for one GenAI call."""
    attributes = {
        SemanticConvention.GEN_AI_APPLICATION_NAME: application_name,
        SemanticConvention.GEN_AI_PROVIDER_NAME: provider,
        SemanticConvention.GEN_AI_ENVIRONMENT: environment,
        SemanticConvention.GEN_AI_OPERATION: SemanticConvention.GEN_AI_OPERATION_TYPE_CHAT,
        SemanticConvention.GEN_AI_REQUEST_MODEL: model,
    }
    _ensure_requests_counter().add(1, attributes)
    try:
        _ensure_cost_histogram().record(float(cost or 0.0), attributes)
    except Exception:
        # Cost recording is best-effort - never let it break the chat path.
        pass
