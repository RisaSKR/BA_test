from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.embeddings_gemini import GeminiEmbeddings

INDEX_BASE_DIR = Path("index")
_indices = {}

def load_faq_index(brand: str = "mizumi"):
    if brand in _indices:
        return _indices[brand]
        
    emb = GeminiEmbeddings()
    index_path = INDEX_BASE_DIR / f"{brand}_faiss"
    
    if not index_path.exists():
        raise FileNotFoundError(f"No index found for brand '{brand}' at {index_path}")

    index = FAISS.load_local(str(index_path), embeddings=emb, allow_dangerous_deserialization=True)
    _indices[brand] = index
    return index
def retrieve_faq_tool(query: str, brand: str = "mizumi", k: int = 10) -> dict:
    """Retrieves FAQ information for a specific brand."""
    try:
        db = load_faq_index(brand)
        docs: list[Document] = db.similarity_search(query, k=k)
        return {"matches": [{"text": d.page_content, "source": d.metadata.get("source"), "image_url": d.metadata.get("image_url")} for d in docs]}
    except Exception as e:
        return {"error": str(e), "matches": []}
