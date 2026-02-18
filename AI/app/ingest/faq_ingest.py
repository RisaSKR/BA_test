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

def format_product_text(p: dict) -> str:
    lines = []
    lines.append(f"Product: {p.get('canonical_name', 'Unknown')} ({p.get('variant', '')})")
    lines.append(f"Category: {p.get('category', 'N/A')}")
    if p.get("aliases"):
        lines.append(f"Aliases/Search Terms: {', '.join(p['aliases'])}")
    
    facts = p.get("facts", {})
    if facts:
        fact_str = ", ".join([f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in facts.items()])
        lines.append(f"Key Facts: {fact_str}")
    
    suitability = p.get("suitability", {})
    if suitability:
        skin_types = ", ".join(suitability.get("skin_types", []))
        lines.append(f"Suitable for: {skin_types} skin.")
        if "age_min_months" in suitability:
            lines.append(f"Age: {suitability.get('age_min_months')} months+")
        if "pregnancy_safe" in suitability:
            lines.append(f"Pregnancy Safe: {'Yes' if suitability.get('pregnancy_safe') else 'No'}")
        if "vegan" in suitability:
            lines.append(f"Vegan: {'Yes' if suitability.get('vegan') else 'No'}")
        if "coral_safe" in suitability:
            lines.append(f"Coral Safe: {'Yes' if suitability.get('coral_safe') else 'No'}")

    faq = p.get("faq", {})
    if faq:
        lines.append("Frequently Asked Questions:")
        for q, a in faq.items():
            lines.append(f"- {q.replace('_', ' ').capitalize()}: {a}")
    
    ingredients = p.get("ingredients", {})
    if ingredients:
        if "list" in ingredients:
            lines.append(f"Ingredients: {', '.join(ingredients['list'])}")
        elif "inci_raw" in ingredients:
            lines.append(f"Ingredients: {ingredients['inci_raw']}")
    
    return "\n".join(lines)

def read_json_products(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    docs = []
    if isinstance(data, list):
        for item in data:
            text = format_product_text(item)
            docs.append(Document(page_content=text, metadata={"source": path.name, "product_code": item.get("product_code")}))
    elif isinstance(data, dict):
        # check if it's a product mapping (keys are codes, values are dicts)
        has_sub_dicts = any(isinstance(v, dict) for v in data.values())
        if has_sub_dicts:
            for key, val in data.items():
                if isinstance(val, dict):
                    # If it looks like a product (has canonical_name or variant), format it nicely
                    if "canonical_name" in val or "variant" in val:
                        if "product_code" not in val:
                            val["product_code"] = key
                        text = format_product_text(val)
                        docs.append(Document(page_content=text, metadata={"source": path.name, "product_code": key}))
                    else:
                        # Just a generic nested dict (like faqs.json)
                        text = f"{key}:\n{json.dumps(val, ensure_ascii=False, indent=2)}"
                        docs.append(Document(page_content=text, metadata={"source": path.name}))
                else:
                    # Simple key-value (like aliases.json maybe)
                    text = f"{key}: {val}"
                    docs.append(Document(page_content=text, metadata={"source": path.name}))
        else:
            # Single flat dictionary
            text = format_product_text(data)
            # Check if this worked or returned "Unknown"
            if "Unknown" in text and len(data) > 3: # heuristics
                 text = json.dumps(data, ensure_ascii=False, indent=2)
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

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
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
