import json
import urllib.request

from mcp_server_qdrant.embeddings.base import EmbeddingProvider

DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaProvider(EmbeddingProvider):
    """
    Ollama implementation of the embedding provider.
    Calls the local Ollama API — no model loaded in-process.
    :param model_name: Ollama model name (e.g. nomic-embed-text).
    :param base_url: Ollama base URL (default: http://localhost:11434).
    :param vector_size: Dimension of the output vectors.
    """

    def __init__(self, model_name: str, base_url: str = DEFAULT_OLLAMA_URL, vector_size: int = 768):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self._vector_size = vector_size

    def _embed(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self.model_name, "input": texts}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["embeddings"]

    async def embed_documents(self, documents: list[str]) -> list[list[float]]:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._embed(documents))

    async def embed_query(self, query: str) -> list[float]:
        import asyncio
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: self._embed([query]))
        return results[0]

    def get_vector_name(self) -> str:
        return f"ollama-{self.model_name.split(':')[0].lower()}"

    def get_vector_size(self) -> int:
        return self._vector_size
