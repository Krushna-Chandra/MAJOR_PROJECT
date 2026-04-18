import React, { useState } from "react";
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

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";
const ANALYZER_RESULT_STORAGE_KEY = "resumeAnalyzerResult";

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isValidJobDescription(value) {
  return (value.match(/[A-Za-z][A-Za-z0-9+#./-]*/g) || []).length >= 20;
}

function ResumeAnalyzer() {
  const navigate = useNavigate();
  const [resumeName, setResumeName] = useState("");
  const [resumeDataUrl, setResumeDataUrl] = useState("");
  const [resumeBytes, setResumeBytes] = useState(0);
  const [jobDescription, setJobDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadInputKey, setUploadInputKey] = useState(0);

  const handleResumeFile = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const isPdf =
      file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setError("Please upload a PDF resume.");
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setResumeName(file.name);
      setResumeBytes(file.size || 0);
      setResumeDataUrl(typeof reader.result === "string" ? reader.result : "");
      setError("");
      setLoading(false);
    };
    reader.onerror = () => {
      setError("We could not read this file. Please try another PDF.");
    };
    reader.readAsDataURL(file);
  };

  const resetAnalyzer = () => {
    setResumeName("");
    setResumeDataUrl("");
    setResumeBytes(0);
    setJobDescription("");
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
    if (!isValidJobDescription(jobDescription)) {
      setError(
        "Please add a valid job description with enough detail before running the analysis."
      );
      return;
    }

    try {
      setLoading(true);
      setError("");

      const token = localStorage.getItem("token");
      const response = await axios.post(
        `${API_BASE_URL}/resume-analyzer`,
        {
          file_name: resumeName,
          resume_data_url: resumeDataUrl,
          job_description: jobDescription,
        },
        {
          headers: token
            ? {
                Authorization: `Bearer ${token}`,
              }
            : {},
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
                app form. Upload your PDF, preview it instantly, add the target
                job description, and get a full review once the report is ready.
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
                <div className="resume-studio-empty-icon">
                  <FileSearch size={22} />
                </div>
                <strong>Preview appears here</strong>
                <p>Your uploaded resume will be shown here before analysis starts.</p>
              </div>
            )}

            <div className="resume-studio-field">
              <label htmlFor="job-description">Target job description</label>
              <textarea
                id="job-description"
                className="resume-studio-textarea"
                placeholder="Paste the full job description here. This report now uses the target role to score fit, highlight weak areas, and flag spelling issues tied to the job."
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
              />
              <small className="resume-studio-field-note">
                Paste the full job description. The analyzer uses it to extract required skills, education, experience, role-fit gaps, and ATS keywords.
              </small>
            </div>

            <div className="resume-studio-actions">
              <button
                className="resume-studio-btn is-primary"
                onClick={analyzeResume}
                disabled={!resumeDataUrl || loading || !isValidJobDescription(jobDescription)}
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
                <li>Paste the target job description you want to match.</li>
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
