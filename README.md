# Liquid AI LLM Chatbot Assignment

A complete login-protected chatbot system using:

- **Frontend:** React + Vite, OpenAI ChatKit React, and custom Tailwind styling tailored to mimic a modern, Google Gemini-style interface (featuring a responsive chat history sidebar and a clean, borderless chat layout). No raw CSS files are used beyond the Tailwind import.
- **Backend:** FastAPI, JWT authentication, SQLAlchemy, SQLite persistence, and a self-hosted OpenAI ChatKit endpoint.
- **LLM:** Liquid AI LFM model served locally by Ollama and called through LangChain.
- **Memory/history:** SQLite stores exact per-user threads/messages. Qdrant stores vectorized conversation turns for semantic memory recall.

## Folder structure

```text
backend/                 FastAPI API, authentication, ChatKit server, LangChain, Qdrant memory
frontend/                React + shadcn/ui + OpenAI ChatKit interface
REPORT.md                One-page assignment report in markdown
docker-compose.yml       Local Qdrant, Ollama, backend, and frontend stack
```

## Prerequisites

- Docker Desktop or Docker Engine
- Optional local mode: Python 3.12, Node 22, Qdrant, and Ollama

## Fast Docker run

Start the stack:

```bash
docker compose up --build
```

In another terminal, pull the Liquid AI model into Ollama:

```bash
docker compose exec ollama ollama run hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF
```

After the model is available, open:

```text
http://localhost:5173
```

Create an account, sign in, and start chatting. The first request can be slow while Ollama warms the model and FastEmbed downloads the embedding model.

## Manual development run

Terminal 1: Qdrant

```bash
docker run --rm -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant:latest
```

Terminal 2: Ollama + Liquid AI model

```bash
ollama serve
ollama run hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF
```

Terminal 3: backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 4: frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Core API routes

```text
POST /api/auth/register       Register and receive a JWT
POST /api/auth/login          Login and receive a JWT
GET  /api/auth/me             Current authenticated user
GET  /api/threads             Per-user chat history summaries
GET  /api/threads/{id}/messages  Per-user transcript
POST /chatkit                 OpenAI ChatKit-compatible endpoint
```

## How the workflow satisfies the assignment

1. **Login authentication:** Users register/login with email and password. Passwords are hashed with bcrypt and requests use JWT Bearer auth.
2. **Chatbot access after login:** The React app protects the chatbot route. ChatKit requests include the JWT in the Authorization header.
3. **Liquid AI model integration:** The backend uses LangChain's `ChatOllama` client to call the Liquid AI LFM GGUF model served by Ollama.
4. **Persistent chat history:** ChatKit thread metadata and items are stored in SQLite with the authenticated user id. Returning users can reload transcripts from the history panel.
5. **Qdrant memory:** Each user/assistant turn is embedded and saved in Qdrant. New questions retrieve only that user's relevant previous snippets and add them to the model context.

## Environment variables

Backend variables are in `backend/.env.example`; frontend variables are in `frontend/.env.example`.

Most important values:

```text
JWT_SECRET=replace-with-a-long-random-secret
QDRANT_URL=http://localhost:6333
OLLAMA_BASE_URL=http://localhost:11434
LIQUID_MODEL=hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF
VITE_API_URL=http://localhost:8000
```

## GitHub submission

1. Replace the placeholder GitHub URL in `REPORT.md` and the DOCX report with your real repository URL.
2. Add group member names, IDs, and section.
3. Push the project:

```bash
git init
git add .
git commit -m "Complete Liquid AI chatbot assignment"
git branch -M main
git remote add origin https://github.com/Hasin-ai/liquid-ai-chatbot-assignment.git
git push -u origin main
```
# ChatBot
