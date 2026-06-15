import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Spinner, StatusBadge, ScoreRing } from "../components/ui.jsx";

function ApplicationRow({ app }) {
  const job = app.job || {};
  return (
    <div className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center">
      <ScoreRing score={app.screening?.score} />
      <div className="flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-semibold text-slate-900">{job.title || "Job"}</h3>
          <StatusBadge status={app.status} />
        </div>
        <p className="text-sm text-slate-500">
          {job.company} · applied {app.created_at ? new Date(app.created_at).toLocaleDateString() : ""}
        </p>
        {app.status === "interview_completed" && (
          <p className="mt-1 text-sm text-slate-600">
            Interview score: <strong>{app.interview?.score ?? "—"}</strong> · {app.interview?.recommendation}
          </p>
        )}
      </div>

      <div className="flex shrink-0 gap-2">
        {app.status === "interview_invited" && (
          <Link to={`/applications/${app.id}/interview`} className="btn-primary">
            Start interview
          </Link>
        )}
        {app.status === "interview_completed" && (
          <Link to={`/applications/${app.id}/interview`} className="btn-ghost">
            View result
          </Link>
        )}
        {job.id && (
          <Link to={`/jobs/${job.id}`} className="btn-ghost">
            View job
          </Link>
        )}
      </div>
    </div>
  );
}

export default function CandidateDashboard() {
  const [apps, setApps] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/applications/me")
      .then(setApps)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-900">My applications</h1>
      <p className="mt-1 text-sm text-slate-500">Track screening results and interview invites.</p>

      <div className="mt-6 space-y-4">
        {error && <p className="text-rose-600">{error}</p>}
        {!apps && !error && <Spinner />}
        {apps && apps.length === 0 && (
          <div className="card p-8 text-center">
            <p className="text-slate-600">You haven’t applied to anything yet.</p>
            <Link to="/" className="btn-primary mt-4">
              Browse jobs
            </Link>
          </div>
        )}
        {apps?.map((a) => (
          <ApplicationRow key={a.id} app={a} />
        ))}
      </div>
    </div>
  );
}
