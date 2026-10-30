"""Generate the per-pod app charts for the HR Assistant SUSE AI Factory blueprints.

For each variant, writes catalog/components/<variant>-{app,handbook,policy-db,load-gen}: one
chart per app pod, each vendoring charts/<variant> (alias "hr") with only its own
workload switched on. The inference engine, Qdrant and OpenSearch are SUSE charts
listed directly in the blueprints (catalog/blueprints/<variant>-*.yaml).

Usage (needs PyYAML): python3 scripts/gen-hr-assistant-components.py .
Edit VARIANTS/COMPONENTS below, bump the variant's version, re-run, then update
the blueprint chartVersions."""
import os, sys, textwrap, yaml

ROOT = sys.argv[1]

VARIANTS = {
    "hr-assistant-vllm": dict(
        title="HR Assistant (vLLM)", base_version="0.1.16", version="0.1.3", blueprint="hr-assistant-vllm-1-7-0.yaml",
        engine="vllm", engine_desc="SUSE vLLM, Qdrant and OpenSearch", nodeport=30081,
        models=["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen3.6-35B-A3B", "meta-llama/Llama-3.3-70B-Instruct", "openai/gpt-oss-120b"],
        llm_values={"vllm": {"enabled": False}, "vllmEndpoint": "http://vllm-router-service:80"},
        q_endpoint=dict(variable="hr.vllmEndpoint", label="vLLM Router URL", default="http://vllm-router-service:80",
                        description="OpenAI-compatible endpoint of the <b>vllm</b> component's router (release <code>vllm</code> creates Service <code>vllm-router-service</code>)."),
        model_label="Model served by vLLM", calls="the vLLM router"),
    "hr-assistant": dict(
        title="HR Assistant (Ollama)", base_version="1.19.1", version="0.1.2", blueprint="hr-assistant-1-2-0.yaml",
        engine="ollama", engine_desc="SUSE Ollama, Qdrant and OpenSearch", nodeport=30080,
        models=["llama3.2:latest", "llama3.2:1b", "llama3.1:8b", "qwen2.5:7b"],
        llm_values={"ollama": {"enabled": False}, "ollamaEndpoint": "http://ollama:11434"},
        q_endpoint=dict(variable="hr.ollamaEndpoint", label="Ollama URL", default="http://ollama:11434",
                        description="Endpoint of the <b>ollama</b> component (release <code>ollama</code> creates Service <code>ollama</code>)."),
        model_label="Model served by Ollama", calls="Ollama"),
}

def deep(d, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

def off(variant, cfg):
    """Everything off; each component switches its own workload back on."""
    v = {
        "fullnameOverride": variant,
        "serviceAccount": {"create": False},
        "components": {"hrAssistant": False, "employeeHandbook": False, "hrPolicyDb": False},
        "loadGenerator": {"enabled": False},
        "qdrant": {"enabled": False, "url": "http://qdrant:6333"},
        "opensearch": {"enabled": False, "url": "http://opensearch-cluster-master:9200"},
        # App images are public (ghcr.io, registry.suse.com/bci); AI Factory delivers
        # its own pull secret to the SUSE charts.
        "imagePullSecrets": [],
    }
    v.update(yaml.safe_load(yaml.safe_dump(cfg["llm_values"])))
    v["model"] = cfg["models"][0]
    v["observability"] = {"connectivityCheck": False}
    return v

Q_OTLP = [
    dict(variable="hr.otlpEndpoint", label="OTLP Endpoint", group="Observability", type="string", required=False, default="",
         description="OpenTelemetry collector address (scheme://host:port).<br><br><b>Leave blank to auto-discover</b> the shared SUSE AI collector in the Collector Namespace below."),
    dict(variable="hr.observability.collectorNamespace", label="Collector Namespace", group="Observability", type="string", required=False, default="observability",
         description="Namespace holding the shared SUSE AI OpenTelemetry collector (installed from the ai-observability-collector chart)."),
]

def q_llm(cfg):
    model = dict(variable="hr.model", label=cfg["model_label"], group="LLM", type="enum", required=True, default=cfg["models"][0], options=cfg["models"],
                 description=f"Must match the model served by the <b>{cfg['engine']}</b> component. Reported as gen_ai.request.model and sent on every request.")
    e = cfg["q_endpoint"]
    endpoint = dict(variable=e["variable"], label=e["label"], group="LLM", type="string", required=True, default=e["default"], description=e["description"])
    return [model, endpoint]

def q_service(default, nodeport=None):
    qs = [dict(variable="hr.service.type", label="Service Type", group="Service Access", type="enum", required=True, default=default,
               options=["ClusterIP", "NodePort", "LoadBalancer"],
               description="How this app's Service is exposed. ClusterIP keeps it in-cluster (port-forward to reach it).")]
    if nodeport:
        qs.append(dict(variable="hr.service.nodePort", label="Dashboard NodePort", group="Service Access", type="int", default=nodeport,
                       show_if="hr.service.type=NodePort", description="NodePort for the dashboard (range 30000-32767)."))
    return qs

def components(cfg):
    return [
      dict(name="app", pod="HR Assistant app",
           summary=f"The HR Assistant conversational app. Calls {cfg['calls']} and fans out to employee-handbook and hr-policy-db.",
           values=lambda v: (deep(v, "components.hrAssistant", True), deep(v, "observability.connectivityCheck", True), deep(v, "service.type", "ClusterIP")),
           questions=q_llm(cfg) + q_service("ClusterIP") + Q_OTLP),
      dict(name="handbook", pod="Employee Handbook app",
           summary=f"Employee Handbook RAG app: answers questions from the bundled HR documents using {cfg['calls']}.",
           values=lambda v: (deep(v, "components.employeeHandbook", True), deep(v, "observability.connectivityCheck", True), deep(v, "service.type", "ClusterIP")),
           questions=q_llm(cfg) + q_service("ClusterIP") + Q_OTLP),
      dict(name="policy-db", pod="HR Policy DB app + dashboard",
           summary=f"HR Policy Database app and the demo dashboard (at /). Uses Qdrant and OpenSearch for retrieval and {cfg['calls']} for answers.",
           values=lambda v: (deep(v, "components.hrPolicyDb", True), deep(v, "observability.connectivityCheck", True),
                             deep(v, "service.type", "NodePort"), deep(v, "service.nodePort", cfg["nodeport"])),
           questions=q_llm(cfg) + [
                      dict(variable="hr.qdrant.url", label="Qdrant URL", group="Retrieval", type="string", required=True, default="http://qdrant:6333",
                           description="REST URL of the <b>qdrant</b> component (SUSE AI chart, release <code>qdrant</code>)."),
                      dict(variable="hr.opensearch.url", label="OpenSearch URL", group="Retrieval", type="string", required=True, default="http://opensearch-cluster-master:9200",
                           description="REST URL of the <b>opensearch</b> component (SUSE Application Collection chart).")]
                     + q_service("NodePort", cfg["nodeport"]) + Q_OTLP),
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

for variant, cfg in VARIANTS.items():
    for c in components(cfg):
        chart = f"{variant}-{c['name']}"
        d = os.path.join(ROOT, "catalog", "components", chart); os.makedirs(os.path.join(d, "templates"), exist_ok=True)
        meta = {
            "apiVersion": "v2", "name": chart,
            "description": f"{cfg['title']} component: {c['pod']}. One of the components of the {variant} SUSE AI Factory blueprint.",
            "type": "application", "version": cfg["version"], "appVersion": "latest",
            "dependencies": [{"name": variant, "version": cfg["base_version"], "repository": f"file://../../../charts/{variant}", "alias": "hr"}],
            "keywords": ["ai", "llm", "hr", "demo", cfg["engine"], "suse-ai-factory"],
            "maintainers": [{"name": "SUSE AI Team", "email": "ai-team@suse.com"}],
            "home": "https://github.com/wiredquill/ai-demos",
            "annotations": {"catalog.cattle.io/display-name": f"{cfg['title']} - {c['pod']}"},
        }
        open(os.path.join(d, "Chart.yaml"), "w").write(
            "# Generated by scripts/gen-hr-assistant-components.py - edit there and re-run.\n" + dump(meta))
        v = off(variant, cfg); c["values"](v)
        open(os.path.join(d, "values.yaml"), "w").write(textwrap.dedent(f"""\
            # {c['pod']} - a single-workload release of charts/{variant}.
            #
            # Every value of the base chart can be set under "hr:". Everything except this
            # component's own workload is switched off; the shared fullnameOverride keeps
            # the Service names ({variant}-<workload>) the same as in the
            # all-in-one install, so the components find each other in one namespace.
            """) + dump({"hr": v}))
        open(os.path.join(d, "questions.yaml"), "w").write(dump({"questions": c["questions"]}))
        open(os.path.join(d, "app-readme.md"), "w").write(f"# {cfg['title']}: {c['pod']}\n\n{c['summary']}\n\n"
            f"Part of the **{variant}** SUSE AI Factory blueprint ({cfg['engine_desc']} plus four app components). "
            "Install all components into the same namespace (the blueprint does this for you).\n")
        open(os.path.join(d, "README.md"), "w").write(f"# {chart}\n\n{c['summary']}\n\n"
            f"This chart is one component of the `{variant}` SUSE AI Factory blueprint "
            f"(`catalog/blueprints/{cfg['blueprint']}`). It vendors `charts/{variant}` "
            f"(alias `hr`) and enables only this workload. See `charts/{variant}/README.md` for the "
            "full component list, how the components connect, and how to install the blueprint.\n")
        open(os.path.join(d, "templates", "NOTES.txt"), "w").write(
            f"{c['pod']} installed as release {{{{ .Release.Name }}}} in namespace {{{{ .Release.Namespace }}}}.\n"
            f"It is one of the {variant} blueprint components; install the others into the same namespace.\n")
        print("wrote", chart)
