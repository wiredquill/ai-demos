import json
import os

import openlit
import patch
from apps import rag101, rag102, simple
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

otlp_endpoint = os.getenv("OTLP_ENDPOINT")
ollama_url = os.getenv("OLLAMA_ENDPOINT")
os.environ["OLLAMA_SERVER_URL"] = ollama_url
os.environ["OLLAMA_HOST"] = ollama_url
ollama_api_key = os.getenv("OLLAMA_API_KEY")
app_name = os.getenv("APP_NAME")
collect_gpu_stats = os.getenv("COLLECT_GPU_STATS", "false") == "true"

# Sovereign Data Compliance Configuration
deployment_region = os.getenv("DEPLOYMENT_REGION", "americas")
deployment_country = os.getenv("DEPLOYMENT_COUNTRY", "United States")
acknowledge_data_sovereignty = os.getenv("ACKNOWLEDGE_DATA_SOVEREIGNTY", "true") == "true"

# Load country sovereignty configuration
countries_config = {}
try:
    with open("./countries.json", "r") as f:
        countries_data = json.load(f)
        countries_config = countries_data.get("countries", {})
except FileNotFoundError:
    print("Warning: countries.json not found. Sovereign data compliance checks disabled.")

# Get current country's sovereignty requirements
current_country_config = countries_config.get(deployment_country, {})
requires_sovereignty_compliance = current_country_config.get("requiresSovereigntyCompliance", False)


# Pydantic models for sovereign data compliance
class SovereignDataInfo(BaseModel):
    region: str
    country: str
    requiresSovereigntyCompliance: bool
    dataLaws: list
    sovereigntyDetails: str = None
    complianceAcknowledged: bool


openlit.init(
    otlp_endpoint=otlp_endpoint,
    disable_batch=True,
    capture_message_content=True,
    application_name=app_name,
    pricing_json="./pricing.json",
    collect_gpu_stats=collect_gpu_stats,
)

patch.patch_openlit()


@app.get("/")
def read_root():
    return {
        "Status": "Ready",
        "Application": "HR Assistant - Sovereign Data Edition",
        "Deployment": {
            "region": deployment_region,
            "country": deployment_country,
            "complianceEnabled": requires_sovereignty_compliance,
        },
    }


@app.get("/sovereign-data-info")
def get_sovereign_data_info():
    """
    Returns sovereign data compliance information for the current deployment.
    """
    country_info = countries_config.get(deployment_country, {})

    return SovereignDataInfo(
        region=deployment_region,
        country=deployment_country,
        requiresSovereigntyCompliance=country_info.get("requiresSovereigntyCompliance", False),
        dataLaws=country_info.get("dataLaws", []),
        sovereigntyDetails=country_info.get("sovereigntyDetails"),
        complianceAcknowledged=acknowledge_data_sovereignty,
    )


@app.get("/ask")
def ask():
    """
    Main HR Assistant endpoint. Includes sovereign data compliance context in responses.
    """
    # Build compliance context for the response
    compliance_context = {
        "deploymentRegion": deployment_region,
        "deploymentCountry": deployment_country,
        "sovereigntyCompliant": requires_sovereignty_compliance and acknowledge_data_sovereignty,
    }

    result = f"App {app_name} error"
    if app_name == "HRAssistant":
        result = simple.hr_assistance_workflow()
    elif app_name == "HRPolicyDatabase":
        result = rag101.start_hr_policy_system()
    elif app_name == "EmployeeHandbook":
        result = rag102.start_handbook_system()
    else:
        result = f"'{app_name}' not know."

    return {
        "answer": result,
        "complianceContext": compliance_context,
        "sovereignDataCompliance": {"enabled": requires_sovereignty_compliance, "acknowledged": acknowledge_data_sovereignty},
    }
