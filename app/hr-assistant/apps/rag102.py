import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)


import os

import openlit
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from openlit.__helpers import get_chat_model_cost
from patch.suse_ai_metrics import record_suse_ai_metrics

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
llm_endpoint = os.getenv("LLM_ENDPOINT")

MODEL = os.getenv("MODEL", "llama3.2")

_openlit_conf = openlit.OpenlitConfig()


class SuseAiMetricsCallback(BaseCallbackHandler):
    """Records the SUSE AI gen_ai.total.requests/cost metrics openlit's native
    langchain instrumentor doesn't (see patch/suse_ai_metrics.py).

    Ollama only: langchain_ollama (OllamaLLM, a plain completion LLM) passes
    Ollama's raw response straight through as generation_info, so
    prompt_eval_count/eval_count are available the same way as the native
    ollama client in rag101.py, and this callback is the only place that
    records the SUSE AI metrics for it.

    langchain_openai's ChatOpenAI (used for vLLM) calls the same
    openai.resources.chat.completions.Completions.create path
    patch/openlit_vllm.py already wraps with full span + SUSE AI metric
    recording, so this callback does nothing on that path to avoid
    double-counting requests/cost.
    """

    def on_llm_end(self, response, **kwargs):
        if LLM_PROVIDER == "vllm":
            return
        try:
            generation_info = response.generations[0][0].generation_info or {}
            input_tokens = generation_info.get("prompt_eval_count", 0)
            output_tokens = generation_info.get("eval_count", 0)
            cost = get_chat_model_cost(MODEL, _openlit_conf.pricing_info, input_tokens, output_tokens)
            record_suse_ai_metrics(_openlit_conf.application_name, _openlit_conf.environment, LLM_PROVIDER, MODEL, cost)
        except Exception as e:
            print(f"SUSE AI metrics recording failed (non-fatal): {e}")


def _build_llm():
    """OllamaLLM (Ollama) and ChatOpenAI (vLLM's OpenAI-compatible router) are
    imported lazily and branched on LLM_PROVIDER so the unused provider's
    LangChain integration is never loaded.
    """
    callback_manager = CallbackManager([StreamingStdOutCallbackHandler(), SuseAiMetricsCallback()])
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


@openlit.trace
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
