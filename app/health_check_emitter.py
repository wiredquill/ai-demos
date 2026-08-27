"""
Synthetic health-check spans for ai-compare's SUSE AI components.

ai-compare's Ollama (and the Open WebUI / Pipelines services) are either
scraped by the ollama otel sidecar or instrumented on their own side, so the
ai-compare APP itself never emits a SERVER span *about* them that carries the
suse.ai.component.* identity. The collector's dedicated "topology" exporter -
the thing that actually computes SUSE AI component HEALTH STATE - is fed
exclusively by the traces/topology pipeline: every metrics pipeline exports
only to the generic otlp endpoint, never to topology. A component can exist
(metrics create component identity) but can never get a health state without
a span of its own carrying its component identity.

This gives them a trace presence: a small periodic span per service, wrapped
around the same liveness check the collector/sidecar polls, carrying the
identical suse.ai.component.* resource identity the metrics pipeline stamps -
so the topology exporter has a real span to compute health from, the same way
it does for every application.

Same pattern as hr-assistant's health_check_emitter.py (verified-working fix
that made qdrant/opensearch report green, 2026-08-26).
"""

import os
import time

import requests
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

OTLP_ENDPOINT = os.environ["OTLP_ENDPOINT"]
NAMESPACE = os.environ["SUSE_AI_NAMESPACE"]
CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "30"))


def make_tracer(component_name, component_type, check_url):
    """Independent TracerProvider per component - each needs its own Resource
    (service.name/suse.ai.component.*), and Resource is fixed per provider."""
    resource = Resource.create(
        {
            "service.name": component_name,
            "service.namespace": NAMESPACE,
            "service.instance.id": component_name,
            "k8s.namespace.name": NAMESPACE,
            "suse.ai.managed": "true",
            "suse.ai.component.name": component_name,
            "suse.ai.component.type": component_type,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{OTLP_ENDPOINT}/v1/traces")))
    tracer = provider.get_tracer(f"{component_name}.health_check")
    return tracer, component_name, check_url


def run_check(tracer, component_name, check_url):
    # Liveness semantics: any HTTP response (even 4xx) means the server is up -
    # these targets are root endpoints whose exact health path we don't control
    # (open-webui / pipelines), so "the server answered" is the health signal.
    # A connection failure / timeout is the ERROR case.
    with tracer.start_as_current_span(f"{component_name}.health_check", kind=SpanKind.CLIENT) as span:
        span.set_attribute("http.url", check_url)
        try:
            resp = requests.get(check_url, timeout=5)
            span.set_attribute("http.status_code", resp.status_code)
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))


def main():
    # ollama: inference-engine (scraped by the otel sidecar, no gen_ai spans of
    # its own). open-webui / pipelines: application components instrumented on
    # their own side - give them a health span of their own too. Targets are
    # only configured when the chart enables that service, so skip missing env.
    specs = [
        ("OLLAMA_URL", "ollama", "inference-engine", "/"),
        ("OPEN_WEBUI_URL", "open-webui", "application", "/health"),
        ("PIPELINES_URL", "pipelines", "application", "/health"),
    ]
    checks = []
    for env_var, component_name, component_type, path in specs:
        base_url = os.environ.get(env_var)
        if not base_url:
            print(f"health-check-emitter: {env_var} not set, skipping {component_name}", flush=True)
            continue
        checks.append(make_tracer(component_name, component_type, base_url + path))
    print(f"health-check-emitter started (interval={CHECK_INTERVAL}s), targets: {[c[1] for c in checks]}", flush=True)
    while True:
        for tracer, component_name, check_url in checks:
            try:
                run_check(tracer, component_name, check_url)
                print(f"{component_name} health-check span sent", flush=True)
            except Exception as e:
                print(f"{component_name} health-check failed to emit: {e}", flush=True)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
