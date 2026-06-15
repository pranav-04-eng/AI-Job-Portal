"""jobs-service (:8002) — the job board + application pipeline.

Candidates browse/apply; recruiters post jobs and review applicants.

The apply flow is the orchestration hub: when a candidate uploads a resume,
this service forwards it to screening-service (LangGraph), stores the verdict,
and gates the voice interview on the screening score (SCREEN_PASS_THRESHOLD).
"""
import json

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.config import SCREEN_PASS_THRESHOLD, SCREENING_URL, db_path
from common.db import init_db, make_session
from common.security import get_current_user, require_recruiter

from .models import Application, Job

DB_URL = db_path("jobs")
SessionLocal = make_session(DB_URL)
init_db(DB_URL)

app = FastAPI(title="jobs-service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Serialization
# --------------------------------------------------------------------------- #
def job_dict(j: Job) -> dict:
    return {
        "id": j.id,
        "recruiter_id": j.recruiter_id,
        "recruiter_name": j.recruiter_name,
        "company": j.company,
        "title": j.title,
        "location": j.location,
        "employment_type": j.employment_type,
        "description": j.description,
        "requirements": j.requirements,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "created_at": j.created_at.isoformat() if j.created_at else None,
    }


def _loads(s, default):
    try:
        return json.loads(s) if s else default
    except (json.JSONDecodeError, TypeError):
        return default


def application_dict(a: Application, job: Job | None = None) -> dict:
    return {
        "id": a.id,
        "job_id": a.job_id,
        "job": job_dict(job) if job else None,
        "candidate_id": a.candidate_id,
        "candidate_name": a.candidate_name,
        "candidate_email": a.candidate_email,
        "status": a.status,
        "screening": {
            "score": a.screening_score,
            "recommendation": a.screening_recommendation,
            "summary": a.screening_summary,
            "strengths": _loads(a.screening_strengths, []),
            "gaps": _loads(a.screening_gaps, []),
            "matched_skills": _loads(a.matched_skills, []),
            "missing_skills": _loads(a.missing_skills, []),
        },
        "interview": {
            "thread_id": a.interview_thread_id,
            "score": a.interview_score,
            "recommendation": a.interview_recommendation,
            "summary": a.interview_summary,
            "assessment": _loads(a.interview_assessment, {}),
        },
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #
class JobIn(BaseModel):
    title: str
    company: str
    location: str = "Remote"
    employment_type: str = "Full-time"
    description: str = ""
    requirements: str = ""
    salary_min: int | None = None
    salary_max: int | None = None


class InterviewResultIn(BaseModel):
    thread_id: str | None = None
    score: int | None = None
    recommendation: str | None = None
    summary: str = ""
    assessment: dict = {}


class DecisionIn(BaseModel):
    decision: str  # "hired" | "declined"


# --------------------------------------------------------------------------- #
# Public browsing
# --------------------------------------------------------------------------- #
@app.get("/jobs")
def list_jobs(
    q: str | None = Query(None, description="search in title/company"),
    location: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)
    if q:
        like = f"%{q}%"
        query = query.filter((Job.title.ilike(like)) | (Job.company.ilike(like)))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    jobs = query.order_by(Job.created_at.desc()).all()
    return [job_dict(j) for j in jobs]


@app.get("/jobs/mine")
def my_jobs(recruiter=Depends(require_recruiter), db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.recruiter_id == recruiter["user_id"])
        .order_by(Job.created_at.desc())
        .all()
    )
    # Attach a quick applicant count for the recruiter dashboard.
    out = []
    for j in jobs:
        d = job_dict(j)
        d["applicant_count"] = db.query(Application).filter(Application.job_id == j.id).count()
        out.append(d)
    return out


@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job_dict(job)


# --------------------------------------------------------------------------- #
# Recruiter: post jobs / review applicants
# --------------------------------------------------------------------------- #
@app.post("/jobs", status_code=201)
def create_job(body: JobIn, recruiter=Depends(require_recruiter), db: Session = Depends(get_db)):
    job = Job(
        recruiter_id=recruiter["user_id"],
        recruiter_name=recruiter.get("email", "recruiter"),
        **body.model_dump(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job_dict(job)


@app.get("/jobs/{job_id}/applications")
def job_applications(job_id: int, recruiter=Depends(require_recruiter), db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.recruiter_id != recruiter["user_id"]:
        raise HTTPException(403, "Not your job posting")
    apps = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.screening_score.desc().nullslast())
        .all()
    )
    return [application_dict(a, job) for a in apps]


@app.patch("/applications/{app_id}/decision")
def recruiter_decision(
    app_id: int,
    body: DecisionIn,
    recruiter=Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    if body.decision not in ("hired", "declined"):
        raise HTTPException(400, "decision must be 'hired' or 'declined'")
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    job = db.get(Job, a.job_id)
    if not job or job.recruiter_id != recruiter["user_id"]:
        raise HTTPException(403, "Not your job posting")
    a.status = body.decision
    db.commit()
    db.refresh(a)
    return application_dict(a, job)


# --------------------------------------------------------------------------- #
# Candidate: apply (screening orchestration) + track applications
# --------------------------------------------------------------------------- #
@app.post("/jobs/{job_id}/apply", status_code=201)
async def apply(
    job_id: int,
    resume: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user["role"] != "candidate":
        raise HTTPException(403, "Only candidates can apply")
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    existing = (
        db.query(Application)
        .filter(Application.job_id == job_id, Application.candidate_id == user["user_id"])
        .first()
    )
    if existing:
        raise HTTPException(409, "You have already applied to this job")

    resume_bytes = await resume.read()

    # Hand the PDF to screening-service (LangGraph). This is the orchestration.
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{SCREENING_URL}/screen",
                files={"resume": (resume.filename or "resume.pdf", resume_bytes,
                                  resume.content_type or "application/pdf")},
                data={
                    "job_title": job.title,
                    "job_description": job.description or "",
                    "job_requirements": job.requirements or "",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(502, f"Screening service unreachable: {exc}")

    if resp.status_code != 200:
        detail = resp.json().get("detail", resp.text) if resp.content else "screening failed"
        raise HTTPException(resp.status_code, f"Screening failed: {detail}")

    verdict = resp.json()
    score = int(verdict.get("score") or 0)
    passed = score >= SCREEN_PASS_THRESHOLD

    a = Application(
        job_id=job_id,
        candidate_id=user["user_id"],
        candidate_name=user.get("email", "candidate"),
        candidate_email=user.get("email", ""),
        status="interview_invited" if passed else "rejected",
        resume_text=verdict.get("resume_text", ""),
        screening_score=score,
        screening_recommendation=verdict.get("recommendation"),
        screening_summary=verdict.get("summary", ""),
        screening_strengths=json.dumps(verdict.get("strengths", [])),
        screening_gaps=json.dumps(verdict.get("gaps", [])),
        matched_skills=json.dumps(verdict.get("matched_skills", [])),
        missing_skills=json.dumps(verdict.get("missing_skills", [])),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return application_dict(a, job)


@app.get("/applications/me")
def my_applications(user=Depends(get_current_user), db: Session = Depends(get_db)):
    apps = (
        db.query(Application)
        .filter(Application.candidate_id == user["user_id"])
        .order_by(Application.created_at.desc())
        .all()
    )
    out = []
    for a in apps:
        out.append(application_dict(a, db.get(Job, a.job_id)))
    return out


@app.get("/applications/{app_id}")
def get_application(app_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    job = db.get(Job, a.job_id)
    owns = a.candidate_id == user["user_id"] or (job and job.recruiter_id == user["user_id"])
    if not owns:
        raise HTTPException(403, "Not your application")
    return application_dict(a, job)


@app.patch("/applications/{app_id}/interview-result")
def save_interview_result(
    app_id: int,
    body: InterviewResultIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist the voice-interview outcome once the candidate finishes it."""
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(404, "Application not found")
    if a.candidate_id != user["user_id"]:
        raise HTTPException(403, "Not your application")
    if a.status == "rejected":
        raise HTTPException(409, "This application did not pass screening")

    a.interview_thread_id = body.thread_id
    a.interview_score = body.score
    a.interview_recommendation = body.recommendation
    a.interview_summary = body.summary
    a.interview_assessment = json.dumps(body.assessment)
    a.status = "interview_completed"
    db.commit()
    db.refresh(a)
    return application_dict(a, db.get(Job, a.job_id))


@app.get("/")
def health():
    return {"status": "ok", "service": "jobs"}
