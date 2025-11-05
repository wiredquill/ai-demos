import os

import openai
import openlit
from openai import OpenAI

MODEL = os.getenv("MODEL", "llama3.2")

ollama_url = os.getenv("OLLAMA_ENDPOINT")

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
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": f"Log this HR interaction for compliance tracking and audit purposes"}],
    )

    return completion.choices[0].message.content


@openlit.trace
def hr_assistance_workflow():
    hr_inquiry = receive_hr_inquiry()
    professional_response = generate_professional_response(hr_inquiry)
    # signature = generate_signature(professional_response)
    signature = ""
    return professional_response + "\n\n" + signature
