import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Spinner, ScoreRing, Pill, Alert, StatusBadge } from "../components/ui.jsx";

function ScreeningResult({ application }) {
  const s = application.screening;
  const passed = application.status === "interview_invited";
  return (
    <div className="card p-6">
      <div className="flex items-center gap-4">
        <ScoreRing score={s.score} />
        <div>
          <h2 className="text-lg font-bold text-slate-900">
            {passed ? "You're through to the interview! 🎉" : "Thanks for applying"}
          </h2>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={application.status} />
            <span className="text-sm text-slate-500">
              recommendation: <strong>{s.recommendation}</strong>
            </span>
          </div>
        </div>
      </div>

      <p className="mt-4 text-slate-700">{s.summary}</p>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400">Strengths</h3>
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            {s.strengths?.length ? (
              s.strengths.map((x, i) => <li key={i}>✓ {x}</li>)
            ) : (
              <li className="text-slate-400">—</li>
            )}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400">Gaps</h3>
          <ul className="mt-2 space-y-1 text-sm text-slate-700">
            {s.gaps?.length ? (
              s.gaps.map((x, i) => <li key={i}>• {x}</li>)
            ) : (
              <li className="text-slate-400">—</li>
            )}
          </ul>
        </div>
      </div>

      {(s.matched_skills?.length > 0 || s.missing_skills?.length > 0) && (
        <div className="mt-5">
          <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400">Skill match</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {s.matched_skills?.map((x, i) => (
              <Pill key={`m${i}`} tone="green">
                {x}
              </Pill>
            ))}
            {s.missing_skills?.map((x, i) => (
              <Pill key={`x${i}`} tone="red">
                {x}
              </Pill>
            ))}
          </div>
        </div>
      )}

      <div className="mt-6 border-t border-slate-100 pt-5">
        {passed ? (
          <Link to={`/applications/${application.id}/interview`} className="btn-primary">
            Start voice interview →
          </Link>
        ) : (
          <Alert tone="info">
            Your resume didn’t clear the bar for this role this time. You can still apply to other
            roles — <Link to="/" className="font-semibold underline">browse jobs</Link>.
          </Alert>
        )}
      </div>
    </div>
  );
}

export default function Apply() {
  const { id } = useParams();
  const navigate = useNavigate();
  const fileRef = useRef(null);

  const [job, setJob] = useState(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get(`/jobs/${id}`, { auth: false }).then(setJob).catch((e) => setError(e.message));
  }, [id]);

  async function onSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      const form = new FormData();
      form.append("resume", file);
      const app = await api.postForm(`/jobs/${id}/apply`, form);
      setResult(app);
    } catch (err) {
      // already applied -> send them to their dashboard
      if (/already applied/i.test(err.message)) {
        navigate("/applications");
        return;
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="mb-4 text-xl font-bold text-slate-900">
          Application to {job?.title} at {job?.company}
        </h1>
        <ScreeningResult application={result} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to={`/jobs/${id}`} className="text-sm text-brand-700 hover:underline">
        ← Back to job
      </Link>
      <div className="card mt-3 p-6">
        <h1 className="text-xl font-bold text-slate-900">
          Apply{job ? ` — ${job.title}` : ""}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Upload your resume as a PDF. Our AI screener (LangGraph-orchestrated) reads it, compares it
          to the role, and scores your fit.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <label
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center transition hover:border-brand-400 hover:bg-brand-50"
            onClick={() => fileRef.current?.click()}
          >
            <span className="text-3xl">📄</span>
            <span className="mt-2 text-sm font-medium text-slate-700">
              {file ? file.name : "Click to choose your resume (PDF)"}
            </span>
            <span className="mt-1 text-xs text-slate-400">PDF only · max ~5MB</span>
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>

          <button className="btn-primary w-full" disabled={!file || busy}>
            {busy ? "AI is screening your resume…" : "Submit application"}
          </button>
          {busy && (
            <div className="flex justify-center">
              <Spinner label="Extracting text → analyzing fit → scoring" />
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
