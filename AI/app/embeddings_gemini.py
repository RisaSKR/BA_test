import os
import time
from typing import List
from google import genai
from google.genai import types
from langchain_core.embeddings import Embeddings

# Pick up embedding model from .env
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

class GeminiEmbeddings(Embeddings):
    """
    Simple wrapper around Google Gemini embeddings.
    Works with the FAISS + LangChain pipeline.

    Methods:
      - embed_documents(list[str]) -> list[list[float]]
      - embed_query(str) -> list[float]
      - close() -> None
    """

    def __init__(self, model: str = EMBED_MODEL):
        self.client = genai.Client()
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of document chunks in batches of 100."""
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            res = self.client.models.embed_content(
                model=self.model,
                contents=batch,
            )
            all_embeddings.extend([e.values for e in res.embeddings])
            time.sleep(1)  # Pause for 1 second after each batch
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        res = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return res.embeddings[0].values
    
    def close(self):
        if hasattr(self.client, "close"):
            self.client.close()