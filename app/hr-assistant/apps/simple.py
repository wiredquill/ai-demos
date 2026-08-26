import os

import openai
import openlit
import requests
from openai import OpenAI

MODEL = os.getenv("MODEL", "llama3.2")

ollama_url = os.getenv("OLLAMA_ENDPOINT")

client = OpenAI(
    base_url=f"{ollama_url}/v1",
    api_key="ollama",  # required, but unused
)

# --- Cross-service orchestration --------------------------------------------
#
# HRAssistant is the orchestrator: these are real HTTP calls to the other two
# services' own /ask endpoints (a genuine Service-to-Service hop, not an
# in-process function call), specifically so SUSE Observability's topology
# exporter sees a real edge between distinct Kubernetes Services. No manual
# traceparent injection is needed: main.py's openlit.init() enables the
# OpenTelemetry requests instrumentor, which injects the header on every
# requests.* call automatically; the receiving app's FastAPIInstrumentor
# (also wired in main.py) extracts it, continuing the same trace.
HR_POLICY_DB_URL = os.getenv("GENAI_HR_POLICY_DB_URL")
EMPLOYEE_HANDBOOK_URL = os.getenv("GENAI_EMPLOYEE_HANDBOOK_URL")
DOWNSTREAM_TIMEOUT = int(os.getenv("DOWNSTREAM_TIMEOUT_SECONDS", "90"))


@openlit.trace
def consult_hr_policy_database() -> str:
    if not HR_POLICY_DB_URL:
        return "(HR Policy Database not configured)"
    try:
        resp = requests.get(f"{HR_POLICY_DB_URL}/ask", timeout=DOWNSTREAM_TIMEOUT)
        resp.raise_for_status()
        return str(resp.json().get("answer", ""))[:1000]
    except Exception as e:
        # Same fallback philosophy as rag101/rag102: never 500 /ask because a
        # downstream service is temporarily unavailable.
        print(f"HRPolicyDatabase call failed: {e}")
        return "(HR Policy Database unavailable)"


@openlit.trace
def consult_employee_handbook() -> str:
    if not EMPLOYEE_HANDBOOK_URL:
        return "(Employee Handbook not configured)"
    try:
        resp = requests.get(f"{EMPLOYEE_HANDBOOK_URL}/ask", timeout=DOWNSTREAM_TIMEOUT)
        resp.raise_for_status()
        return str(resp.json().get("answer", ""))[:1000]
    except Exception as e:
        print(f"EmployeeHandbook call failed: {e}")
        return "(Employee Handbook unavailable)"


@openlit.trace
def receive_hr_inquiry():
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Generate an HR inquiry about employee benefits and workplace policies"}],
    )

    return completion.choices[0].message.content


@openlit.trace
def generate_signature(response: str):
    completion = openai.Completion.create(
        model=MODEL,
        prompt="add a signature to the HR response:\n\n" + response,
    )

    return completion.choices[0].text


@openlit.trace
def generate_professional_response(inquiry: str, policy_context: str = "", handbook_context: str = ""):
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": (
                    "Convert this inquiry to professional HR language and provide a helpful response. "
                    "Use this context from our policy database and employee handbook where relevant:\n\n"
                    f"Inquiry:\n{inquiry}\n\n"
                    f"Policy database context:\n{policy_context}\n\n"
                    f"Employee handbook context:\n{handbook_context}\n"
                ),
            }
        ],
    )

    log_interaction_for_compliance()

    return completion.choices[0].message.content


@openlit.trace
def log_interaction_for_compliance():
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Log this HR interaction for compliance tracking and audit purposes"}],
    )

    return completion.choices[0].message.content


@openlit.trace
def hr_assistance_workflow():
    hr_inquiry = receive_hr_inquiry()
    # Sequential, not concurrent: the OTel span context lives in a contextvar
    # that does not cross into a new thread without explicitly copying it, so
    # a naive thread pool here would silently orphan these two calls from the
    # parent trace. Sequential is correct-by-construction for this demo.
    policy_answer = consult_hr_policy_database()
    handbook_answer = consult_employee_handbook()
    professional_response = generate_professional_response(hr_inquiry, policy_answer, handbook_answer)
    # signature = generate_signature(professional_response)
    signature = ""
    return professional_response + "\n\n" + signature
