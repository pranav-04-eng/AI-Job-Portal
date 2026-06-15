"""screening-service (:8003) — AI resume screening, LangGraph-orchestrated.

Receives a resume PDF + the job's text, extracts the resume text, runs it
through the screening graph (extract_profile -> analyze_fit -> score) and
returns a structured verdict. jobs-service calls this during /apply; it is not
exposed through the gateway.
"""
import io

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pypdf import PdfReader

from .screening_graph import screen_resume

app = FastAPI(title="screening-service")


def _extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # malformed / not a PDF
        raise HTTPException(400, f"Could not read PDF: {exc}")
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return text.strip()


@app.post("/screen")
async def screen(
    resume: UploadFile = File(...),
    job_title: str = Form(...),
    job_description: str = Form(""),
    job_requirements: str = Form(""),
):
    raw = await resume.read()
    if not raw:
        raise HTTPException(400, "Empty resume upload")

    resume_text = _extract_pdf_text(raw)
    if len(resume_text) < 30:
        raise HTTPException(
            422,
            "Could not extract readable text from the PDF. If it's a scanned "
            "image, please upload a text-based PDF.",
        )

    result = screen_resume(
        resume_text=resume_text,
        job_title=job_title,
        job_description=job_description,
        job_requirements=job_requirements,
    )
    # Hand the parsed text back too so jobs-service can store it on the application.
    result["resume_text"] = resume_text
    return result


@app.get("/")
def health():
    return {"status": "ok", "service": "screening"}
