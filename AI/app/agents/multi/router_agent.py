import os
import uuid
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.prompt_loader import PromptLoader

# Import specialists
from app.agents.base_agent import build_base_agent as build_general_agent
from app.agents.multi.faq_agent import build_faq_agent

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


ss = InMemorySessionService()

# ---------- helper to run a sub‑agent once ----------
async def _run_subagent(agent: LlmAgent, text: str, session_id: str = None, app_name: str = "cs-app") -> str:
    if session_id is None:
        session_id = f"chat-{uuid.uuid4()}"

    user_id = "demo-user"

    s = await ss.create_session(app_name=app_name, user_id=user_id, session_id= session_id)

    runner = Runner(agent=agent, app_name=app_name, session_service=ss)

    msg = types.Content(role="user", parts=[types.Part(text=text)])
    async for ev in runner.run_async(user_id=s.user_id, session_id=s.id, new_message=msg):
        if ev.is_final_response() and ev.content and ev.content.parts:
            for p in ev.content.parts:
                if getattr(p, "text", None):
                    return p.text
    return "(no response)"


# ---------- tools the router can call ----------
async def faq_tool(question: str) -> str:
    """Answer all questions about products, branch info, and general FAQs."""
    return await _run_subagent(build_faq_agent(), question)


#async def fallback_tool(question: str) -> str:
#    """General CSR fallback (MiMi)."""
#    return await _run_subagent(build_general_agent(), question)


# ---------- build the router agent ----------
def build_router_agent() -> LlmAgent:
    instruction = PromptLoader().load("router.yaml")

    return LlmAgent(
        name="Router",
        model=GEMINI_MODEL,
        instruction=instruction,
        tools=[faq_tool],
        description="Routes all queries to the MizuMi FAQ Expert.",
    )