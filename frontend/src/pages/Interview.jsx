import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, API, getToken } from "../api";
import { Spinner, ScoreRing, Alert, StatusBadge } from "../components/ui.jsx";

function getSupportedAudioMimeType() {
  if (typeof MediaRecorder === "undefined") return null;
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) || null;
}

function playBase64Wav(b64) {
  if (!b64) return;
  new Audio("data:audio/wav;base64," + b64).play().catch(() => {});
}

export default function Interview() {
  const { id } = useParams(); // application id
  const [application, setApplication] = useState(null);
  const [loadError, setLoadError] = useState("");

  const [threadId, setThreadId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [log, setLog] = useState([]); // [{q, a}]
  const [assessment, setAssessment] = useState(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");

  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const recordedMimeType = useRef("audio/webm");

  useEffect(() => {
    api
      .get(`/applications/${id}`)
      .then((a) => {
        setApplication(a);
        if (a.interview?.assessment && Object.keys(a.interview.assessment).length) {
          setAssessment(a.interview.assessment);
        }
      })
      .catch((e) => setLoadError(e.message));
  }, [id]);

  const role = application?.job?.title || "the role";

  async function startInterview() {
    setBusy(true);
    setStatus("Generating the first question…");
    setLog([]);
    setAssessment(null);
    try {
      const data = await api.post("/interview/start", {
        role,
        application_id: Number(id),
      });
      setThreadId(data.thread_id);
      setQuestion(data.question_text);
      playBase64Wav(data.question_audio);
      setStatus(data.audio_warning || "Listen, then record your answer.");
    } catch (e) {
      setStatus("Error: " + e.message);
    }
    setBusy(false);
  }

  async function startRecording() {
    if (!question || !threadId) return setStatus("Start the interview first.");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      return setStatus("Audio recording is not supported in this browser.");
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedAudioMimeType();
      chunks.current = [];
      recordedMimeType.current = mimeType || "audio/webm";
      const mr = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mr.addEventListener("dataavailable", (e) => {
        if (e.data && e.data.size > 0) chunks.current.push(e.data);
      });
      mr.addEventListener("stop", () => stream.getTracks().forEach((t) => t.stop()));
      mediaRecorder.current = mr;
      mr.start();
      setRecording(true);
      setStatus("Recording… speak your answer.");
    } catch (e) {
      setStatus("Microphone error: " + (e.message || "permission denied"));
    }
  }

  async function stopAndSubmit() {
    const mr = mediaRecorder.current;
    if (!mr) return;
    setRecording(false);
    setBusy(true);
    setStatus("Transcribing and thinking…");

    await new Promise((resolve) => {
      mr.addEventListener("stop", resolve, { once: true });
      mr.stop();
    });

    if (chunks.current.length === 0) {
      setStatus("No audio captured. Please try again.");
      setBusy(false);
      return;
    }

    const blob = new Blob(chunks.current, { type: recordedMimeType.current });
    const form = new FormData();
    form.append("thread_id", threadId);
    const ext = recordedMimeType.current.includes("mp4") ? "m4a" : "webm";
    form.append("audio", blob, `answer.${ext}`);

    // Use raw fetch here: multipart body + bearer token, no JSON wrapper.
    try {
      const res = await fetch(`${API}/interview/answer`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || "Failed to submit answer");

      setLog((prev) => [...prev, { q: question, a: data.transcript }]);

      if (data.done) {
        setQuestion(null);
        setAssessment(data.assessment);
        playBase64Wav(data.closing_audio);
        setStatus(data.audio_warning || "Interview complete.");
        await persistResult(data.assessment);
      } else {
        setQuestion(data.question_text);
        playBase64Wav(data.question_audio);
        setStatus(data.audio_warning || "Listen, then record your next answer.");
      }
    } catch (e) {
      setStatus("Error: " + e.message);
    }
    setBusy(false);
  }

  async function persistResult(a) {
    try {
      await api.patch(`/applications/${id}/interview-result`, {
        thread_id: threadId,
        score: a?.overall_score ?? null,
        recommendation: a?.recommendation ?? null,
        summary: a?.summary ?? "",
        assessment: a || {},
      });
    } catch {
      /* non-fatal: candidate still sees their result */
    }
  }

  if (loadError) return <Alert tone="error">{loadError}</Alert>;
  if (!application) return <Spinner label="Loading interview…" />;

  const alreadyDone = application.status === "interview_completed" && assessment;
  const notInvited = application.status === "rejected";

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/applications" className="text-sm text-brand-700 hover:underline">
        ← My applications
      </Link>

      <div className="mt-3 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Voice interview</h1>
          <p className="text-sm text-slate-500">
            {application.job?.title} · {application.job?.company}
          </p>
        </div>
        <StatusBadge status={application.status} />
      </div>

      {notInvited ? (
        <Alert tone="error">This application didn’t pass resume screening.</Alert>
      ) : (
        <>
          {/* Pre-start */}
          {!threadId && !assessment && (
            <div className="card mt-5 p-6 text-center">
              <p className="text-slate-600">
                You’ll be asked a few questions out loud. Listen, record your spoken answer, and
                submit. An AI assessment follows at the end.
              </p>
              <button onClick={startInterview} disabled={busy} className="btn-primary mt-5">
                {busy ? "Preparing…" : "Begin interview"}
              </button>
            </div>
          )}

          {/* Active question */}
          {question && (
            <div className="card mt-5 p-6">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-400">
                Interviewer asks
              </p>
              <p className="mt-2 text-lg text-slate-800">{question}</p>
              <div className="mt-5">
                {!recording ? (
                  <button onClick={startRecording} disabled={busy} className="btn-primary">
                    🎙️ Record answer
                  </button>
                ) : (
                  <button onClick={stopAndSubmit} className="btn-danger animate-pulse">
                    ⏹ Stop &amp; submit
                  </button>
                )}
              </div>
            </div>
          )}

          {status && <p className="mt-3 text-sm text-slate-500">{status}</p>}

          {/* Transcript */}
          {log.length > 0 && (
            <div className="card mt-5 p-6">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-400">Transcript</h3>
              <div className="mt-3 space-y-3">
                {log.map((t, i) => (
                  <div key={i} className="border-l-2 border-brand-200 pl-3">
                    <p className="text-sm font-medium text-slate-700">Q{i + 1}: {t.q}</p>
                    <p className="text-sm text-slate-500">You: {t.a}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final assessment */}
          {assessment && (
            <div className="card mt-5 p-6">
              <div className="flex items-center gap-4">
                <ScoreRing score={assessment.overall_score} />
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Interview assessment</h3>
                  <p className="text-sm text-slate-500">
                    Recommendation: <strong>{assessment.recommendation}</strong>
                  </p>
                </div>
              </div>
              <p className="mt-4 text-slate-700">{assessment.summary}</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">Strengths</h4>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {assessment.strengths?.map((x, i) => <li key={i}>✓ {x}</li>) || "—"}
                  </ul>
                </div>
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">
                    Areas to improve
                  </h4>
                  <ul className="mt-2 space-y-1 text-sm text-slate-700">
                    {assessment.weaknesses?.map((x, i) => <li key={i}>• {x}</li>) || "—"}
                  </ul>
                </div>
              </div>
              {!alreadyDone && (
                <p className="mt-5 text-sm text-brand-700">
                  Saved to your application. The recruiter can now review it.
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
