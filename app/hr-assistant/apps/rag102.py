import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)


import os

import openlit
from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_ollama import OllamaLLM
from openlit.__helpers import get_chat_model_cost
from patch.suse_ai_metrics import record_suse_ai_metrics

ollama_url = os.getenv("OLLAMA_ENDPOINT")

MODEL = os.getenv("MODEL", "llama3.2")

_openlit_conf = openlit.OpenlitConfig()


class SuseAiMetricsCallback(BaseCallbackHandler):
    """Records the SUSE AI gen_ai.total.requests/cost metrics openlit's native
    langchain instrumentor doesn't (see patch/suse_ai_metrics.py). langchain_ollama
    passes Ollama's raw response straight through as generation_info, so
    prompt_eval_count/eval_count are available the same way as the native
    ollama client in rag101.py.
    """

    def on_llm_end(self, response, **kwargs):
        try:
            generation_info = response.generations[0][0].generation_info or {}
            input_tokens = generation_info.get("prompt_eval_count", 0)
            output_tokens = generation_info.get("eval_count", 0)
            cost = get_chat_model_cost(MODEL, _openlit_conf.pricing_info, input_tokens, output_tokens)
            record_suse_ai_metrics(_openlit_conf.application_name, _openlit_conf.environment, "ollama", MODEL, cost)
        except Exception as e:
            print(f"SUSE AI metrics recording failed (non-fatal): {e}")


@openlit.trace
def start_handbook_system():
    # EmployeeHandbook previously answered from a Milvus-backed (milvus-lite,
    # embedded-only - no real deployed service) vectorstore built from the HR
    # PDFs. Milvus was dropped from the demo (redundant with Qdrant, which is
    # a real separately-deployed service and already the vectordb HRPolicyDatabase
    # uses) rather than migrating this app onto Qdrant too, so it answers
    # directly from the model now.
    llm = OllamaLLM(
        model=MODEL,
        callback_manager=CallbackManager([StreamingStdOutCallbackHandler(), SuseAiMetricsCallback()]),
        stop=["<|eot_id|>"],
    )
    result = llm.invoke("What are the employee onboarding procedures?")
    print(result)
    return result


if __name__ == "__main__":
    start_handbook_system()
