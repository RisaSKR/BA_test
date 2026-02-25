import os
from functools import partial
from google.adk.agents import LlmAgent
from app.prompt_loader import PromptLoader
from app.tools.faq_tools import retrieve_faq_tool

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# ── Cache agents per brand (built once, reused for all requests) ───────────────
_faq_agents: dict[str, LlmAgent] = {}

def build_faq_agent(brand: str = "mizumi") -> LlmAgent:
    """Builds (or returns cached) FAQ agent for a specific brand."""
    if brand in _faq_agents:
        return _faq_agents[brand]

    # Load brand-specific instruction
    instruction = PromptLoader().load(f"brands/{brand}/instruction.yaml")
    
    # Create a brand-specific version of the retrieval tool
    brand_tool = partial(retrieve_faq_tool, brand=brand)
    brand_tool.__name__ = "retrieve_tool" # Keep name consistent for the LLM
    brand_tool.__doc__ = f"Retrieves product and FAQ information for {brand}."

    agent = LlmAgent(
        name=f"{brand.capitalize()}Expert",
        model=GEMINI_MODEL,
        instruction=instruction,
        tools=[brand_tool],
        description=f"Expert for {brand} products and FAQs.",
    )
    _faq_agents[brand] = agent
    return agent
