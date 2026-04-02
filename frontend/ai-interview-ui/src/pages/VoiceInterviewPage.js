import React, { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import "../App.css";
import {
  clean,
  formatProviderName,
  normalizeEvaluation,
  normalizeReport,
  safeErrorText,
  safeScore,
  safeText,
} from "../utils/interviewReport";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

function buildPayload(context) {
  const selectedOptions = Array.isArray(context.selectedOptions) ? context.selectedOptions.filter(Boolean) : [];
  const selectedMode = context.selectedMode || context.stage || "";

  return {
    category: context.category || (context.resumeText ? "resume" : "general"),
    selected_mode: selectedMode || "general",
    job_role: context.jobRole || (selectedMode !== "language" ? selectedOptions[0] : "") || "",
    primary_language:
      context.primaryLanguage ||
      context.primary_language ||
      (selectedMode === "language" ? selectedOptions[0] : "") ||
      "",
    selected_options: selectedOptions,
    experience: context.experience || "Not specified",
    config_mode: context.configMode || "standard",
    question_count: context.customQuestionCount || context.questionCount || 5,
    practice_type: context.practiceType || "voice interview",
    interview_mode_time: context.interviewModeTime || null,
    time_mode_interval: context.timeModeInterval || null,
    resume_text: context.resumeText || "",
  };
}

function VoiceInterviewPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const context = location.state || {};
  const payload = buildPayload(context);
  const SpeechRecognition =
    typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

  const rootRef = useRef(null);
  const videoRef = useRef(null);
  const recognitionRef = useRef(null);
  const pauseTimerRef = useRef(null);
  const countdownFinishedRef = useRef(false);
  const cameraRef = useRef(null);
  const speakingRef = useRef(false);
  const autoListenRef = useRef(false);
  const finishInterviewRef = useRef(null);
  const sessionIdRef = useRef("");
  const indexRef = useRef(0);
  const busyRef = useRef(false);
  const fullscreenBlockedRef = useRef(false);
  const startedRef = useRef(false);
  const endingRef = useRef(false);
  const draftRef = useRef("");
  const interimRef = useRef("");

  const [sessionId, setSessionId] = useState("");
  const [providers, setProviders] = useState({});
  const [sessionMeta, setSessionMeta] = useState({});
  const [questionOutline, setQuestionOutline] = useState([]);
  const [question, setQuestion] = useState("");
  const [questionType, setQuestionType] = useState("practical");
  const [index, setIndex] = useState(0);
  const [total, setTotal] = useState(0);
  const [draft, setDraft] = useState("");
  const [interim, setInterim] = useState("");
  const [status, setStatus] = useState("Ready to begin.");
  const [error, setError] = useState("");
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [fullscreenBlocked, setFullscreenBlocked] = useState(false);
  const [latestEval, setLatestEval] = useState(null);
  const [history, setHistory] = useState([]);
  const [timeLeftSeconds, setTimeLeftSeconds] = useState(null);
  const [viewportWidth, setViewportWidth] = useState(typeof window !== "undefined" ? window.innerWidth : 1440);

  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    indexRef.current = index;
  }, [index]);

  useEffect(() => {
    busyRef.current = busy;
  }, [busy]);

  useEffect(() => {
    fullscreenBlockedRef.current = fullscreenBlocked;
  }, [fullscreenBlocked]);

  useEffect(() => {
    startedRef.current = started;
  }, [started]);

  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  useEffect(() => {
    interimRef.current = interim;
  }, [interim]);

  useEffect(() => {
    const onResize = () => setViewportWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const isCompactLayout = viewportWidth < 1180;
  const transcript = clean(`${draft} ${interim}`);
  const title = safeText(payload.job_role || payload.primary_language || payload.category || "Interview");

  const buildLocalFallbackReport = useCallback((endedEarly = false) => {
    const evaluations = history.map((item) => normalizeEvaluation(item));
    const scores = evaluations.map((item) => safeScore(item.score));
    const overallScore = scores.length
      ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
      : 0;
    const topStrengths = Array.from(new Set(evaluations.flatMap((item) => item.strengths || []))).slice(0, 3);
    const improvementAreas = Array.from(new Set(evaluations.flatMap((item) => item.gaps || []))).slice(0, 3);
    const fallbackSessionId = sessionIdRef.current || `local-${Date.now()}`;

    return normalizeReport(
      {
        session_id: fallbackSessionId,
        overall_score: overallScore,
        ended_early: endedEarly,
        summary: evaluations.length
          ? "The backend session was unavailable at completion time, so this report was prepared from the answers and evaluations already captured on this page."
          : "No evaluated answers were available to generate a full report.",
        top_strengths: topStrengths,
        improvement_areas: improvementAreas,
        strongest_questions: evaluations.filter((item) => item.score >= 75).map((item) => item.question).slice(0, 3),
        needs_work_questions: evaluations.filter((item) => item.score < 60).map((item) => item.question).slice(0, 3),
        evaluations,
        answers: evaluations.map((item) => item.answer),
        question_outline: questionOutline,
        questions_answered: evaluations.length,
        total_questions: total || questionOutline.length || evaluations.length,
        providers,
        context: payload,
      },
      payload
    );
  }, [history, payload, providers, questionOutline, total]);

  const resolveTimerMinutes = () => {
    if (payload.config_mode === "time" && payload.time_mode_interval) {
      return Number(payload.time_mode_interval) || null;
    }
    if (payload.practice_type === "interview" && payload.interview_mode_time) {
      return Number(payload.interview_mode_time) || null;
    }
    return null;
  };

  const stopSpeech = useCallback(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    speakingRef.current = false;
    setAiSpeaking(false);
  }, []);

  const speak = useCallback((text) =>
    new Promise((resolve) => {
      const value = clean(text);
      if (!value || !window.speechSynthesis) {
        resolve();
        return;
      }
      stopSpeech();
      const utterance = new SpeechSynthesisUtterance(value);
      speakingRef.current = true;
      setAiSpeaking(true);
      utterance.lang = "en-US";
      utterance.onend = () => {
        speakingRef.current = false;
        setAiSpeaking(false);
        resolve();
      };
      utterance.onerror = () => {
        speakingRef.current = false;
        setAiSpeaking(false);
        resolve();
      };
      window.speechSynthesis.speak(utterance);
    }), [stopSpeech]);

  const authHeaders = () => {
    const token = localStorage.getItem("token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const stopListening = ({ keepAutoListen = false } = {}) => {
    if (!keepAutoListen) {
      autoListenRef.current = false;
    }
    if (pauseTimerRef.current) {
      clearTimeout(pauseTimerRef.current);
      pauseTimerRef.current = null;
    }
    if (recognitionRef.current) {
      recognitionRef.current.onresult = null;
      recognitionRef.current.onerror = null;
      recognitionRef.current.onend = null;
      try {
        recognitionRef.current.stop();
      } catch {}
    }
    recognitionRef.current = null;
    setListening(false);
  };

  const ensureFullscreen = async () => {
    if (document.fullscreenElement) return true;
    const target = rootRef.current || document.documentElement;
    if (!target.requestFullscreen) {
      throw new Error("Fullscreen is not supported in this browser.");
    }
    await target.requestFullscreen();
    if (!document.fullscreenElement) {
      throw new Error("Fullscreen did not start.");
    }
    return true;
  };

  const exitFullscreen = async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      }
    } catch {}
  };

  const attachCameraPreview = async () => {
    if (!cameraRef.current || !videoRef.current) return;
    videoRef.current.srcObject = cameraRef.current;
    videoRef.current.muted = true;
    videoRef.current.playsInline = true;
    try {
      await videoRef.current.play();
    } catch {}
  };

  const startCamera = async () => {
    if (cameraRef.current) {
      await attachCameraPreview();
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    cameraRef.current = stream;
    await attachCameraPreview();
  };

  const stopCamera = () => {
    if (cameraRef.current) {
      cameraRef.current.getTracks().forEach((track) => track.stop());
    }
    cameraRef.current = null;
  };

  const startListening = () => {
    if (!SpeechRecognition || busyRef.current || fullscreenBlockedRef.current || endingRef.current || !startedRef.current) {
      return;
    }

    stopListening({ keepAutoListen: true });
    autoListenRef.current = true;

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setListening(true);
      setStatus("Listening for your answer automatically...");
    };

    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";

      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0]?.transcript || "";
        if (event.results[i].isFinal) {
          finalText += ` ${piece}`;
        } else {
          interimText += ` ${piece}`;
        }
      }

      if (clean(finalText)) {
        setDraft((prev) => clean(`${prev} ${finalText}`));
      }
      setInterim(clean(interimText));

      if (clean(`${finalText} ${interimText}`)) {
        if (pauseTimerRef.current) clearTimeout(pauseTimerRef.current);
        pauseTimerRef.current = setTimeout(() => {
          submitAnswer();
        }, 1800);
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        autoListenRef.current = false;
        setError("Microphone access was blocked. Please allow microphone access.");
      }
      if (event.error === "audio-capture") {
        autoListenRef.current = false;
        setError("Microphone could not capture audio. Please check your device.");
      }
      setListening(false);
    };

    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
      if (
        autoListenRef.current &&
        !busyRef.current &&
        !fullscreenBlockedRef.current &&
        !endingRef.current &&
        startedRef.current &&
        !speakingRef.current
      ) {
        window.setTimeout(() => {
          startListening();
        }, 250);
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const askQuestion = async ({ promptText, preface = "" }) => {
    if (preface) {
      await speak(preface);
    }
    await speak(promptText);
    if (SpeechRecognition) {
      startListening();
    } else {
      setStatus("Speech recognition is unavailable. You can type and submit your answer.");
    }
  };

  const finishInterview = useCallback(async ({ endedEarly = false, spokenClose = "Thank you. This interview is over. I am preparing your report." } = {}) => {
    if (endingRef.current) return;
    if (!sessionIdRef.current) {
      const fallbackReport = buildLocalFallbackReport(endedEarly);
      navigate(`/reports/${fallbackReport.session_id}`, {
        replace: true,
        state: {
          report: fallbackReport,
          context: payload,
        },
      });
      return;
    }
    endingRef.current = true;
    stopListening();
    setBusy(true);
    setStatus("Preparing your report...");
    setError("");

    try {
      await speak(spokenClose);
      const response = await axios.post(
        `${API_BASE_URL}/ai-interview/complete`,
        { session_id: sessionIdRef.current, ended_early: endedEarly },
        { headers: authHeaders() }
      );
      const normalizedReport = normalizeReport(response.data, payload);
      stopSpeech();
      stopCamera();
      await exitFullscreen();
      navigate(`/reports/${sessionIdRef.current}`, {
        replace: true,
        state: {
          report: normalizedReport,
          context: payload,
        },
      });
    } catch (requestError) {
      const requestMessage = safeErrorText(
        requestError.response?.data?.detail ||
        requestError.response?.data ||
        requestError.message ||
        "Failed to complete the interview."
      );

      if (requestMessage.toLowerCase().includes("interview session not found")) {
        const fallbackReport = buildLocalFallbackReport(endedEarly);
        stopSpeech();
        stopCamera();
        await exitFullscreen();
        navigate(`/reports/${fallbackReport.session_id}`, {
          replace: true,
          state: {
            report: fallbackReport,
            context: payload,
          },
        });
        return;
      }

      endingRef.current = false;
      setError(requestMessage);
      setStatus("Could not prepare the report.");
    } finally {
      setBusy(false);
    }
  }, [buildLocalFallbackReport, navigate, payload, speak, stopSpeech]);

  const submitAnswer = async () => {
    const answer = clean(`${draftRef.current} ${interimRef.current}`);
    if (!answer || !sessionIdRef.current || busyRef.current || endingRef.current) {
      return;
    }

    stopListening();
    setBusy(true);
    setStatus("Evaluating your answer...");
    setError("");

    try {
      const response = await axios.post(`${API_BASE_URL}/ai-interview/evaluate`, {
        session_id: sessionIdRef.current,
        question_index: indexRef.current,
        answer,
      });

      const normalized = {
        ...normalizeEvaluation(response.data),
        next_question: safeText(response.data?.next_question),
        is_complete: Boolean(response.data?.is_complete),
      };

      setLatestEval(normalized);
      setHistory((prev) => [...prev, normalized]);
      setProviders((prev) => ({
        ...prev,
        evaluation_provider: normalized.provider || prev.evaluation_provider,
      }));

      setDraft("");
      setInterim("");

      if (normalized.is_complete) {
        await finishInterview({
          endedEarly: false,
          spokenClose: safeText(normalized.assistant_reply) || "Thank you. This interview is over. I am preparing your report.",
        });
        return;
      }

      const nextIndex = indexRef.current + 1;
      const nextOutline = questionOutline[nextIndex] || {};
      setIndex(nextIndex);
      setQuestion(normalized.next_question || "");
      setQuestionType(safeText(nextOutline.question_type) || "practical");
      setStatus("Next question ready.");
      await askQuestion({
        promptText: `Question ${nextIndex + 1}. ${normalized.next_question || "Please continue."}`,
        preface: safeText(normalized.assistant_reply) || "Thank you. Let us continue.",
      });
    } catch (requestError) {
      setError(
        safeErrorText(
          requestError.response?.data?.detail ||
          requestError.response?.data ||
          requestError.message ||
          "Failed to evaluate the answer."
        )
      );
      setStatus("Evaluation failed.");
    } finally {
      setBusy(false);
    }
  };

  const beginVoiceInterview = async () => {
    setBusy(true);
    setError("");
    setLatestEval(null);
    setHistory([]);
    setDraft("");
    setInterim("");
    countdownFinishedRef.current = false;
    endingRef.current = false;

    try {
      await ensureFullscreen();
      await startCamera();
      const response = await axios.post(`${API_BASE_URL}/ai-interview/start`, payload, {
        headers: authHeaders(),
      });
      const data = response.data || {};
      const outline = Array.isArray(data.question_outline) ? data.question_outline : [];
      const nextSessionId = safeText(data.session_id);

      sessionIdRef.current = nextSessionId;
      setSessionId(nextSessionId);
      setProviders(data.providers || {});
      setSessionMeta(data.meta || {});
      setQuestion(safeText(data.current_question));
      setQuestionType(safeText(outline[0]?.question_type) || "practical");
      setQuestionOutline(outline);
      setTotal(Number(data.total_questions) || outline.length || 0);
      setIndex(0);
      setStarted(true);
      setFullscreenBlocked(false);
      setStatus("Interview started.");

      const timerMinutes = resolveTimerMinutes();
      setTimeLeftSeconds(timerMinutes ? timerMinutes * 60 : null);

      await attachCameraPreview();
      await askQuestion({
        preface: safeText(data.assistant_intro) || "Hello. Let us begin.",
        promptText: `Question 1. ${safeText(data.current_question)}`,
      });
    } catch (requestError) {
      const mediaErrorName = requestError?.name || requestError?.cause?.name;
      const isMediaError =
        mediaErrorName === "NotAllowedError" ||
        mediaErrorName === "NotFoundError" ||
        mediaErrorName === "NotReadableError";

      setError(
        isMediaError
          ? "Camera or microphone access failed on the interview page. Please allow access and try again."
          : safeErrorText(
              requestError.response?.data?.detail ||
              requestError.response?.data ||
              requestError.message ||
              "Failed to start the interview."
            )
      );
      setStatus("Interview could not start.");
    } finally {
      setBusy(false);
    }
  };

  const restoreFullscreen = async () => {
    try {
      await ensureFullscreen();
      setFullscreenBlocked(false);
      setError("");
      setStatus("Fullscreen restored. Continue answering.");
      await askQuestion({
        preface: "Fullscreen restored.",
        promptText: "Please continue your answer.",
      });
    } catch (requestError) {
      setError(safeErrorText(requestError.message || "Fullscreen is required to continue."));
    }
  };

  const handleEndInterview = async () => {
    if (!sessionIdRef.current || endingRef.current) {
      navigate("/");
      return;
    }
    const confirmed = window.confirm("End the interview now and generate your report from the answers so far?");
    if (!confirmed) return;

    await finishInterview({
      endedEarly: true,
      spokenClose: "Thank you for attending this interview. I am ending the session now and generating your performance report.",
    });
  };

  useEffect(() => {
    finishInterviewRef.current = finishInterview;
  }, [finishInterview]);

  useEffect(() => {
    const onFullscreenChange = () => {
      if (!startedRef.current || endingRef.current) return;
      if (!document.fullscreenElement) {
        stopListening();
        stopSpeech();
        setFullscreenBlocked(true);
        setStatus("Interview paused until fullscreen is restored.");
        setError("Fullscreen was exited. Re-enter fullscreen to continue.");
      }
    };

    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, [stopSpeech]);

  useEffect(() => {
    if (!started || busy || fullscreenBlocked || endingRef.current || timeLeftSeconds == null || timeLeftSeconds <= 0) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setTimeLeftSeconds((previous) => {
        if (previous == null) return previous;
        if (previous <= 1) {
          window.clearInterval(intervalId);
          if (!countdownFinishedRef.current) {
            countdownFinishedRef.current = true;
            finishInterviewRef.current?.({
              endedEarly: true,
              spokenClose: "The timer has ended. Thank you. I am preparing your report now.",
            });
          }
          return 0;
        }
        return previous - 1;
      });
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [started, busy, fullscreenBlocked, timeLeftSeconds]);

  useEffect(() => {
    if (started && cameraRef.current && videoRef.current) {
      attachCameraPreview();
    }
  }, [started]);

  useEffect(() => () => {
    stopListening();
    stopSpeech();
    stopCamera();
    exitFullscreen();
  }, [stopSpeech]);

  const timerLabel =
    timeLeftSeconds == null
      ? "No active timer"
      : `${Math.floor(timeLeftSeconds / 60).toString().padStart(2, "0")}:${(timeLeftSeconds % 60).toString().padStart(2, "0")}`;

  return (
    <div
      className="mock-page reveal"
      ref={rootRef}
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%)",
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      <div style={{ maxWidth: 1380, margin: "0 auto", padding: "24px 20px 36px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap", marginBottom: 24 }}>
          <div>
            <div style={{ display: "inline-block", padding: "8px 14px", borderRadius: 999, background: "rgba(79,70,229,0.08)", color: "#4338ca", fontWeight: 800, fontSize: 12, textTransform: "uppercase" }}>
              AI Interview Page
            </div>
            <h1 style={{ margin: "14px 0 6px", color: "#1f2a44" }}>{safeText(title) || "Interview"}</h1>
            <p style={{ margin: 0, color: "#5b6480", lineHeight: 1.6 }}>
              Start the session, answer by voice, and let the assistant evaluate your response step by step.
            </p>
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <button className="go-back-btn" onClick={() => navigate(-1)}>Back</button>
            <button className="mock-btn" onClick={() => navigate("/")}>Home</button>
            {started ? (
              <button className="mock-btn" onClick={handleEndInterview} style={{ background: "linear-gradient(135deg, #dc2626, #f97316)" }}>
                End Interview
              </button>
            ) : null}
          </div>
        </div>

        {error ? <div style={{ marginBottom: 18, padding: 14, borderRadius: 16, background: "rgba(239,68,68,0.08)", color: "#b91c1c", fontWeight: 700 }}>{safeText(error)}</div> : null}
        {fullscreenBlocked ? <div style={{ marginBottom: 18, padding: 18, borderRadius: 18, background: "#fff7ed", color: "#9a3412", display: "flex", justifyContent: "space-between", gap: 16, alignItems: "center", flexWrap: "wrap" }}><span>Fullscreen is required while the interview is running.</span><button className="mock-btn" onClick={restoreFullscreen}>Re-enter Fullscreen</button></div> : null}

        {!started ? (
          <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "minmax(0,1.1fr) minmax(320px,0.9fr)", gap: 24, alignItems: "start" }}>
            <div style={{ background: "white", borderRadius: 28, padding: 28, boxShadow: "0 24px 60px rgba(88,107,176,0.14)" }}>
              <h2 style={{ marginTop: 0, color: "#1f2a44" }}>Ready for your AI interview</h2>
              <p style={{ color: "#4f5873", lineHeight: 1.8 }}>
                The assistant will speak each question, start listening automatically, and evaluate your answer using the configured AI providers.
              </p>
              <div style={{ display: "grid", gap: 12, marginTop: 18, color: "#4f5873" }}>
                <div>Category: {safeText(payload.category)}</div>
                <div>Mode: {safeText(payload.selected_mode)}</div>
                <div>Role: {safeText(payload.job_role) || "General"}</div>
                <div>Language: {safeText(payload.primary_language) || "Not selected"}</div>
                <div>Experience: {safeText(payload.experience)}</div>
                <div>Questions: {safeScore(payload.question_count)}</div>
                <div>Config mode: {safeText(payload.config_mode)}</div>
                <div>Timer: {resolveTimerMinutes() ? `${resolveTimerMinutes()} minutes` : "Off"}</div>
                <div>Speech recognition: {SpeechRecognition ? "Automatic voice capture enabled" : "Unavailable, typed fallback enabled"}</div>
              </div>
              <button className="mock-btn" onClick={beginVoiceInterview} disabled={busy} style={{ marginTop: 24, background: "linear-gradient(135deg, #4338ca, #7c3aed)" }}>
                {busy ? "Starting..." : "Enter Fullscreen and Begin"}
              </button>
            </div>

            <div style={{ background: "#111c42", color: "#eef2ff", borderRadius: 28, padding: 26 }}>
              <h3 style={{ marginTop: 0 }}>Session flow</h3>
              <div style={{ display: "grid", gap: 14, lineHeight: 1.7 }}>
                <div>1. Start the session and enter fullscreen.</div>
                <div>2. The assistant asks the question aloud.</div>
                <div>3. Your spoken response is captured automatically.</div>
                <div>4. The AI evaluates your answer and continues the session.</div>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "minmax(300px,0.9fr) minmax(0,1.1fr)", gap: 20, alignItems: "start" }}>
            <div style={{ display: "grid", gap: 18, minWidth: 0 }}>
              <div style={{ background: "#0f172a", padding: 18, borderRadius: 28 }}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  style={{
                    width: "100%",
                    minHeight: isCompactLayout ? 220 : 300,
                    maxHeight: isCompactLayout ? 320 : 380,
                    objectFit: "cover",
                    background: "#020617",
                    borderRadius: 20,
                  }}
                />
                <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, color: "#e2e8f0" }}>
                  <span>Question {Math.min(index + 1, total || 1)} of {total || 1}</span>
                  <strong>{safeText(aiSpeaking ? "Assistant speaking" : listening ? "Listening automatically" : status)}</strong>
                </div>
                <div style={{ marginTop: 12, color: "#cbd5e1", display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                  <span>Question type: {safeText(questionType) || "Adaptive"}</span>
                  <span>Timer: {timerLabel}</span>
                </div>
              </div>

              <div style={{ background: "white", borderRadius: 24, padding: 22, boxShadow: "0 20px 50px rgba(88,107,176,0.12)" }}>
                <h3 style={{ marginTop: 0, color: "#1f2a44" }}>Session providers</h3>
                <div style={{ display: "grid", gap: 10, color: "#4f5873" }}>
                  <div>Generation: {formatProviderName(providers.generation_provider, "generation") || "Pending"}</div>
                  <div>Evaluation: {formatProviderName(providers.evaluation_provider, "evaluation") || "Pending"}</div>
                  <div>Summary: {formatProviderName(providers.summary_provider, "summary") || "Pending"}</div>
                  <div>Answers reviewed: {history.length}</div>
                  <div>Difficulty: {safeText(sessionMeta.difficulty || payload.experience) || "Adaptive"}</div>
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gap: 18, minWidth: 0 }}>
              <div style={{ background: "linear-gradient(135deg, #4338ca, #2563eb)", color: "white", borderRadius: 28, padding: 26 }}>
                <div style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", opacity: 0.9 }}>Current question</div>
                <h2 style={{ margin: "12px 0 0", lineHeight: 1.45, fontSize: isCompactLayout ? 24 : 30 }}>{safeText(question) || "Loading question..."}</h2>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 20 }}>
                  <button className="mock-btn" onClick={() => askQuestion({ promptText: `Question ${index + 1}. ${safeText(question)}` })} style={{ background: "rgba(255,255,255,0.16)" }}>Repeat Question</button>
                  <button className="mock-btn" onClick={startListening} disabled={busy || fullscreenBlocked || !SpeechRecognition} style={{ background: "rgba(255,255,255,0.16)" }}>Restart Listening</button>
                </div>
              </div>

              <div style={{ background: "white", borderRadius: 24, padding: 24, boxShadow: "0 20px 50px rgba(88,107,176,0.12)" }}>
                <h3 style={{ marginTop: 0, color: "#1f2a44" }}>Your answer</h3>
                <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Your spoken answer will appear here automatically. You can refine it before submitting." style={{ width: "100%", minHeight: isCompactLayout ? 140 : 170, borderRadius: 18, border: "1px solid rgba(148,163,184,0.28)", padding: 16, resize: "vertical" }} />
                <div style={{ marginTop: 12, padding: 14, borderRadius: 16, background: "rgba(14,165,233,0.08)", color: "#0f5f82" }}>
                  Live transcript: {safeText(interim || transcript) || "Waiting for your answer..."}
                </div>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 18 }}>
                  <button className="mock-btn" onClick={submitAnswer} disabled={!clean(transcript) || busy || fullscreenBlocked} style={{ background: "linear-gradient(135deg, #059669, #10b981)" }}>
                    {busy ? "Processing..." : "Submit Now"}
                  </button>
                  <button className="go-back-btn" onClick={() => { stopListening(); setDraft(""); setInterim(""); startListening(); }} disabled={busy}>Clear and Retry</button>
                </div>

                {latestEval ? (
                  <div style={{ marginTop: 20, paddingTop: 18, borderTop: "1px solid rgba(148,163,184,0.22)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
                      <h3 style={{ margin: 0, color: "#1f2a44" }}>Latest evaluation</h3>
                      <strong>Score {safeScore(latestEval.score)}/100</strong>
                    </div>
                    <p style={{ color: "#4f5873", lineHeight: 1.7 }}>{safeText(latestEval.feedback)}</p>
                    <div style={{ color: "#4f5873", display: "grid", gap: 8 }}>
                      {latestEval.strengths.slice(0, 2).map((item) => <div key={item}>- {item}</div>)}
                      {latestEval.gaps.slice(0, 2).map((item) => <div key={item}>- {item}</div>)}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default VoiceInterviewPage;
