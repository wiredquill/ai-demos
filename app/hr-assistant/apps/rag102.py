import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)


import os

from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
llm_endpoint = os.getenv("LLM_ENDPOINT")

MODEL = os.getenv("MODEL", "llama3.2")


def _build_llm():
    """OllamaLLM (Ollama) and ChatOpenAI (vLLM's OpenAI-compatible router) are
    imported lazily and branched on LLM_PROVIDER so the unused provider's
    LangChain integration is never loaded.
    """
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
    if LLM_PROVIDER == "vllm":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=MODEL,
            base_url=f"{llm_endpoint}/v1",
            api_key="unused",
            callback_manager=callback_manager,
            stop=["<|eot_id|>"],
        )
    from langchain_ollama import OllamaLLM

    return OllamaLLM(
        model=MODEL,
        callback_manager=callback_manager,
        stop=["<|eot_id|>"],
    )


def start_handbook_system():
    # EmployeeHandbook previously answered from a Milvus-backed (milvus-lite,
    # embedded-only - no real deployed service) vectorstore built from the HR
    # PDFs. Milvus was dropped from the demo (redundant with Qdrant, which is
    # a real separately-deployed service and already the vectordb HRPolicyDatabase
    # uses) rather than migrating this app onto Qdrant too, so it answers
    # directly from the model now.
    llm = _build_llm()
    response = llm.invoke("What are the employee onboarding procedures?")
    # OllamaLLM.invoke() returns a plain string; ChatOpenAI.invoke() (vLLM)
    # returns an AIMessage whose text lives in .content.
    result = response.content if hasattr(response, "content") else response
    print(result)
    return result


if __name__ == "__main__":
    start_handbook_system()
