import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Alert } from "../components/ui.jsx";

export default function NewJob() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "",
    company: "",
    location: "Remote",
    employment_type: "Full-time",
    description: "",
    requirements: "",
    salary_min: "",
    salary_max: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = {
        ...form,
        salary_min: form.salary_min ? Number(form.salary_min) : null,
        salary_max: form.salary_max ? Number(form.salary_max) : null,
      };
      const job = await api.post("/jobs", payload);
      navigate(`/recruiter/jobs/${job.id}/applicants`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/recruiter" className="text-sm text-brand-700 hover:underline">
        ← Back to dashboard
      </Link>
      <div className="card mt-3 p-6">
        <h1 className="text-xl font-bold text-slate-900">Post a job</h1>
        <p className="mt-1 text-sm text-slate-500">
          The description and requirements are what the AI screener matches resumes against — be
          specific.
        </p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Job title</label>
              <input className="input" value={form.title} onChange={set("title")} required />
            </div>
            <div>
              <label className="label">Company</label>
              <input className="input" value={form.company} onChange={set("company")} required />
            </div>
            <div>
              <label className="label">Location</label>
              <input className="input" value={form.location} onChange={set("location")} />
            </div>
            <div>
              <label className="label">Employment type</label>
              <select className="input" value={form.employment_type} onChange={set("employment_type")}>
                <option>Full-time</option>
                <option>Part-time</option>
                <option>Contract</option>
                <option>Internship</option>
              </select>
            </div>
            <div>
              <label className="label">Salary min ($)</label>
              <input
                className="input"
                type="number"
                value={form.salary_min}
                onChange={set("salary_min")}
              />
            </div>
            <div>
              <label className="label">Salary max ($)</label>
              <input
                className="input"
                type="number"
                value={form.salary_max}
                onChange={set("salary_max")}
              />
            </div>
          </div>

          <div>
            <label className="label">Description</label>
            <textarea className="input min-h-24" value={form.description} onChange={set("description")} />
          </div>
          <div>
            <label className="label">Requirements</label>
            <textarea
              className="input min-h-24"
              value={form.requirements}
              onChange={set("requirements")}
              placeholder="e.g. 5+ years Python, FastAPI, PostgreSQL, AWS…"
            />
          </div>

          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Posting…" : "Publish job"}
          </button>
        </form>
      </div>
    </div>
  );
}
