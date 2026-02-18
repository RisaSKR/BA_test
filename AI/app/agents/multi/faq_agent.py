import os
from functools import partial
from google.adk.agents import LlmAgent
from app.prompt_loader import PromptLoader
from app.tools.faq_tools import retrieve_faq_tool

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

def build_faq_agent(brand: str = "mizumi") -> LlmAgent:
    """Builds an FAQ agent for a specific brand."""
    
    # Load brand-specific instruction
    instruction = PromptLoader().load(f"brands/{brand}/instruction.yaml")
    
    # Create a brand-specific version of the retrieval tool
    brand_tool = partial(retrieve_faq_tool, brand=brand)
    brand_tool.__name__ = "retrieve_tool" # Keep name consistent for the LLM
    brand_tool.__doc__ = f"Retrieves product and FAQ information for {brand}."

    return LlmAgent(
        name=f"{brand.capitalize()}Expert",
        model=GEMINI_MODEL,
        instruction=instruction,
        tools=[brand_tool],
        description=f"Expert for {brand} products and FAQs.",
    )
