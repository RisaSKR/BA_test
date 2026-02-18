import os
import uuid 
import asyncio
import logging
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.tools.tools import retrieve_tool
from app.prompt_loader import PromptLoader

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

def build_base_agent():
    instruction = PromptLoader().load("base.yaml")
    return LlmAgent(
        name="MiMi",
        model=GEMINI_MODEL,
        instruction=instruction,
        description="Thai customer service agent with RAG (Gemini embeddings)",
        tools=[retrieve_tool],
    )

ss = InMemorySessionService()

#Main Chat Logic
#session_id parameter
async def chat_once(user_text: str, session_id: str) -> dict:
    try:
        agent = build_base_agent()


        user_id = "demo-user"

        s = await ss.create_session(app_name="cs-app", user_id= user_id, session_id= session_id)

        runner = Runner(agent=agent, app_name="cs-app", session_service=ss)
        msg = types.Content(role="user", parts=[types.Part(text=user_text)])

        async for ev in runner.run_async(user_id=s.user_id, session_id=s.id, new_message=msg):
            if ev.is_final_response():
                # Safely extract the agent's response
                text_content = ""
                if ev.content and ev.content.parts and len(ev.content.parts) > 0:
                    text_content = ev.content.parts[0].text
                
                # Extract token usage if available
                token_usage = {}
                if hasattr(ev, "usage_metadata") and ev.usage_metadata:
                    # Convert object to dict if necessary, or just extract fields
                    # The raw log shows keys: candidates_token_count, prompt_token_count, total_token_count
                    if isinstance(ev.usage_metadata, dict):
                        token_usage = ev.usage_metadata
                    else:
                        # existing SDK object? try .model_dump() or accessing attributes
                        try:
                            token_usage = ev.usage_metadata.model_dump()
                        except:
                            # Fallback: manually copy known fields
                            token_usage = {
                                "total_token_count": getattr(ev.usage_metadata, "total_token_count", 0),
                                "prompt_token_count": getattr(ev.usage_metadata, "prompt_token_count", 0),
                                "candidates_token_count": getattr(ev.usage_metadata, "candidates_token_count", 0)
                            }

                return {
                    "text": text_content,
                    "usage": token_usage
                }
                
        return {"text": "(no response received)", "usage": {}}

# If any error (an "Exception") occurs in the 'try' block, the code jumps here.        
    except Exception as e:
        logging.error(f"Error in chat_once: {e}")

        # Return a user-friendly error message.
        return f"Error: {str(e)}"