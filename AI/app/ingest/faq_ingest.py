from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from tqdm import tqdm
import pandas as pd
import json
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.embeddings_gemini import GeminiEmbeddings

load_dotenv()
DATA_DIR = Path("faq_data")
INDEX_BASE_DIR = Path("index")

def read_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for p in reader.pages:
        try:
            parts.append(p.extract_text() or "")
        except Exception:
            parts.append("")
    return "\n".join(parts)

def read_xlsx_text(path: Path) -> list:
    df = pd.read_excel(path)
    docs = []
    # Assume columns: 'question', 'answer'
    if 'question' in df.columns and 'answer' in df.columns:
        for _, row in df.iterrows():
            text = f"Q: {row['question']}\nA: {row['answer']}"
            docs.append(Document(page_content=text, metadata={"source": path.name}))
    else:
        # If only one column, treat each cell as a passage
        for col in df.columns:
            for val in df[col].dropna():
                docs.append(Document(page_content=str(val), metadata={"source": path.name}))
    return docs

def format_product_text(p: dict, variant: dict = None) -> str:
    lines = []
    base_name = p.get('canonical_name', 'Unknown')
    if variant:
        lines.append(f"Product: {base_name} - Shade: {variant.get('shade_name', 'N/A')}")
        if variant.get('variant_name'):
            lines.append(f"Variant Name: {variant['variant_name']}")
        if variant.get('shade_description'):
            lines.append(f"Shade Description: {variant['shade_description']}")
    else:
        var = p.get('variant')
        if var:
            if isinstance(var, dict):
                # Extract a readable name if it's a dict, e.g. from 'code' or 'name'
                v_str = var.get('variant_name') or var.get('name') or var.get('code') or ""
                if v_str:
                    lines.append(f"Product: {base_name} ({v_str})")
                else:
                    lines.append(f"Product: {base_name}")
            else:
                lines.append(f"Product: {base_name} ({var})")
        else:
            lines.append(f"Product: {base_name}")
    
    lines.append(f"Category: {p.get('category', 'N/A')}")
    
    code = variant.get('variant_code') if variant else (p.get('product_code') or p.get('code'))
    if code:
        lines.append(f"Product Code: {code}")
        
    if p.get("thai_name"):
        lines.append(f"Thai Name: {p['thai_name']}")
    if p.get("short_name"):
        lines.append(f"Short Name: {p['short_name']}")
    if p.get("aliases"):
        lines.append(f"Aliases/Search Terms: {', '.join(p['aliases'])}")
    
    facts = p.get("facts", {})
    if facts:
        fact_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in facts.items()])
        lines.append(f"Key Facts: {fact_str}")
    
    tech = p.get("key_technology", {})
    if tech:
        tech_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in tech.items()])
        lines.append(f"Key Technology: {tech_str}")

    benefits = p.get("skin_benefits", {})
    if benefits:
        benefit_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in benefits.items()])
        lines.append(f"Skin Benefits: {benefit_str}")

    suitability = p.get("suitability", {})
    if suitability:
        skin_types = ", ".join(suitability.get("skin_types", []))
        lines.append(f"Suitable for: {skin_types} skin.")
        if "age_min_years" in suitability:
            lines.append(f"Age: {suitability.get('age_min_years')} years+")
        if "pregnancy_safe" in suitability:
            lines.append(f"Pregnancy Safe: {'Yes' if suitability.get('pregnancy_safe') else 'No'}")
        if "vegan" in suitability:
            lines.append(f"Vegan: {'Yes' if suitability.get('vegan') else 'No'}")
        
        # Corrected field access based on context
        if p.get("vegan"): lines.append("Vegan: Yes")
        if p.get("coral_safe"): lines.append("Coral Safe: Yes")

    usage = p.get("usage", {})
    if usage:
        usage_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in usage.items()])
        lines.append(f"Usage Info: {usage_str}")

    usage_method = p.get("usage_method", {})
    if usage_method:
        if isinstance(usage_method, dict):
            summary = usage_method.get("instruction_summary")
            if summary:
                lines.append(f"Usage Instruction: {summary}")
            duration = usage_method.get("mask_duration_minutes")
            if duration:
                lines.append(f"Mask Duration: {duration} minutes")
            steps = usage_method.get("steps")
            if steps and isinstance(steps, list):
                lines.append(f"Usage Steps: {' -> '.join(steps)}")
        else:
            lines.append(f"Usage Method: {usage_method}")

    info_ctx = p.get("information_context", "")
    if info_ctx:
        lines.append(f"Description: {info_ctx}")

    faq = p.get("faq", {})
    if faq:
        lines.append("Frequently Asked Questions:")
        for q, a in faq.items():
            lines.append(f"- {q.replace('_', ' ').capitalize()}: {a}")
    
    ingredients = p.get("ingredients", {})
    if ingredients:
        if isinstance(ingredients, list):
            lines.append(f"Ingredients: {', '.join(ingredients)}")
        elif isinstance(ingredients, dict):
            if "list" in ingredients:
                lines.append(f"Ingredients: {', '.join(ingredients['list'])}")
            elif "inci_raw" in ingredients:
                lines.append(f"Ingredients: {ingredients['inci_raw']}")
    
    return "\n".join(lines)

def read_json_products(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    docs = []
    
    def process_item(key, val, source):
        # Handle variants if they exist
        variants = val.get("variants", [])
        if variants:
            for v in variants:
                text = format_product_text(val, variant=v)
                # Use variant image_url if available, else fallback to product image_url
                img_url = v.get("image_url") or val.get("image_url")
                docs.append(Document(
                    page_content=text, 
                    metadata={
                        "source": source, 
                        "product_code": v.get("variant_code") or key, 
                        "image_url": img_url
                    }
                ))
        else:
            text = format_product_text(val)
            docs.append(Document(
                page_content=text, 
                metadata={
                    "source": source, 
                    "product_code": val.get("product_code") or key, 
                    "image_url": val.get("image_url")
                }
            ))

    if isinstance(data, list):
        for item in data:
            process_item(item.get("product_code", "unknown"), item, path.name)
    elif isinstance(data, dict):
        # brand or meta keys can be skipped or added as global facts
        for key, val in data.items():
            if key == "brand":
                continue 

            if key == "brand_ambassadors" and isinstance(val, list):
                # Special handling for ambassadors
                for ambassador in val:
                    name = ambassador.get("ambassador", "Unknown Ambassador")
                    # Make the first line the name for better matching in base_agent.py
                    text = f"{name}\n"
                    text += f"Role: Brand Ambassador\n"
                    text += f"Series: {', '.join(ambassador.get('series', []))}\n"
                    if ambassador.get("description"):
                        text += f"Description: {ambassador['description']}\n"
                    
                    # Extract any image url either as 'image_url' or a custom 'xxx_image_url'
                    img_url = ambassador.get("image_url")
                    if not img_url:
                        for k, v in ambassador.items():
                            if k.endswith("_image_url") and isinstance(v, str):
                                img_url = v
                                break
                    
                    docs.append(Document(
                        page_content=text, 
                        metadata={
                            "source": path.name, 
                            "image_url": img_url
                        }
                    ))
                continue

            if isinstance(val, dict):
                if "canonical_name" in val or "variant" in val or "product_code" in val:
                    process_item(key, val, path.name)
                elif key == "best_seller_recommendations":
                    # Special handling for best seller recommendations
                    title = val.get("title", "Best Sellers")
                    for cat in val.get("categories", []):
                        cat_text = f"{title}\nCategory: {cat.get('category_name')}\n"
                        cat_text += json.dumps(cat, ensure_ascii=False, indent=2)
                        docs.append(Document(page_content=cat_text, metadata={"source": path.name}))
                else:
                    # Generic dict indexing
                    text = f"{key}:\n{json.dumps(val, ensure_ascii=False, indent=2)}"
                    img_url = val.get("image_url")
                    docs.append(Document(page_content=text, metadata={"source": path.name, "image_url": img_url}))
            elif not isinstance(val, list):
                 # Simple key-value Pair
                 text = f"{key}: {val}"
                 docs.append(Document(page_content=text, metadata={"source": path.name}))
    
    return docs

def process_brand(brand_path: Path, emb: GeminiEmbeddings):
    brand_name = brand_path.name
    print(f"\n--- Processing Brand: {brand_name} ---")
    
    docs = []
    # Use rglob to support multi-folder structure automatically
    pdfs = sorted(brand_path.rglob("*.pdf"))
    xlsxs = sorted(brand_path.rglob("*.xlsx"))
    jsons = sorted(brand_path.rglob("*.json"))
    txts = sorted(brand_path.rglob("*.txt"))
    mds = sorted(brand_path.rglob("*.md"))
    
    if not (pdfs or xlsxs or jsons or txts or mds):
        print(f" No supported files found in {brand_path}. Skipping.")
        return

    for pdf in pdfs:
        print(f" Reading PDF: {pdf.relative_to(brand_path)}")
        text = read_pdf_text(pdf)
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": pdf.name, "brand": brand_name}))

    for txt in txts:
        print(f" Reading TXT: {txt.relative_to(brand_path)}")
        with open(txt, "r", encoding="utf-8") as f:
            text = f.read()
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": txt.name, "brand": brand_name}))

    for md in mds:
        print(f" Reading MD: {md.relative_to(brand_path)}")
        with open(md, "r", encoding="utf-8") as f:
            text = f.read()
        if text.strip():
            docs.append(Document(page_content=text, metadata={"source": md.name, "brand": brand_name}))

    for xlsx in xlsxs:
        print(f" Reading XLSX: {xlsx.relative_to(brand_path)}")
        xlsx_docs = read_xlsx_text(xlsx)
        for d in xlsx_docs:
            d.metadata["brand"] = brand_name
            d.metadata["source"] = xlsx.name
        docs.extend(xlsx_docs)

    for j in jsons:
        print(f" Reading JSON: {j.relative_to(brand_path)}")
        brand_docs = read_json_products(j)
        for d in brand_docs:
            d.metadata["brand"] = brand_name
        docs.extend(brand_docs)


    if not docs:
        print(f" No text extracted for {brand_name}.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=500)
    chunks = splitter.split_documents(docs)
    print(f"[{brand_name}] Chunked into {len(chunks)} passages.")

    print(f"[{brand_name}] Embedding chunks...")
    index = FAISS.from_documents(chunks, embedding=emb)

    brand_index_dir = INDEX_BASE_DIR / f"{brand_name}_faiss"
    brand_index_dir.mkdir(parents=True, exist_ok=True)
    index.save_local(str(brand_index_dir))
    print(f"[{brand_name}] Built FAISS index -> {brand_index_dir}")

def main():
    if not DATA_DIR.exists():
        print(f"Data directory {DATA_DIR} not found.")
        return

    emb = GeminiEmbeddings()
    
    # Get all subdirectories in faq_data
    brands = [d for d in DATA_DIR.iterdir() if d.is_dir()]
    
    if not brands:
        print("No brand subdirectories found in faq_data.")
        # Fallback to root if any files exist?
        if list(DATA_DIR.glob("*.*")):
            print("Found files in root of faq_data. Processing as 'default' brand.")
            process_brand(DATA_DIR, emb)
        return

    for brand_dir in brands:
        process_brand(brand_dir, emb)

if __name__ == "__main__":
    main()
