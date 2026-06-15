import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Spinner, Pill, salaryLabel } from "../components/ui.jsx";

export default function RecruiterDashboard() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/jobs/mine")
      .then(setJobs)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Your job postings</h1>
          <p className="mt-1 text-sm text-slate-500">Post roles and review screened applicants.</p>
        </div>
        <Link to="/recruiter/jobs/new" className="btn-primary">
          + Post a job
        </Link>
      </div>

      <div className="mt-6 space-y-4">
        {error && <p className="text-rose-600">{error}</p>}
        {!jobs && !error && <Spinner />}
        {jobs && jobs.length === 0 && (
          <div className="card p-8 text-center">
            <p className="text-slate-600">No postings yet.</p>
            <Link to="/recruiter/jobs/new" className="btn-primary mt-4">
              Post your first job
            </Link>
          </div>
        )}
        {jobs?.map((job) => (
          <div key={job.id} className="card flex items-center justify-between gap-4 p-5">
            <div>
              <h3 className="text-base font-semibold text-slate-900">{job.title}</h3>
              <p className="text-sm text-slate-500">
                {job.company} · {job.location}
              </p>
              <div className="mt-2 flex gap-2">
                <Pill tone="green">{salaryLabel(job)}</Pill>
                <Pill>{job.employment_type}</Pill>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className="text-sm text-slate-600">
                <strong>{job.applicant_count}</strong> applicant
                {job.applicant_count === 1 ? "" : "s"}
              </span>
              <Link to={`/recruiter/jobs/${job.id}/applicants`} className="btn-ghost">
                Review applicants
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
