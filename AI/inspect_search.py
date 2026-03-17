
from dotenv import load_dotenv
load_dotenv()
from app.retrieval import search_kb
import asyncio
import json

async def inspect():
    results = search_kb("MizuMi Multi-Micellar 4X Smooth Cleansing Water Acne")
    if results.get("matches"):
        print(json.dumps(results["matches"][0], indent=2, ensure_ascii=False))
    else:
        print("No matches found")

if __name__ == "__main__":
    asyncio.run(inspect())
