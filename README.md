# MedIntel AI

**Turn medical documents into clarity — in seconds.**

MedIntel AI is a full-stack medical intelligence platform that reads your prescriptions, lab reports, and imaging files, explains them in plain language, and keeps a living timeline of your health history. Upload once, chat with context, compare trends over time.

> Built for learning, demos, and personal health organization — **not** a replacement for your doctor.

---

## Screenshots

### Authentication
<p align="center">
  <img src="readme/login.png" alt="Login page" width="720" />
</p>

<p align="center">
  <img src="readme/signUp.png" alt="Sign up page" width="720" />
</p>

### Dashboard & upload
<p align="center">
  <img src="readme/Dashboard.png" alt="Dashboard — upload and analyze medical files" width="720" />
</p>

### Reports & comparison
<p align="center">
  <img src="readme/ReportPage.png" alt="Reports list and report viewer" width="720" />
</p>

<p align="center">
  <img src="readme/ComparisonReportPage.png" alt="Compare two medical reports" width="720" />
</p>

### AI chat & medical timeline
<p align="center">
  <img src="readme/AIChatPAge.png" alt="AI chat with medical context" width="720" />
</p>

<p align="center">
  <img src="readme/HIstoryPage.png" alt="Medical history timeline" width="720" />
</p>

---

## Why MedIntel AI?

| Problem | How MedIntel helps |
|--------|---------------------|
| Dense PDFs and handwritten prescriptions | Gemini Vision + text analysis extracts findings, medicines, and conditions |
| “What did my last report say?” | RAG chat grounded in **your** uploaded reports |
| Scattered files across folders | Medical timeline + saved reports in one place |
| Re-uploading the same scan | SHA-256 duplicate detection — instant reuse, optional save to history |

---

## Features

### Document intelligence
- **PDFs** — lab results, discharge summaries, digital reports  
- **Images** — X-rays, MRIs, CT scans, prescriptions (including handwriting)  
- **Structured output** — summary, severity, findings, medicines, conditions, recommendations  

### Two analysis modes
- **Quick analysis** — one-off insight, nothing persisted to your timeline  
- **Save to medical history** — PDF report generation, FAISS indexing, timeline entry, active medicines  

### Clinical workspace
- **Dashboard** — drag-and-drop upload with live status  
- **Reports** — browse, open, and download generated PDFs  
- **AI chat** — ask follow-ups with RAG over your documents  
- **Timeline** — chronological view of saved events, conditions, and medications  
- **Compare** — AI-powered diff between two saved reports  

### Under the hood
- JWT authentication  
- PostgreSQL (Supabase-compatible) persistence  
- Redis session memory for multi-turn chat (optional — degrades gracefully)  
- FAISS vector search for semantic retrieval  
- Local file storage with optional AWS S3  

---

## Architecture

```mermaid
flowchart TB
    subgraph Client
        UI[React + Vite + Tailwind]
    end

    subgraph API
        FastAPI[FastAPI Backend]
        Agent[Medical Analysis Agent]
    end

    subgraph AI
        Gemini[Gemini 2.5 Flash]
        RAG[RAG + FAISS]
    end

    subgraph Data
        PG[(PostgreSQL)]
        Redis[(Redis)]
        Disk[Local / S3 Storage]
        FAISS[(FAISS Index)]
    end

    UI -->|REST + JWT| FastAPI
    FastAPI --> Agent
    Agent --> Gemini
    Agent --> RAG
    RAG --> FAISS
    Agent --> PG
    Agent --> Disk
    FastAPI --> Redis
```

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, TanStack Query, Zustand, React Router, Axios |
| **Backend** | FastAPI, SQLAlchemy (async), Pydantic, Uvicorn |
| **AI** | Google Gemini (`gemini-2.5-flash`), embeddings, vision |
| **Data** | PostgreSQL, Redis, FAISS, local disk or S3 |
| **Ops** | Docker Compose |

---

## Quick start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (optional, recommended)  
- **Or** Python 3.11+, Node 20+, PostgreSQL, Redis  
- A [Gemini API key](https://aistudio.google.com/apikey)

### 1. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` — at minimum set:

```env
GEMINI_API_KEY=your-key-here
SECRET_KEY=use-a-long-random-string
```

For **local** development (without Docker Postgres), point `DATABASE_URL` at your database:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
FAISS_INDEX_PATH=./data/faiss_index
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

> AWS credentials are optional. Without them, uploads are stored under `backend/data/uploads/`.

### 2. Run with Docker

```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |

### 3. Run locally (development)

**Terminal 1 — backend**

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**, register an account, and upload your first file.

**Tip:** Enable **Save to Medical History** *before* selecting a file if you want the timeline populated.

---

## Project structure

```
medicAI/
├── readme/                # Screenshots for documentation
├── screenshot/            # Source screenshots (also copied to readme/)
├── backend/
│   ├── app/
│   │   ├── api/           # Auth, upload, reports, chat, timeline
│   │   ├── agents/        # Medical analysis orchestration
│   │   ├── db/            # Async SQLAlchemy setup
│   │   ├── models/        # Users, reports, history, medicines
│   │   ├── rag/           # FAISS store + retrieval pipeline
│   │   ├── schemas/       # Request/response models
│   │   └── services/      # Gemini, PDF, S3, Redis
│   ├── data/              # Uploads + FAISS index (local dev)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/    # Layout, file upload
│       ├── pages/         # Auth, dashboard, chat, reports, timeline
│       └── lib/           # API client + auth interceptors
└── docker-compose.yml
```

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Create account |
| `POST` | `/api/auth/login` | Login → JWT |
| `POST` | `/api/upload/analyze` | Upload file (`save_to_history`, optional `question`) |
| `GET` | `/api/upload/reports` | List reports (`?saved_only=true` optional) |
| `GET` | `/api/reports/{id}` | Report detail |
| `POST` | `/api/reports/compare` | Compare two reports |
| `GET` | `/api/timeline` | Medical history timeline |
| `POST` | `/api/chat` | Chat with RAG context |
| `GET` | `/health` | Health check |

Full schema and try-it-out UI: **http://localhost:8000/docs**

---

## Environment variables

See [`backend/.env.example`](backend/.env.example) for the full list.

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Powers analysis and chat |
| `SECRET_KEY` | Yes | JWT signing |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` |
| `REDIS_URL` | No | Chat memory; app works without Redis |
| `FAISS_INDEX_PATH` | Yes | Path to vector index directory |
| `AWS_*` / `S3_BUCKET` | No | S3 upload; omit for local disk |
| `GEMINI_MODEL` | No | Default: `gemini-2.5-flash` |
| `CORS_ORIGINS` | No | Comma-separated frontend origins |

---

## Deploying to GitHub

Keep secrets out of version control:

```bash
git rm -r --cached backend/.env backend/venv backend/data frontend/node_modules 2>/dev/null || true
git add .gitignore
git status   # confirm .env and venv are NOT staged
```

- Copy `backend/.env.example` → `backend/.env` on each machine  
- **Never commit** `.env`, `venv/`, `node_modules/`, or `backend/data/`  
- Use your host’s secret manager (Railway, Render, GitHub Actions, etc.) in production  

---

## Roadmap ideas

- [ ] FHIR / EHR export  
- [ ] Family profiles & caregiver sharing  
- [ ] Multilingual report summaries  
- [ ] Mobile PWA  

Contributions welcome — open an issue or PR with your idea.

---

## Disclaimer

**MedIntel AI is for informational and educational purposes only.** It does not provide medical advice, diagnosis, or treatment. Always consult a qualified healthcare professional for health decisions. Do not use this tool in emergencies.

---
