
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from app.retrieval import search_kb

async def verify():
    # Search for the product that was showing dictionary data
    query = "MizuMi PDRN Platinum Black Mask Instant Moist"
    results = search_kb(query)
    
    print("\n--- Verification Results ---")
    if results.get("matches"):
        for i, match in enumerate(results["matches"][:3]):
            print(f"\nMatch {i+1}:")
            print(match["text"])
    else:
        print("No matches found.")

if __name__ == "__main__":
    asyncio.run(verify())
