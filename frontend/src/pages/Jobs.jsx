import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Spinner, Pill, salaryLabel } from "../components/ui.jsx";

function JobCard({ job }) {
  return (
    <Link
      to={`/jobs/${job.id}`}
      className="card block p-5 transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{job.title}</h3>
          <p className="text-sm text-slate-500">
            {job.company} · {job.location}
          </p>
        </div>
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-lg font-bold text-brand-700">
          {job.company?.[0]?.toUpperCase() || "?"}
        </div>
      </div>
      <p className="mt-3 line-clamp-2 text-sm text-slate-600">{job.description}</p>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Pill tone="green">{salaryLabel(job)}</Pill>
        <Pill>{job.employment_type}</Pill>
      </div>
    </Link>
  );
}

export default function Jobs() {
  const [jobs, setJobs] = useState(null);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setJobs(null);
    const qs = search ? `?q=${encodeURIComponent(search)}` : "";
    api
      .get(`/jobs${qs}`, { auth: false })
      .then((data) => active && setJobs(data))
      .catch((e) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [search]);

  return (
    <div>
      {/* Hero / search */}
      <section className="mb-8 rounded-2xl bg-gradient-to-br from-brand-700 to-brand-500 px-6 py-10 text-white">
        <h1 className="text-3xl font-extrabold sm:text-4xl">Find a job that loves you back</h1>
        <p className="mt-2 max-w-xl text-brand-50">
          Apply once, let AI screen your resume, and interview by voice — all in one place.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(q.trim());
          }}
          className="mt-6 flex max-w-xl gap-2"
        >
          <input
            className="input flex-1 text-slate-800"
            placeholder="Search title or company…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button className="btn bg-white text-brand-700 hover:bg-brand-50">Search</button>
        </form>
      </section>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-slate-900">
          {search ? `Results for “${search}”` : "Open roles"}
        </h2>
        {search && (
          <button
            onClick={() => {
              setQ("");
              setSearch("");
            }}
            className="text-sm text-brand-700 hover:underline"
          >
            Clear
          </button>
        )}
      </div>

      {error && <p className="text-rose-600">{error}</p>}
      {!jobs && !error && <Spinner label="Loading jobs…" />}
      {jobs && jobs.length === 0 && (
        <p className="text-slate-500">No jobs found. Try a different search.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {jobs?.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>
    </div>
  );
}
