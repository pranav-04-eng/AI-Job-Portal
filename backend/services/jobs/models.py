from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from common.db import Base


def _now():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    recruiter_id = Column(Integer, index=True, nullable=False)
    recruiter_name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    title = Column(String, nullable=False, index=True)
    location = Column(String, default="Remote")
    employment_type = Column(String, default="Full-time")  # Full-time | Part-time | Contract
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, index=True, nullable=False)
    candidate_id = Column(Integer, index=True, nullable=False)
    candidate_name = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)

    # Lifecycle: rejected -> (screen failed) | interview_invited -> interviewing
    #            -> interview_completed -> hired / declined
    status = Column(String, default="screening", index=True)

    resume_text = Column(Text, default="")

    # Resume-screening verdict (from screening-service / LangGraph)
    screening_score = Column(Integer, nullable=True)
    screening_recommendation = Column(String, nullable=True)
    screening_summary = Column(Text, default="")
    screening_strengths = Column(Text, default="[]")   # JSON-encoded list
    screening_gaps = Column(Text, default="[]")        # JSON-encoded list
    matched_skills = Column(Text, default="[]")        # JSON-encoded list
    missing_skills = Column(Text, default="[]")        # JSON-encoded list

    # Voice-interview outcome (from interview-service)
    interview_thread_id = Column(String, nullable=True)
    interview_score = Column(Integer, nullable=True)
    interview_recommendation = Column(String, nullable=True)
    interview_summary = Column(Text, default="")
    interview_assessment = Column(Text, default="{}")  # JSON-encoded dict

    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
