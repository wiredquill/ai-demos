import openlit
from wrapt import wrap_function_wrapper

from .openlit_ollama import chat_completions_create, embed

__all__ = ["patch_openlit", "chat_completions_create", "embed"]


def patch_openlit():
    conf = openlit.OpenlitConfig()
    version = ""
    environment = conf.environment
    application_name = conf.application_name
    tracer = conf.tracer
    pricing_info = conf.pricing_info
    trace_content = conf.trace_content
    metrics = conf.metrics_dict
    disable_metrics = conf.disable_metrics

    # sync embed
    wrap_function_wrapper(
        "ollama",
        "embed",
        embed(
            "ollama.embed",
            version,
            environment,
            application_name,
            tracer,
            pricing_info,
            trace_content,
            metrics,
            disable_metrics,
        ),
    )
    wrap_function_wrapper(
        "ollama",
        "Client.embed",
        embed(
            "ollama.embed",
            version,
            environment,
            application_name,
            tracer,
            pricing_info,
            trace_content,
            metrics,
            disable_metrics,
        ),
    )

    # Patch OpenAI chat completions to detect Ollama endpoint
    wrap_function_wrapper(
        "openai.resources.chat.completions",
        "Completions.create",
        chat_completions_create(
            "openai.chat.completions.create",
            version,
            environment,
            application_name,
            tracer,
            pricing_info,
            trace_content,
            metrics,
            disable_metrics,
        ),
    )
