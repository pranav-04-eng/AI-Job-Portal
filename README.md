# AI Voice Interview — POC

A proof-of-concept of the voice-based AI interview stage: the AI asks questions
out loud (Groq Orpheus TTS), you answer by speaking (Groq Whisper STT), and a
LangGraph state machine loops through a few questions, then scores you with an
LLM (Groq Llama). This is the "AI interview" node from the larger hiring pipeline.

## What happens
1. You pick a role and start the interview.
2. The graph generates question 1, the browser plays it as speech.
3. You record a spoken answer; it's transcribed and fed back into the graph
   via LangGraph's `interrupt()` / `Command(resume=...)` mechanism.
4. After 3 questions (`MAX_QUESTIONS` in `interview_graph.py`) the graph runs an
   assessment node and returns a structured score.

## Prerequisites
- Python 3.10+
- Node 18+
- A Groq API key (https://console.groq.com)

## Run the backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then put your real key in .env
uvicorn main:app --reload --port 8000
```

## Run the frontend (separate terminal)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Notes / things to know for a POC
- **Mic access needs a secure context.** `localhost` counts as secure, so the
  Vite dev server works. If you serve it from a LAN IP you'll need HTTPS.
- **State is in-memory** (`MemorySaver`). Restarting the backend loses any
  in-progress interview. For the real system, use the Postgres checkpointer so
  paused sessions survive restarts — that's what makes the multi-day HR-approval
  gate possible.
- **Model IDs change.** The Groq STT/TTS/LLM model names are set at the top of
  `groq_clients.py`. If one returns a 404, check console.groq.com/docs/models.
- **Latency.** TTS + STT + LLM are each a network round trip, so expect a couple
  of seconds between turns. `whisper-large-v3-turbo` is faster if you want it.
- **Browsers record WebM/Opus**, which Groq's Whisper endpoint accepts directly —
  no ffmpeg conversion needed in this POC.
- This covers the interview loop only. Wiring it into the full pipeline means
  this graph becomes the "AI interview" interrupt node, and the assessment score
  feeds the next decision/HR step.
