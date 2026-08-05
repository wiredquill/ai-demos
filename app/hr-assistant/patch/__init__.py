import openlit
from opentelemetry import trace
from wrapt import wrap_function_wrapper

from .ollama_embeddings import OllamaEmbeddings
from .openlit_ollama import chat_completions_create


def patch_openlit():
    conf = openlit.OpenlitConfig()
    version = ""
    environment = conf.environment
    application_name = conf.application_name
    # openlit >= 1.44 no longer hangs the tracer off OpenlitConfig; openlit.init()
    # has already installed the global tracer provider by this point.
    tracer = trace.get_tracer("openlit.otel.tracing")
    pricing_info = conf.pricing_info
    trace_content = conf.capture_message_content
    metrics = conf.metrics_dict
    disable_metrics = conf.disable_metrics

    # Ollama's native client is instrumented by openlit itself (it wraps
    # ollama._client.Client._request, which covers chat, generate and embed), so
    # only the OpenAI-compatible path needs a wrapper of our own. main.py disables
    # openlit's openai instrumentor so this stays the single span for those calls.
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
