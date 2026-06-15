import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Alert } from "../components/ui.jsx";

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "candidate",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await signup(form);
      navigate(user.role === "recruiter" ? "/recruiter" : "/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const RoleCard = ({ value, title, desc }) => (
    <button
      type="button"
      onClick={() => setForm({ ...form, role: value })}
      className={`flex-1 rounded-lg border p-3 text-left transition ${
        form.role === value
          ? "border-brand-500 bg-brand-50 ring-2 ring-brand-100"
          : "border-slate-300 hover:border-slate-400"
      }`}
    >
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      <div className="mt-0.5 text-xs text-slate-500">{desc}</div>
    </button>
  );

  return (
    <div className="mx-auto max-w-md">
      <div className="card p-8">
        <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
        <p className="mt-1 text-sm text-slate-500">Join HireVoice in a few seconds.</p>

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {error && <Alert tone="error">{error}</Alert>}

          <div className="flex gap-3">
            <RoleCard value="candidate" title="I'm a candidate" desc="Find & apply to jobs" />
            <RoleCard value="recruiter" title="I'm a recruiter" desc="Post jobs & hire" />
          </div>

          <div>
            <label className="label">Full name</label>
            <input className="input" value={form.full_name} onChange={set("full_name")} required />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={form.email} onChange={set("email")} required />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={set("password")}
              minLength={6}
              required
            />
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Creating account…" : "Sign up"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-brand-700 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
