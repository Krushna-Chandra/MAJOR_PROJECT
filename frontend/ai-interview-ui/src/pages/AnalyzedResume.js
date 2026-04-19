import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import { normalizeRoleText } from "../utils/roleSearch";

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

function AnalyzedResume() {
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedSection, setExpandedSection] = useState(null);

  const state = location.state || {};
  const reviewData = state.reviewData || EMPTY_REVIEW;
  const resumeDataUrl = state.resumeDataUrl || "";
  const resumeName = state.resumeName || "";
  const jobRole = state.jobRole || "";
  const currentFocusAreas = state.currentFocusAreas || [];
  const selectedQuestionCount = state.selectedQuestionCount || 10;

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

  const skillCount = (extractedSections.technical_skills || []).length;
  const projectCount = combinedProjectInternshipItems.length;
  const experienceCount = (extractedSections.experience || []).length;
  const educationCount = (extractedSections.educational_qualifications || []).length;

  return (
    <div className="analyzed-unique-page">
      <MiniNavbar />

      {/* Animated Background */}
      <div className="analyzed-bg-animation">
        <div className="analyzed-blob blob-1"></div>
        <div className="analyzed-blob blob-2"></div>
        <div className="analyzed-blob blob-3"></div>
      </div>

      {/* Main Content */}
      <div className="analyzed-main-wrapper">
        {/* Profile Card */}
        <div className="analyzed-profile-hero">
          <div className="analyzed-profile-left">
            <div className="analyzed-avatar-large">
              {reviewData.candidate_name
                ?.split(/\s+/)
                .slice(0, 2)
                .map((p) => p[0]?.toUpperCase())
                .join("") || "CV"}
            </div>
            <div className="analyzed-profile-info">
              <h1>{reviewData.candidate_name || resumeName.replace(/\.pdf$/i, "")}</h1>
              <p className="analyzed-target-role">{jobRole}</p>
              <div className="analyzed-readiness-badge">
                <span className={reviewData.interview_ready ? "ready" : "pending"}>
                  {reviewData.interview_ready ? "✓ Interview Ready" : "⚡ Review Recommended"}
                </span>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="analyzed-stats-grid">
            <div className="analyzed-stat-card">
              <div className="analyzed-stat-number">{skillCount}</div>
              <div className="analyzed-stat-label">Skills</div>
            </div>
            <div className="analyzed-stat-card">
              <div className="analyzed-stat-number">{projectCount}</div>
              <div className="analyzed-stat-label">Projects</div>
            </div>
            <div className="analyzed-stat-card">
              <div className="analyzed-stat-number">{experienceCount}</div>
              <div className="analyzed-stat-label">Experience</div>
            </div>
            <div className="analyzed-stat-card">
              <div className="analyzed-stat-number">{educationCount}</div>
              <div className="analyzed-stat-label">Education</div>
            </div>
          </div>
        </div>

        {/* Signals Grid - Fields Present/Missing */}
        <div className="analyzed-signals-grid">
          <div className="analyzed-signal-card">
            <div className="analyzed-signal-header">
              <strong>Skills</strong>
              <span className="analyzed-signal-badge present">Present</span>
            </div>
            {skillCount > 0 ? (
              <div className="analyzed-signal-items">
                {(extractedSections.technical_skills || []).slice(0, 3).map((skill, idx) => (
                  <span key={idx} className="analyzed-signal-item">{skill}</span>
                ))}
              </div>
            ) : (
              <p className="analyzed-signal-empty">No skills found</p>
            )}
          </div>

          <div className="analyzed-signal-card">
            <div className="analyzed-signal-header">
              <strong>Experience</strong>
              <span className={`analyzed-signal-badge ${experienceCount > 0 ? "present" : "missing"}`}>
                {experienceCount > 0 ? "Present" : "Missing"}
              </span>
            </div>
            {experienceCount > 0 ? (
              <div className="analyzed-signal-items">
                {(extractedSections.experience || []).slice(0, 2).map((exp, idx) => (
                  <span key={idx} className="analyzed-signal-item">{exp.substring(0, 30)}</span>
                ))}
              </div>
            ) : (
              <p className="analyzed-signal-empty">No experience found</p>
            )}
          </div>

          <div className="analyzed-signal-card">
            <div className="analyzed-signal-header">
              <strong>Education</strong>
              <span className={`analyzed-signal-badge ${educationCount > 0 ? "present" : "missing"}`}>
                {educationCount > 0 ? "Present" : "Missing"}
              </span>
            </div>
            {educationCount > 0 ? (
              <div className="analyzed-signal-items">
                {(extractedSections.educational_qualifications || []).slice(0, 2).map((edu, idx) => (
                  <span key={idx} className="analyzed-signal-item">{edu.substring(0, 30)}</span>
                ))}
              </div>
            ) : (
              <p className="analyzed-signal-empty">No education found</p>
            )}
          </div>

          <div className="analyzed-signal-card">
            <div className="analyzed-signal-header">
              <strong>Projects</strong>
              <span className={`analyzed-signal-badge ${projectCount > 0 ? "present" : "missing"}`}>
                {projectCount > 0 ? "Present" : "Missing"}
              </span>
            </div>
            {projectCount > 0 ? (
              <div className="analyzed-signal-items">
                {combinedProjectInternshipItems.slice(0, 2).map((proj, idx) => (
                  <span key={idx} className="analyzed-signal-item">{proj.substring(0, 30)}</span>
                ))}
              </div>
            ) : (
              <p className="analyzed-signal-empty">No projects found</p>
            )}
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="analyzed-content-grid">
          {/* Left Side - PDF */}
          <div className="analyzed-pdf-container">
            <div className="analyzed-pdf-box">
              {resumeDataUrl && (
                <iframe
                  title="Resume preview"
                  src={resumeDataUrl}
                  className="analyzed-pdf-embed"
                />
              )}
            </div>
          </div>

          {/* Right Side - Analysis Cards */}
          <div className="analyzed-cards-stack">
            {/* Career Objective */}
            {extractedSections.career_objective && (
              <div className="analyzed-modern-card objective-card">
                <div className="analyzed-card-icon">🎯</div>
                <div className="analyzed-card-content">
                  <h3>Career Objective</h3>
                  <p>{extractedSections.career_objective}</p>
                </div>
              </div>
            )}

            {/* Skills Section */}
            {skillCount > 0 && (
              <div className="analyzed-modern-card skills-card">
                <div className="analyzed-card-header">
                  <div className="analyzed-card-icon">💻</div>
                  <div>
                    <h3>Technical Skills</h3>
                    <span className="analyzed-card-count">{skillCount} skills</span>
                  </div>
                </div>
                <div className="analyzed-skills-display">
                  {extractedSections.technical_skills.slice(0, 8).map((skill) => (
                    <div key={skill} className="analyzed-skill-badge">
                      {skill}
                    </div>
                  ))}
                  {skillCount > 8 && (
                    <div className="analyzed-skill-badge more">+{skillCount - 8} more</div>
                  )}
                </div>
              </div>
            )}

            {/* Projects/Internships */}
            {projectCount > 0 && (
              <div className="analyzed-modern-card projects-card">
                <div className="analyzed-card-header">
                  <div className="analyzed-card-icon">🚀</div>
                  <div>
                    <h3>Projects & Internships</h3>
                    <span className="analyzed-card-count">{projectCount} items</span>
                  </div>
                </div>
                <div className="analyzed-items-list">
                  {combinedProjectInternshipItems.slice(0, 5).map((item) => (
                    <div key={item} className="analyzed-list-item">
                      <span className="analyzed-item-dot"></span>
                      {item}
                    </div>
                  ))}
                  {projectCount > 5 && (
                    <div className="analyzed-list-item more">
                      <span className="analyzed-item-dot"></span>
                      +{projectCount - 5} more
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Experience */}
            {experienceCount > 0 && (
              <div className="analyzed-modern-card experience-card">
                <div className="analyzed-card-header">
                  <div className="analyzed-card-icon">💼</div>
                  <div>
                    <h3>Experience</h3>
                    <span className="analyzed-card-count">{experienceCount} entries</span>
                  </div>
                </div>
                <div className="analyzed-items-list">
                  {(extractedSections.experience || []).slice(0, 4).map((exp) => (
                    <div key={exp} className="analyzed-list-item">
                      <span className="analyzed-item-dot"></span>
                      {exp}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Interview Focus */}
            {currentFocusAreas.length > 0 && (
              <div className="analyzed-modern-card focus-card">
                <div className="analyzed-card-header">
                  <div className="analyzed-card-icon">🎤</div>
                  <div>
                    <h3>Interview Focus</h3>
                    <span className="analyzed-card-count">Key Areas</span>
                  </div>
                </div>
                <div className="analyzed-focus-tags">
                  {currentFocusAreas.map((area) => (
                    <span key={area} className="analyzed-focus-tag">
                      {area}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Hobbies */}
            {(extractedSections.hobbies || []).length > 0 && (
              <div className="analyzed-modern-card hobbies-card">
                <div className="analyzed-card-header">
                  <div className="analyzed-card-icon">🎨</div>
                  <div>
                    <h3>Hobbies & Interests</h3>
                    <span className="analyzed-card-count">{extractedSections.hobbies.length} interests</span>
                  </div>
                </div>
                <div className="analyzed-hobbies-chips">
                  {extractedSections.hobbies.map((hobby) => (
                    <span key={hobby} className="analyzed-hobby-chip">
                      {hobby}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* CTA Buttons */}
            <div className="analyzed-cta-buttons">
              <button
                className="analyzed-btn-secondary"
                onClick={() => navigate("/")}
              >
                🏠 Home
              </button>
              <button
                className="analyzed-btn-secondary"
                onClick={() => navigate(-1)}
              >
                ← Back
              </button>
              <button
                className="analyzed-btn-primary"
                onClick={() =>
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
                      experience: "Resume-based",
                      questionCount: selectedQuestionCount,
                      practiceType: "voice interview",
                      resumeInsights: reviewData,
                    },
                  })
                }
              >
                Start Interview →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AnalyzedResume;
