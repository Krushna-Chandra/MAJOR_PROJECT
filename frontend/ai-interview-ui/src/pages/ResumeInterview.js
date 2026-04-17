import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import resumeHero from "../assets/resume.png";

function ResumeInterview() {
  const navigate = useNavigate();
  const location = useLocation();
  const [resumeName, setResumeName] = useState("");
  const [resumeText, setResumeText] = useState("");
  const [resumeUrl, setResumeUrl] = useState("");
  const [resumeDataUrl, setResumeDataUrl] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [stage, setStage] = useState("upload"); // upload | preview | role

  // restore from session storage if available
  React.useEffect(() => {
    const nav = location.state || {};
    const stored = sessionStorage.getItem("resumeForm");
    let saved = {};

    if (stored) {
      try {
        saved = JSON.parse(stored) || {};
      } catch {}
    }

    const source = { ...saved, ...nav };
    if (source.resumeName) setResumeName(source.resumeName);
    if (source.resumeText) setResumeText(source.resumeText);
    if (source.resumeDataUrl) setResumeDataUrl(source.resumeDataUrl);
    if (source.jobRole) setJobRole(source.jobRole);
    if (source.stage) setStage(source.stage);
  }, [location.state]);

  // keep storage in sync
  React.useEffect(() => {
    sessionStorage.setItem(
      "resumeForm",
      JSON.stringify({ resumeName, resumeText, resumeUrl, resumeDataUrl, jobRole, stage })
    );
  }, [resumeName, resumeText, resumeUrl, resumeDataUrl, jobRole, stage]);

  const jobOptions = [
    "Software Engineer",
    "Data Scientist",
    "Product Manager",
    "Sales Representative",
    "Customer Support",
    "Marketing Specialist",
    "HR Coordinator",
    "Business Analyst"
  ];

  const handleResumeFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (file.type !== "application/pdf") {
      alert("Only PDF files are allowed at this time.");
      return;
    }
    setResumeName(file.name);
    setResumeUrl(URL.createObjectURL(file));

    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result || "";
      setResumeText(text);
      setResumeDataUrl(text);
      setStage("preview");
    };
    reader.readAsText(file);
  };

  const startInterview = () => {
    if (!resumeText || !jobRole) return;
    navigate("/interview", {
      state: { jobRole, resumeText, resumeDataUrl, resumeName, stage: "role" }
    });
  };

  return (
    <div className="mock-page resume-page reveal">
      <MiniNavbar />

      {/* home button */}
      <div style={{ position: "absolute", top: 20, right: 20 }}>
        <button
          className="mock-btn"
          onClick={() => navigate("/")}
          style={{ padding: "6px 12px" }}
        >
          Home
        </button>
      </div>

      {/* hero */}
      <div className="mock-hero resume-hero">
        <div style={{ maxWidth: 720 }}>
          <h1>Resume-based Interview</h1>
          <p>
            Upload your resume and pick a role, and we'll craft questions
            that align with your experience and targets.
          </p>
        </div>
        <img src={resumeHero} alt="Resume Interview" className="mock-hero-img" />
      </div>

      {/* form card */}
      <div className="mock-section" style={{ maxWidth: 600, margin: "40px auto" }}>
        <div className="card" style={{ padding: 30, borderRadius: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
          {stage === "upload" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Upload PDF Resume</h2>

              <div style={{ display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
                <label
                  htmlFor="resume-upload"
                  style={{
                    border: "2px dashed #9ca3af",
                    padding: 30,
                    width: "100%",
                    textAlign: "center",
                    borderRadius: 8,
                    cursor: "pointer",
                    color: "#6b7280"
                  }}
                >
                  {resumeName ? resumeName : "Click to select a PDF"}
                  <input
                    id="resume-upload"
                    type="file"
                    accept="application/pdf"
                    hidden
                    onChange={handleResumeFile}
                  />
                </label>

                <button
                  className="go-back-btn"
                  onClick={() => navigate(-1)}
                >
                  Back
                </button>
              </div>
            </>
          )}

          {stage === "preview" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Preview Resume</h2>
              {resumeUrl && (
                <iframe
                  title="Resume preview"
                  src={resumeUrl}
                  style={{ width: "100%", height: 400, border: "1px solid #d1d5db" }}
                />
              )}
              <div style={{ marginTop: 20, display: "flex", gap: 20, justifyContent: "center" }}>
                <button
                  className="mock-btn"
                  style={{ background: "rgba(255,255,255,0.15)", color: "#1e1e2f", minWidth: 100 }}
                  onClick={() => setStage("upload")}
                >
                  Change File
                </button>
                <button
                  className="mock-btn"
                  style={{ background: "#059669", minWidth: 100 }}
                  onClick={() => setStage("role")}
                  disabled={!resumeText}
                >
                  Next
                </button>
              </div>
            </>
          )}

          {stage === "role" && (
            <>
              <h2 style={{ marginBottom: 20 }}>Choose Role</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
                <select
                  value={jobRole}
                  onChange={(e) => setJobRole(e.target.value)}
                  style={{ padding: 10, width: "80%", borderRadius: 6 }}
                >
                  <option value="">-- choose job role --</option>
                  {jobOptions.map((r, i) => (
                    <option key={i} value={r}>{r}</option>
                  ))}
                </select>

                <button
                  className="mock-btn"
                  style={{ marginTop: 10, width: "80%" }}
                  disabled={!jobRole}
                  onClick={startInterview}
                >
                  Start Interview
                </button>

                <button
                  className="mock-btn"
                  style={{ background: "rgba(255,255,255,0.15)", color: "#1e1e2f", width: "50%" }}
                  onClick={() => setStage("preview")}
                >
                  Back
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
export default ResumeInterview;
