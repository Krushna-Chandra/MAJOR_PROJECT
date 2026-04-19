import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import resumeHero from "../assets/resume.png";
import {
  CORPORATE_JOB_ROLES,
  getResolvedJobRole,
  getRoleSuggestions,
  normalizeRoleText,
} from "../utils/roleSearch";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const RESUME_INTERVIEW_STORAGE_KEY = "resumeInterviewFlow";

const HOW_IT_WORKS_CARDS = [
  {
    accent: "accent-cyan",
    step: "01",
    title: "Upload Your Resume",
    body: "Choose a PDF resume and confirm the preview before moving to the interview setup.",
  },
  {
    accent: "accent-violet",
    step: "02",
    title: "Pick Your Role",
    body: "Select the target job role so the interview can align the resume with the right expectations.",
  },
  {
    accent: "accent-amber",
    step: "03",
    title: "Review Extracted Signals",
    body: "See technical skills, projects, internships, experience, and hobbies beside the resume preview.",
  },
  {
    accent: "accent-emerald",
    step: "04",
    title: "Start Resume Interview",
    body: "The backend uses your extracted profile to ask a more human mix of technical and HR-style questions.",
  },
];

const EMPTY_REVIEW = {
  candidate_name: "",
  raw_resume_text: "",
  normalized_resume_text: "",
  simple_resume_text: "",
  extracted: {
    career_objective: "",
    educational_qualifications: [],
    technical_skills: [],
    projects: [],
    internships: [],
    experience: [],
    achievements: [],
    languages: [],
    hobbies: [],
  },
  recommended_focus: [],
  interview_ready: false,
  ready_reason: "",
};

function ResumeInterview() {
  const navigate = useNavigate();
  const location = useLocation();

  const [resumeName, setResumeName] = useState("");
  const [resumeDataUrl, setResumeDataUrl] = useState("");
  const [resumeBytes, setResumeBytes] = useState(0);
  const [resumeText, setResumeText] = useState("");
  const [jobRole, setJobRole] = useState("");
  const [stage, setStage] = useState("upload");
  const [reviewData, setReviewData] = useState(EMPTY_REVIEW);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [roleSuggestions, setRoleSuggestions] = useState([]);
  const [showRoleSuggestions, setShowRoleSuggestions] = useState(false);
  const [selectedQuestionCount, setSelectedQuestionCount] = useState(10);

  const authHeaders = () => {
    const token = localStorage.getItem("token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  useEffect(() => {
    const navState = location.state || {};
    const stored = sessionStorage.getItem(RESUME_INTERVIEW_STORAGE_KEY);
    let saved = {};

    if (stored) {
      try {
        saved = JSON.parse(stored) || {};
      } catch {
        saved = {};
      }
    }

    const source = { ...saved, ...navState };
    setResumeName(source.resumeName || "");
    setResumeDataUrl(source.resumeDataUrl || "");
    setResumeBytes(source.resumeBytes || 0);
    setResumeText(source.resumeText || "");
    setJobRole(source.jobRole || "");
    setStage(source.stage || "upload");
    setReviewData(source.reviewData || EMPTY_REVIEW);
  }, [location.state]);

  useEffect(() => {
    sessionStorage.setItem(
      RESUME_INTERVIEW_STORAGE_KEY,
      JSON.stringify({
        resumeName,
        resumeDataUrl,
        resumeBytes,
        resumeText,
        jobRole,
        stage,
        reviewData,
      })
    );
  }, [jobRole, resumeBytes, resumeDataUrl, resumeName, resumeText, reviewData, stage]);

  const canGoToRoleStage = Boolean(resumeDataUrl);
  const canRequestReview = Boolean(resumeDataUrl && jobRole.trim());
  const canStartInterview = Boolean(reviewData.interview_ready && resumeText && jobRole.trim());

  const extractedSections = reviewData.extracted || EMPTY_REVIEW.extracted;
  const combinedProjectInternshipItems = useMemo(() => {
    const merged = [];
    const seen = new Set();
    [...(extractedSections.internships || []), ...(extractedSections.projects || [])].forEach(
      (item) => {
        const cleaned = String(item || "").trim();
        const canonical = normalizeRoleText(cleaned);
        if (!cleaned || !canonical || seen.has(canonical)) return;
        seen.add(canonical);
        merged.push(cleaned);
      }
    );
    return merged;
  }, [extractedSections.internships, extractedSections.projects]);

  const currentFocusAreas = useMemo(() => {
    const candidates = [
      ...(reviewData.recommended_focus || []),
      ...(extractedSections.technical_skills || []),
      ...combinedProjectInternshipItems,
      ...(extractedSections.experience || []),
      ...(extractedSections.hobbies || []),
    ];
    const deduped = [];
    const seen = new Set();
    candidates.forEach((item) => {
      const cleaned = String(item || "").trim();
      if (!cleaned || cleaned.length > 90) return;
      const canonical = normalizeRoleText(cleaned);
      if (!canonical || seen.has(canonical)) return;
      seen.add(canonical);
      deduped.push(cleaned);
    });
    return deduped.slice(0, 10);
  }, [combinedProjectInternshipItems, extractedSections.experience, extractedSections.hobbies, extractedSections.technical_skills, reviewData.recommended_focus]);

  const simpleResumePreview = useMemo(() => {
    const sourceText =
      reviewData.normalized_resume_text ||
      reviewData.raw_resume_text ||
      resumeText ||
      "";
    const lines = sourceText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);

    const emailMatch = sourceText.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
    const phoneMatch = sourceText.match(/(\+?\d[\d\s/()-]{8,}\d)/);
    const locationLine =
      lines.find((line) => /pin-|dist-|at\/po-|via-|balasore|remuna/i.test(line)) || "";
    const resumeNameLabel =
      reviewData.candidate_name || resumeName.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ").trim() || "Candidate";
    const initials = resumeNameLabel
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "CV";

    return {
      name: reviewData.candidate_name || resumeNameLabel,
      role: jobRole || "Resume-based Interview",
      email: emailMatch?.[0] || "",
      phone: phoneMatch?.[0] || "",
      location: locationLine,
      initials,
      summary: extractedSections.career_objective || "",
      education: extractedSections.educational_qualifications || [],
      achievements: extractedSections.achievements || [],
      skills: extractedSections.technical_skills || [],
      projects: combinedProjectInternshipItems,
      languages: extractedSections.languages || [],
      interests: extractedSections.hobbies || [],
    };
  }, [
    combinedProjectInternshipItems,
    extractedSections.achievements,
    extractedSections.career_objective,
    extractedSections.educational_qualifications,
    extractedSections.hobbies,
    extractedSections.languages,
    extractedSections.technical_skills,
    jobRole,
    resumeName,
    resumeText,
    reviewData.candidate_name,
    reviewData.normalized_resume_text,
    reviewData.raw_resume_text,
  ]);

  const handleResumeFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("Please upload a PDF resume only.");
      return;
    }

    setLoading(true);
    setError("");
    setReviewData(EMPTY_REVIEW);
    setResumeText("");

    const reader = new FileReader();
    reader.onload = () => {
      const nextDataUrl = typeof reader.result === "string" ? reader.result : "";
      if (!nextDataUrl) {
        setLoading(false);
        setError("We could not read this PDF. Please try another file.");
        return;
      }
      setResumeName(file.name);
      setResumeDataUrl(nextDataUrl);
      setResumeBytes(file.size || 0);
      setStage("preview");
      setLoading(false);
    };
    reader.onerror = () => {
      setLoading(false);
      setError("We could not read this PDF. Please try another file.");
    };
    reader.readAsDataURL(file);
  };

  const handleJobRoleChange = (event) => {
    const value = event.target.value;
    setJobRole(value);
    setShowRoleSuggestions(true);
    if (value.trim()) {
      setRoleSuggestions(getRoleSuggestions(value, CORPORATE_JOB_ROLES));
    } else {
      setRoleSuggestions([]);
    }
  };

  const handleJobRoleBlur = () => {
    window.setTimeout(() => {
      setShowRoleSuggestions(false);
      const resolvedRole = getResolvedJobRole(jobRole, CORPORATE_JOB_ROLES);
      if (
        resolvedRole &&
        normalizeRoleText(resolvedRole) !== normalizeRoleText(jobRole)
      ) {
        setJobRole(resolvedRole);
      }
    }, 120);
  };

  const selectRoleSuggestion = (role) => {
    setJobRole(role);
    setRoleSuggestions(getRoleSuggestions(role, CORPORATE_JOB_ROLES));
    setShowRoleSuggestions(false);
  };

  const extractResumeInsights = async () => {
    if (!canRequestReview) {
      setError("Upload a resume and choose a job role first.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const resolvedRole = getResolvedJobRole(jobRole, CORPORATE_JOB_ROLES) || jobRole.trim();
      const response = await axios.post(
        `${API_BASE_URL}/resume-interview/extract`,
        {
          file_name: resumeName,
          resume_data_url: resumeDataUrl,
          job_role: resolvedRole,
        },
        {
          headers: authHeaders(),
          timeout: 180000,
        }
      );

      setJobRole(resolvedRole);
      setResumeText(response.data?.resume_text || "");
      const reviewDataObj = {
        candidate_name: response.data?.candidate_name || "",
        raw_resume_text: response.data?.raw_resume_text || response.data?.resume_text || "",
        normalized_resume_text:
          response.data?.normalized_resume_text ||
          response.data?.resume_text ||
          "",
        simple_resume_text:
          response.data?.simple_resume_text ||
          response.data?.normalized_resume_text ||
          response.data?.resume_text ||
          "",
        extracted: response.data?.extracted || EMPTY_REVIEW.extracted,
        recommended_focus: response.data?.recommended_focus || [],
        interview_ready: Boolean(response.data?.interview_ready),
        ready_reason: response.data?.ready_reason || "",
      };
      setReviewData(reviewDataObj);

      // Navigate to AnalyzedResume page with all data
      setTimeout(() => {
        navigate("/analyzed-resume", {
          state: {
            reviewData: reviewDataObj,
            resumeDataUrl,
            resumeName,
            jobRole: resolvedRole,
            resumeText: response.data?.resume_text || "",
            resumeBytes,
            currentFocusAreas,
            selectedQuestionCount,
          },
        });
      }, 800); // Small delay to let loading overlay complete
    } catch (requestError) {
      const statusCode = requestError?.response?.status;
      const backendDetail = requestError?.response?.data?.detail;
      if (requestError?.code === "ECONNABORTED") {
        setError("Resume review is taking too long. Please try again, or use a smaller/cleaner PDF resume.");
      } else if (statusCode === 404) {
        setError("The resume review endpoint was not found. Restart the backend server so `/resume-interview/extract` becomes available.");
      } else if (!requestError?.response) {
        setError(`Could not complete resume review. ${requestError?.message || "No response was received from the backend."}`);
      } else {
        setError(
          backendDetail ||
            `Resume review failed with status ${statusCode}. Please try again after restarting the backend.`
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const startInterview = () => {
    if (!canStartInterview) {
      setError(
        reviewData.ready_reason ||
          "At least one clear skill, project, or experience signal is required before starting the interview."
      );
      return;
    }

    navigate("/interview", {
      state: {
        category: "resume",
        selectedMode: "role",
        stage: "role",
        jobRole,
        resumeText,
        resumeDataUrl,
        resumeName,
        resumeBytes,
        selectedOptions: currentFocusAreas,
        focusAreas: currentFocusAreas,
        experience: "Resume-based",
        questionCount: selectedQuestionCount,
        practiceType: "voice interview",
        resumeInsights: reviewData,
      },
    });
  };

  const resetFlow = () => {
    setResumeName("");
    setResumeDataUrl("");
    setResumeBytes(0);
    setResumeText("");
    setJobRole("");
    setStage("upload");
    setReviewData(EMPTY_REVIEW);
    setRoleSuggestions([]);
    setShowRoleSuggestions(false);
    setError("");
  };

  const renderSignalCard = (label, items, emptyText) => {
    const hasItems = Array.isArray(items) ? items.length > 0 : Boolean(items);
    return (
    <div
      className="resume-studio-quick-card"
      style={{
        minHeight: 160,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10 }}>
          <strong style={{ display: "block" }}>{label}</strong>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "6px 10px",
              borderRadius: 999,
              background: hasItems ? "rgba(5, 150, 105, 0.12)" : "rgba(239, 68, 68, 0.10)",
              color: hasItems ? "#047857" : "#b91c1c",
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            {hasItems ? "Present" : "Missing"}
          </span>
        </div>
        {Array.isArray(items) && items.length ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {items.map((item) => (
              <span
                key={`${label}-${item}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "8px 12px",
                  borderRadius: 999,
                  background: "rgba(15, 23, 42, 0.06)",
                  color: "#0f172a",
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                {item}
              </span>
            ))}
          </div>
        ) : !Array.isArray(items) && hasItems ? (
          <p style={{ margin: 0 }}>{items}</p>
        ) : (
          <p style={{ margin: 0 }}>{emptyText}</p>
        )}
      </div>
    </div>
    );
  };

  const renderSimpleResumeSection = (title, content) => (
    <section className="resume-simple-preview__section">
      <h4>{title}</h4>
      {content}
    </section>
  );

  return (
    <div className="mock-page resume-page reveal">
      <MiniNavbar />

      <div style={{ position: "absolute", top: 20, right: 20 }}>
        <button
          className="mock-btn"
          onClick={() => navigate("/")}
          style={{ padding: "6px 12px" }}
        >
          Home
        </button>
      </div>

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

      <section className="mock-section how-it-works-section" style={{ marginTop: 10 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <h2 style={{ marginBottom: 10 }}>How It Works</h2>
          <p style={{ color: "#475569", margin: 0 }}>
            Keep the landing page feel, but make the interview flow smarter after the resume is uploaded.
          </p>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 18,
          }}
        >
          {HOW_IT_WORKS_CARDS.map((card) => (
            <div key={card.step} className={`how-it-works-card ${card.accent}`}>
              <span>{card.step}</span>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="mock-section" style={{ maxWidth: 1180, margin: "36px auto 48px" }}>
        {error ? (
          <div
            style={{
              marginBottom: 18,
              padding: "16px 18px",
              borderRadius: 16,
              background: "#fff1f2",
              border: "1px solid #fecdd3",
              color: "#9f1239",
              fontWeight: 600,
            }}
          >
            {error}
          </div>
        ) : null}

        {/* Loading Overlay */}
        {loading && (
          <div style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.5)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}>
            <div style={{
              background: "white",
              borderRadius: 24,
              padding: "60px 40px",
              textAlign: "center",
              boxShadow: "0 20px 60px rgba(0, 0, 0, 0.3)",
              maxWidth: 420,
            }}>
              {/* Loading Illustration */}
              <div style={{
                fontSize: 60,
                marginBottom: 20,
                animation: "bounce 1.5s infinite ease-in-out",
              }}>
                📄
              </div>
              
              <h2 style={{
                margin: "0 0 12px 0",
                color: "#0f172a",
                fontSize: "1.5rem",
              }}>
                Analyzing Your Resume
              </h2>
              
              <p style={{
                margin: "0 0 28px 0",
                color: "#64748b",
                fontSize: "0.95rem",
              }}>
                Extracting skills, experience, and key signals...
              </p>
              
              {/* Progress Bar */}
              <div style={{
                background: "#e2e8f0",
                borderRadius: 999,
                height: 8,
                overflow: "hidden",
                marginBottom: 24,
              }}>
                <div style={{
                  height: "100%",
                  background: "linear-gradient(90deg, #2563eb, #7c3aed)",
                  borderRadius: 999,
                  animation: "slideIn 2s ease-in-out infinite",
                  width: "100%",
                }}></div>
              </div>
              
              <p style={{
                margin: 0,
                color: "#94a3b8",
                fontSize: "0.85rem",
              }}>
                This may take up to 30 seconds...
              </p>
            </div>

            <style>{`
              @keyframes bounce {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
              }
              @keyframes slideIn {
                0% { transform: translateX(-100%); }
                50% { transform: translateX(100%); }
                100% { transform: translateX(100%); }
              }
            `}</style>
          </div>
        )}

        {stage !== "review" && (
          <div
            className="resume-studio-card"
            style={{
              maxWidth: 760,
              margin: "0 auto",
              padding: 28,
            }}
          >
            {stage === "upload" && (
              <>
                <div style={{ marginBottom: 24 }}>
                  <span style={{ color: "#0f766e", fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: 12 }}>
                    Stage 1
                  </span>
                  <h2 style={{ margin: "10px 0 8px" }}>Upload Resume PDF</h2>
                  <p style={{ margin: 0, color: "#475569" }}>
                    Start by uploading the resume you want the interview to follow.
                  </p>
                </div>

                <label
                  htmlFor="resume-upload"
                  style={{
                    display: "block",
                    border: "2px dashed #94a3b8",
                    borderRadius: 24,
                    padding: 34,
                    textAlign: "center",
                    cursor: "pointer",
                    background: "linear-gradient(135deg, rgba(255,255,255,0.86), rgba(240,249,255,0.92))",
                  }}
                >
                  <div style={{ fontSize: 18, fontWeight: 800, color: "#0f172a", marginBottom: 8 }}>
                    {resumeName || "Click to choose a resume PDF"}
                  </div>
                  <div style={{ color: "#64748b" }}>
                    PDF only. After upload, you can preview the resume before extracting interview signals.
                  </div>
                  <input
                    id="resume-upload"
                    type="file"
                    accept="application/pdf"
                    hidden
                    onChange={handleResumeFile}
                  />
                </label>

                <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between", gap: 14 }}>
                  <button className="go-back-btn" onClick={() => navigate(-1)} disabled={loading}>
                    Back
                  </button>
                  {loading ? (
                    <div style={{ alignSelf: "center", color: "#475569", fontWeight: 700 }}>Preparing PDF...</div>
                  ) : null}
                </div>
              </>
            )}

            {stage === "preview" && (
              <>
                <div style={{ marginBottom: 20 }}>
                  <span style={{ color: "#0f766e", fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: 12 }}>
                    Stage 2
                  </span>
                  <h2 style={{ margin: "10px 0 8px" }}>Preview Resume</h2>
                  <p style={{ margin: 0, color: "#475569" }}>
                    Confirm the uploaded file before choosing the target role.
                  </p>
                </div>
                <div className="resume-analyzer-preview-card" style={{ padding: 14 }}>
                  {resumeDataUrl ? (
                    <iframe
                      title="Resume preview"
                      src={resumeDataUrl}
                      style={{ width: "100%", height: 480, border: 0, borderRadius: 18 }}
                    />
                  ) : null}
                </div>
                <div style={{ marginTop: 12, color: "#64748b", fontWeight: 600 }}>
                  {resumeName} {resumeBytes ? `• ${(resumeBytes / 1024).toFixed(1)} KB` : ""}
                </div>
                <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between", gap: 14 }}>
                  <button
                    className="mock-btn"
                    style={{ background: "rgba(255,255,255,0.12)", color: "#0f172a" }}
                    onClick={resetFlow}
                    disabled={loading}
                  >
                    Change File
                  </button>
                  <button
                    className="mock-btn"
                    style={{ background: "#059669" }}
                    onClick={() => setStage("role")}
                    disabled={!canGoToRoleStage || loading}
                  >
                    Next
                  </button>
                </div>
              </>
            )}

            {stage === "role" && (
              <>
                <div style={{ marginBottom: 20 }}>
                  <span style={{ color: "#0f766e", fontWeight: 800, letterSpacing: "0.08em", textTransform: "uppercase", fontSize: 12 }}>
                    Stage 3
                  </span>
                  <h2 style={{ margin: "10px 0 8px" }}>Choose Job Role</h2>
                  <p style={{ margin: 0, color: "#475569" }}>
                    This role helps the backend align the resume with the right interview expectations.
                  </p>
                </div>

                <div style={{ position: "relative" }}>
                  <input
                    type="text"
                    value={jobRole}
                    onChange={handleJobRoleChange}
                    onBlur={handleJobRoleBlur}
                    onFocus={() => setShowRoleSuggestions(true)}
                    placeholder="Search a job role..."
                    style={{
                      width: "100%",
                      padding: "14px 16px",
                      borderRadius: 16,
                      border: "1px solid #cbd5e1",
                      background: "#fff",
                      fontSize: 15,
                    }}
                  />

                  {showRoleSuggestions && roleSuggestions.length > 0 ? (
                    <div
                      style={{
                        position: "absolute",
                        top: 56,
                        left: 0,
                        right: 0,
                        background: "#fff",
                        border: "1px solid #cbd5e1",
                        borderRadius: 16,
                        boxShadow: "0 20px 40px rgba(15, 23, 42, 0.12)",
                        zIndex: 20,
                        maxHeight: 250,
                        overflowY: "auto",
                      }}
                    >
                      {roleSuggestions.map((role) => (
                        <button
                          key={role}
                          type="button"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => selectRoleSuggestion(role)}
                          style={{
                            display: "block",
                            width: "100%",
                            textAlign: "left",
                            padding: "12px 14px",
                            border: 0,
                            background: "transparent",
                            cursor: "pointer",
                            color: "#0f172a",
                          }}
                        >
                          {role}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div style={{ marginTop: 22, display: "flex", justifyContent: "space-between", gap: 14 }}>
                  <button
                    className="mock-btn"
                    style={{ background: "rgba(255,255,255,0.12)", color: "#0f172a" }}
                    onClick={() => setStage("preview")}
                    disabled={loading}
                  >
                    Back
                  </button>
                  <button
                    className="mock-btn"
                    style={{ background: "#2563eb" }}
                    onClick={extractResumeInsights}
                    disabled={!canRequestReview || loading}
                  >
                    {loading ? "Analyzing..." : "Analyze My Resume"}
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ResumeInterview;
