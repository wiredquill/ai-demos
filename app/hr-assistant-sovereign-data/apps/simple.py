import json
import os

import openai
import openlit
from openai import OpenAI

MODEL = os.getenv("MODEL", "llama3.2")

ollama_url = os.getenv("OLLAMA_ENDPOINT")

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
    print("Warning: countries.json not found. Sovereign data compliance checks disabled in simple.py.")

client = OpenAI(
    base_url=f"{ollama_url}/v1",
    api_key="ollama",  # required, but unused
)


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
def generate_professional_response(inquiry: str):
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": f"Convert this inquiry to professional HR language and provide a helpful response:\n\n{inquiry}",
            }
        ],
    )

    log_interaction_for_compliance()

    return completion.choices[0].message.content


@openlit.trace
def log_interaction_for_compliance():
    country_info = countries_config.get(deployment_country, {})
    requires_sovereignty = country_info.get("requiresSovereigntyCompliance", False)

    # Enhanced compliance logging with sovereign data context
    compliance_message = "Log this HR interaction for compliance tracking and audit purposes. "
    if requires_sovereignty:
        compliance_message += (
            f"Region: {deployment_region}, Country: {deployment_country}, "
            f"Data Sovereignty Required: Yes, Acknowledged: {acknowledge_data_sovereignty}"
        )
    else:
        compliance_message += (
            f"Region: {deployment_region}, Country: {deployment_country}, " f"Data Sovereignty Requirements: None"
        )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": compliance_message}],
    )

    return completion.choices[0].message.content


@openlit.trace
def add_sovereignty_compliance_notice():
    """
    Generates a data sovereignty compliance notice if required by the deployment region/country.
    """
    country_info = countries_config.get(deployment_country, {})
    requires_sovereignty = country_info.get("requiresSovereigntyCompliance", False)

    if not requires_sovereignty:
        return ""

    if not acknowledge_data_sovereignty:
        return "\n\n⚠️ WARNING: Data Sovereignty Compliance Not Acknowledged\n"

    data_laws = country_info.get("dataLaws", [])
    sovereignty_details = country_info.get("sovereigntyDetails", "")

    notice = "\n\n📋 Data Sovereignty Compliance Notice:\n"
    notice += f"Deployment Country: {deployment_country}\n"
    notice += f"Applicable Data Protection Laws: {', '.join(data_laws)}\n"
    if sovereignty_details:
        notice += f"Details: {sovereignty_details}\n"
    notice += f"✓ Compliance Acknowledged: {acknowledge_data_sovereignty}\n"

    return notice


@openlit.trace
def hr_assistance_workflow():
    hr_inquiry = receive_hr_inquiry()
    professional_response = generate_professional_response(hr_inquiry)
    # signature = generate_signature(professional_response)
    signature = ""

    # Add sovereignty compliance notice if required
    compliance_notice = add_sovereignty_compliance_notice()

    return professional_response + "\n\n" + signature + compliance_notice
