import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Spinner, ScoreRing, StatusBadge, Pill, Alert } from "../components/ui.jsx";

function ApplicantCard({ app, onDecision }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const s = app.screening || {};
  const iv = app.interview || {};

  async function decide(decision) {
    setBusy(true);
    try {
      await onDecision(app.id, decision);
    } finally {
      setBusy(false);
    }
  }

  const decided = app.status === "hired" || app.status === "declined";

  return (
    <div className="card p-5">
      <div className="flex items-start gap-4">
        <ScoreRing score={s.score} />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-slate-900">{app.candidate_name}</h3>
            <StatusBadge status={app.status} />
          </div>
          <p className="text-sm text-slate-500">{app.candidate_email}</p>
          <p className="mt-2 text-sm text-slate-600">{s.summary}</p>

          {iv.score != null && (
            <p className="mt-1 text-sm text-violet-700">
              Voice interview: <strong>{iv.score}</strong> · {iv.recommendation}
            </p>
          )}

          <button
            onClick={() => setOpen((o) => !o)}
            className="mt-2 text-sm font-medium text-brand-700 hover:underline"
          >
            {open ? "Hide details" : "View details"}
          </button>

          {open && (
            <div className="mt-3 space-y-3 border-t border-slate-100 pt-3 text-sm">
              {s.matched_skills?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {s.matched_skills.map((x, i) => (
                    <Pill key={`m${i}`} tone="green">{x}</Pill>
                  ))}
                  {s.missing_skills?.map((x, i) => (
                    <Pill key={`x${i}`} tone="red">{x}</Pill>
                  ))}
                </div>
              )}
              {iv.summary && (
                <p className="text-slate-600">
                  <span className="font-semibold">Interview notes:</span> {iv.summary}
                </p>
              )}
            </div>
          )}
        </div>

        {!decided && app.status === "interview_completed" && (
          <div className="flex shrink-0 flex-col gap-2">
            <button onClick={() => decide("hired")} disabled={busy} className="btn-primary">
              Hire
            </button>
            <button onClick={() => decide("declined")} disabled={busy} className="btn-ghost">
              Decline
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function JobApplicants() {
  const { id } = useParams();
  const [apps, setApps] = useState(null);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  function load() {
    api.get(`/jobs/${id}`, { auth: false }).then(setJob).catch(() => {});
    api
      .get(`/jobs/${id}/applications`)
      .then(setApps)
      .catch((e) => setError(e.message));
  }
  useEffect(load, [id]);

  async function onDecision(appId, decision) {
    await api.patch(`/applications/${appId}/decision`, { decision });
    load();
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/recruiter" className="text-sm text-brand-700 hover:underline">
        ← Back to dashboard
      </Link>
      <h1 className="mt-3 text-2xl font-bold text-slate-900">
        Applicants{job ? ` · ${job.title}` : ""}
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Ranked by AI screening score. Hire/decline opens once a candidate finishes the interview.
      </p>

      <div className="mt-6 space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        {!apps && !error && <Spinner />}
        {apps && apps.length === 0 && (
          <div className="card p-8 text-center text-slate-600">No applicants yet.</div>
        )}
        {apps?.map((a) => (
          <ApplicantCard key={a.id} app={a} onDecision={onDecision} />
        ))}
      </div>
    </div>
  );
}
