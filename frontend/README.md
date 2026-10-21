# AI Resume Reviewer - Web Application

A full-stack web application wrapped around the AI Resume Reviewer pipeline. It provides a modern interface for uploading resumes, evaluating candidate fit against specific roles, inspecting ATS compatibility, and reviewing past evaluations.

---

## Architecture Overview

```text
frontend/
├── api/                  # FastAPI backend server
│   ├── database.py       # SQLAlchemy SQLite connection and session management
│   ├── models.py         # Database model (Review table with file_hash & job_title uniqueness)
│   ├── requirements.txt  # Python backend dependencies
│   └── main.py           # API endpoints, concurrency locking, and pipeline integration
├── data/                 # SQLite storage (gitignored)
│   └── reviews.db        # Persisted review records
├── web/                  # Next.js 15 App Router web application
│   ├── src/app/          # Review dashboard (/) and history table (/history)
│   ├── src/components/   # shadcn/ui components & theme toggles
│   ├── src/types/        # TypeScript interfaces matching pipeline schema
│   └── .env.local        # Environment configuration (NEXT_PUBLIC_API_URL)
├── .gitignore            # Git exclusions for data/, node_modules, .next, and env files
└── README.md             # Setup and run guide
```

---

## Prerequisites

1. **Python 3.10+**: Ensure Python is installed with pip.
2. **Node.js 18+ / 20+** and **npm**: Required for the Next.js frontend.
3. **Ollama**: Local LLM server running on `http://localhost:11434` with the model `huihui_ai/qwen3.5-abliterated:9b`.

---

## Step-by-Step Setup & Run

### Step 1: Start Ollama

Ensure Ollama is running and has pulled the required model:

```bash
# Start Ollama service (if not already running as a daemon)
ollama serve

# Verify or pull the model specified by the pipeline
ollama pull huihui_ai/qwen3.5-abliterated:9b
```

---

### Step 2: Start the FastAPI Backend (`frontend/api`)

1. Open a terminal and navigate to the `frontend/api` directory:
   ```bash
   cd frontend/api
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure parent project dependencies from the root `pyproject.toml` or `requirements.txt` are also installed in your Python environment).*

3. Start the FastAPI server using Uvicorn:
   ```bash
   uvicorn main:app --reload --reload-dir . --host 127.0.0.1 --port 8000
   ```

The backend will be available at:
- **API Base**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/api/health`

---

### Step 3: Start the Next.js Frontend (`frontend/web`)

1. Open a second terminal and navigate to `frontend/web`:
   ```bash
   cd frontend/web
   ```

2. Verify or create `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. Install frontend packages:
   ```bash
   npm install
   ```

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```

Open your browser and navigate to:
- **Web App**: `http://localhost:3000`
- **Review Dashboard**: `http://localhost:3000/`
- **Review History**: `http://localhost:3000/history`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/review` | Uploads a PDF resume (`file`, max 5 MB), `job_title`, and optional `force`. Computes SHA-256 hash. Returns cached evaluation if previously run (unless `force=true`). |
| `GET` | `/api/reviews` | Lists stored reviews with pagination (`page`, `size`) and search (`q` filtering filename or job title). |
| `GET` | `/api/reviews/{id}` | Retrieves full stored review details, scores, and skills breakdown. |
| `DELETE` | `/api/reviews/{id}` | Deletes a stored review by ID. |
| `GET` | `/api/health` | Health check verifying FastAPI and Ollama connectivity. |

---

## Key Design Highlights

1. **Zero Root Modifications**: All frontend, API, database, and configuration files live exclusively within `frontend/`.
2. **Concurrency & File Safety**: The root pipeline writes to shared paths in `outputs/` using relative directories. The backend acquires a global `threading.Lock()` and temporarily locks the working directory to the repository root for each run, preventing concurrent race conditions.
3. **Execution Offloading**: Calls to `run_pipeline` run inside `asyncio.to_thread` to keep FastAPI's event loop fully responsive.
4. **Smart Cache & Re-run**: Duplicate resume submissions for the same role return cached results instantly (`already_reviewed: true`), with an in-UI prompt allowing the user to trigger a fresh re-run (`force=true`).
5. **Modern UI**: Built with Next.js 15, Tailwind CSS, Lucide icons, and shadcn/ui components (`Card`, `Button`, `Input`, `Select`, `Badge`, `Progress`, `Table`, `Tabs`, `Dialog`, `Alert`, `Skeleton`, `Sonner`), complete with light and dark mode support.
