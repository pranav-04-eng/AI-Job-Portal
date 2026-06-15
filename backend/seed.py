"""Seed demo data: one recruiter, one candidate, and a handful of jobs.

    PYTHONPATH=. .venv/bin/python seed.py

Idempotent — re-running it won't duplicate the demo accounts or jobs.

Demo logins:
    recruiter@demo.com / password123   (posts jobs, reviews applicants)
    candidate@demo.com / password123   (browses + applies)
"""
from common.config import db_path
from common.db import init_db, make_session
from common.security import hash_password
from services.auth.models import User
from services.jobs.models import Job

RECRUITER = {"email": "recruiter@demo.com", "full_name": "Dana Recruiter",
             "password": "password123", "role": "recruiter"}
CANDIDATE = {"email": "candidate@demo.com", "full_name": "Sam Candidate",
             "password": "password123", "role": "candidate"}

JOBS = [
    {
        "title": "Senior Python Engineer",
        "company": "Northwind Labs",
        "location": "Remote (US)",
        "employment_type": "Full-time",
        "salary_min": 140000, "salary_max": 180000,
        "description": "Build and scale the data platform powering our analytics "
                       "products. You'll own services end-to-end, from API design "
                       "to deployment.",
        "requirements": "5+ years Python. Strong with FastAPI or Django, "
                        "PostgreSQL, and AWS. Experience with async, testing, and "
                        "CI/CD. Bonus: LangGraph / LLM orchestration.",
    },
    {
        "title": "Frontend Engineer (React)",
        "company": "Brightwave",
        "location": "New York, NY",
        "employment_type": "Full-time",
        "salary_min": 120000, "salary_max": 155000,
        "description": "Craft delightful, accessible UIs for our hiring platform. "
                       "Work closely with design and backend to ship fast.",
        "requirements": "3+ years React. Solid TypeScript, modern CSS (Tailwind), "
                        "and state management. Care about performance and a11y.",
    },
    {
        "title": "ML Engineer, NLP",
        "company": "Northwind Labs",
        "location": "Remote (Global)",
        "employment_type": "Contract",
        "salary_min": 130000, "salary_max": 170000,
        "description": "Design retrieval and evaluation pipelines for our LLM "
                       "features. Ship models that hold up in production.",
        "requirements": "Experience with LLMs, RAG, and evaluation. Python, "
                        "PyTorch or JAX. Comfortable with prompt + graph "
                        "orchestration frameworks.",
    },
    {
        "title": "Product Designer",
        "company": "Brightwave",
        "location": "San Francisco, CA",
        "employment_type": "Full-time",
        "salary_min": 110000, "salary_max": 145000,
        "description": "Own the end-to-end design of candidate-facing flows, from "
                       "research through high-fidelity prototypes.",
        "requirements": "4+ years product design. Strong portfolio, Figma, and a "
                        "track record shipping web products.",
    },
]


def get_or_create_user(SessionLocal, spec) -> User:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == spec["email"]).first()
        if user:
            return user
        user = User(
            email=spec["email"],
            full_name=spec["full_name"],
            password_hash=hash_password(spec["password"]),
            role=spec["role"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def main():
    auth_url, jobs_url = db_path("auth"), db_path("jobs")
    init_db(auth_url)
    init_db(jobs_url)

    AuthSession = make_session(auth_url)
    JobsSession = make_session(jobs_url)

    recruiter = get_or_create_user(AuthSession, RECRUITER)
    candidate = get_or_create_user(AuthSession, CANDIDATE)
    print(f"Recruiter: {recruiter.email} (id={recruiter.id})")
    print(f"Candidate: {candidate.email} (id={candidate.id})")

    db = JobsSession()
    try:
        created = 0
        for spec in JOBS:
            exists = (
                db.query(Job)
                .filter(Job.title == spec["title"], Job.company == spec["company"])
                .first()
            )
            if exists:
                continue
            db.add(Job(recruiter_id=recruiter.id, recruiter_name=recruiter.email, **spec))
            created += 1
        db.commit()
        total = db.query(Job).count()
        print(f"Jobs: +{created} created, {total} total.")
    finally:
        db.close()

    print("\nDemo logins:")
    print("  recruiter@demo.com / password123")
    print("  candidate@demo.com / password123")


if __name__ == "__main__":
    main()
