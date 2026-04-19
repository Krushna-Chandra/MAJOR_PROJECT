import React, { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BadgeCheck,
  CircleAlert,
  FileSearch,
  FileText,
  LoaderCircle,
  SearchCheck,
  Sparkles,
  WandSparkles,
} from "lucide-react";
import "../App.css";
import {
  CORPORATE_JOB_ROLES,
  getResolvedJobRole,
  getRoleSuggestions,
  normalizeRoleText,
} from "../utils/roleSearch";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const ANALYZER_RESULT_STORAGE_KEY = "resumeAnalyzerResult";

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const EXPERIENCE_OPTIONS = [
  "Fresher",
  "1-3 years",
  "3-5 years",
  "5+ years",
];

function buildCareerObjective(role, experience) {
  const cleanRole = getResolvedJobRole(role, CORPORATE_JOB_ROLES);
  if (!cleanRole) return "";

  const normalizedRole = cleanRole.toLowerCase();
  const experienceLabel = experience || "Fresher";
  const normalizedExperience = experienceLabel.toLowerCase();
  const isFresherLike = ["entry level", "fresher", "intern", "0-1 years"].includes(normalizedExperience);

  const roleFocus =
    /data|analyst|analytics|business intelligence|power bi|tableau/.test(normalizedRole)
      ? "use analytical thinking, reporting skills, and data interpretation to support better business decisions"
      : /frontend|ui|ux|web|react|angular|vue/.test(normalizedRole)
        ? "build clean, responsive, and user-friendly digital experiences"
        : /backend|software|developer|engineer|full stack|devops|cloud|security|qa|automation|sre|database/.test(normalizedRole)
          ? "apply technical problem-solving, development knowledge, and project experience to build reliable solutions"
          : /product|project|scrum/.test(normalizedRole)
            ? "support planning, execution, collaboration, and delivery across teams"
            : /marketing|sales|customer success|operations|finance|hr|talent|recruit/.test(normalizedRole)
              ? "contribute strong communication, coordination, and business skills in a results-driven team"
              : "apply relevant skills, practical knowledge, and a growth mindset in a professional role";

  if (isFresherLike) {
    return `Motivated and enthusiastic fresher seeking a ${cleanRole} role where I can ${roleFocus} while learning from real-world work, strengthening my professional capabilities, and contributing with dedication from the beginning of my career.`;
  }

  if (normalizedExperience === "1-3 years") {
    return `Early-career professional seeking a ${cleanRole} role where I can ${roleFocus}, build on my existing experience, and contribute with consistency, adaptability, and a strong learning mindset.`;
  }

  if (normalizedExperience === "3-5 years") {
    return `Experienced professional seeking a ${cleanRole} role where I can ${roleFocus}, take ownership of meaningful work, and deliver strong results through practical experience and collaboration.`;
  }

  if (normalizedExperience === "5+ years") {
    return `Seasoned professional seeking a ${cleanRole} role where I can ${roleFocus}, drive high-quality outcomes, and add value through deep hands-on experience and dependable execution.`;
  }

  return `Results-oriented professional seeking a ${cleanRole} role where I can ${roleFocus}, contribute effectively based on my ${experienceLabel.toLowerCase()} background, and continue growing through meaningful work and measurable impact.`;
}

function generateJobDescription(role, experience) {
  const cleanRole = getResolvedJobRole(role, CORPORATE_JOB_ROLES);
  if (!cleanRole) return "";
  const cleanExperience = experience || "Fresher";
  const careerObjective = buildCareerObjective(cleanRole, cleanExperience);
  return `Job Role: ${cleanRole}
Experience: ${cleanExperience}
Career Objective: ${careerObjective}`;
}

function ResumeAnalyzer() {
  const navigate = useNavigate();
  const [resumeName, setResumeName] = useState("");
  const [resumeDataUrl, setResumeDataUrl] = useState("");
  const [resumeBytes, setResumeBytes] = useState(0);
  const [jobRole, setJobRole] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [roleSuggestions, setRoleSuggestions] = useState([]);
  const [showRoleSuggestions, setShowRoleSuggestions] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadInputKey, setUploadInputKey] = useState(0);

  const authHeaders = () => {
    const token = localStorage.getItem("token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const clearUploadedResume = () => {
    setResumeName("");
    setResumeDataUrl("");
    setResumeBytes(0);
    setUploadError("");
    setUploadInputKey((current) => current + 1);
  };

  const handleResumeFile = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      clearUploadedResume();
      setUploadError("Please upload a PDF file only.");
      return;
    }

    setLoading(true);
    setError("");
    setUploadError("");

    const reader = new FileReader();
    reader.onload = () => {
      const nextDataUrl = typeof reader.result === "string" ? reader.result : "";
      if (!nextDataUrl) {
        clearUploadedResume();
        setUploadError("We could not read this file. Please try another PDF.");
        setLoading(false);
        return;
      }

      setResumeName(file.name);
      setResumeBytes(file.size || 0);
      setResumeDataUrl(nextDataUrl);
      setUploadError("");
      setError("");
      setLoading(false);
    };
    reader.onerror = () => {
      clearUploadedResume();
      setUploadError("We could not read this file. Please try another PDF.");
      setLoading(false);
    };
    reader.readAsDataURL(file);
  };

  useEffect(() => {
    setJobDescription(generateJobDescription(jobRole, experienceLevel));
  }, [jobRole, experienceLevel]);

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
    setShowRoleSuggestions(false);
    setRoleSuggestions(getRoleSuggestions(role, CORPORATE_JOB_ROLES));
  };

  const resetAnalyzer = () => {
    setResumeName("");
    setResumeDataUrl("");
    setResumeBytes(0);
    setJobRole("");
    setExperienceLevel("");
    setJobDescription("");
    setRoleSuggestions([]);
    setShowRoleSuggestions(false);
    setUploadError("");
    setError("");
    setLoading(false);
    setUploadInputKey((current) => current + 1);

    try {
      sessionStorage.removeItem(ANALYZER_RESULT_STORAGE_KEY);
    } catch {
      // Storage cleanup failure should not block the UI reset.
    }
  };

  const analyzeResume = async () => {
    if (!resumeDataUrl) {
      setError("Upload your resume PDF first.");
      return;
    }
    if (!jobRole.trim() || !experienceLevel.trim()) {
      setError(
        "Please choose a job role and experience level before running the analysis."
      );
      return;
    }

    try {
      setLoading(true);
      setError("");

      const response = await axios.post(
        `${API_BASE_URL}/resume-analyzer`,
        {
          file_name: resumeName,
          resume_data_url: resumeDataUrl,
          job_description: jobDescription,
        },
        {
          headers: authHeaders(),
          timeout: 60000,
        }
      );

      const resultPayload = {
        fileName: resumeName,
        resumeDataUrl,
        resumeBytes,
        jobDescription,
        createdAt: new Date().toISOString(),
        analyzedAt: new Date().toISOString(),
        result: response.data,
      };

      try {
        sessionStorage.setItem(
          ANALYZER_RESULT_STORAGE_KEY,
          JSON.stringify(resultPayload)
        );
      } catch {
        // Navigation state still carries the report if browser storage is unavailable.
      }
      navigate("/resume-analyzer/results", {
        state: { resultPayload },
      });
    } catch (requestError) {
      setError(
        requestError?.code === "ECONNABORTED"
          ? "The analysis is taking too long. Please try again with a smaller or cleaner text-based PDF."
          : requestError?.response?.data?.detail ||
            "Resume analysis failed. Please try again with a clear PDF resume."
      );
    } finally {
      setLoading(false);
    }
  };

  const quickChecks = [
    {
      icon: <SearchCheck size={18} />,
      title: "ATS scan",
      body: "Structure, missing sections, readability, contact detection, and keyword alignment.",
    },
    {
      icon: <Sparkles size={18} />,
      title: "Quality review",
      body: "Strengths, weak areas, impact language, and what needs to be added next.",
    },
    {
      icon: <BadgeCheck size={18} />,
      title: "Actionable output",
      body: "A clean report that is easy to review beside your original PDF.",
    },
  ];

  const insightCards = [
    {
      icon: <FileSearch size={18} />,
      title: "What the scan checks",
      body: "Sections, contact details, resume strength, role-fit keywords, and improvement priorities.",
    },
    {
      icon: <WandSparkles size={18} />,
      title: "Why this page is different",
      body: "This flow stays focused on one task only: turning your resume into a clearer and stronger document.",
    },
  ];

  return (
    <div className="resume-studio-page">
      <main className="resume-studio-shell">
        <section className="resume-studio-hero reveal">
          <div className="resume-studio-kicker">Resume Lab</div>
          <div className="resume-studio-hero-grid">
            <div className="resume-studio-hero-copy">
              <h1>Upload your resume. See what is weak. Leave with a sharper draft.</h1>
              <p>
                This analyzer is built like a focused workspace, not a typical
                app form. Upload your PDF, preview it instantly, choose a target
                role and experience level, and get a full review once the report is ready.
              </p>

              <div className="resume-studio-quick-grid">
                {quickChecks.map((item) => (
                  <article key={item.title} className="resume-studio-quick-card">
                    <div className="resume-studio-quick-icon">{item.icon}</div>
                <strong>{item.title}</strong>
                <p>{item.body}</p>
                  </article>
                ))}
              </div>
            </div>

            <div className="resume-studio-hero-board" aria-hidden="true">
              <div className="resume-studio-board-panel is-main">
                <span>Resume Score Flow</span>
                <strong>Scan, diagnose, improve</strong>
                <div className="resume-studio-board-lines">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
              <div className="resume-studio-board-panel is-note">
                <span>Missing Sections</span>
                <strong>Detected instantly</strong>
              </div>
              <div className="resume-studio-board-panel is-note-alt">
                <span>Role Match</span>
                <strong>Optional job-fit check</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="resume-studio-workbench reveal">
          <section className="resume-studio-card resume-studio-editor">
            <div className="resume-studio-section-head">
              <div>
                <span>Upload Workspace</span>
                <h2>Drop in the resume you want to review</h2>
              </div>
              <div className="resume-studio-head-icon">
                <FileText size={20} />
              </div>
            </div>

            <label className="resume-studio-upload" htmlFor="resume-analyzer-upload">
              <div className="resume-studio-upload-icon">
                <FileText size={24} />
              </div>
              <div className="resume-studio-upload-copy">
                <strong>{resumeName || "Choose a PDF resume"}</strong>
                <span>
                  {resumeName
                    ? `Selected file - ${formatFileSize(resumeBytes)}`
                    : "Upload a text-based PDF so the analyzer can read it cleanly."}
                </span>
              </div>
              <input
                key={uploadInputKey}
                id="resume-analyzer-upload"
                type="file"
                accept="application/pdf"
                hidden
                onChange={handleResumeFile}
              />
            </label>

            {resumeDataUrl ? (
              <div className="resume-studio-preview">
                <div className="resume-studio-preview-top">
                  <div>
                    <span>Live Preview</span>
                    <h3>{resumeName}</h3>
                  </div>
                  <div className="resume-studio-meta-pills">
                    <span>{formatFileSize(resumeBytes)}</span>
                    <span>PDF loaded</span>
                  </div>
                </div>
                <iframe
                  className="resume-studio-frame"
                  src={resumeDataUrl}
                  title="Uploaded resume preview"
                />
              </div>
            ) : (
              <div className="resume-studio-empty-preview">
                {uploadError ? (
                  <div className="resume-studio-preview-upload-alert" role="alert">
                    <div className="resume-studio-empty-icon is-error">
                      <CircleAlert size={22} />
                    </div>
                    <strong>Upload not accepted</strong>
                    <p>{uploadError}</p>
                  </div>
                ) : (
                  <>
                    <div className="resume-studio-empty-icon">
                      <FileSearch size={22} />
                    </div>
                    <strong>Preview appears here</strong>
                    <p>Your uploaded resume will be shown here before analysis starts.</p>
                  </>
                )}
              </div>
            )}

            <div className="resume-studio-field">
              <label htmlFor="job-role">Target role</label>
              <div className="resume-studio-autocomplete">
                <input
                  id="job-role"
                  className="resume-studio-input"
                  placeholder="Search a job role — e.g. Software Engineer"
                  value={jobRole}
                  onChange={handleJobRoleChange}
                  onFocus={() => setShowRoleSuggestions(true)}
                  onBlur={handleJobRoleBlur}
                  autoComplete="off"
                />
                {showRoleSuggestions && roleSuggestions.length > 0 && (
                  <ul className="resume-studio-suggestions">
                    {roleSuggestions.map((role) => (
                      <li
                        key={role}
                        onMouseDown={() => selectRoleSuggestion(role)}
                      >
                        {role}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <small className="resume-studio-field-note">
                Start typing to see matching roles. If the exact role is not listed, the field suggests and corrects to the closest matching job role.
              </small>
            </div>

            <div className="resume-studio-field">
              <label htmlFor="experience-level">Experience level</label>
              <select
                id="experience-level"
                className="resume-studio-input"
                value={experienceLevel}
                onChange={(event) => setExperienceLevel(event.target.value)}
              >
                <option value="">Select experience level</option>
                {EXPERIENCE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
              <small className="resume-studio-field-note">
                Choose how much experience the target role requires.
              </small>
            </div>

            <div className="resume-studio-field">
              <label>Generated target job description</label>
              <textarea
                className="resume-studio-textarea"
                value={jobDescription}
                readOnly
                rows={5}
              />
              <small className="resume-studio-field-note">
                The analyzer generates this description from your selected role and experience.
              </small>
            </div>

            <div className="resume-studio-actions">
              <button
                className="resume-studio-btn is-primary"
                onClick={analyzeResume}
                disabled={!resumeDataUrl || loading || !jobRole.trim() || !experienceLevel.trim()}
              >
                {loading ? (
                  <>
                    <span className="spinner" />
                    Analyzing Resume...
                  </>
                ) : (
                  <>
                    Open Full Analysis
                    <ArrowRight size={18} />
                  </>
                )}
              </button>

              <button
                className="resume-studio-btn is-secondary"
                type="button"
                onClick={resetAnalyzer}
              >
                Reset
              </button>
            </div>

            {error ? <div className="resume-studio-alert is-error">{error}</div> : null}

            {loading ? (
              <div className="resume-studio-progress">
                <div className="resume-studio-progress-head">
                  <div className="resume-studio-progress-icon">
                    <LoaderCircle size={20} />
                  </div>
                  <div>
                    <span>Analysis in progress</span>
                    <h3>We are building your report now</h3>
                  </div>
                </div>
                <div className="resume-studio-progress-bar">
                  <span />
                </div>
                <p>
                  Stay on this page while the scan finishes. The results screen
                  opens only after the full report is ready.
                </p>
              </div>
            ) : null}
          </section>

          <aside className="resume-studio-side">
            <section className="resume-studio-card resume-studio-side-card">
              <div className="resume-studio-section-head">
                <div>
                  <span>Inside the report</span>
                  <h2>What you will get back</h2>
                </div>
                <div className="resume-studio-head-icon">
                  <Sparkles size={20} />
                </div>
              </div>

              <div className="resume-studio-side-list">
                {insightCards.map((item) => (
                  <article key={item.title} className="resume-studio-side-item">
                    <div className="resume-studio-side-icon">{item.icon}</div>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.body}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="resume-studio-card resume-studio-side-card is-dark">
              <span className="resume-studio-note-label">Workflow</span>
              <h3>One clean path from raw PDF to final feedback.</h3>
              <ol className="resume-studio-timeline">
                <li>Upload your resume and verify the preview.</li>
                <li>Select the target job role and experience you want to match.</li>
                <li>Run analysis and wait for the completed report.</li>
                <li>Review required skills, education, weak areas, and stronger bullet ideas.</li>
              </ol>
            </section>

            <section className="resume-studio-card resume-studio-side-card is-soft">
              <div className="resume-studio-side-item">
                <div className="resume-studio-side-icon">
                  <CircleAlert size={18} />
                </div>
                <div>
                  <strong>Best results</strong>
                  <p>
                    Use a clear text-based PDF. Scanned image resumes can still
                    fail if the text cannot be extracted.
                  </p>
                </div>
              </div>
            </section>
          </aside>
        </section>
      </main>
    </div>
  );
}

export default ResumeAnalyzer;
