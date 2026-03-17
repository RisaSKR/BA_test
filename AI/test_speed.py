import os
import time
from dotenv import load_dotenv
load_dotenv()

from app.embeddings_gemini import GeminiEmbeddings
from app.tools.faq_tools import retrieve_faq_tool

def test_speed():
    print("Testing Embedding Latency (3 times)...")
    emb = GeminiEmbeddings()
    for i in range(3):
        start = time.time()
        v = emb.embed_query("กันแดด")
        end = time.time()
        print(f"Run {i+1}: Embedding took: {end - start:.4f}s")

    print("\nTesting Retrieval Latency (3 times)...")
    for i in range(3):
        start = time.time()
        results = retrieve_faq_tool("กันแดด", brand="mizumi", k=5)
        end = time.time()
        print(f"Run {i+1}: Retrieval took: {end - start:.4f}s")

if __name__ == "__main__":
    test_speed()
