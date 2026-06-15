import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import { Spinner } from "./components/ui.jsx";
import { useAuth } from "./auth.jsx";

import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import Jobs from "./pages/Jobs.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Apply from "./pages/Apply.jsx";
import Interview from "./pages/Interview.jsx";
import CandidateDashboard from "./pages/CandidateDashboard.jsx";
import RecruiterDashboard from "./pages/RecruiterDashboard.jsx";
import NewJob from "./pages/NewJob.jsx";
import JobApplicants from "./pages/JobApplicants.jsx";

// Gate a route on being logged in (and optionally on a role).
function Protected({ children, role }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (role && user.role !== role) {
    return <Navigate to="/" replace />;
  }
  return children;
}

export default function App() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />

          <Route
            path="/jobs/:id/apply"
            element={
              <Protected role="candidate">
                <Apply />
              </Protected>
            }
          />
          <Route
            path="/applications"
            element={
              <Protected role="candidate">
                <CandidateDashboard />
              </Protected>
            }
          />
          <Route
            path="/applications/:id/interview"
            element={
              <Protected role="candidate">
                <Interview />
              </Protected>
            }
          />

          <Route
            path="/recruiter"
            element={
              <Protected role="recruiter">
                <RecruiterDashboard />
              </Protected>
            }
          />
          <Route
            path="/recruiter/jobs/new"
            element={
              <Protected role="recruiter">
                <NewJob />
              </Protected>
            }
          />
          <Route
            path="/recruiter/jobs/:id/applicants"
            element={
              <Protected role="recruiter">
                <JobApplicants />
              </Protected>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
