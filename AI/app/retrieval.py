from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.embeddings_gemini import GeminiEmbeddings

INDEX_BASE_DIR = Path("index")
_indices = {}

_emb_instance = None

def _get_embeddings():
    global _emb_instance
    if _emb_instance is None:
        _emb_instance = GeminiEmbeddings()
    return _emb_instance

def load_index(brand: str = "mizumi"):
    if brand in _indices:
        return _indices[brand]
        
    emb = _get_embeddings()
    # Dynamic path based on brand name
    index_path = INDEX_BASE_DIR / f"{brand}_faiss"
    
    if not index_path.exists():
        raise FileNotFoundError(f"No FAISS index found for brand: {brand} at {index_path}")
        
    index = FAISS.load_local(str(index_path), embeddings=emb, allow_dangerous_deserialization=True)
    _indices[brand] = index
    return index
def search_kb(query: str, brand: str = "mizumi", k: int = 10)-> dict:
    """
    Search the local FAISS index for relevant chunks of a specific brand.
    """
    try:
        db = load_index(brand)
        docs: list[Document] = db.similarity_search(query, k=k)
        return {"matches": [{"text": d.page_content, "source": d.metadata.get("source"), "image_url": d.metadata.get("image_url")} for d in docs]}
    except Exception as e:
        return {"error": str(e), "matches": []}

