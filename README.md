# 🤖 MiMi AI: Intelligent Customer Service Engine

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/Language-Thai%20%2F%20English-blue" alt="Language">
  <img src="https://img.shields.io/badge/Model-Gemini%202.0%20Flash-orange" alt="Model">
  <img src="https://img.shields.io/badge/Framework-FastAPI-009688" alt="Framework">
</p>

**MiMi AI** is a high-performance, agentic customer service engine designed to automate complex user interactions. Serving as the "brain" of the customer support ecosystem, it leverages Google's Gemini models and a sophisticated Retrieval-Augmented Generation (RAG) architecture to provide accurate, brand-aligned responses in real-time.

---

## ✨ Key Features

- **🇹🇭 Native Thai Support**: Expertly tuned for Thai language nuances, professional formatting, and cultural context.
- **🧠 Agentic Multi-Brand Architecture**: Supports multiple brand personas (e.g., MizuMi) with dedicated instructions and knowledge bases.
- **📚 Advanced RAG System**: Real-time retrieval from indexed FAQs, store policies, and product documentation using FAISS.
- **📊 Token usage Tracking**: Precise monitoring of prompt, candidate, and total token counts for cost management.
- **⚡ High Performance**: Built on FastAPI with asynchronous processing for rapid response times.
- **🔗 Seamless Middleware Integration**: Designed to integrate effortlessly with Shopee, Lazada, and other social commerce platforms.

---

## 🏗️ Technical Architecture

MiMi operates as the core intelligence layer between the messaging platforms and the Large Language Model:

1.  **Entry Point**: `AI/server.py` exposes a RESTful API.
2.  **Logic Layer**: `AI/app/agents/base_agent.py` manages session persistence and agent execution.
3.  **Retrieval**: `retrieve_tool` queries FAISS indices to ground the model's responses in factual data.
4.  **LLM**: Processes the combined prompt (Instruction + Context + Knowledge) using Gemini 2.0 Flash.

---

## 📁 Project Structure

```text
MiMi/
├── AI/
│   ├── app/                # Core Logic
│   │   ├── agents/         # Agent definitions and session management
│   │   ├── prompts/        # YAML-based brand instructions & personas
│   │   ├── tools/          # RAG and lookup utilities
│   │   └── ingest/         # Data indexing and embedding scripts
│   ├── faq_data/           # Raw knowledge source (PDF, XLSX, CSV)
│   ├── index/              # Generated FAISS vector indices
│   ├── server.py           # FastAPI Production Server
│   └── main.py             # CLI Testing Interface
├── .env                    # Secrets & API Keys (External)
└── requirements.txt        # Dependency Manifest
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Google Gemini API Key

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/RisaSKR/BA.git
cd BA

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

cd AI
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3-flash-preview
```

### 3. Data Ingestion

Before running the server, ingest your data to build the search index:

```bash
# Ingest FAQ and Policy data
python AI/app/ingest/faq_ingest.py
```

### 4. Launching the Engine

```bash
# Start the API Server
python AI/server.py
```
The server defaults to `http://localhost:8001`.

---

## 📡 API Documentation

### POST `/chat`

Primary endpoint for sending user messages and receiving agent responses.

**Request Body:**
```json
{
  "platform_user_id": "shopee_user_001",
  "platform_conversation_id": "conv_98765",
  "text": "มีโปรโมชั่นอะไรบ้างคะ?",
  "context": {}
}
```

**Successful Response:**
```json
{
  "text": "สวัสดีค่ะ! สำหรับแบรนด์ MizuMi ตอนนี้มีโปรโมชั่นพิเศษ...",
  "usage": {
    "total_token_count": 245,
    "prompt_token_count": 180,
    "candidates_token_count": 65
  }
}
```

---

## 🛠️ Brand & Knowledge Management

### Adding a New Brand
1. Define a new YAML instruction in `AI/app/prompts/brands/[brand_name]/`.
2. Update the `PromptLoader` logic to switch between brands based on context or headers.

### Updating Knowledge
1. Drop new source files (PDF, CSV, XLSX) into `AI/faq_data/`.
2. Re-run the ingestion script to refresh the vector store.

---

## 🛡️ License

© 2025 MiMi AI Team. All rights reserved.
