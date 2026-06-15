"""interview-service (:8004) — the AI voice interview.

POST /interview/start   -> creates a session, returns the first question (text + audio)
POST /interview/answer  -> transcribes the uploaded answer, resumes the graph,
                           returns the next question OR the final assessment

Only candidates who passed resume screening reach this (the frontend gates it),
so the service simply requires a valid candidate token and runs the graph.
"""
import uuid

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from langgraph.types import Command
from pydantic import BaseModel

from common import groq_clients as groq
from common.security import get_current_user

from .interview_graph import graph

app = FastAPI(title="interview-service")


class StartRequest(BaseModel):
    role: str = "Software Engineer"
    application_id: int | None = None  # for the candidate's own tracking


def _extract_interrupt(result: dict):
    intr = result.get("__interrupt__")
    return intr[0].value if intr else None


def _synthesize_or_none(text: str):
    """Best-effort TTS. If model terms aren't accepted, run text-only."""
    try:
        return groq.synthesize(text), None
    except groq.TTSModelTermsRequired as exc:
        return None, str(exc)


@app.post("/interview/start")
def start(req: StartRequest, user=Depends(get_current_user)):
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
        "question_audio": question_audio,
        "audio_warning": audio_warning,
    }


@app.post("/interview/answer")
async def answer(
    thread_id: str = Form(...),
    audio: UploadFile = File(...),
    user=Depends(get_current_user),
):
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
    return {"status": "ok", "service": "interview"}
