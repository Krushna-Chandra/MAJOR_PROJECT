import React, { useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";
import { useInterviewFullscreenGuard } from "../hooks/useInterviewFullscreenGuard";
import { useRevealFullscreenWarning } from "../hooks/useRevealFullscreenWarning";
import { isFullscreenActive, requestInterviewFullscreen } from "../utils/interviewFullscreenGuard";

const primeInterviewVoiceApis = () => {
  try {
    if (window.speechSynthesis) {
      const utterance = new SpeechSynthesisUtterance(".");
      utterance.volume = 0;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
    }
  } catch {}

  try {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => {
      window.setTimeout(() => {
        try {
          recognition.abort();
        } catch {}
      }, 80);
    };
    recognition.onerror = () => {};
    recognition.onend = () => {};
    recognition.start();
  } catch {}
};

function Interview() {
  const navigate = useNavigate();
  const location = useLocation();
  const customContext = location.state || {};
  const cancelSetup = useCallback(() => {
    navigate("/", { replace: true });
  }, [navigate]);
  const { fullscreenBlocked, restoreFullscreen, cancelFullscreenGuard } =
    useInterviewFullscreenGuard({ onCancel: cancelSetup });
  useRevealFullscreenWarning(fullscreenBlocked);

  const [status, setStatus] = useState("Ready to launch your live interview.");
  const [isLaunching, setIsLaunching] = useState(false);

  const handleGoBack = () => {
    navigate("/instructions", { state: customContext });
  };

  const beginInterview = async () => {
    setIsLaunching(true);
    setStatus("Opening the live interview room...");

    try {
      if (!isFullscreenActive()) {
        await requestInterviewFullscreen(document.documentElement);
      }
      primeInterviewVoiceApis();
    } catch (error) {
      setStatus("Fullscreen is required before the live interview can start.");
      setIsLaunching(false);
      return;
    }

    navigate("/voice-interview", {
      state: {
        ...customContext,
        forceFreshSession: true,
        startSource: "interview-page",
      },
    });
  };

  return (
    <>
      <div className="mock-page reveal" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", paddingBottom: 0 }}>
        <div
          style={{
            padding: "16px 40px",
            background: "rgba(30, 30, 47, 0.9)",
            color: "white",
            display: "flex",
            justifyContent: "flex-start",
            alignItems: "center",
          }}
        >
          <h3 style={{ margin: 0 }}>Live Interview</h3>
        </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <div className="mock-section" style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ maxWidth: 920, margin: "0 auto", textAlign: "center" }}>
            <h1>Ready to Start Your Interview?</h1>
            <p style={{ fontSize: 14, color: "#6b7280", marginTop: 10 }}>
              Status: <strong>{status}</strong>
            </p>

            <button
              className="mock-btn"
              style={{ background: "#5b21b6", marginTop: 24, padding: "16px 32px", fontSize: 16 }}
              onClick={beginInterview}
              disabled={isLaunching}
            >
              {isLaunching ? "Starting..." : "Start Interview"}
            </button>

            <button className="go-back-btn" onClick={handleGoBack}>
              Go Back
            </button>
          </div>
        </div>
      </div>

      <div className="footer" style={{ marginTop: "auto", marginBottom: 0 }}>
        Launch screen ready - continue in the fullscreen session from permissions
      </div>

      </div>

      {fullscreenBlocked ? (
        <div className="voice-ai-modal-overlay">
          <div className="voice-ai-modal-card" data-fullscreen-warning tabIndex="-1">
            <div className="voice-ai-modal-eyebrow">Fullscreen Required</div>
            <h2 className="voice-ai-modal-title">
              The interview launch is paused because fullscreen mode was exited.
            </h2>
            <p className="voice-ai-modal-copy">
              Stay in fullscreen to continue the interview launch, or cancel this interview setup now.
            </p>
            <div className="voice-ai-modal-actions">
              <button className="go-back-btn" onClick={cancelFullscreenGuard}>
                Cancel Interview Setup
              </button>
              <button className="mock-btn" onClick={restoreFullscreen}>
                Stay in Fullscreen
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export default Interview;
