"""Generate charts/hr-assistant-vllm-<component> (one chart per app pod) for the hr-assistant-vllm AI Factory blueprint.

vLLM, Qdrant and OpenSearch are SUSE charts listed directly in the blueprint; these are the four app pods.

Usage (needs PyYAML): python3 scripts/gen-hr-assistant-vllm-components.py .
Edit COMPONENTS below, bump VERSION, re-run, then update the blueprint chartVersions."""
import os, sys, textwrap, yaml

ROOT = sys.argv[1]
BASE_VERSION = "0.1.13"
VERSION = "0.1.1"
MODEL_OPTIONS = ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen3.6-35B-A3B",
                 "meta-llama/Llama-3.3-70B-Instruct", "openai/gpt-oss-120b"]

def off():
    """Everything off; each component switches its own workload back on."""
    return {
        "fullnameOverride": "hr-assistant-vllm",
        "serviceAccount": {"create": False},
        "components": {"hrAssistant": False, "employeeHandbook": False, "hrPolicyDb": False},
        "loadGenerator": {"enabled": False},
        "qdrant": {"enabled": False, "url": "http://qdrant:6333"},
        "opensearch": {"enabled": False, "url": "http://opensearch-cluster-master:9200"},
        # App images are public (ghcr.io, registry.suse.com/bci); AI Factory delivers
        # its own pull secret to the SUSE charts.
        "imagePullSecrets": [],
        "vllm": {"enabled": False},
        "vllmEndpoint": "http://vllm-router-service:80",
        "model": "Qwen/Qwen2.5-7B-Instruct",
        "observability": {"connectivityCheck": False},
    }

def deep(d, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

# --- shared question blocks -------------------------------------------------
Q_OTLP = [
    dict(variable="hr.otlpEndpoint", label="OTLP Endpoint", group="Observability", type="string", required=False, default="",
         description="OpenTelemetry collector address (scheme://host:port).<br><br><b>Leave blank to auto-discover</b> the shared SUSE AI collector in the Collector Namespace below."),
    dict(variable="hr.observability.collectorNamespace", label="Collector Namespace", group="Observability", type="string", required=False, default="observability",
         description="Namespace holding the shared SUSE AI OpenTelemetry collector (installed from the ai-observability-collector chart)."),
]
Q_MODEL = dict(variable="hr.model", label="Model served by vLLM", group="LLM", type="enum", required=True, default=MODEL_OPTIONS[0], options=MODEL_OPTIONS,
               description="Must match the model served by the <b>vllm</b> component. Reported as gen_ai.request.model and sent on every request.")
Q_VLLM = dict(variable="hr.vllmEndpoint", label="vLLM Router URL", group="LLM", type="string", required=True, default="http://vllm-router-service:80",
              description="OpenAI-compatible endpoint of the <b>vllm</b> component's router (release <code>vllm</code> creates Service <code>vllm-router-service</code>).")
def q_service(default, nodeport=None):
    qs = [dict(variable="hr.service.type", label="Service Type", group="Service Access", type="enum", required=True, default=default,
               options=["ClusterIP", "NodePort", "LoadBalancer"],
               description="How this app's Service is exposed. ClusterIP keeps it in-cluster (port-forward to reach it).")]
    if nodeport:
        qs.append(dict(variable="hr.service.nodePort", label="Dashboard NodePort", group="Service Access", type="int", default=nodeport,
                       show_if="hr.service.type=NodePort", description="NodePort for the dashboard (range 30000-32767)."))
    return qs

COMPONENTS = [
  dict(name="app", pod="HR Assistant app",
       summary="The HR Assistant conversational app. Calls the vLLM router and fans out to employee-handbook and hr-policy-db.",
       values=lambda v: (deep(v, "components.hrAssistant", True), deep(v, "observability.connectivityCheck", True), deep(v, "service.type", "ClusterIP")),
       questions=[Q_MODEL, Q_VLLM] + q_service("ClusterIP") + Q_OTLP),
  dict(name="handbook", pod="Employee Handbook app",
       summary="Employee Handbook RAG app: answers questions from the bundled HR documents using the vLLM router.",
       values=lambda v: (deep(v, "components.employeeHandbook", True), deep(v, "observability.connectivityCheck", True), deep(v, "service.type", "ClusterIP")),
       questions=[Q_MODEL, Q_VLLM] + q_service("ClusterIP") + Q_OTLP),
  dict(name="policy-db", pod="HR Policy DB app + dashboard",
       summary="HR Policy Database app and the demo dashboard (at /). Uses Qdrant and OpenSearch for retrieval and the vLLM router for answers.",
       values=lambda v: (deep(v, "components.hrPolicyDb", True), deep(v, "observability.connectivityCheck", True),
                         deep(v, "service.type", "NodePort"), deep(v, "service.nodePort", 30081)),
       questions=[Q_MODEL, Q_VLLM,
                  dict(variable="hr.qdrant.url", label="Qdrant URL", group="Retrieval", type="string", required=True, default="http://qdrant:6333",
                       description="REST URL of the <b>qdrant</b> component (SUSE AI chart, release <code>qdrant</code>)."),
                  dict(variable="hr.opensearch.url", label="OpenSearch URL", group="Retrieval", type="string", required=True, default="http://opensearch-cluster-master:9200",
                       description="REST URL of the <b>opensearch</b> component (SUSE Application Collection chart).")]
                 + q_service("NodePort", 30081) + Q_OTLP),
  dict(name="load-gen", pod="Load generator + health-check emitter",
       summary="Keeps the demo busy: polls the three apps' /ask endpoints, and emits health-check spans for Qdrant and OpenSearch so they get a health state in SUSE Observability.",
       values=lambda v: (deep(v, "loadGenerator.enabled", True), deep(v, "observability.connectivityCheck", True)),
       questions=[dict(variable="hr.loadGenerator.intervalSeconds", label="Load Generation Interval (seconds)", group="Load Generator", type="int", default=45, required=True,
                       description="How often the three apps are polled. Keep at 120 or lower: SUSE AI components expire ~2 minutes after their last telemetry.")] + Q_OTLP),
]

class Dumper(yaml.SafeDumper):
    pass
def str_presenter(d, s):
    return d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None)
Dumper.add_representer(str, str_presenter)
def dump(o):
    return yaml.dump(o, Dumper=Dumper, sort_keys=False, width=1000, allow_unicode=True)

for c in COMPONENTS:
    chart = f"hr-assistant-vllm-{c['name']}"
    d = os.path.join(ROOT, "charts", chart); os.makedirs(os.path.join(d, "templates"), exist_ok=True)
    meta = {
        "apiVersion": "v2", "name": chart,
        "description": f"HR Assistant (vLLM) component: {c['pod']}. One of the components of the hr-assistant-vllm SUSE AI Factory blueprint.",
        "type": "application", "version": VERSION, "appVersion": "latest",
        "dependencies": [{"name": "hr-assistant-vllm", "version": BASE_VERSION, "repository": "file://../hr-assistant-vllm", "alias": "hr"}],
        "keywords": ["ai", "llm", "hr", "demo", "vllm", "suse-ai-factory"],
        "maintainers": [{"name": "SUSE AI Team", "email": "ai-team@suse.com"}],
        "home": "https://github.com/wiredquill/ai-demos",
        "annotations": {"catalog.cattle.io/display-name": f"HR Assistant (vLLM) - {c['pod']}"},
    }
    open(os.path.join(d, "Chart.yaml"), "w").write(
        "# Generated by scripts/gen-hr-assistant-vllm-components.py - edit there and re-run.\n" + dump(meta))
    v = off(); c["values"](v)
    open(os.path.join(d, "values.yaml"), "w").write(textwrap.dedent(f"""\
        # {c['pod']} - a single-workload release of charts/hr-assistant-vllm.
        #
        # Every value of the base chart can be set under "hr:". Everything except this
        # component's own workload is switched off; the shared fullnameOverride keeps
        # the Service names (hr-assistant-vllm-<workload>) the same as in the
        # all-in-one install, so the components find each other in one namespace.
        """) + dump({"hr": v}))
    open(os.path.join(d, "questions.yaml"), "w").write(dump({"questions": c["questions"]}))
    open(os.path.join(d, "app-readme.md"), "w").write(f"# HR Assistant (vLLM): {c['pod']}\n\n{c['summary']}\n\n"
        "Part of the **hr-assistant-vllm** SUSE AI Factory blueprint (SUSE vLLM, Qdrant and OpenSearch plus four app components). "
        "Install all components into the same namespace (the blueprint does this for you).\n")
    open(os.path.join(d, "README.md"), "w").write(f"# {chart}\n\n{c['summary']}\n\n"
        "This chart is one component of the `hr-assistant-vllm` SUSE AI Factory blueprint "
        "(`catalog/blueprints/hr-assistant-vllm-1-4-3.yaml`). It vendors `charts/hr-assistant-vllm` "
        "(alias `hr`) and enables only this workload. See `charts/hr-assistant-vllm/README.md` for the "
        "full component list, how the components connect, and how to install the blueprint.\n")
    open(os.path.join(d, "templates", "NOTES.txt"), "w").write(
        f"{c['pod']} installed as release {{{{ .Release.Name }}}} in namespace {{{{ .Release.Namespace }}}}.\n"
        "It is one of the hr-assistant-vllm blueprint components; install the others into the same namespace.\n")
    print("wrote", chart)
