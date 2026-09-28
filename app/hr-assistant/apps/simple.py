import os
from concurrent.futures import ThreadPoolExecutor

import requests
from openai import OpenAI

MODEL = os.getenv("MODEL", "llama3.2")

# Ollama and vLLM both speak the OpenAI-compatible /v1 API, so this client
# construction is provider-agnostic — main.py sets LLM_ENDPOINT from whichever
# of OLLAMA_ENDPOINT/VLLM_ENDPOINT is active for this deployment.
llm_endpoint = os.getenv("LLM_ENDPOINT")

client = OpenAI(
    base_url=f"{llm_endpoint}/v1",
    api_key="unused",  # required by the SDK, ignored by both Ollama and vLLM
)

# --- Cross-service orchestration --------------------------------------------
#
# HRAssistant is the orchestrator: these are real HTTP calls to the other two
# services' own /ask endpoints (a genuine Service-to-Service hop, not an
# in-process function call).
HR_POLICY_DB_URL = os.getenv("GENAI_HR_POLICY_DB_URL")
EMPLOYEE_HANDBOOK_URL = os.getenv("GENAI_EMPLOYEE_HANDBOOK_URL")
DOWNSTREAM_TIMEOUT = int(os.getenv("DOWNSTREAM_TIMEOUT_SECONDS", "90"))


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


def receive_hr_inquiry():
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Generate an HR inquiry about employee benefits and workplace policies"}],
    )

    return completion.choices[0].message.content


def generate_signature(response: str):
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "add a signature to the HR response:\n\n" + response}],
    )

    return completion.choices[0].message.content


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


def log_interaction_for_compliance():
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Log this HR interaction for compliance tracking and audit purposes"}],
    )

    return completion.choices[0].message.content


def hr_assistance_workflow():
    hr_inquiry = receive_hr_inquiry()
    # HRPolicyDatabase and EmployeeHandbook are independent downstream calls -
    # run them concurrently instead of back-to-back, since each is itself a
    # multi-step LLM chain and dominates this app's own end-to-end latency.
    with ThreadPoolExecutor(max_workers=2) as executor:
        policy_future = executor.submit(consult_hr_policy_database)
        handbook_future = executor.submit(consult_employee_handbook)
        policy_answer = policy_future.result()
        handbook_answer = handbook_future.result()
    professional_response = generate_professional_response(hr_inquiry, policy_answer, handbook_answer)
    signature = ""
    return professional_response + "\n\n" + signature
