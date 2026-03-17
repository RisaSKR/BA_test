
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.agents.base_agent import chat_once

async def test():
    result = await chat_once("MizuMi UV Water Serum", "test-session")
    print(f"TEXT: {result.get('text')[:50]}...")
    print(f"IMAGE: {result.get('image_url')}")

if __name__ == "__main__":
    asyncio.run(test())
