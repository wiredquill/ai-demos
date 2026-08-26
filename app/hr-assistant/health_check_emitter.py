# pylint: disable=broad-exception-caught
"""
Synthetic health-check spans for Qdrant and OpenSearch.

Neither service is an instrumented application - they're plain HTTP backends
polled by the collector's Prometheus/Elasticsearch receivers, so they only
ever appear in SUSE Observability via metrics. The collector's dedicated
"topology" exporter - the thing that actually computes SUSE AI component
health - is fed exclusively by the traces/topology pipeline (see
templates/otel-collector-values-suse-ai.yaml's service.pipelines): every
metrics pipeline only exports via the generic otlp_grpc endpoint, never via
topology. Real apps (HRAssistant, EmployeeHandbook, HRPolicyDatabase) get a
health state because they produce real request spans; Qdrant/OpenSearch never
do, so their components exist (metrics can create component identity) but can
never get a health state under this pipeline design.

This gives them a trace presence: a small periodic span per service, wrapped
around the same liveness check the collector itself uses (Qdrant's root
endpoint, OpenSearch's _cluster/health), carrying the identical
suse.ai.component.* resource identity the collector's transform/qdrant and
resource/opensearch processors already stamp onto their metrics - so the
topology exporter has a real span to compute health from, the same way it
does for every application.
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
    with tracer.start_as_current_span(f"{component_name}.health_check", kind=SpanKind.CLIENT) as span:
        span.set_attribute("http.url", check_url)
        try:
            resp = requests.get(check_url, timeout=5)
            span.set_attribute("http.status_code", resp.status_code)
            if resp.ok:
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, f"HTTP {resp.status_code}"))
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))


def main():
    checks = [
        make_tracer("qdrant", "vectordb", f"{os.environ['QDRANT_URL']}/"),
        make_tracer("opensearch", "search-engine", f"{os.environ['OPENSEARCH_URL']}/_cluster/health"),
    ]
    print(f"health-check-emitter started (interval={CHECK_INTERVAL}s), targets: qdrant, opensearch", flush=True)
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
