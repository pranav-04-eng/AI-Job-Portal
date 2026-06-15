import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const linkClass = ({ isActive }) =>
    `px-3 py-2 text-sm font-medium rounded-md transition ${
      isActive ? "text-brand-700 bg-brand-50" : "text-slate-600 hover:text-slate-900"
    }`;

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 text-lg font-extrabold text-slate-900">
          <span className="text-xl">💼</span>
          Hire<span className="text-brand-600">Voice</span>
        </Link>

        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>
            Jobs
          </NavLink>

          {user?.role === "candidate" && (
            <NavLink to="/applications" className={linkClass}>
              My applications
            </NavLink>
          )}
          {user?.role === "recruiter" && (
            <NavLink to="/recruiter" className={linkClass}>
              Recruiter
            </NavLink>
          )}

          {user ? (
            <div className="ml-2 flex items-center gap-3">
              <span className="hidden text-sm text-slate-500 sm:inline">
                {user.full_name || user.email}
              </span>
              <button onClick={handleLogout} className="btn-ghost">
                Log out
              </button>
            </div>
          ) : (
            <div className="ml-2 flex items-center gap-2">
              <Link to="/login" className="btn-ghost">
                Log in
              </Link>
              <Link to="/signup" className="btn-primary">
                Sign up
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  );
}
