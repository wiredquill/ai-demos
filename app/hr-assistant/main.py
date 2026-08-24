import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import openlit
import patch
from apps import rag101, rag102, simple
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

otlp_endpoint = os.getenv("OTLP_ENDPOINT")
ollama_url = os.getenv("OLLAMA_ENDPOINT")
os.environ["OLLAMA_SERVER_URL"] = ollama_url
os.environ["OLLAMA_HOST"] = ollama_url
ollama_api_key = os.getenv("OLLAMA_API_KEY")
app_name = os.getenv("APP_NAME")
collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false") == "true"

openlit.init(
    otlp_endpoint=otlp_endpoint,
    disable_batch=True,
    capture_message_content=True,
    application_name=app_name,
    pricing_json="./pricing.json",
    collect_gpu_stats=collect_gpu_stats,
    # The OpenAI SDK here only ever talks to Ollama's /v1 endpoint. openlit's own
    # openai instrumentor would report gen_ai.provider.name=openai, which puts a
    # bogus OpenAI inference engine in the SUSE AI topology, so patch_openlit()
    # owns that path instead and reports Ollama.
    disabled_instrumentors=["openai"],
)

patch.patch_openlit()

# --- Dashboard support: in-memory stats + log ring buffer -------------------
#
# The demo dashboard polls /stats and /logs. Stats are plain counters bumped in
# /ask; logs are a ring buffer fed by a stdout tee, so every print() in the app
# (LLM answers, RAG traces, datastore searches) is visible without a log
# aggregator. This is intentionally simple — it exists to show the app is
# processing data, not to replace real logging.

_start_time = datetime.now(timezone.utc)
_stats = {"requests": 0, "errors": 0, "last_answer": ""}
_log_ring = deque(maxlen=200)


class _RingTee:
    """Tee stdout into the ring buffer as well as the real stdout."""

    def __init__(self, stream):
        self._stream = stream

    def write(self, data):
        self._stream.write(data)
        if data.strip():
            _log_ring.append(f"{datetime.now(timezone.utc).isoformat()} {data.rstrip()}")
        return len(data)

    def flush(self):
        self._stream.flush()


sys.stdout = _RingTee(sys.stdout)


@app.get("/")
def read_root():
    return {"Status": "Ready"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Apple-design live dashboard (see dashboard.html).

    Served by the app itself so the browser polls /stats and /logs same-origin
    — no extra deployment, no CORS. The dashboard exists purely to show the
    demo processing data; SUSE Observability is the real monitoring surface.
    """
    html = Path(__file__).parent / "dashboard.html"
    if html.exists():
        return HTMLResponse(html.read_text())
    return HTMLResponse("<h1>dashboard.html missing from image</h1>", status_code=500)


@app.get("/ask")
def ask():
    _stats["requests"] += 1
    try:
        result = f"App {app_name} error"
        if app_name == "HRAssistant":
            result = simple.hr_assistance_workflow()
        elif app_name == "HRPolicyDatabase":
            result = rag101.start_hr_policy_system()
        elif app_name == "EmployeeHandbook":
            result = rag102.start_handbook_system()
        else:
            result = f"'{app_name}' not know."
        _stats["last_answer"] = str(result)[:500]
        return {"answer": result}
    except Exception as e:
        _stats["errors"] += 1
        raise


@app.get("/stats")
def stats():
    """Counter snapshot for the dashboard: requests handled, errors, uptime.

    For the RAG app (HRPolicyDatabase) this also includes vector-database and
    search-engine activity so the dashboard can show data being processed.
    """
    payload = {
        "app": app_name,
        "requests": _stats["requests"],
        "errors": _stats["errors"],
        "uptime_seconds": int((datetime.now(timezone.utc) - _start_time).total_seconds()),
    }
    if app_name == "HRPolicyDatabase":
        payload["rag"] = rag101.get_rag_stats()
    return payload


@app.get("/logs")
def logs():
    """Most recent application log lines (ring buffer, newest last)."""
    return {"logs": list(_log_ring)}
