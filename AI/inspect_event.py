
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.agents.base_agent import build_base_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def inspect():
    agent = build_base_agent()
    ss = InMemorySessionService()
    await ss.create_session(app_name="cs-app", user_id="test", session_id="test")
    runner = Runner(agent=agent, app_name="cs-app", session_service=ss)
    msg = types.Content(role="user", parts=[types.Part(text="MizuMi UV Water Serum")])
    
    async for ev in runner.run_async(user_id="test", session_id="test", new_message=msg):
        print(f"Event type: {type(ev)}")
        print(f"Attributes: {[a for a in dir(ev) if not a.startswith('_')]}")
        if hasattr(ev, 'content'):
            print(f"Content: {ev.content}")
        # If it's a tool call event
        try:
            if hasattr(ev, 'tool_call'):
                 print(f"Tool Call: {ev.tool_call}")
        except: pass

if __name__ == "__main__":
    asyncio.run(inspect())
