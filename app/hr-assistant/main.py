import os
from typing import Union

import openlit
import patch
from apps import rag101, rag102, simple
from fastapi import FastAPI

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
    trace_content=True,
    application_name=app_name,
    pricing_json="./pricing.json",
    collect_gpu_stats=collect_gpu_stats,
)

patch.patch_openlit()


@app.get("/")
def read_root():
    return {"Status": "Ready"}


@app.get("/ask")
def ask():
    result = f"App {app_name} error"
    if app_name == "HRAssistant":
        result = simple.hr_assistance_workflow()
    elif app_name == "HRPolicyDatabase":
        result = rag101.start_hr_policy_system()
    elif app_name == "EmployeeHandbook":
        result = rag102.start_handbook_system()
    else:
        result = f"'{app_name}' not know."
    return {"answer": result}
