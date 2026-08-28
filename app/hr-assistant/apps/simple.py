import contextvars
import os
from concurrent.futures import ThreadPoolExecutor

import openai
import openlit
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
    # HRPolicyDatabase and EmployeeHandbook are independent downstream calls -
    # run them concurrently instead of back-to-back, since each is itself a
    # multi-step LLM chain and dominates this app's own end-to-end latency
    # (its SERVER span duration is what SUSE Observability's span-duration
    # monitor evaluates). A plain ThreadPoolExecutor would silently orphan
    # these two calls from the parent trace: the OTel span context lives in a
    # contextvar, which a new thread does not inherit on its own. Explicitly
    # copying the current context into each submitted call is what keeps them
    # nested under this span and keeps their outgoing requests.* calls
    # carrying this trace's traceparent header, exactly as the sequential
    # version did.
    #
    # Each submission needs its OWN copy_context() call: a single captured
    # Context object can only be entered (via ctx.run) by one thread at a
    # time - reusing the same copy for both concurrent submissions raises
    # "RuntimeError: cannot enter context: ... is already entered" as soon as
    # both threads try to run it at once.
    with ThreadPoolExecutor(max_workers=2) as executor:
        policy_future = executor.submit(contextvars.copy_context().run, consult_hr_policy_database)
        handbook_future = executor.submit(contextvars.copy_context().run, consult_employee_handbook)
        policy_answer = policy_future.result()
        handbook_answer = handbook_future.result()
    professional_response = generate_professional_response(hr_inquiry, policy_answer, handbook_answer)
    # signature = generate_signature(professional_response)
    signature = ""
    return professional_response + "\n\n" + signature
