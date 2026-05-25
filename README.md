# MedIntel AI

AI-powered medical intelligence platform with separate frontend and backend architecture.

## Features

- Upload medical documents (PDFs, prescriptions, blood reports) and images (X-rays, MRIs, CT scans)
- AI analysis via Gemini Pro & Vision APIs
- Generate detailed PDF medical reports
- RAG-powered chat with medical history context
- FAISS vector search for semantic retrieval
- Redis session memory for conversational context
- Duplicate file detection via SHA-256 hashing
- Two modes: Quick Analysis (no save) vs Persistent Medical History
- Report comparison and medical timeline

## Tech Stack

**Frontend:** React, TypeScript, Tailwind CSS, React Query, Axios, Zustand, React Router, WebSockets

**Backend:** FastAPI, PostgreSQL, Redis, FAISS, LangChain, Gemini API, AWS S3, Docker

## Quick Start

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY
```

### 2. Run with Docker

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Local development

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
medicAI/
├── backend/
│   └── app/
│       ├── api/          # REST & WebSocket routes
│       ├── agents/       # Medical analysis agent
│       ├── db/           # Database setup
│       ├── models/       # SQLAlchemy models
│       ├── rag/          # FAISS + RAG pipeline
│       ├── schemas/      # Pydantic schemas
│       ├── services/     # S3, PDF, Gemini, Redis
│       └── utils/        # Auth, hashing
├── frontend/
│   └── src/
│       ├── components/   # Layout, FileUpload
│       ├── pages/        # Auth, Dashboard, Chat, Reports, Timeline
│       ├── lib/          # API client
│       └── store/        # Zustand state
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register user |
| POST | `/api/auth/login` | Login (JWT) |
| POST | `/api/upload/analyze` | Upload & analyze file |
| GET | `/api/upload/reports` | List saved reports |
| GET | `/api/reports/{id}` | Get report details |
| POST | `/api/reports/compare` | Compare two reports |
| GET | `/api/timeline` | Medical history timeline |
| POST | `/api/chat` | Chat with AI |
| WS | `/api/ws/chat/{session_id}` | Streaming chat |

## Environment Variables

See `backend/.env.example` for all configuration options. Key variables:

- `GEMINI_API_KEY` — Required for AI analysis
- `AWS_*` — Optional; falls back to local file storage if not set
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string

## Disclaimer

MedIntel AI is for informational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.
