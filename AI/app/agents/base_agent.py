import os
import re
import json
import asyncio
import logging
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.tools.tools import retrieve_tool
from app.prompt_loader import PromptLoader

from app.agents.multi.faq_agent import build_faq_agent
from app.utils.logger import log_chat

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# ── Product image catalog ──────────────────────────────────────────────────────
# Pre-built lookup: clean_product_name (lowercase) → image_url
# Loaded once at startup from faq_data/<brand>/products.json so that we can
# resolve images for any product MiMi mentions, even if the RAG didn't happen
# to retrieve that product's chunk in this turn.
_catalog_cache: dict[str, dict] = {}  # brand → {name: image_url}

def _clean_name(raw: str) -> str:
    """Normalise a product name for fuzzy matching."""
    c = raw.split("(")[0].split(" - ")[0]
    c = re.sub(r'\s+SPF\d+\+?\s*PA\+{1,4}', '', c, flags=re.IGNORECASE)
    return c.strip().lower()

def _load_catalog(brand: str = "mizumi") -> dict:
    """Return {clean_name: image_url} for every product in products.json."""
    if brand in _catalog_cache:
        return _catalog_cache[brand]

    catalog: dict[str, str] = {}
    faq_dir = Path("faq_data") / brand
    products_file = faq_dir / "products.json"

    if products_file.exists():
        try:
            with open(products_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, val in data.items():
                if not isinstance(val, dict):
                    continue
                img = val.get("image_url")
                if not img:
                    continue
                # Index by canonical_name (the name MiMi uses in responses)
                canon = val.get("canonical_name", "")
                if canon:
                    catalog[_clean_name(canon)] = img
        except Exception as e:
            logging.warning(f"Could not load product catalog for {brand}: {e}")

    _catalog_cache[brand] = catalog
    logging.info(f"Product catalog loaded for '{brand}': {len(catalog)} entries")
    return catalog


# ── Cache agent at module level (built once, reused for all requests) ──────────
_base_agent: LlmAgent | None = None

def build_base_agent() -> LlmAgent:
    global _base_agent
    if _base_agent is None:
        instruction = PromptLoader().load("base.yaml")
        _base_agent = LlmAgent(
            name="MiMi",
            model=GEMINI_MODEL,
            instruction=instruction,
            description="Thai customer service agent with RAG (Gemini embeddings)",
            tools=[retrieve_tool],
        )
    return _base_agent

ss = InMemorySessionService()

#Main Chat Logic
#session_id parameter
async def chat_once(user_text: str, session_id: str, brand: str = "mizumi", store_id: str = "onsite_default", image: str | None = None) -> dict:
    try:
        agent = build_faq_agent(brand)


        user_id = "demo-user"

        # Reuse existing session if it already exists.
        # `InMemorySessionService.create_session` will overwrite an existing
        # session when given the same ID, which would erase the conversation
        # history.  Instead, try to fetch first and only create if missing.
        s = await ss.get_session(app_name="cs-app", user_id=user_id, session_id=session_id)
        if s is None:
            s = await ss.create_session(app_name="cs-app", user_id=user_id, session_id=session_id)

        runner = Runner(agent=agent, app_name="cs-app", session_service=ss)
        
        # Prepare parts for multimodal support
        parts = []
        if user_text:
            parts.append(types.Part(text=user_text))
        
        if image:
            # Handle base64 image (data:image/png;base64,xxxx or just xxxx)
            try:
                if "," in image:
                    mime_part, data_part = image.split(",", 1)
                    mime = mime_part.split(":")[1].split(";")[0]
                else:
                    mime = "image/jpeg" # fallback
                    data_part = image
                
                parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=data_part)))
                logging.info(f"Adding image part with mime: {mime}")
            except Exception as img_err:
                logging.error(f"Failed to parse image data: {img_err}")

        # Ensure we have at least one part for the runner
        if not parts:
            parts.append(types.Part(text="สวัสดีค่ะ"))

        msg = types.Content(role="user", parts=parts)

        found_products = []
        async for ev in runner.run_async(user_id=s.user_id, session_id=s.id, new_message=msg):
            # Capture products from tool responses in the current turn
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        result = part.function_response.response
                        if isinstance(result, dict) and "matches" in result:
                            for m in result["matches"]:
                                img_url = m.get("image_url")
                                if img_url:
                                    text = m.get("text", "")
                                    lines = text.split("\n")
                                    name = ""

                                    for line in lines:
                                        if line.startswith("Product: "):
                                            name = line.replace("Product: ", "").strip()
                                            break  # only need the product name

                                    if not name and lines:
                                        name = lines[0].strip()

                                    # ── Build a clean base name for matching ──────────
                                    clean = name
                                    clean = clean.split("(")[0]      # drop "(ฝาสีฟ้า)" etc
                                    clean = clean.split(" - ")[0]    # drop "- Shade: ..." etc
                                    # Drop SPF/PA specs like "SPF50+ PA++++"
                                    clean = re.sub(r'\s+SPF\d+\+?\s*PA\+{1,4}', '', clean, flags=re.IGNORECASE)
                                    base_name = clean.strip().lower()

                                    # Also build a no-brand version for cases where
                                    # MiMi writes the name without the "MizuMi" prefix
                                    short_name = re.sub(r'^mizumi\s+', '', base_name).strip()
                                    
                                    # Check if we already have this product by image OR normalized name
                                    if not any(p["image"] == img_url or p["_base"] == base_name for p in found_products):
                                        found_products.append({
                                            "name": name,
                                            "image": img_url,
                                            "_base": base_name,    # e.g. "mizumi uv water serum"
                                            "_short": short_name,  # e.g. "uv water serum"
                                        })
            
            if ev.is_final_response():
                # Safely extract the agent's response
                text_content = ""
                if ev.content and ev.content.parts and len(ev.content.parts) > 0:
                    text_content = ev.content.parts[0].text

                # Extract token usage
                token_usage = {}
                if hasattr(ev, "usage_metadata") and ev.usage_metadata:
                    try:
                        token_usage = ev.usage_metadata.model_dump()
                    except:
                        token_usage = {"total_token_count": getattr(ev.usage_metadata, "total_token_count", 0)}

                # ── Smart image filtering ─────────────────────────────────────
                # Only show images for products that MiMi actually mentioned in her response. We compare each candidate product's base name
                # against the response text (case-insensitive) so accidental RAG hits from unrelated chunks don't produce stray cards.
                response_lower = text_content.lower() if text_content else ""

                mentioned_products = []
                # Pre-load the catalog for fallback matching
                catalog = _load_catalog(brand)

                # 1. Try matching from found_products (those retrieved by tools in this turn)
                for p in found_products:
                    base  = p.get("_base", "")
                    short = p.get("_short", "")
                    matched = (
                        (base  and base  in response_lower) or
                        (short and len(short) >= 8 and short in response_lower)
                    )
                    if matched:
                        mentioned_products.append(p)

                # 2. Fallback: If MiMi mentioned products that weren't in tool results (e.g. from her prompt memory)
                # search the catalog for matches in her response text
                existing_bases = {p["_base"] for p in mentioned_products}
                for clean_name, img_url in catalog.items():
                    if clean_name in response_lower and clean_name not in existing_bases:
                        # Find a display name (try to find uppercase version in the text or use catalog key)
                        display_name = clean_name.title()
                        mentioned_products.append({
                            "name": display_name,
                            "image": img_url,
                            "_base": clean_name
                        })

                # Final cleaning and hard cap
                final_products = []
                seen_images = set()
                for p in mentioned_products:
                    img = p.get("image")
                    if img and img not in seen_images:
                        product_data = {k: v for k, v in p.items() if not k.startswith("_")}
                        final_products.append(product_data)
                        seen_images.add(img)
                    if len(final_products) >= 5:
                        break

                all_images = [p["image"] for p in final_products]

                # Extract bubble options
                bubble_options = []
                bubble_matches = re.findall(r'\[BUBBLE:\s*(.*?)\]', text_content)
                if bubble_matches:
                    bubble_options = [b.strip() for b in bubble_matches]
                    # Remove the bubble text from the final text_content
                    text_content = re.sub(r'\[BUBBLE:\s*.*?\]', '', text_content).strip()

                # ── Save Logs ──────────────────────────────────────────────────
                try:
                    log_chat(
                        session_id=session_id,
                        user_query=user_text,
                        bot_response=text_content,
                        tokens=token_usage,
                        brand=brand,
                        store_id=store_id,
                        metadata={
                            "product_count": len(final_products),
                            "has_bubbles": len(bubble_options) > 0
                        }
                    )
                except Exception as log_err:
                    logging.error(f"Logging failed: {log_err}")

                return {
                    "text": text_content,
                    "products": final_products,
                    "all_images": all_images,
                    "image_url": all_images[0] if all_images else None,
                    "usage": token_usage,
                    "bubble_options": bubble_options
                }

        return {"text": "(no response received)", "image_url": None, "all_images": [], "products": [], "usage": {}, "bubble_options": []}

    except Exception as e:
        logging.error(f"Error in chat_once: {e}")

        # Return a user-friendly error message.
        return f"Error: {str(e)}"

async def get_history(session_id: str) -> list[dict]:
    """Return a list of role/text dicts for the specified conversation."""
    try:
        s = await ss.get_session(app_name="cs-app", user_id="demo-user", session_id=session_id)
        if not s:
            return []
        msgs = []
        for ev in s.events:
            if ev.content and ev.content.parts:
                for p in ev.content.parts:
                    if getattr(p, "text", None):
                        clean_text = p.text
                        if p.role == "model":
                            clean_text = re.sub(r'\[BUBBLE:\s*.*?\]', '', clean_text).strip()
                        msgs.append({"role": p.role, "text": clean_text})
        return msgs
    except Exception:
        return []