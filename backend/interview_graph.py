"""The interview as a LangGraph state machine.

Flow:  generate_question -> await_answer -(loop)-> ... -> assess -> END

`await_answer` calls interrupt(), which pauses the whole graph and checkpoints
its state. The web layer resumes it with Command(resume=<transcript>) once the
candidate has spoken. interrupt() is the FIRST line of that node on purpose:
LangGraph re-runs a node from the top when it resumes, so anything before the
interrupt would run twice. Keeping it first makes resume side-effect-free.

This POC uses MemorySaver (in-memory). For the real system, swap in the
Postgres checkpointer so paused interviews survive restarts.
"""
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

import groq_clients as groq

MAX_QUESTIONS = 3


class InterviewState(TypedDict):
    role: str
    count: int                  # how many questions have been asked
    current_question: str
    history: List[Dict[str, str]]   # [{"q": ..., "a": ...}, ...]
    assessment: dict


def generate_question(state: InterviewState) -> dict:
    """Ask the LLM for the next question, given the role and what's been said."""
    transcript = "\n".join(
        f"Q{i+1}: {t['q']}\nA{i+1}: {t['a']}" for i, t in enumerate(state["history"])
    ) or "(no questions asked yet)"

    messages = [
        {
            "role": "system",
            "content": (
                f"You are a professional interviewer for a {state['role']} role. "
                "Ask ONE concise spoken-style interview question at a time. "
                "If there is prior conversation, ask a natural follow-up that digs "
                "deeper or moves to a new relevant area. Return only the question "
                "text, no numbering or preamble."
            ),
        },
        {"role": "user", "content": f"Conversation so far:\n{transcript}\n\nNext question:"},
    ]
    question = groq.chat(messages).strip().strip('"')
    return {"current_question": question, "count": state["count"] + 1}


def await_answer(state: InterviewState) -> dict:
    """Pause here until the web layer resumes with the transcribed answer."""
    answer = interrupt({
        "question": state["current_question"],
        "number": state["count"],
    })
    new_history = state["history"] + [
        {"q": state["current_question"], "a": answer}
    ]
    return {"history": new_history}


def route_after_answer(state: InterviewState) -> str:
    return "assess" if state["count"] >= MAX_QUESTIONS else "continue"


def assess(state: InterviewState) -> dict:
    """Score the full transcript and return a structured verdict."""
    transcript = "\n".join(
        f"Q{i+1}: {t['q']}\nA{i+1}: {t['a']}" for i, t in enumerate(state["history"])
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"You are assessing a candidate for a {state['role']} role based on "
                "their interview transcript. Return a JSON object with exactly these "
                "keys: overall_score (integer 0-100), strengths (array of strings), "
                "weaknesses (array of strings), recommendation (one of: advance, hold, "
                "reject), summary (2-3 sentence string). Be fair and base everything "
                "only on what the candidate actually said."
            ),
        },
        {"role": "user", "content": f"Transcript:\n{transcript}"},
    ]
    import json
    raw = groq.chat(messages, json_mode=True)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"overall_score": None, "summary": raw,
                  "strengths": [], "weaknesses": [], "recommendation": "hold"}
    return {"assessment": parsed}


def build_graph():
    b = StateGraph(InterviewState)
    b.add_node("generate_question", generate_question)
    b.add_node("await_answer", await_answer)
    b.add_node("assess", assess)
    b.add_edge(START, "generate_question")
    b.add_edge("generate_question", "await_answer")
    b.add_conditional_edges(
        "await_answer",
        route_after_answer,
        {"continue": "generate_question", "assess": "assess"},
    )
    b.add_edge("assess", END)
    return b.compile(checkpointer=MemorySaver())


graph = build_graph()
