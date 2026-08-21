import json
import os

import ollama
import openlit
from pymilvus import MilvusClient, model

MILVUS_URL = "./rag101.db"
MODEL = os.getenv("MODEL", "llama3.2")
EMBEDDING_MODEL = "bge-large"

embedding_fn = model.DefaultEmbeddingFunction()

# Keep a single MilvusClient for the lifetime of the process. milvus-lite's
# embedded server is bound to the client that started it; creating a fresh
# MilvusClient per request (the pymilvus 2.x pattern) lets the old embedded
# server on 127.0.0.1:<port> die, and the next request fails with
# "Fail connecting to server ... server unavailable". A module-level client
# keeps the server alive across /ask calls.
_milvus_client = None


def get_milvus_client():
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient(MILVUS_URL)
    return _milvus_client

documents = [
    "Employees are entitled to 20 days of paid vacation per year after one year of service.",
    "Remote work policy allows up to 3 days per week with manager approval.",
    "Health insurance coverage includes medical, dental, and vision with company contribution.",
]

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_benefits_information",
            "description": "Get employee benefits information including vacation, health insurance, and policies",
            "parameters": {
                "type": "object",
                "properties": {
                    "benefit_type": {
                        "type": "string",
                        "description": "The type of benefit (vacation, health, remote_work)",
                    },
                    "employee_level": {
                        "type": "string",
                        "description": "Employee level (junior, senior, manager)",
                    },
                },
                "required": ["benefit_type", "employee_level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_policy_database",
            "description": "Search HR policies and employee guidelines in the policy database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


@openlit.trace
def initialize_policy_database():
    vectors = embedding_fn.encode_documents(documents)
    # The output vector has 768 dimensions, matching the collection that we just created.
    print("Dim:", embedding_fn.dim, vectors[0].shape)  # Dim: 768 (768,)

    # Each entity has id, vector representation, raw text, and a subject label.
    data = [{"id": i, "vector": vectors[i], "text": documents[i], "subject": "history"} for i in range(len(vectors))]
    print("Data has", len(data), "entities, each with fields: ", data[0].keys())
    print("Vector dim:", len(data[0]["vector"]))
    return data


@openlit.trace
def build_policy_vault():
    data = initialize_policy_database()
    # Create a collection and insert the data
    client = get_milvus_client()
    client.create_collection(
        collection_name="demo_collection",
        dimension=768,
    )
    client.insert(collection_name="demo_collection", data=data)


# Simulates an API call to get flight times
# In a real application, this would fetch data from a live database or API
@openlit.trace
def get_benefits_information(benefit_type: str, employee_level: str) -> str:
    benefits = {
        "vacation-junior": {
            "days": "15 days",
            "accrual": "1.25 days per month",
            "carryover": "5 days max",
        },
        "vacation-senior": {
            "days": "20 days",
            "accrual": "1.67 days per month",
            "carryover": "10 days max",
        },
        "health-all": {
            "medical": "90% coverage",
            "dental": "80% coverage",
            "vision": "100% coverage",
        },
        "remote_work-all": {
            "days_per_week": "3 days max",
            "approval": "Manager required",
            "equipment": "Company provided",
        },
        "vacation-manager": {
            "days": "25 days",
            "accrual": "2.08 days per month",
            "carryover": "15 days max",
        },
        "health-manager": {
            "medical": "95% coverage",
            "dental": "90% coverage",
            "vision": "100% coverage",
        },
    }
    key = f"{benefit_type}-{employee_level}".lower()
    return json.dumps(benefits.get(key, {"error": "Benefit information not found"}))


# Search data related to Artificial Intelligence in a vector database


@openlit.trace
def search_policy_database(query: str) -> str:
    query_vectors = embedding_fn.encode_queries([query])
    client = get_milvus_client()
    res = client.search(
        collection_name="demo_collection",
        data=query_vectors,
        limit=2,
        output_fields=["text", "subject"],  # specifies fields to be returned
    )
    print(res)
    return json.dumps(res)


@openlit.trace
def send_query_to_hr_ai(messages):
    # First API call: Send the query and function description to the model
    client = ollama.Client()
    response = client.chat(
        model=MODEL,
        messages=messages,
        tools=tools,
    )
    return response


@openlit.trace
def process_hr_ai_response(messages, response):
    # Process function calls made by the model
    if response["message"].get("tool_calls"):
        available_functions = {
            "get_benefits_information": get_benefits_information,
            "search_policy_database": search_policy_database,
        }

        for tool in response["message"]["tool_calls"]:
            function_to_call = available_functions[tool["function"]["name"]]
            function_args = tool["function"]["arguments"]
            function_response = function_to_call(**function_args)
            # Add function response to the conversation
            messages.append(
                {
                    "role": "tool",
                    "content": function_response,
                }
            )
    # Second API call: Get final response from the model
    client = ollama.Client()
    final_response = client.chat(model=MODEL, messages=messages)
    print(final_response["message"]["content"])
    return final_response


@openlit.trace
def handle_hr_inquiry(question: str):
    client = ollama.Client()

    # Initialize conversation with a user query

    messages = [{"role": "user", "content": question}]

    # First API call: Send the query and function description to the model
    response = send_query_to_hr_ai(messages)

    # Add the model's response to the conversation history
    messages.append(response["message"])

    # Check if the model decided to use the provided function
    if not response["message"].get("tool_calls"):
        print("The model didn't use the function. Its response was:")
        print(response["message"]["content"])
        return

    # Process function calls made by the model
    return process_hr_ai_response(messages, response)


@openlit.trace
def start_hr_policy_system():
    try:
        build_policy_vault()

        question = "What are the vacation benefits for senior employees?"
        handle_hr_inquiry(question)

        question = "What is our remote work policy?"
        return handle_hr_inquiry(question)
    except Exception as e:
        # Fall back to a plain LLM answer if the vector store is unavailable.
        # Keeps /ask returning 200 (and telemetry flowing) during vector-store
        # outages instead of surfacing a 500 to the load generator.
        print(f"RAG unavailable, falling back to plain LLM: {e}")
        client = ollama.Client()
        response = client.chat(
            model=MODEL,
            messages=[{"role": "user", "content": "What is our remote work policy?"}],
        )
        return response
