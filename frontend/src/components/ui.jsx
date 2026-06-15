// Small presentational helpers shared across pages.

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-3 text-slate-500">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

const STATUS_STYLES = {
  screening: "bg-amber-100 text-amber-800",
  interview_invited: "bg-blue-100 text-blue-800",
  interview_completed: "bg-violet-100 text-violet-800",
  rejected: "bg-rose-100 text-rose-700",
  hired: "bg-brand-100 text-brand-800",
  declined: "bg-slate-200 text-slate-600",
};

const STATUS_LABELS = {
  screening: "Screening",
  interview_invited: "Interview invited",
  interview_completed: "Interview completed",
  rejected: "Not advanced",
  hired: "Hired",
  declined: "Declined",
};

export function StatusBadge({ status }) {
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        STATUS_STYLES[status] || "bg-slate-100 text-slate-600"
      }`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export function ScoreRing({ score }) {
  const value = Math.max(0, Math.min(100, Number(score) || 0));
  const color =
    value >= 75 ? "text-brand-600" : value >= 50 ? "text-amber-500" : "text-rose-500";
  return (
    <div className="relative h-16 w-16 shrink-0">
      <svg viewBox="0 0 36 36" className="h-16 w-16 -rotate-90">
        <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e2e8f0" strokeWidth="3" />
        <circle
          cx="18"
          cy="18"
          r="15.9"
          fill="none"
          className={color}
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={`${value} 100`}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-slate-700">
        {value}
      </span>
    </div>
  );
}

export function Pill({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    green: "bg-brand-50 text-brand-700",
    red: "bg-rose-50 text-rose-600",
  };
  return (
    <span className={`inline-block rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Alert({ children, tone = "info" }) {
  const tones = {
    info: "bg-blue-50 text-blue-800 border-blue-200",
    error: "bg-rose-50 text-rose-700 border-rose-200",
    success: "bg-brand-50 text-brand-800 border-brand-200",
  };
  if (!children) return null;
  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>
  );
}

export function salaryLabel(job) {
  const { salary_min, salary_max } = job;
  const fmt = (n) => `$${Math.round(n / 1000)}k`;
  if (salary_min && salary_max) return `${fmt(salary_min)} – ${fmt(salary_max)}`;
  if (salary_min) return `from ${fmt(salary_min)}`;
  if (salary_max) return `up to ${fmt(salary_max)}`;
  return "Not disclosed";
}
