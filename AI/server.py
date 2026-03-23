from dotenv import load_dotenv  
load_dotenv()


import uvicorn
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.agents.base_agent import chat_once, get_history
import logging
import os

from app.root_agent import root_agent

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

from app.tools.faq_tools import load_faq_index

@app.on_event("startup")
async def startup_event():
    """Pre-load indices and models at startup."""
    try:
        load_faq_index("mizumi")
        logger.info("Successfully pre-loaded FAISS index for 'mizumi'")
    except Exception as e:
        logger.error(f"Failed to pre-load index: {e}")

# Create static directory if it doesn't exist
current_file_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_file_dir, "static")
os.makedirs(static_dir, exist_ok=True)

logger.info(f"Static directory: {static_dir}")

# ── Chat test UI ──────────────────────────────────────────────────────────────
@app.get("/")
def serve_chat_ui():
    """Serve the chat test page at the root URL."""
    response = FileResponse(os.path.join(static_dir, "chat.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response

# ── Static files (images, etc.) ───────────────────────────────────────────────
# IMPORTANT: Mount AFTER the route definitions, otherwise it catches all routes
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Define the data format expected from the Middleware
class UserMessage(BaseModel):
    platform_user_id: str
    platform_conversation_id: str
    text: str
    image: str | None = None  # Added for image support (Base64)
    context: dict | None = None
    # optional brand field (or supply via context)
    brand: str | None = None
    store_id: str | None = None
    language: str | None = "TH"

from fastapi.responses import StreamingResponse
import json
from app.agents.base_agent import chat_stream

@app.post("/chat_stream")
async def chat_stream_endpoint(message: UserMessage):
    """Streaming chat endpoint that yields chunks as they arrive."""
    brand = message.brand
    if not brand and message.context:
        brand = message.context.get("brand")
    if not brand:
        brand = "mizumi"

    async def event_generator():
        async for chunk in chat_stream(
            message.text,
            message.platform_conversation_id,
            brand=brand,
            store_id=message.store_id or "onsite_default",
            language=message.language,
            image=message.image
        ):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/chat")
async def chat(message: UserMessage):
    """Primary chat endpoint used by the UI and middleware.

    The `brand` can be supplied directly or via `message.context`. If
    nothing is provided it defaults to ``mizumi`` (matching
    ``chat_once``'s default).
    """
    # determine which brand to use
    brand = message.brand
    if not brand and message.context:
        brand = message.context.get("brand")
    if not brand:
        brand = "mizumi"

    # forward to shared helper that now builds a brand-specific agent
    response_data = await chat_once(
        message.text,
        message.platform_conversation_id,
        brand=brand,
        store_id=message.store_id or "onsite_default",
        language=message.language,
        image=message.image
    )
    return response_data

# simple history endpoint to return previous conversation turns
@app.get("/history")
async def history(conversation_id: str):
    """Return a list of past messages for the given session ID."""
    msgs = await get_history(conversation_id)
    return {"messages": msgs}

# feedback endpoint to log user sentiment
class FeedbackData(BaseModel):
    session_id: str
    message_text: str
    feedback: str

from app.utils.logger import update_feedback

@app.post("/feedback")
async def log_feedback(data: FeedbackData):
    """Log user feedback (like/dislike) into the main chat_logs table."""
    logger.info(f"FEEDBACK [{data.feedback}] - Session: {data.session_id}")
    
    try:
        update_feedback(data.session_id, data.message_text, data.feedback)
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Failed to update feedback: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("Starting MiMi API Server on port 3171...")
    print("Open http://localhost:3171 to test the chat UI")
    uvicorn.run(app, host="0.0.0.0", port=3171)