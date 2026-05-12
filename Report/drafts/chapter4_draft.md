# CHAPTER 4: SYSTEM DEVELOPMENT

## 4.1 Introduction

This chapter documents the system development phase of the ShieldGuard Vishing Detection System, covering the full transition from the FYP1 prototype into a production-grade, multi-layered detection platform in FYP2. The development follows a Hybrid Rapid Application Development (RAD) methodology, as established in Chapter 3, allowing continuous improvement of detection algorithms and the user interface based on iterative testing and evaluation.

In FYP1, the project delivered a functional baseline: a Streamlit prototype backed by classical machine learning models (SVM, Logistic Regression, Random Forest) and a lightweight character-level neural network, all operating on TF-IDF features extracted from ASR-generated transcripts. These models were evaluated as experimental baselines, and SVM was selected as the final production classifier because it offered the best balance of accuracy, inference speed, calibrated probability output, and explainable TF-IDF feature weights. This baseline achieved strong metrics (SVM: 98.51% accuracy, 0.9809 macro F1; Logistic Regression: 98.51% accuracy, 0.9811 macro F1) under leakage-safe evaluation, as reported in Chapter 3.

FYP2 extends this foundation with three major architectural upgrades: (1) migration from Streamlit to a full-stack React.js + FastAPI architecture for improved scalability and user experience; (2) integration of a Hybrid ML + LLM analysis engine combining classical ML with Retrieval-Augmented Generation (RAG) and agentic AI reasoning via Ollama; and (3) implementation of enterprise-grade security controls including JWT authentication, brute-force protection, rate limiting, and audit logging via Supabase. These enhancements transform the system from an academic prototype into a defensible, near-real-time vishing detection platform.

The development is documented across multiple iterative versions, each building upon the previous to demonstrate progressive refinement. This approach aligns with recommendations in recent vishing detection literature, where layered detection architectures combining classical ML baselines with advanced AI reasoning have shown improved robustness against evolving social engineering tactics (Phang et al., 2024; Ma et al., 2025).

## 4.2 Preparation and Environment Setup

The development environment was configured to support concurrent machine learning inference, LLM-based reasoning, and a responsive web frontend. Given the computational demands of running both TF-IDF-based classifiers and a local LLM (Llama 3.2 via Ollama), the hardware requirements are more demanding than the FYP1 baseline.

**Table 4.1: Hardware Specification**

| Category | Specification | Price |
| :--- | :--- | :--- |
| Device | HP VICTUS 16-e0xxx | RM 3,899 |
| Operating System | Microsoft Windows 11 Home Single Language | Owned |
| CPU | AMD Ryzen 5 5600H with Radeon Graphics, 3301 MHz, 6 Core(s), 12 Logical Processor(s) | RM 850 |
| RAM | 16GB DDR4 | RM 250 |
| Storage | 512 HDD & 512 SSD | RM 350 |
| GPU | NVIDIA GTX 1050 | RM 650 |

Minimum recommended for smooth running: 8GB RAM, SSD storage, and a modern CPU. GPU is not required for deployed ML inference because the final SVM model runs efficiently on CPU. Earlier Logistic Regression, Random Forest, and neural network models were evaluated during experimentation, but they are not loaded by the production app.

**Table 4.2: Software and Libraries Used**

| Category | Tools / Libraries | Purpose |
| :--- | :--- | :--- |
| IDE / Environment | Visual Studio Code, Jupyter Notebook | Primary development and experimentation environments. |
| Language (Backend) | Python 3.12.2 | Core language for ML inference, API logic, and data handling. |
| Language (Frontend) | JavaScript (ES6+) | Used with React.js for the interactive user dashboard. |
| Web Framework | FastAPI 0.100+ with Uvicorn | High-performance asynchronous API server replacing the FYP1 Streamlit backend. |
| Frontend Framework | React.js 18.2.0 with Vite | Component-based SPA framework for building the ShieldGuard dashboard. |
| Machine Learning | scikit-learn 1.3.0 | Implements TF-IDF vectorization, SVM (CalibratedClassifierCV), and pipeline persistence. |
| Deep Learning | TensorFlow / Keras | Used during experimentation for a neural-network baseline; not required by the final deployed SVM app. |
| Speech-to-Text | OpenAI Whisper (base model) | Local ASR engine to transcribe uploaded audio files into text. |
| LLM Engine | Ollama (Llama 3.2:3b) | Runs the local Large Language Model for agentic AI reasoning in Phase 2. |
| Vector Database | ChromaDB | Persistent vector store for Retrieval-Augmented Generation (RAG) scam library. |
| Embedding Model | all-MiniLM-L6-v2 (sentence-transformers) | 384-dimensional CPU-friendly embeddings for semantic similarity search. |
| Cloud Database | Supabase (PostgreSQL) | User management, audit logging, rate limiting, and login attempt tracking. |
| Authentication | python-jose (JWT) | JSON Web Token generation and validation for stateless API authentication. |
| Data Handling | NumPy, Pandas | Dataset loading, cleaning, and statistical analysis. |
| NLP | NLTK (WordNetLemmatizer) | Lemmatization in the preprocessing pipeline to normalise word forms. |
| Imbalance Handling | imbalanced-learn (SMOTE) | Synthetic oversampling experiments during model training. |
| Model Persistence | Joblib | Serialisation and deserialisation of trained scikit-learn pipelines. |
| Visualisation | Matplotlib | Confusion matrices, training curves, and performance comparison charts. |
| Version Control | Git & GitHub | Source control, branching strategy, and collaborative development tracking. |
| API Testing | Postman | Manual verification of all FastAPI endpoints before frontend integration. |

**Table 4.3: Tools Used in Local Development Environment**

| Tool | Purpose | Justification |
| :--- | :--- | :--- |
| VS Code | Primary IDE | Provides integrated terminal, Python/JS extensions, and Git integration. |
| Postman | API endpoint testing | Allows manual testing of authentication, analysis, and transcription routes. |
| Git & GitHub | Version control | Enables trackable code changes, branching for feature isolation, and rollback. |
| Ollama Desktop | Local LLM hosting | Runs Llama 3.2:3b locally without cloud dependency for privacy and cost control. |
| Chrome DevTools | Frontend debugging | Inspects API calls, state management, and rendering performance. |

## 4.3 System Architecture Overview

The ShieldGuard system follows a three-tier architecture consisting of a React.js frontend, a FastAPI backend, and a data/model persistence layer. The backend itself implements a layered cascade architecture for detection, where each layer adds deeper analysis.

**[IMAGE PLACEHOLDER: Figure 4.1 — System Architecture Diagram]**
*(Instruction: Insert the system architecture diagram showing: User → React Frontend → FastAPI Backend → [Phase 1: ML Layer (TF-IDF + SVM)] → [Phase 2: Hybrid Engine → RAG (ChromaDB) + LLM Agents (Ollama)] → Result returned to Frontend. Also show Supabase for auth/audit and Whisper for ASR.)*

**Table 4.4: System Component Overview and Responsibilities**

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Frontend Dashboard** | React.js + Vite | Accepts transcript text or audio uploads, displays analysis results with confidence gauges, keyword highlights, and AI explanations. |
| **API Gateway** | FastAPI + Uvicorn | Exposes RESTful endpoints for authentication, analysis, transcription, history, and health checks. Handles CORS, JWT validation, and rate limiting. |
| **Authentication Layer** | JWT + Supabase | Manages user registration, login, brute-force lockout (5 attempts / 15 min), and session tokens. |
| **ML Inference Engine** | scikit-learn | Loads the final SVM v3 production model at startup. Applies identical preprocessing (normalisation + lemmatization) as training, then classifies via TF-IDF features. |
| **Hybrid Analysis Engine** | hybrid_engine.py | Orchestrates the ML → RAG → LLM cascade. Applies threshold gates and cross-checks ML vs LLM verdicts for divergence detection. |
| **RAG Module** | ChromaDB + sentence-transformers | Embeds all known vishing transcripts into a vector store. At query time, retrieves the top-N most similar historical scam cases to provide context to the LLM. |
| **LLM Agent Layer** | Ollama (Llama 3.2:3b) | Agentic AI reasoning layer that analyses the transcript, ML evidence, and RAG results to produce natural-language explanations, tactic identification, and action recommendations. |
| **Whisper ASR** | OpenAI Whisper (base) | Converts uploaded audio files (.wav, .mp3, .m4a, .ogg, .flac, .webm) into text transcripts for downstream analysis. |
| **Audit & Logging** | Supabase PostgreSQL | Records every analysis event (username, input length, model used, verdict, confidence, timestamp) for accountability and compliance. |
