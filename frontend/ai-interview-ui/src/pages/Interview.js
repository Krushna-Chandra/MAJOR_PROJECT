import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";
import VoiceInterview from "./VoiceInterview";

function Interview() {
  const navigate = useNavigate();
  const location = useLocation();
  const customContext = location.state || {};

  const [status, setStatus] = useState("Ready to launch your live interview.");
  const [embeddedInterviewContext, setEmbeddedInterviewContext] = useState(null);

  const handleGoBack = () => {
    navigate("/instructions", { state: customContext });
  };

  const beginInterview = async () => {
    setStatus("Opening the live interview room...");

    setEmbeddedInterviewContext({
      ...customContext,
      forceFreshSession: true,
      startSource: "interview-page",
    });
  };

  if (embeddedInterviewContext) {
    return <VoiceInterview embeddedContext={embeddedInterviewContext} autoStart />;
  }

  return (
    <div
      className="mock-page reveal"
      style={{ minHeight: "100vh", display: "flex", flexDirection: "column", paddingBottom: 0 }}
    >
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
            >
              Start Interview in Fullscreen
            </button>

            <button className="go-back-btn" onClick={handleGoBack}>
              Go Back
            </button>
          </div>
        </div>
      </div>

      <div className="footer" style={{ marginTop: "auto", marginBottom: 0 }}>
        Launch screen ready - fullscreen is required before the live interview begins
      </div>
    </div>
  );
}

export default Interview;
