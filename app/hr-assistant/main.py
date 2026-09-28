import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

# LLM_PROVIDER selects which endpoint env var to read: OLLAMA_ENDPOINT for
# "ollama" (the default) or VLLM_ENDPOINT for "vllm". The result is published
# as LLM_ENDPOINT for the app modules below.
#
# This MUST run before `from apps import ...` below: apps/simple.py,
# apps/rag101.py and apps/rag102.py all read os.getenv("LLM_ENDPOINT") at
# module import time, not inside a function, so LLM_ENDPOINT has to already
# be in os.environ before those modules are imported or they capture None.
_llm_provider = os.getenv("LLM_PROVIDER", "ollama")
_llm_endpoint = os.getenv("VLLM_ENDPOINT") if _llm_provider == "vllm" else os.getenv("OLLAMA_ENDPOINT")
os.environ["LLM_ENDPOINT"] = _llm_endpoint
if _llm_provider == "ollama":
    # The native `ollama` client (used by apps/rag101.py) and langchain_ollama
    # (apps/rag102.py) both read these instead of taking the URL as an argument.
    os.environ["OLLAMA_SERVER_URL"] = _llm_endpoint
    os.environ["OLLAMA_HOST"] = _llm_endpoint

from apps import rag101, rag102, simple  # noqa: E402  (see LLM_ENDPOINT comment above)
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

app_name = os.getenv("APP_NAME")

# --- Dashboard support: in-memory stats + log ring buffer -------------------
#
# The demo dashboard polls /stats and /logs. Stats are plain counters bumped in
# /ask; logs are a ring buffer fed by a stdout tee, so every print() in the app
# (LLM answers, RAG traces, datastore searches) is visible without a log
# aggregator. This is intentionally simple — it exists to show the app is
# processing data, not to replace real logging.

_start_time = datetime.now(timezone.utc)
_stats = {"requests": 0, "errors": 0, "last_answer": ""}
_log_ring: deque[str] = deque(maxlen=200)


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

    def isatty(self):
        # fastapi-cli / uvicorn call sys.stdout.isatty() at startup to decide
        # whether to use rich logs. Without this the app crashed on boot:
        # AttributeError: '_RingTee' object has no attribute 'isatty'.
        return self._stream.isatty()

    def fileno(self):
        return self._stream.fileno()


sys.stdout = _RingTee(sys.stdout)  # type: ignore[assignment]


@app.get("/health")
def health():
    return {"Status": "Ready"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Apple-design live dashboard (see dashboard.html).

    Served by the app itself so the browser polls /stats and /logs same-origin
    — no extra deployment, no CORS. The dashboard exists purely to show the
    demo processing data.

    Lives at / (not /dashboard) so it's the landing page at the Service's
    NodePort/URL. hr-policy-db's chart httpGet probes hit / expecting any
    2xx-399 response - probes don't care about body content-type, so serving
    HTML here instead of the old {"Status": "Ready"} JSON doesn't break them.
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
