from dotenv import load_dotenv  
load_dotenv()


import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from app.agents.base_agent import chat_once
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Define the data format expected from the Middleware
class UserMessage(BaseModel):
    platform_user_id: str
    platform_conversation_id: str
    text: str
    context: dict | None = None

@app.post("/chat")
async def chat(message: UserMessage):
    logger.info(f"Received message from {message.platform_user_id}: {message.text}")
    
    # Pass the text and conversation ID to your existing chat logic
    response_data = await chat_once(message.text, message.platform_conversation_id)
    
    # Return the response in the JSON format the Middleware expects, now with usage
    return response_data

if __name__ == "__main__":
    print("Starting MiMi API Server on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)