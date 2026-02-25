# 📂 MiMi AI: Project Architecture & Structure

This document provides a detailed map of the **MiMi AI** codebase. This project serves as the core intelligence (agentic engine) that powers customer service automation, integrating seamlessly with middleware and messaging platforms.

---

## 🏗️ Root Directory

| Path | Category | Description |
| :--- | :--- | :--- |
| **`.env`** | Config | Essential secrets: `GOOGLE_API_KEY`, `GEMINI_MODEL`. |
| **`AI/`** | Core | The primary source code for the AI engine. |
| **`docs/`** | Docs | Extended guides: `architecture_guide.md`, `brand_onboarding.md`. |
| **`README.md`** | Docs | High-level project overview and setup guide. |
| **`PROJECT_STRUCTURE.md`** | Docs | This file; a comprehensive architectural map. |
| **`.venv/`** | Environment | Python virtual environment with all core dependencies. |

---

## 🧠 `AI/` - The Core Engine

The `AI` folder encapsulates the FastAPI server and the agentic RAG orchestration logic.

### 📁 Root Source Files
- **`server.py`**: The production entry point. Exposes the `/chat` API using FastAPI and Uvicorn.
- **`main.py`**: A CLI-based entry point for direct terminal testing.
- **`requirements.txt`**: Manages backend dependencies (FastAPI, Google GenAI SDK, FAISS).

### 📁 `AI/app/` - Application Logic
This is where the modular agent and tool logic resides.

#### 🤖 `app/agents/`
The decision-making layer of the chatbot.
- **`base_agent.py`**: Core implementation of the `LlmAgent`. Handles session creation and Gemini integration.
- **`root_agent.py`**: Configures and exports the primary agent instance.
- **`multi/`**: (Experimental) Contains multi-agent logic including `router_agent.py` and specialized `faq_agent.py`.

#### 🎨 `app/prompts/`
The "personality" and "instructions" for our agents.
- **`base.yaml`**: Standard system instructions for the base agent.
- **`router.yaml`**: Intent classification and routing logic.
- **`brands/mizumi/`**: Brand-specific personas (e.g., `instruction.yaml`).

#### �️ `app/tools/`
Capabilities the agents can use.
- **`tools.py`**: General tool registry.
- **`faq_tools.py`**: RAG-based lookup tools to query knowledge bases.

#### � `app/ingest/`
Data processing and indexing pipeline.
- **`faq_ingest.py`**: Ingests source data (PDF/XLSX/CSV) into the FAISS vector index.

#### 🧩 `app/ Core Utilities`
- **`retrieval.py`**: The RAG engine; handles FAISS index loading and similarity searches.
- **`embeddings_gemini.py`**: Integration for Gemini's embedding models.
- **`prompt_loader.py`**: Safely parses YAML files to dynamically load agent personas.

---

## 📚 Data & Knowledge Base

| Directory | Content |
| :--- | :--- |
| **`AI/faq_data/`** | Raw brand knowledge (PDF, XLSX, CSV). This is the source of truth for RAG. |
| **`AI/index/`** | Generated FAISS vector database indices. Created by ingestion scripts. |

---

## 🛠️ Brand-Specific Management

To add or modify a brand persona:
1. Navigate to `AI/app/prompts/brands/[brand_name]/`.
2. Edit the `instruction.yaml` file to define the bot's behavior, tone, and specific rules.
3. Update `AI/faq_data/` with any new knowledge documentation and run the ingestion scripts.

---

## 🛡️ License & Maintenance

Designed and maintained for high-performance Thai customer service automation.
*Last Updated: 2026-02-05*

