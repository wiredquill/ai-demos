# OpenTelemetry for Hermes. Installed into the venv's site-packages, so every
# process the venv's python starts (hermes, and anything it runs with that
# python) loads it before Hermes's own code.
#
# Off unless OTEL_EXPORTER_OTLP_ENDPOINT is set (the client pod passes it with
# `openshell sandbox create --env` when the chart's observability is on). Then
# OpenLit instruments the openai SDK Hermes calls the model with, and sends
# GenAI traces and metrics over OTLP/HTTP:
#
#   OTEL_EXPORTER_OTLP_ENDPOINT  collector base URL, e.g. http://...:4318
#   OTEL_SERVICE_NAME            service.name (default hermes-agent)
#   HERMES_OTEL_ENVIRONMENT      deployment.environment (default default)
#   HERMES_OTEL_CAPTURE_CONTENT  true = prompts and replies in the spans
#   HERMES_OTEL_LOG              where exporter errors go (default /tmp/hermes-otel.log)
#
# Exporter and instrumentation logs go to that file, never stderr: stderr is
# the terminal Hermes draws its UI in, and a missing collector would scribble
# over it. Any failure here leaves Hermes running without telemetry.
import os

if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
    try:
        import logging

        handler = logging.FileHandler(
            os.environ.get("HERMES_OTEL_LOG", "/tmp/hermes-otel.log")
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
        for name in ("opentelemetry", "openlit"):
            logger = logging.getLogger(name)
            logger.addHandler(handler)
            logger.propagate = False

        import openlit

        service = os.environ.get("OTEL_SERVICE_NAME", "hermes-agent")
        openlit.init(
            application_name=service,
            service_name=service,
            environment=os.environ.get("HERMES_OTEL_ENVIRONMENT", "default"),
            capture_message_content=os.environ.get(
                "HERMES_OTEL_CAPTURE_CONTENT", "true"
            ).lower()
            == "true",
        )

        # vLLM answers non-streaming calls (cron jobs, summaries) with
        # "prompt_tokens_details": null, and OpenLit 1.44.0 calls .get() on it:
        # the span records an AttributeError and loses its token counts. Hand
        # OpenLit's openai parser empty dicts instead of nulls.
        import openlit.instrumentation.openai.utils as _openai_utils

        _as_dict = _openai_utils.response_as_dict

        def _response_as_dict(response):
            data = _as_dict(response)
            if isinstance(data, dict):
                if data.get("usage") is None and "usage" in data:
                    data["usage"] = {}
                usage = data.get("usage")
                if isinstance(usage, dict):
                    for key in ("prompt_tokens_details", "completion_tokens_details"):
                        if usage.get(key) is None:
                            usage[key] = {}
            return data

        _openai_utils.response_as_dict = _response_as_dict

        # One-shot mode (`hermes -z`) leaves through os._exit, past the atexit
        # hooks that flush the exporters, so the model call's span (it ends
        # with the stream) would never be sent. Flush first, briefly: a
        # missing collector must not hold the exit up.
        from opentelemetry import _logs, metrics, trace

        _os_exit = os._exit

        def _flush_then_exit(code):
            for provider in (
                trace.get_tracer_provider,
                metrics.get_meter_provider,
                _logs.get_logger_provider,
            ):
                try:
                    provider().force_flush(1000)
                except Exception:  # noqa: BLE001
                    pass
            _os_exit(code)

        os._exit = _flush_then_exit
    except Exception:  # noqa: BLE001 - telemetry must never stop the agent
        pass
