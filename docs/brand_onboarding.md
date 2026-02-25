# 🚀 MiMi AI: Brand Onboarding Guide

This guide details the process of adding a new brand persona and its knowledge base to the MiMi AI engine.

## 📋 Steps to Onboard a New Brand

### 1. Define the Brand Persona
Create a directory for the brand and add an `instruction.yaml` file to define its behavior.

- **Path**: `AI/app/prompts/brands/[brand_name]/instruction.yaml`
- **Goal**: Define the "Voice" of the brand.
- **Key Sections**:
    - `persona`: Name (e.g., MiMi), tone (warm, professional), and background.
    - `policies`: Step-by-step rules (e.g., language rules, greeting protocols).
    - `guardrails`: What the bot *cannot* do or say.
    - `behavior_rules`: Specialized logic (e.g., how to handle recommendations or comparisons).

> [!TIP]
> Use the existing `mizumi/instruction.yaml` as a template. Maintain the "ULTRA BREVITY" style for cleaner chat interactions.

### 2. Prepare the Knowledge Base
Collect the brand's documentation (FAQs, product details, manuals) in supported formats.

- **Path**: `AI/faq_data/[brand_name]/`
- **Supported Formats**: PDF, XLSX, CSV, TXT, MD.
- **Organization**: Group files logically by category (e.g., `products.json`, `general_faqs.xlsx`).

### 3. Build the Search Index (Ingestion)
Convert the raw documentation into a searchable vector index.

Run the ingestion script from the `AI` directory:
```bash
python app/ingest/faq_ingest.py
```
This script will:
1. Scan the `faq_data` folder.
2. Generate embeddings using Google Gemini.
3. Create a FAISS index in `AI/index/[brand_name]/`.

### 4. Integration & Routing
Update the `Router Agent` if the new brand requires special routing logic.

- **File**: `AI/app/agents/multi/router_agent.py`
- **Process**: Ensure the router is aware of when to hand off to the new brand's `FAQAgent`.

---

## 🏗️ Brand Folder Structure Template

```text
AI/
├── app/
│   └── prompts/
│       └── brands/
│           └── brand_x/
│               └── instruction.yaml  <-- Bot Personality
├── faq_data/
│   └── brand_x/
│       ├── products.xlsx             <-- Knowledge Source
│       └── policies.pdf              <-- Knowledge Source
└── index/
    └── brand_x/                      <-- Generated Search Index (DO NOT EDIT)
```

## ✅ Launch Checklist
- [ ] Brand persona `instruction.yaml` created and tested.
- [ ] Knowledge sources uploaded to `faq_data`.
- [ ] Ingestion script completed without errors.
- [ ] `/chat` endpoint tested with brand-specific context.
