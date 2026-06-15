import React, { useState, useRef } from "react";

const API = "http://localhost:8000";

function getSupportedAudioMimeType() {
  if (typeof MediaRecorder === "undefined") return null;
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
  ];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || null;
}

function playBase64Wav(b64) {
  if (!b64) return null;
  const audio = new Audio("data:audio/wav;base64," + b64);
  audio.play().catch(() => {});
  return audio;
}

export default function App() {
  const [role, setRole] = useState("Software Engineer");
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

  async function startInterview() {
    setBusy(true);
    setStatus("Generating first question...");
    setLog([]);
    setAssessment(null);
    try {
      const res = await fetch(`${API}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to start interview");
      }
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
    if (!question || !threadId) {
      setStatus("Start the interview first.");
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("Microphone is not supported in this browser.");
      return;
    }

    if (typeof MediaRecorder === "undefined") {
      setStatus("Audio recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = getSupportedAudioMimeType();
      chunks.current = [];
      recordedMimeType.current = mimeType || "audio/webm";

      const mr = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mr.addEventListener("dataavailable", (e) => {
        if (e.data && e.data.size > 0) chunks.current.push(e.data);
      });
      mr.addEventListener("stop", () => {
        stream.getTracks().forEach((t) => t.stop());
      });
      mr.addEventListener("error", (e) => {
        setRecording(false);
        setBusy(false);
        setStatus(`Recorder error: ${e.error?.message || "unknown error"}`);
      });

      mediaRecorder.current = mr;
      mr.start();
      setRecording(true);
      setStatus("Recording... speak your answer.");
    } catch (e) {
      setStatus("Microphone error: " + (e.message || "permission denied"));
    }
  }

  async function stopAndSubmit() {
    const mr = mediaRecorder.current;
    if (!mr) return;
    setRecording(false);
    setBusy(true);
    setStatus("Transcribing and thinking...");

    await new Promise((resolve) => {
      mr.addEventListener("stop", resolve, { once: true });
      mr.stop();
    });

    if (chunks.current.length === 0) {
      setStatus("No audio captured. Please try recording again.");
      setBusy(false);
      return;
    }

    const blob = new Blob(chunks.current, { type: recordedMimeType.current });
    const form = new FormData();
    form.append("thread_id", threadId);
    const extension = recordedMimeType.current.includes("mp4") ? "m4a" : "webm";
    form.append("audio", blob, `answer.${extension}`);

    try {
      const res = await fetch(`${API}/interview/answer`, {
        method: "POST",
        body: form,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || "Failed to submit answer");
      }

      setLog((prev) => [...prev, { q: question, a: data.transcript }]);

      if (data.done) {
        setQuestion(null);
        setAssessment(data.assessment);
        playBase64Wav(data.closing_audio);
        setStatus(data.audio_warning || "Interview complete.");
      } else {
        setQuestion(data.question_text);
        playBase64Wav(data.question_audio);
        setStatus(
          data.audio_warning || "Listen, then record your next answer.",
        );
      }
    } catch (e) {
      setStatus("Error: " + e.message);
    }
    setBusy(false);
  }

  return (
    <div
      style={{
        maxWidth: 640,
        margin: "40px auto",
        fontFamily: "system-ui",
        padding: 16,
      }}
    >
      <h1>AI Voice Interview (POC)</h1>

      {!threadId && (
        <div>
          <label>
            Role:{" "}
            <input
              value={role}
              onChange={(e) => setRole(e.target.value)}
              style={{ padding: 6 }}
            />
          </label>
          <button
            onClick={startInterview}
            disabled={busy}
            style={{ marginLeft: 12, padding: "6px 14px" }}
          >
            Start interview
          </button>
        </div>
      )}

      {question && (
        <div
          style={{
            marginTop: 24,
            padding: 16,
            background: "#f3f3f0",
            borderRadius: 8,
          }}
        >
          <strong>Interviewer:</strong> {question}
          <div style={{ marginTop: 14 }}>
            {!recording ? (
              <button
                onClick={startRecording}
                disabled={busy}
                style={{ padding: "8px 16px" }}
              >
                Record answer
              </button>
            ) : (
              <button onClick={stopAndSubmit} style={{ padding: "8px 16px" }}>
                Stop &amp; submit
              </button>
            )}
          </div>
        </div>
      )}

      <p style={{ color: "#666", marginTop: 16 }}>{status}</p>

      {log.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Transcript</h3>
          {log.map((t, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              <div>
                <strong>Q{i + 1}:</strong> {t.q}
              </div>
              <div style={{ color: "#444" }}>
                <strong>You:</strong> {t.a}
              </div>
            </div>
          ))}
        </div>
      )}

      {assessment && (
        <div
          style={{
            marginTop: 24,
            padding: 16,
            border: "1px solid #ddd",
            borderRadius: 8,
          }}
        >
          <h3>Assessment</h3>
          <p>
            <strong>Score:</strong> {assessment.overall_score} / 100
          </p>
          <p>
            <strong>Recommendation:</strong> {assessment.recommendation}
          </p>
          <p>
            <strong>Summary:</strong> {assessment.summary}
          </p>
          {assessment.strengths?.length > 0 && (
            <p>
              <strong>Strengths:</strong> {assessment.strengths.join(", ")}
            </p>
          )}
          {assessment.weaknesses?.length > 0 && (
            <p>
              <strong>Weaknesses:</strong> {assessment.weaknesses.join(", ")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
