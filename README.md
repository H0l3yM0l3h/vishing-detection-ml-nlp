# ShieldGuard — AI-Powered Vishing Detection System

> Hybrid ML + LLM + RAG multi-agent system for detecting voice phishing (vishing) attacks.

## Quick Start

**Backend** (Terminal 1):
```powershell
cd backend
..\\.venv\Scripts\activate
python main.py
```

**Frontend** (Terminal 2):
```powershell
cd frontend
npm install
npm run dev
```

**Open:** http://localhost:5173

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| ML Classifier | TF-IDF + SVM/LR/RF/NN | Fast classification (98.5% accuracy) |
| RAG Search | ChromaDB + MiniLM-L6-v2 | Historical scam pattern matching |
| Multi-Agent LLM | CrewAI + Ollama (Llama 3.2 3B) | Verdict reasoning with 4 AI agents |

## Documentation

See [LLMContext.md](LLMContext.md) for the complete system documentation.
