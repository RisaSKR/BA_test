# 🤖 MiMi AI: Intelligent Customer Service Engine

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen" alt="Status">
  <img src="https://img.shields.io/badge/Language-Thai%20%2F%20English%20%2F%20Chinese-blue" alt="Language">
  <img src="https://img.shields.io/badge/Model-Gemini%203.0%20Flash-orange" alt="Model">
  <img src="https://img.shields.io/badge/Framework-FastAPI-009688" alt="Framework">
</p>

**MiMi AI** is a high-performance, agentic customer service engine designed to automate complex user interactions. Serving as the "brain" of the customer support ecosystem, it leverages Google's Gemini models and a sophisticated Retrieval-Augmented Generation (RAG) architecture to provide accurate, brand-aligned responses in real-time.

---

## ✨ Key Features

- **🌍 Multilingual Intelligence**: Native-quality support for **Thai**, **English**, and **Chinese** with real-time translation capabilities.
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
4.  **LLM**: Processes the combined prompt (Instruction + Context + Knowledge) using Gemini 3.0 Flash.

---

## 📁 Project Structure

```text
BA_test/
├── AI/                     # Core Engine
│   ├── app/                # Application Logic (Agents & Tools)
│   ├── faq_data/           # Knowledge Base (PDF, XLSX, CSV, JSON)
│   ├── static/             # Chat UI Frontend (HTML, CSS, JS)
│   ├── index/              # Search Indices (FAISS)
│   ├── server.py           # FastAPI Production Server
│   └── main.py             # CLI Testing Interface
├── .env                    # Secrets & API Keys
└── requirements.txt        # Dependencies
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
cd BA_test

# Create and activate virtual environment (windows)
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
The server defaults to `http://localhost:3171`.

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
1. Drop new source files (PDF, CSV, XLSX, JSON) into `AI/faq_data/`.
2. Re-run the ingestion script to refresh the vector store.

---

## 📖 Extended Documentation

For a deeper dive into the system and how to manage it, refer to these guides:

- [🏗️ Architecture Guide](file:///c:/Users/sirisa/BA_test/docs/architecture_guide.md): Deep dive into the multi-agent orchestration and RAG system.
- [🚀 Brand Onboarding Guide](file:///c:/Users/sirisa/BA_test/docs/brand_onboarding.md): Step-by-step guide on adding new brands and knowledge documentation.

---

## 🛡️ License

© 2025 MiMi AI Team. All rights reserved.
