
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from app.embeddings_gemini import GeminiEmbeddings

load_dotenv()

def test_search(query):
    index_path = Path("index/mizumi_faiss")
    if not index_path.exists():
        print(f"Index not found at {index_path}. please run: python -m app.ingest.faq_ingest")
        return
    
    emb = GeminiEmbeddings()
    db = FAISS.load_local(str(index_path), embeddings=emb, allow_dangerous_deserialization=True)
    
    print(f"\nQuery: {query}")
    results = db.similarity_search(query, k=3)
    
    for i, res in enumerate(results):
        print(f"\nMatch {i+1}:")
        print(f"Source: {res.metadata.get('source')}")
        print(f"Image: {res.metadata.get('image_url')}")
        print(f"Content:\n{res.page_content}")

if __name__ == "__main__":
    # Test with a question from faqs.json
    test_search("MizuMi UV Water Serum ใช้ได้ตั้งแต่อายุเท่าไหร่?")
    # Test with a product detail
    test_search("หาครีมกันแดดสำหรับผิวแพ้ง่าย")
