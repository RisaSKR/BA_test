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

def _get_display_name(raw: str) -> str:
    """Gets a nice display name by removing brackets and SPF specs, but keeping case."""
    c = raw.split("(")[0].split(" - ")[0]
    c = re.sub(r'\s+SPF\d+\+?\s*PA\+{1,4}', '', c, flags=re.IGNORECASE)
    return c.strip()

def _load_catalog(brand: str = "mizumi") -> dict:
    """Return {normalized_name: {"image": url, "name": display_name}} for every product."""
    if brand in _catalog_cache:
        return _catalog_cache[brand]

    catalog: dict[str, dict] = {}
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
                
                canon = val.get("canonical_name", "")
                if canon:
                    display = _get_display_name(canon)
                    catalog[_clean_name(canon)] = {
                        "name": display,
                        "image": img,
                        "variant": val.get("variant", ""),
                        "information_context": val.get("information_context", "")
                    }
            
            # Also integrate aliases into the image-detection catalog
            # this ensures that if MiMi mentions an alias (e.g. from aliases.json), 
            # we can still show the product image.
            aliases_file = faq_dir / "aliases.json"
            if aliases_file.exists():
                with open(aliases_file, "r", encoding="utf-8") as f:
                    aliases_data = json.load(f)
                for alias, code in aliases_data.items():
                    p_info = data.get(code)
                    if p_info and p_info.get("image_url"):
                        disp = _get_display_name(p_info.get("canonical_name", alias))
                        catalog[alias.lower().strip()] = {
                            "name": disp,
                            "image": p_info["image_url"],
                            "variant": p_info.get("variant", ""),
                            "information_context": p_info.get("information_context", "")
                        }
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

# ── Shared helpers for response processing ────────────────────────────────────

def _extract_products_from_event(ev, found_products: list) -> bool:
    """Update found_products list from a runner event. Returns True if a tool call was detected."""
    if not ev.content or not ev.content.parts:
        return False
    
    detected = False
    for part in ev.content.parts:
        # Check for start of tool call
        if hasattr(part, "function_call") and part.function_call:
            detected = True
        
        # Check for tool call response
        if hasattr(part, "function_response") and part.function_response:
            detected = True
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
                                break

                        if not name and lines:
                            name = lines[0].strip()

                        clean = name
                        clean = clean.split("(")[0]
                        clean = clean.split(" - ")[0]
                        clean = re.sub(r'\s+SPF\d+\+?\s*PA\+{1,4}', '', clean, flags=re.IGNORECASE)
                        base_name = clean.strip().lower()
                        short_name = re.sub(r'^mizumi\s+', '', base_name).strip()
                        
                        if not any(p["image"] == img_url or p["_base"] == base_name for p in found_products):
                            found_products.append({
                                "name": _get_display_name(name),
                                "image": img_url,
                                "_base": base_name,
                                "_short": short_name,
                            })
    return detected

def _process_metadata(ev, text_content: str, found_products: list, brand: str) -> dict:
    """Extract products, bubble options, and token usage from the final event."""
    # Extract token usage
    token_usage = {}
    if hasattr(ev, "usage_metadata") and ev.usage_metadata:
        try:
            token_usage = ev.usage_metadata.model_dump()
        except:
            token_usage = {"total_token_count": getattr(ev.usage_metadata, "total_token_count", 0)}

    # Extract localized card descriptions from text tags like [DESC: Name | Text] or [DESC: Name : Text]
    # This allows the trilingual bot to translate the info_context on the fly.
    card_descriptions = {}
    # Handles both [DESC: Name | Text] and [DESC: Name : Text] with optional spaces
    desc_matches = re.findall(r'\[DESC:\s*(.*?)\s*[\|:]\s*(.*?)\]', text_content, re.IGNORECASE)
    for name, desc in desc_matches:
        card_descriptions[name.strip().lower()] = desc.strip()

    def get_localized_desc(target_name: str, fallback: str) -> str:
        target_lower = target_name.lower().strip()
        # Direct match
        if target_lower in card_descriptions:
            return card_descriptions[target_lower]
        # Partial match: if tag name is part of target name or vice versa
        for tag_name, tag_desc in card_descriptions.items():
            if tag_name and (tag_name in target_lower or target_lower in tag_name):
                return tag_desc
        return fallback

    # Smart image filtering & Ordering
    response_lower = text_content.lower() if text_content else ""
    mentioned_products = []
    catalog = _load_catalog(brand)

    for p in found_products:
        base  = p.get("_base", "")
        short = p.get("_short", "")
        pos = 999999
        found = False
        
        if base and base in response_lower:
            pos = min(pos, response_lower.find(base))
            found = True
        if short and len(short) >= 8 and short in response_lower:
            pos = min(pos, response_lower.find(short))
            found = True
            
        if found:
            p["_pos"] = pos
            # Enrich with detailed metadata from our catalog lookup
            if base in catalog:
                p["variant"] = catalog[base].get("variant", "")
                # Preference: 1. AI provided localized desc, 2. Catalog desc
                p["information_context"] = get_localized_desc(base, catalog[base].get("information_context", ""))
            mentioned_products.append(p)

    existing_bases = {p["_base"] for p in mentioned_products}
    for clean_name, info in catalog.items():
        if clean_name in response_lower and clean_name not in existing_bases:
            pos = response_lower.find(clean_name)
            mentioned_products.append({
                "name": info["name"],
                "image": info["image"],
                "variant": info.get("variant", ""),
                "information_context": get_localized_desc(clean_name, info.get("information_context", "")),
                "_base": clean_name,
                "_pos": pos
            })

    mentioned_products.sort(key=lambda x: x.get("_pos", 999999))

    final_products = []
    seen_images = set()
    for p in mentioned_products:
        img = p.get("image")
        if img and img not in seen_images:
            product_data = {k: v for k, v in p.items() if not k.startswith("_")}
            final_products.append(product_data)
            seen_images.add(img)
        if len(final_products) >= 10:
            break

    # Extract bubble options
    bubble_options = []
    bubble_matches = re.findall(r'\[BUBBLE:\s*(.*?)\]', text_content, re.IGNORECASE)
    if bubble_matches:
        bubble_options = [b.strip() for b in bubble_matches]
    
    # Processed text (bubbles and DESC tags removed)
    clean_text = re.sub(r'\[BUBBLE:\s*.*?\]', '', text_content, flags=re.IGNORECASE)
    clean_text = re.sub(r'\[DESC:\s*.*?\]', '', clean_text, flags=re.IGNORECASE).strip()

    return {
        "text": clean_text,
        "products": final_products,
        "bubble_options": bubble_options,
        "usage": token_usage,
        "all_images": [p["image"] for p in final_products]
    }

# ── Main Chat Logic ────────────────────────────────────────────────────────────

async def chat_stream(user_text: str, session_id: str, brand: str = "mizumi", store_id: str = "onsite_default", language: str | None = "TH", image: str | None = None):
    """Streaming version of chat_once. Yields chunks of text and final metadata."""
    try:
        agent = build_faq_agent(brand)
        user_id = "demo-user"

        s = await ss.get_session(app_name="cs-app", user_id=user_id, session_id=session_id)
        if s is None:
            s = await ss.create_session(app_name="cs-app", user_id=user_id, session_id=session_id)

        runner = Runner(agent=agent, app_name="cs-app", session_service=ss)
        
        parts = []
        if user_text:
            # Inject language preference if provided
            if language:
                parts.append(types.Part(text=f"[Preferred Language: {language}]\n{user_text}"))
            else:
                parts.append(types.Part(text=user_text))
        
        if image:
            try:
                if "," in image:
                    mime_part, data_part = image.split(",", 1)
                    mime = mime_part.split(":")[1].split(";")[0]
                else:
                    mime = "image/jpeg"
                    data_part = image
                parts.append(types.Part(inline_data=types.Blob(mime_type=mime, data=data_part)))
            except Exception as img_err:
                logging.error(f"Failed to parse image data: {img_err}")

        if not parts:
            parts.append(types.Part(text="สวัสดีค่ะ"))
        msg = types.Content(role="user", parts=parts)

        found_products = []
        full_text = ""
        last_yielded_len = 0
        
        async for ev in runner.run_async(user_id=s.user_id, session_id=s.id, new_message=msg):
            # 1. Extract products/tools
            has_tool_activity = _extract_products_from_event(ev, found_products)
            if has_tool_activity and not full_text:
                status_text = "MiMi กำลังค้นหาข้อมูลให้นะคะ..."
                if language == "EN": status_text = "MiMi is searching for info for you..."
                elif language == "中文": status_text = "MiMi 正在为您搜索信息..."
                yield {"type": "status", "text": status_text}

            # 2. Extract text chunks
            if ev.content and ev.content.parts and len(ev.content.parts) > 0:
                text_part = ev.content.parts[0].text
                if text_part and len(text_part) > last_yielded_len:
                    chunk = text_part[last_yielded_len:]
                    # If this chunk is just a dot or space at the start, skip it
                    if not full_text and chunk.strip() in ("", ".", "\n"):
                        last_yielded_len = len(text_part)
                        continue

                    last_yielded_len = len(text_part)
                    full_text = text_part
                    yield {"type": "content", "text": chunk}

            # 3. Handle final response
            if ev.is_final_response():
                # Note: full_text should be the same as ev.content.parts[0].text
                meta = _process_metadata(ev, full_text, found_products, brand)
                
                # Save Logs
                try:
                    log_chat(
                        session_id=session_id,
                        user_query=user_text,
                        bot_response=meta["text"],
                        tokens=meta["usage"],
                        brand=brand,
                        store_id=store_id,
                        metadata={
                            "product_count": len(meta["products"]),
                            "has_bubbles": len(meta["bubble_options"]) > 0,
                            "is_stream": True
                        }
                    )
                except Exception as log_err:
                    logging.error(f"Logging failed: {log_err}")

                yield {
                    "type": "metadata",
                    "text": meta["text"],
                    "products": meta["products"],
                    "all_images": meta["all_images"],
                    "image_url": meta["all_images"][0] if meta["all_images"] else None,
                    "usage": meta["usage"],
                    "bubble_options": meta["bubble_options"]
                }
                return

    except Exception as e:
        logging.error(f"Error in chat_stream: {e}")
        yield {"type": "error", "text": str(e)}

async def chat_once(user_text: str, session_id: str, brand: str = "mizumi", store_id: str = "onsite_default", language: str | None = "TH", image: str | None = None) -> dict:
    """Non-streaming version of chat. Collects chunks and returns final result."""
    full_response = {
        "text": "",
        "products": [],
        "all_images": [],
        "image_url": None,
        "usage": {},
        "bubble_options": []
    }
    
    async for chunk in chat_stream(user_text, session_id, brand, store_id, language, image):
        if chunk["type"] == "metadata":
            full_response.update(chunk)
            if "type" in full_response: del full_response["type"]
        elif chunk["type"] == "error":
            return {"text": f"Error: {chunk['text']}", "products": [], "all_images": [], "usage": {}}
            
    if not full_response["text"]:
        full_response["text"] = "(no response received)"
        
    return full_response

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