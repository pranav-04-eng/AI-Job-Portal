# HireVoice — AI hiring portal

A Glassdoor-style job portal where candidates apply with a resume, an
**AI screener (LangGraph)** scores the resume against the role, and strong
matches are invited to an **AI voice interview** (Groq Whisper STT → Llama →
Orpheus TTS) that produces a structured assessment. Recruiters post jobs and
review ranked applicants.

```
                         ┌──────────────────────────────────────┐
   React + Tailwind      │            API gateway :8000          │  (CORS lives here)
   (Vite, :5173)  ─────► │   reverse-proxies by path prefix      │
                         └───┬──────────┬───────────┬────────────┘
                             │          │           │
                  /auth/*    │ /jobs/*  │ /interview/*
                             ▼          ▼           ▼
                      auth :9001   jobs :9002   interview :9004
                                       │
                            (server-to-server on apply)
                                       ▼
                               screening :9003  ── LangGraph: extract → fit → score
```

Each service is its own FastAPI app with its own SQLite DB; they share JWTs
signed with one secret, so a token from auth-service validates everywhere.

## The flow
1. **Sign up / log in** as a *candidate* or *recruiter* (JWT auth).
2. **Recruiter** posts a job (title, description, requirements).
3. **Candidate** browses jobs and **applies with a PDF resume**.
4. **jobs-service** forwards the PDF to **screening-service**, which extracts the
   text and runs the LangGraph screening graph
   (`extract_profile → analyze_fit → score`) to produce a 0–100 fit score.
5. **Screening gates the interview**: score ≥ `SCREEN_PASS_THRESHOLD` (default 60)
   → status `interview_invited`; otherwise auto-rejected.
6. Invited candidates take the **voice interview** (the LangGraph interrupt loop:
   speak → transcribe → next question → assess). The assessment is saved back to
   the application.
7. **Recruiter** reviews applicants ranked by screening score, sees both the
   resume verdict and the interview assessment, and hires / declines.

## Prerequisites
- Python 3.10+ (built/tested on 3.14)
- Node 18+
- A Groq API key — https://console.groq.com

## Run the backend (one command, all services)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then put your REAL GROQ_API_KEY in .env

python seed.py              # demo recruiter + candidate + sample jobs
./start_all.sh              # macOS/Linux — boots all services + gateway
```
On **Windows**, use the PowerShell script instead of `start_all.sh`:
```powershell
python seed.py
./start_all.ps1
# if scripts are blocked: powershell -ExecutionPolicy Bypass -File .\start_all.ps1
```
Either script launches all four services plus the gateway; Ctrl-C stops
everything. The frontend only ever talks to the gateway at
`http://localhost:8000`.

> **You must set a real `GROQ_API_KEY`** in `backend/.env` — resume screening and
> the voice interview both call Groq. Browsing, auth, and posting jobs work
> without it; screening/interview will error until the key is set.

## Run the frontend (separate terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

### Demo logins (after `python seed.py`)
| Role      | Email                | Password    |
|-----------|----------------------|-------------|
| Candidate | candidate@demo.com   | password123 |
| Recruiter | recruiter@demo.com   | password123 |

## Project layout
```
backend/
  gateway.py              # :8000 — CORS + reverse proxy to the services
  common/                 # shared library imported by every service
    config.py             #   env, JWT settings, service URLs, screening threshold
    db.py                 #   SQLAlchemy Base + per-service SQLite helpers
    security.py           #   JWT mint/verify + bcrypt; get_current_user / require_recruiter
    groq_clients.py       #   Whisper STT, Llama chat, Orpheus TTS wrappers
  services/
    auth/                 # :9001 — signup / login / me  (JWT, roles)
    jobs/                 # :9002 — jobs CRUD + applications + apply orchestration
    screening/            # :9003 — PDF parse + LangGraph resume screening
    interview/            # :9004 — voice interview (LangGraph interrupt loop)
  seed.py                 # demo users + jobs
  start_all.sh            # launch everything
frontend/
  src/
    api.js                # fetch wrapper → gateway, bearer token
    auth.jsx              # AuthContext (login/signup/logout, /auth/me bootstrap)
    App.jsx               # routes + role-gated Protected wrapper
    components/           # Navbar + shared UI (ScoreRing, StatusBadge, …)
    pages/                # Login, Signup, Jobs, JobDetail, Apply, Interview,
                          # CandidateDashboard, RecruiterDashboard, NewJob, JobApplicants
```

## Notes
- **Ports:** services run on `9001–9004` and the gateway on `8000` to avoid
  colliding with other local stacks that grab `80xx`. Override any URL via
  `.env`.
- **State is in-memory** for interviews (`MemorySaver`); restarting interview-service
  loses in-progress interviews. Swap in the Postgres checkpointer for production.
- **Each service owns its DB** under `backend/data/*.db` (gitignored). Delete a
  file to reset that service; re-run `seed.py` to repopulate.
- **Mic access needs a secure context** — `localhost` counts, so dev works; a LAN
  IP needs HTTPS.
- **Model IDs** for Groq STT/LLM/TTS are at the top of `common/groq_clients.py`;
  if one 404s, check console.groq.com/docs/models.
- The original single-file POC (`backend/main.py`, `interview_graph.py`,
  `groq_clients.py`) is superseded by `services/interview/` and can be removed.
