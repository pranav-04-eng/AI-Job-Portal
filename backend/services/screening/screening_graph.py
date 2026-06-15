"""Resume screening as a LangGraph state machine.

Flow:  extract_profile -> analyze_fit -> score -> END

Each node is one focused LLM call, so the model reasons in stages instead of
being asked to do everything in a single prompt:

  1. extract_profile  — pull a structured profile out of the raw resume text
  2. analyze_fit      — compare that profile against the job's requirements
  3. score            — turn the fit analysis into a 0-100 score + recommendation

This is deliberately linear (no human-in-the-loop interrupt like the interview
graph) — screening runs to completion in one request. It's a graph rather than
three function calls so the stages are inspectable, swappable, and could later
fan out (e.g. a parallel "culture fit" branch) without rewiring the callers.
"""
import json
from typing import List, TypedDict

from langgraph.graph import START, END, StateGraph

from common import groq_clients as groq


class ScreeningState(TypedDict):
    # Inputs
    job_title: str
    job_description: str
    job_requirements: str
    resume_text: str
    # Accumulated by the nodes
    profile: dict
    fit: dict
    result: dict


def _safe_json(raw: str, fallback: dict) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def extract_profile(state: ScreeningState) -> dict:
    """Turn unstructured resume text into a structured candidate profile."""
    messages = [
        {
            "role": "system",
            "content": (
                "You extract a structured profile from a candidate's resume. "
                "Return a JSON object with exactly these keys: "
                "skills (array of strings), years_experience (number), "
                "titles (array of past job titles), education (string), "
                "summary (2-3 sentence string). Base everything ONLY on the "
                "resume text; do not invent experience."
            ),
        },
        {"role": "user", "content": f"Resume:\n{state['resume_text']}"},
    ]
    raw = groq.chat(messages, json_mode=True)
    profile = _safe_json(
        raw,
        {"skills": [], "years_experience": 0, "titles": [], "education": "", "summary": ""},
    )
    return {"profile": profile}


def analyze_fit(state: ScreeningState) -> dict:
    """Compare the extracted profile against the job's requirements."""
    messages = [
        {
            "role": "system",
            "content": (
                "You assess how well a candidate fits a specific job. Compare the "
                "candidate profile and resume against the job requirements. Return "
                "a JSON object with exactly these keys: matched_skills (array of "
                "strings the candidate clearly has that the job needs), "
                "missing_skills (array of required things the candidate lacks), "
                "concerns (array of short strings), notes (2-3 sentence string). "
                "Be specific and fair."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Job title: {state['job_title']}\n"
                f"Job description: {state['job_description']}\n"
                f"Job requirements: {state['job_requirements']}\n\n"
                f"Candidate profile (JSON): {json.dumps(state['profile'])}\n"
                f"Resume:\n{state['resume_text']}"
            ),
        },
    ]
    raw = groq.chat(messages, json_mode=True)
    fit = _safe_json(
        raw,
        {"matched_skills": [], "missing_skills": [], "concerns": [], "notes": ""},
    )
    return {"fit": fit}


def score(state: ScreeningState) -> dict:
    """Roll the fit analysis up into a single score + recommendation."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are the final resume screener. Given the candidate profile and "
                "the fit analysis, produce a JSON object with exactly these keys: "
                "score (integer 0-100 for how well the candidate matches the role), "
                "recommendation (one of: advance, hold, reject), "
                "strengths (array of strings), gaps (array of strings), "
                "summary (2-3 sentence string explaining the score). "
                "A score of 60+ means the candidate should advance to an interview."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Job title: {state['job_title']}\n"
                f"Profile (JSON): {json.dumps(state['profile'])}\n"
                f"Fit analysis (JSON): {json.dumps(state['fit'])}"
            ),
        },
    ]
    raw = groq.chat(messages, json_mode=True)
    parsed = _safe_json(
        raw,
        {"score": 0, "recommendation": "hold", "strengths": [], "gaps": [],
         "summary": raw or "Could not parse screening result."},
    )

    # Fold in the fit detail so callers get one rich object back.
    result = {
        "score": int(parsed.get("score") or 0),
        "recommendation": parsed.get("recommendation", "hold"),
        "summary": parsed.get("summary", ""),
        "strengths": parsed.get("strengths", []),
        "gaps": parsed.get("gaps", []),
        "matched_skills": state["fit"].get("matched_skills", []),
        "missing_skills": state["fit"].get("missing_skills", []),
        "profile": state["profile"],
    }
    return {"result": result}


def build_graph():
    b = StateGraph(ScreeningState)
    b.add_node("extract_profile", extract_profile)
    b.add_node("analyze_fit", analyze_fit)
    b.add_node("score", score)
    b.add_edge(START, "extract_profile")
    b.add_edge("extract_profile", "analyze_fit")
    b.add_edge("analyze_fit", "score")
    b.add_edge("score", END)
    return b.compile()


graph = build_graph()


def screen_resume(resume_text: str, job_title: str, job_description: str,
                  job_requirements: str) -> dict:
    """Run the full screening graph and return the `result` dict."""
    final = graph.invoke({
        "job_title": job_title,
        "job_description": job_description,
        "job_requirements": job_requirements,
        "resume_text": resume_text,
        "profile": {},
        "fit": {},
        "result": {},
    })
    return final["result"]
