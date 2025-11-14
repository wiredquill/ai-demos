from typing import List, Optional

from langchain_core.embeddings import Embeddings
from ollama import AsyncClient, Client
from pydantic import BaseModel, ConfigDict, PrivateAttr, model_validator
from typing_extensions import Self


class OllamaEmbeddings(BaseModel, Embeddings):
    model: str
    """Model name to use."""

    base_url: Optional[str] = None
    """Base url the model is hosted under."""

    client_kwargs: Optional[dict] = {}
    """Additional kwargs to pass to the httpx Client.
    For a full list of the params, see [this link](https://pydoc.dev/httpx/latest/httpx.Client.html)
    """

    _client: Client = PrivateAttr(default=None)
    """
    The client to use for making requests.
    """

    _async_client: AsyncClient = PrivateAttr(default=None)
    """
    The async client to use for making requests.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    @model_validator(mode="after")
    def _set_clients(self) -> Self:
        """Set clients to use for ollama."""
        client_kwargs = self.client_kwargs or {}
        self._client = Client(host=self.base_url, **client_kwargs)
        self._async_client = AsyncClient(host=self.base_url, **client_kwargs)
        return self

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._client.embed(model=self.model, input=texts)["embeddings"]

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        embedded_docs = (await self._async_client.embed(model=self.model, input=texts))["embeddings"]
        return embedded_docs

    async def aembed_query(self, text: str) -> List[float]:
        """Embed query text."""
        return (await self.aembed_documents([text]))[0]
