import asyncio
import uuid
from dotenv import load_dotenv
load_dotenv()

from app.agents.base_agent import chat_once

def main():
    print("MiMi (RAG with gemini-embedding-001). Type 'exit' to quit.")
    
    #Create ONE session for the entire conversation
    session_id = f"chat-{uuid.uuid4()}"
    
    while True:
        q = input("You: ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        
        #Pass session_id to maintain history
        reply = asyncio.run(chat_once(q, session_id))
        print("MiMi:", reply)

if __name__ == "__main__":
    main()