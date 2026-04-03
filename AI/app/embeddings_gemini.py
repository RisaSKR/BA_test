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
        """Embed a list of document chunks in smaller batches with retries."""
        batch_size = 20  # Reduced batch size
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            max_retries = 5
            base_delay = 5  # Start with 5 seconds delay on error
            
            for attempt in range(max_retries):
                try:
                    res = self.client.models.embed_content(
                        model=self.model,
                        contents=batch,
                    )
                    all_embeddings.extend([e.values for e in res.embeddings])
                    time.sleep(2)  # Healthy pause between successful batches
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"[Quota] Rate limit reached. Retrying batch {i//batch_size + 1} in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                        else:
                            print(f"[Error] Max retries reached for batch {i//batch_size + 1}.")
                            raise e
                    else:
                        raise e
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