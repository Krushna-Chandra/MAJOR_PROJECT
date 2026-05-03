import React, { useMemo } from "react";
import { ArrowLeft, CheckCircle2, FileText, Home, Mic } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import { normalizeRoleText } from "../utils/roleSearch";
import { useScrollToTop } from "../hooks/useScrollToTop";

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

const getInitials = (name, fallback = "CV") => {
  const initials = String(name || "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return initials || fallback;
};

const renderList = (items, emptyText, limit = 5) => {
  const visibleItems = (items || []).filter(Boolean).slice(0, limit);

  if (!visibleItems.length) {
    return <p className="analyzed-pro-empty">{emptyText}</p>;
  }

  return (
    <ul className="analyzed-pro-list">
      {visibleItems.map((item) => (
        <li key={item}>{item}</li>
      ))}
      {(items || []).length > limit ? (
        <li className="analyzed-pro-muted">+{items.length - limit} more</li>
      ) : null}
    </ul>
  );
};

const renderChips = (items, emptyText, limit = 12) => {
  const visibleItems = (items || []).filter(Boolean).slice(0, limit);

  if (!visibleItems.length) {
    return <p className="analyzed-pro-empty">{emptyText}</p>;
  }

  return (
    <div className="analyzed-pro-chip-row">
      {visibleItems.map((item) => (
        <span key={item} className="analyzed-pro-chip">
          {item}
        </span>
      ))}
      {(items || []).length > limit ? (
        <span className="analyzed-pro-chip is-muted">+{items.length - limit} more</span>
      ) : null}
    </div>
  );
};

function AnalyzedResume() {
  useScrollToTop();
  const navigate = useNavigate();
  const location = useLocation();

  const state = location.state || {};
  const reviewData = state.reviewData || EMPTY_REVIEW;
  const resumeDataUrl = state.resumeDataUrl || "";
  const resumeName = state.resumeName || "";
  const jobRole = state.jobRole || "";
  const resumeExperience = state.resumeExperience || "Resume-based";
  const currentFocusAreas = state.currentFocusAreas || [];
  const selectedQuestionCount = state.selectedQuestionCount || 10;

  const extractedSections = reviewData.extracted || EMPTY_REVIEW.extracted;
  const combinedProjectInternshipItems = useMemo(() => {
    const merged = [];
    const seen = new Set();
    [...(extractedSections.internships || []), ...(extractedSections.projects || [])].forEach((item) => {
      const cleaned = String(item || "").trim();
      const canonical = normalizeRoleText(cleaned);
      if (!cleaned || !canonical || seen.has(canonical)) return;
      seen.add(canonical);
      merged.push(cleaned);
    });
    return merged;
  }, [extractedSections.internships, extractedSections.projects]);

  const candidateName =
    reviewData.candidate_name || resumeName.replace(/\.pdf$/i, "").replace(/[_-]+/g, " ") || "Candidate";
  
  // Parse hobbies and languages - handle both array and comma-separated string formats
  const parseItems = (items) => {
    if (!items) return [];
    let itemArray = Array.isArray(items) ? items : [items];
    
    // Flatten and split comma-separated values
    return itemArray
      .map(item => {
        if (!item) return null;
        if (typeof item === 'string') {
          // Split by comma and clean up
          return item.split(',').map(i => i.trim()).filter(Boolean);
        }
        return item;
      })
      .flat()
      .filter(Boolean);
  };
  
  const hobbiesParsed = parseItems(extractedSections.hobbies);
  const languagesParsed = parseItems(extractedSections.languages);
  
  const skillCount = (extractedSections.technical_skills || []).length;
  const projectCount = combinedProjectInternshipItems.length;
  const experienceCount = (extractedSections.experience || []).length;
  const educationCount = (extractedSections.educational_qualifications || []).length;
  const languageCount = languagesParsed.length;
  const hobbyCount = hobbiesParsed.length;

  const startInterview = () => {
    navigate("/interview", {
      state: {
        category: "resume",
        selectedMode: "role",
        stage: "role",
        jobRole,
        resumeText: state.resumeText || "",
        resumeDataUrl,
        resumeName,
        resumeBytes: state.resumeBytes || 0,
        selectedOptions: currentFocusAreas,
        focusAreas: currentFocusAreas,
        experience: resumeExperience,
        questionCount: selectedQuestionCount,
        practiceType: "voice interview",
        resumeInsights: reviewData,
      },
    });
  };

  const summaryStats = [
    { label: "Skills", value: skillCount },
    { label: "Projects", value: projectCount },
    { label: "Experience", value: experienceCount },
    { label: "Education", value: educationCount },
  ];

  return (
    <div className="analyzed-pro-page">
      <MiniNavbar />

      <main className="analyzed-pro-shell">
        <section className="analyzed-pro-header">
          <div className="analyzed-pro-identity">
            <div className="analyzed-pro-avatar">{getInitials(candidateName)}</div>
            <div>
              <div className="analyzed-pro-kicker">Analyzed Resume</div>
              <h1>{candidateName}</h1>
              <p>{jobRole || "Resume-based interview"} · {resumeExperience}</p>
            </div>
          </div>

          <div className="analyzed-pro-actions">
            <button type="button" className="analyzed-pro-icon-btn" onClick={() => navigate("/")}>
              <Home size={18} />
              Home
            </button>
            <button type="button" className="analyzed-pro-icon-btn" onClick={() => navigate(-1)}>
              <ArrowLeft size={18} />
              Back
            </button>
            <button type="button" className="analyzed-pro-primary-btn" onClick={startInterview}>
              <Mic size={18} />
              Start Interview
            </button>
          </div>
        </section>

        <section className="analyzed-pro-summary">
          <article className={`analyzed-pro-readiness ${reviewData.interview_ready ? "is-ready" : "is-pending"}`}>
            <CheckCircle2 size={22} />
            <div>
              <span>{reviewData.interview_ready ? "Interview Ready" : "Review Recommended"}</span>
              <p>{reviewData.ready_reason || "Resume signals were extracted and prepared for interview setup."}</p>
            </div>
          </article>

          <div className="analyzed-pro-stat-grid">
            {summaryStats.map((stat) => (
              <article key={stat.label} className="analyzed-pro-stat">
                <strong>{stat.value}</strong>
                <span>{stat.label}</span>
              </article>
            ))}
          </div>
        </section>

        <section className="analyzed-pro-layout">
          <aside className="analyzed-pro-preview-panel">
            <div className="analyzed-pro-panel-head">
              <div>
                <span>Resume Preview</span>
                <h2>{resumeName || "Uploaded resume"}</h2>
              </div>
              <FileText size={22} />
            </div>
            <div className="analyzed-pro-pdf-frame">
              {resumeDataUrl ? (
                <iframe title="Resume preview" src={resumeDataUrl} className="analyzed-pro-pdf" />
              ) : (
                <div className="analyzed-pro-empty-preview">No resume preview available.</div>
              )}
            </div>
          </aside>

          <div className="analyzed-pro-details">
            {extractedSections.career_objective ? (
              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>Summary</span>
                    <h2>Career Objective</h2>
                  </div>
                </div>
                <p className="analyzed-pro-copy">{extractedSections.career_objective}</p>
              </article>
            ) : null}

            <div className="analyzed-pro-detail-grid">
              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>{skillCount} found</span>
                    <h2>Technical Skills</h2>
                  </div>
                </div>
                {renderChips(extractedSections.technical_skills, "No technical skills found.", 12)}
              </article>

              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>{educationCount} found</span>
                    <h2>Education</h2>
                  </div>
                </div>
                {renderList(extractedSections.educational_qualifications, "No education details found.", 4)}
              </article>
            </div>

            <article className="analyzed-pro-card">
              <div className="analyzed-pro-card-head">
                <div>
                  <span>{projectCount} found</span>
                  <h2>Projects & Internships</h2>
                </div>
              </div>
              {renderList(combinedProjectInternshipItems, "No project or internship details found.", 6)}
            </article>

            <div className="analyzed-pro-detail-grid">
              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>{experienceCount} found</span>
                    <h2>Experience</h2>
                  </div>
                </div>
                {renderList(extractedSections.experience, "No experience entries found.", 4)}
              </article>

              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>{languageCount} found</span>
                    <h2>Languages</h2>
                  </div>
                </div>
                {renderChips(languagesParsed, "No languages found.", 10)}
              </article>

              <article className="analyzed-pro-card">
                <div className="analyzed-pro-card-head">
                  <div>
                    <span>{hobbyCount} found</span>
                    <h2>Interests & Hobbies</h2>
                  </div>
                </div>
                {renderChips(hobbiesParsed, "No hobbies found.", 10)}
              </article>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default AnalyzedResume;
