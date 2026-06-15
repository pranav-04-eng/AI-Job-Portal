"""FastAPI layer that drives the interview graph.

POST /interview/start   -> creates a session, returns the first question (text + audio)
POST /interview/answer  -> transcribes the uploaded answer, resumes the graph,
                           returns the next question OR the final assessment
"""
import uuid
from dotenv import load_dotenv
load_dotenv()  # load GROQ_API_KEY from .env before importing the Groq client

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langgraph.types import Command

import groq_clients as groq
from interview_graph import graph

app = FastAPI(title="Voice Interview POC")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],   # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    role: str = "Software Engineer"


def _extract_interrupt(result: dict):
    """If the graph paused, return the interrupt payload, else None."""
    intr = result.get("__interrupt__")
    if intr:
        return intr[0].value
    return None


def _synthesize_or_none(text: str):
    """Best-effort TTS. If terms were not accepted, keep interview running without audio."""
    try:
        return groq.synthesize(text), None
    except groq.TTSModelTermsRequired as exc:
        return None, str(exc)


@app.post("/interview/start")
def start(req: StartRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    initial = {"role": req.role, "count": 0, "current_question": "",
               "history": [], "assessment": {}}

    result = graph.invoke(initial, config)
    payload = _extract_interrupt(result)
    if not payload:
        raise HTTPException(500, "Graph did not pause for the first question")

    question = payload["question"]
    question_audio, audio_warning = _synthesize_or_none(question)
    return {
        "thread_id": thread_id,
        "done": False,
        "question_number": payload["number"],
        "question_text": question,
        "question_audio": question_audio,  # base64 wav or None
        "audio_warning": audio_warning,
    }


@app.post("/interview/answer")
async def answer(thread_id: str = Form(...), audio: UploadFile = File(...)):
    config = {"configurable": {"thread_id": thread_id}}

    audio_bytes = await audio.read()
    transcript = groq.transcribe(audio_bytes, filename=audio.filename or "answer.webm")

    result = graph.invoke(Command(resume=transcript), config)
    payload = _extract_interrupt(result)

    if payload:  # another question is coming
        question = payload["question"]
        question_audio, audio_warning = _synthesize_or_none(question)
        return {
            "done": False,
            "transcript": transcript,
            "question_number": payload["number"],
            "question_text": question,
            "question_audio": question_audio,
            "audio_warning": audio_warning,
        }

    # No interrupt -> the graph reached END. result holds the final state.
    assessment = result.get("assessment", {})
    closing = "Thank you, that concludes the interview. Your responses are being reviewed."
    closing_audio, audio_warning = _synthesize_or_none(closing)
    return {
        "done": True,
        "transcript": transcript,
        "assessment": assessment,
        "closing_text": closing,
        "closing_audio": closing_audio,
        "audio_warning": audio_warning,
    }


@app.get("/")
def health():
    return {"status": "ok"}
