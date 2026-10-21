"""Generate the per-pod app charts for the AI Compare SUSE AI Factory blueprints.

For each variant, writes catalog/components/<variant>-<component>: one chart per AI Compare
pod, each vendoring charts/<variant> (alias "aic") with only its own workload
switched on. Ollama, Open WebUI and Pipelines are separate charts listed directly
in the blueprints (catalog/blueprints/<variant>-*.yaml).

The base charts' versions are bumped by CI on every merge, so the dependency is a
range (~0.1), not a pin.

Usage (needs PyYAML): python3 scripts/gen-ai-compare-components.py .
Edit VARIANTS below, bump the variant's version, re-run, then update the blueprint
chartVersions."""
import os, sys, textwrap, yaml

ROOT = sys.argv[1]
MODELS = ["llama3.2:latest", "llama3.2:1b", "llama3.1:8b", "qwen2.5:7b"]

def deep(d, path, value):
    keys = path.split(".")
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value

Q_MODEL = [
    dict(variable="aic.ollama.models.main", label="Model", group="LLM", type="enum", required=True, default=MODELS[0], options=MODELS,
         description="Model the app asks Ollama for. Must be one the <b>ollama</b> component pulls."),
]
Q_BACKENDS = [
    dict(variable="aic.ollama.url", label="Ollama URL", group="LLM", type="string", required=True, default="http://ollama-service:11434",
         description="Endpoint of the <b>ollama</b> component (release <code>ollama-service</code> creates Service <code>ollama-service</code>)."),
    dict(variable="aic.openWebui.url", label="Open WebUI URL", group="LLM", type="string", required=True, default="http://open-webui:80",
         description="Endpoint of the <b>open-webui</b> component (release <code>open-webui</code>)."),
    dict(variable="aic.pipelines.url", label="Pipelines URL", group="LLM", type="string", required=True, default="http://pipelines-service:9099",
         description="Endpoint of the <b>open-webui-pipelines</b> component (release <code>pipelines-service</code>)."),
]
def q_service(ui_port, api_port):
    return [
        dict(variable="aic.aiCompare.service.type", label="Service Type", group="Service Access", type="enum", required=True, default="NodePort",
             options=["NodePort", "LoadBalancer", "ClusterIP"], description="How the AI Compare UI (7860) and HTTP API (8080) are exposed."),
        dict(variable="aic.aiCompare.service.nodePort", label="UI NodePort", group="Service Access", type="int", default=ui_port,
             show_if="aic.aiCompare.service.type=NodePort"),
        dict(variable="aic.aiCompare.service.httpApiNodePort", label="HTTP API NodePort", group="Service Access", type="int", default=api_port,
             show_if="aic.aiCompare.service.type=NodePort"),
    ]
Q_OTLP = [
    dict(variable="aic.aiCompare.observability.otlpEndpoint", label="OTLP Endpoint", group="Observability", type="string", required=False,
         default="http://opentelemetry-collector.observability.svc.cluster.local:4318",
         description="OpenTelemetry collector (OTLP HTTP). Default: the shared SUSE AI collector in namespace <code>observability</code>."),
]

VARIANTS = {
    "ai-compare-opentelemetry": dict(
        title="AI Compare (OpenTelemetry)", base_range="~0.1", version="0.1.1", blueprint="ai-compare-opentelemetry-1-4-0.yaml",
        components=[
            dict(name="app", pod="AI Compare app",
                 summary="The AI Compare app: asks the same prompt of Ollama directly and through Open WebUI + Pipelines, and compares the answers. GenAI telemetry, token and cost tracking go to SUSE Observability.",
                 values=lambda v: deep(v, "aiCompare.enabled", True),
                 questions=Q_MODEL + Q_BACKENDS + q_service(31705, 31706) + Q_OTLP),
            dict(name="load-gen", pod="Load generator + health-check emitter",
                 summary="Keeps the demo busy by calling the AI Compare HTTP API on an interval, and emits health-check spans for Ollama, Open WebUI and Pipelines so they get a health state in SUSE Observability.",
                 values=lambda v: deep(v, "frontend.loadSimulator.enabled", True),
                 questions=[dict(variable="aic.frontend.loadSimulator.intervalSeconds", label="Load Generation Interval (seconds)", group="Load Generator",
                                 type="int", default=60, required=True,
                                 description="Keep at 60 or lower: SUSE AI components expire ~2 minutes after their last telemetry.")] + Q_OTLP),
        ]),
    # The SUSE and upstream editions deploy the same four pods (Ollama, Open WebUI,
    # Pipelines, app), so their blueprints compare like for like: same app
    # versions, SUSE versus upstream images.
    "ai-compare-suse": dict(
        title="AI Compare (SUSE)", base_range="~0.1", version="0.1.1", blueprint="ai-compare-suse-1-1-0.yaml", models=False,
        components=[
            dict(name="app", pod="AI Compare app",
                 summary="The AI Compare app (SUSE BCI images): asks the same prompt of Ollama directly and through Open WebUI + Pipelines, and compares the answers.",
                 values=lambda v: deep(v, "aiCompare.enabled", True),
                 questions=Q_BACKENDS + q_service(31703, 31704) + Q_OTLP),
        ]),
    "ai-compare": dict(
        title="AI Compare (upstream)", base_range="~0.1", version="0.1.1", blueprint="ai-compare-1-1-0.yaml", models=False,
        components=[
            dict(name="app", pod="AI Compare app",
                 summary="The AI Compare app (upstream images): asks the same prompt of Ollama directly and through Open WebUI + Pipelines, and compares the answers.",
                 values=lambda v: deep(v, "aiCompare.enabled", True),
                 questions=Q_BACKENDS + q_service(31701, 31702) + Q_OTLP),
        ]),
}

def off(variant, cfg):
    """Everything off; each component switches its own workload back on."""
    ollama = {"enabled": False, "url": "http://ollama-service:11434"}
    if cfg.get("models", True):
        ollama["models"] = {"main": MODELS[0]}
    return {
        "fullnameOverride": variant,
        "aiCompare": {"enabled": False},
        "frontend": {"loadSimulator": {"enabled": False}},
        "ollama": ollama,
        "openWebui": {"enabled": False, "url": "http://open-webui:80"},
        "pipelines": {"enabled": False, "url": "http://pipelines-service:9099"},
        # The app image is public; images that need a secret get the one SUSE AI
        # Factory delivers through global.imagePullSecrets.
        "imagePullSecrets": [],
    }

class Dumper(yaml.SafeDumper):
    pass
def str_presenter(d, s):
    return d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None)
Dumper.add_representer(str, str_presenter)
def dump(o):
    return yaml.dump(o, Dumper=Dumper, sort_keys=False, width=1000, allow_unicode=True)

for variant, cfg in VARIANTS.items():
    for c in cfg["components"]:
        chart = f"{variant}-{c['name']}"
        d = os.path.join(ROOT, "catalog", "components", chart); os.makedirs(os.path.join(d, "templates"), exist_ok=True)
        meta = {
            "apiVersion": "v2", "name": chart,
            "description": f"{cfg['title']} component: {c['pod']}. One of the components of the {variant} SUSE AI Factory blueprint.",
            "type": "application", "version": cfg["version"], "appVersion": "latest",
            "dependencies": [{"name": variant, "version": cfg["base_range"], "repository": f"file://../../../charts/{variant}", "alias": "aic"}],
            "keywords": ["ai", "llm", "ollama", "open-webui", "demo", "suse-ai-factory"],
            "maintainers": [{"name": "SUSE AI Team", "email": "ai-team@suse.com"}],
            "home": "https://github.com/wiredquill/ai-demos",
            "annotations": {"catalog.cattle.io/display-name": f"{cfg['title']} - {c['pod']}"},
        }
        open(os.path.join(d, "Chart.yaml"), "w").write(
            "# Generated by scripts/gen-ai-compare-components.py - edit there and re-run.\n" + dump(meta))
        v = off(variant, cfg); c["values"](v)
        open(os.path.join(d, "values.yaml"), "w").write(textwrap.dedent(f"""\
            # {c['pod']} - a single-workload release of charts/{variant}.
            #
            # Every value of the base chart can be set under "aic:". Everything except this
            # component's own workload is switched off; the shared fullnameOverride keeps
            # the Service names ({variant}-*) the same as in the all-in-one install, so
            # the components find each other in one namespace.
            """) + dump({"aic": v}))
        open(os.path.join(d, "questions.yaml"), "w").write(dump({"questions": c["questions"]}))
        open(os.path.join(d, "app-readme.md"), "w").write(f"# {cfg['title']}: {c['pod']}\n\n{c['summary']}\n\n"
            f"Part of the **{variant}** SUSE AI Factory blueprint (Ollama, Open WebUI and Pipelines plus the AI Compare components). "
            "Install all components into the same namespace (the blueprint does this for you).\n")
        open(os.path.join(d, "README.md"), "w").write(f"# {chart}\n\n{c['summary']}\n\n"
            f"This chart is one component of the `{variant}` SUSE AI Factory blueprint "
            f"(`catalog/blueprints/{cfg['blueprint']}`). It vendors `charts/{variant}` "
            "(alias `aic`) and enables only this workload. See the repository README "
            "(\"SUSE AI Factory Blueprints\") for the component list and how to install the blueprint.\n")
        open(os.path.join(d, "templates", "NOTES.txt"), "w").write(
            f"{c['pod']} installed as release {{{{ .Release.Name }}}} in namespace {{{{ .Release.Namespace }}}}.\n"
            f"It is one of the {variant} blueprint components; install the others into the same namespace.\n")
        print("wrote", chart)
