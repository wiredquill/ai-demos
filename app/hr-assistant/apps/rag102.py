import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)


import os

import openlit
import patch
from langchain import hub
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_milvus import Milvus
from langchain_ollama import OllamaLLM
from pymilvus import MilvusClient

#### Constant For PDF Downloads, If you Change This, Change in Section Below As Well
path_pdfs = "hr-documents/"

#### Initialize Our Documents
documents = []

ollama_url = os.getenv("OLLAMA_ENDPOINT")

MILVUS_URL = "./employee_handbook.db"
MODEL = os.getenv("MODEL", "llama3.2")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-large")


@openlit.trace
def load_hr_documents():
    for file in os.listdir(path_pdfs):
        if file.endswith(".pdf"):
            pdf_path = os.path.join(path_pdfs, file)
            print(pdf_path)
            loader = PyPDFLoader(pdf_path)
            documents.extend(loader.load())


@openlit.trace
def build_handbook_vault():
    # Create a collection to get relation to db.
    client = MilvusClient(MILVUS_URL)
    client.create_collection(
        collection_name="demo_collection",
        dimension=768,
    )


def chunk_policy_documents(alldocs):
    with openlit.start_trace(name="chunk_policy_documents") as trace:
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        trace.set_metadata({"ravmeta": "this is data"})
        trace.set_result("")
        return text_splitter.split_documents(alldocs)


def build_hr_knowledge_base():
    with openlit.start_trace(name="build_hr_knowledge_base") as trace:
        build_handbook_vault()
        embeddings = patch.OllamaEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = Milvus.from_documents(
            documents=chunk_policy_documents(documents),
            embedding=embeddings,
            connection_args={
                "uri": MILVUS_URL,
            },
            collection_name="hr_handbook",
            drop_old=True,
        )
        trace.set_result("")
        return vectorstore


@openlit.trace
def query_handbook_system(query, vectorstore) -> str:
    llm = OllamaLLM(
        model=MODEL,
        callback_manager=CallbackManager([StreamingStdOutCallbackHandler()]),
        stop=["<|eot_id|>"],
    )

    prompt = hub.pull("rlm/rag-prompt")

    qa_chain = RetrievalQA.from_chain_type(llm, retriever=vectorstore.as_retriever(), chain_type_kwargs={"prompt": prompt})

    result = qa_chain.invoke({"query": query})
    return result["result"]


@openlit.trace
def start_handbook_system():
    load_hr_documents()
    vectorstore = build_hr_knowledge_base()
    result = query_handbook_system("What are the employee onboarding procedures?", vectorstore)
    print(result)
    return result


if __name__ == "__main__":
    start_handbook_system()
