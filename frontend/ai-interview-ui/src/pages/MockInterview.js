import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import MiniNavbar from "../components/MiniNavbar";
import mockHero from "../assets/mock.png";
import mistakeImg from "../assets/mistake.png";
import {
  MOCK_JOB_ROLES,
  getResolvedJobRole,
  getRoleSuggestions,
} from "../utils/roleSearch";

function MockInterview() {
  useScrollToTop();
  const navigate = useNavigate();
  const rolesList = MOCK_JOB_ROLES;

  // warn before leaving page when user tries to navigate away
  React.useEffect(() => {
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = "All submissions and saved data will be lost";
      return "All submissions and saved data will be lost";
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  const [showSetup, setShowSetup] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedOptions, setSelectedOptions] = useState([]);
  const [experience, setExperience] = useState("");
  const [configMode, setConfigMode] = useState(null);
  const [questionCount, setQuestionCount] = useState(10);
  const [customQuestionCount, setCustomQuestionCount] = useState("");
  const [practiceType, setPracticeType] = useState("practice");
  const [interviewTime, setInterviewTime] = useState(5);
  const [timeModeValue, setTimeModeValue] = useState("");
  const [confirmedSelection, setConfirmedSelection] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const setupRef = useRef(null);

  useEffect(() => {
    if (showSetup && setupRef.current) {
      setupRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [showSetup]);

  const suggestedRoles = searchTerm.trim()
    ? getRoleSuggestions(searchTerm, rolesList)
    : [];

  const resolveSearchSelection = () => {
    if (!searchTerm.trim()) return;
    const resolvedRole = getResolvedJobRole(searchTerm, rolesList);
    if (!resolvedRole) return;
    setSelectedOptions([resolvedRole]);
    setSearchTerm("");
  };

  const clearSelection = () => {
    setSelectedOptions([]);
    setSearchTerm("");
    setExperience("");
    setConfigMode(null);
    setQuestionCount(10);
    setCustomQuestionCount("");
    setPracticeType("practice");
    setInterviewTime(5);
    setTimeModeValue("");
    setConfirmedSelection(null);
    setIsLocked(false);
  };

  const questionModeValid =
    configMode !== "question" ||
    (questionCount === "custom"
      ? Number(customQuestionCount) >= 10 && Number(customQuestionCount) <= 30
      : Number(questionCount) >= 10 && Number(questionCount) <= 30);

  const timeModeValid = configMode !== "time" || Number(timeModeValue) > 0;
  const interviewTimerValid = practiceType !== "interview" || Number(interviewTime) > 0;
  const isSetupReady =
    selectedOptions.length > 0 &&
    Boolean(experience) &&
    Boolean(configMode) &&
    questionModeValid &&
    timeModeValid &&
    interviewTimerValid;

  const handleConfirm = () => {
    if (!isSetupReady) return;
    const resolvedQuestionCount = questionCount === 'custom' ? Number(customQuestionCount || 0) : Number(questionCount);
    setConfirmedSelection({
      role: selectedOptions[0],
      experience,
      configMode,
      questionCount: configMode === 'question' ? (resolvedQuestionCount || 10) : null,
      customQuestionCount: configMode === 'question' && questionCount === 'custom' ? customQuestionCount : null,
      practiceType,
      interviewModeTime: practiceType === 'interview' ? interviewTime : null,
      timeModeInterval: configMode === 'time' ? timeModeValue : null
    });
    setIsLocked(true);
  };

  return (
    <div className="mock-page reveal">
      <MiniNavbar />

      {/* HERO */}
      <div className="mock-hero" style={{ background: 'linear-gradient(90deg, #FF9800 0%, #FFB74D 100%)' }}>
        <div>
          <h1>Mock Interview</h1>
          <p>
            Practice real interview questions and get instant feedback. Simulate HR, technical, and behavioral rounds.
          </p>
          <button className="mock-btn" onClick={() => setShowSetup(true)}>Start Mock Interview</button>
        </div>
        <img src={mockHero} alt="Mock Interview" className="mock-hero-img" />
      </div>

      {/* PRACTICE MODES HEADER ROW */}
      <div className="mock-section">
        <div className="section-header-row" style={{ justifyContent: "flex-end", display: "none" }}>
          <button className="small-start-btn" onClick={() => setShowSetup(true)}>Start Mock</button>
        </div>
        {/* ✅ CONSOLIDATED CONTENT SECTIONS */}
        <div style={{ marginTop: '30px' }}>
          <div className="aptitude-info-grid">
            <div className="aptitude-info-card aptitude-info-card-learn">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-warm">What you'll learn</div>
              <ul>
                <li>Basic interview communication and response structure</li>
                <li>Industry-specific knowledge and role expectations</li>
                <li>Complete interview flow and performance evaluation</li>
              </ul>
            </div>

            <div className="aptitude-info-card aptitude-info-card-types">
              <div className="aptitude-info-card-tag aptitude-info-card-tag-strong">Question types</div>
              <ul>
                <li>Tell me about yourself, Strengths/weaknesses, Why this company, Career goals</li>
                <li>Technical skills assessment, Project experience, Role-specific scenarios, Industry trends</li>
                <li>Multi-round simulation covering HR, technical, and behavioral questions with comprehensive feedback</li>
              </ul>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center', marginTop: '22px' }}>
            <button className="small-start-btn" onClick={() => setShowSetup(true)}>Start Mock</button>
          </div>
        </div>
      </div>

      {showSetup && (
        <div className="mock-section selection-layout-section" ref={setupRef}>
          <div className="section-title">Mock Interview Setup</div>
          <div className="selection-window">
            <div className="selection-window-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <button
                className="selection-window-back"
                onClick={() => setShowSetup(false)}
              >
                ← Back
              </button>
              <h3 style={{ margin: 0 }}>Choose Job Roles</h3>
              <button
                className="selection-window-refresh"
                onClick={clearSelection}
                title="Reset selections"
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#0f172a',
                  fontSize: '1.3rem',
                  padding: 0
                }}
              >
                ⟳
              </button>
            </div>

            <div style={{ marginBottom: 12, position: 'relative' }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search job roles..."
                  onBlur={() => window.setTimeout(resolveSearchSelection, 100)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      resolveSearchSelection();
                    }
                  }}
                  disabled={isLocked}
                  style={{
                    flex: 1,
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #cbd5e1',
                    background: isLocked ? '#f1f5f9' : '#fff'
                  }}
                />
                {searchTerm && (
                  <button
                    onClick={() => setSearchTerm("")}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 28,
                      height: 28,
                      borderRadius: '50%',
                      border: '1px solid #cbd5e1',
                      background: '#fff',
                      cursor: 'pointer'
                    }}
                    title="Clear"
                  >
                    ×
                  </button>
                )}
              </div>

              {searchTerm.trim() && (
                <div style={{
                  position: 'absolute',
                  top: '46px',
                  left: 0,
                  right: 0,
                  background: '#fff',
                  border: '1px solid #cbd5e1',
                  borderRadius: 8,
                  zIndex: 10,
                  maxHeight: 200,
                  overflowY: 'auto',
                  boxShadow: '0 10px 30px rgba(0,0,0,0.12)'
                }}>
                  {suggestedRoles.length > 0 ? (
                    suggestedRoles.map((opt) => (
                        <div
                          key={opt}
                          onClick={() => {
                            setSelectedOptions([opt]);
                            setSearchTerm("");
                          }}
                          style={{
                            padding: '8px 10px',
                            borderBottom: '1px solid #e2e8f0',
                            cursor: 'pointer'
                          }}
                        >
                          {opt}
                        </div>
                      ))
                  ) : (
                    <div style={{ padding: '8px 10px', color: '#718096' }}>
                      No matching technical roles for "{searchTerm}"
                    </div>
                  )}
                </div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
              {rolesList.map((role) => (
                <label
                  key={role}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '12px',
                    borderRadius: '10px',
                    border: selectedOptions.includes(role) ? '2px solid #2563eb' : '1px solid #d1d5db',
                    background: selectedOptions.includes(role) ? 'rgba(37,99,235,0.08)' : '#fff',
                    cursor: 'pointer'
                  }}
                >
                  <input
                    type="radio"
                    name="select-role"
                    checked={selectedOptions.includes(role)}
                    onChange={() => !isLocked && setSelectedOptions([role])}
                    disabled={isLocked}
                  />
                  <span>{role}</span>
                </label>
              ))}
            </div>

            <div style={{ marginTop: 14, fontSize: 14, color: '#334155' }}>
              Selected role: {selectedOptions[0] || 'None'}
            </div>

            <div style={{ marginTop: 12, marginBottom: 14, border: '1px solid #e2e8f0', borderRadius: 10, padding: 12, background: '#fafbff' }}>
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: 14, color: '#334155', marginBottom: 6, display: 'block' }}>
                  Select experience:
                </label>
                <select
                  value={experience}
                  onChange={(e) => !isLocked && setExperience(e.target.value)}
                  disabled={isLocked}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #cbd5e1',
                    width: '100%',
                    maxWidth: 420,
                    background: isLocked ? '#f1f5f9' : '#fff'
                  }}
                >
                  <option value="" disabled>
                    Select Experience Level
                  </option>
                  <option value="Fresher">Fresher</option>
                  <option value="Mid-level">Mid-level</option>
                  <option value="Experienced">Experienced</option>
                </select>
              </div>

              {experience && (
                <>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#334155', marginBottom: 8 }}>Select Mode</div>
                  <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                    <button
                      onClick={() => setConfigMode('question')}
                      style={{
                        padding: '8px 14px',
                        borderRadius: 6,
                        border: configMode === 'question' ? '2px solid #2563eb' : '1px solid #cbd5e1',
                        background: configMode === 'question' ? '#e0e7ff' : '#fff',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                      disabled={isLocked}
                    >
                      Question Mode
                    </button>
                    <button
                      onClick={() => setConfigMode('time')}
                      style={{
                        padding: '8px 14px',
                        borderRadius: 6,
                        border: configMode === 'time' ? '2px solid #2563eb' : '1px solid #cbd5e1',
                        background: configMode === 'time' ? '#e0e7ff' : '#fff',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                      disabled={isLocked}
                    >
                      Time Mode
                    </button>
                  </div>
                </>
              )}
            </div>

            {configMode === 'question' && (
              <div>
                <label style={{ fontSize: 14, color: '#334155', marginBottom: 6, display: 'block' }}>
                  Number of questions:
                </label>
                <select
                  value={questionCount || 'custom'}
                  onChange={(e) => {
                    if (e.target.value === 'custom') {
                      setQuestionCount('custom');
                      setCustomQuestionCount('');
                    } else {
                      setQuestionCount(Number(e.target.value));
                      setCustomQuestionCount('');
                    }
                  }}
                  disabled={isLocked}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #cbd5e1',
                    width: '100%',
                    maxWidth: 320,
                    background: isLocked ? '#f1f5f9' : '#fff'
                  }}
                >
                  <option value={10}>10</option>
                  <option value={15}>15</option>
                  <option value={20}>20</option>
                  <option value={25}>25</option>
                  <option value={30}>30</option>
                  <option value="custom">Custom</option>
                </select>

                {questionCount === 'custom' && (
                  <input
                    type="number"
                    min={10}
                    max={30}
                    value={customQuestionCount}
                    onChange={(e) => setCustomQuestionCount(e.target.value)}
                    disabled={isLocked}
                    placeholder="Enter 10 to 30 questions"
                    style={{
                      marginTop: 8,
                      width: '100%',
                      maxWidth: 320,
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: '1px solid #cbd5e1'
                    }}
                  />
                )}

                {questionCount === 'custom' && customQuestionCount && !questionModeValid && (
                  <div style={{ marginTop: 8, color: '#b91c1c', fontSize: 13 }}>
                    Enter a custom question count between 10 and 30.
                  </div>
                )}
              </div>
            )}

            {configMode === 'time' && (
              <div style={{ marginBottom: 8 }}>
                <label style={{ fontSize: 14, color: '#334155', marginBottom: 6, display: 'block' }}>
                  Choose sample time (minutes):
                </label>
                <select
                  value={timeModeValue || interviewTime}
                  onChange={(e) => setTimeModeValue(Number(e.target.value))}
                  disabled={isLocked}
                  style={{
                    width: '100%',
                    maxWidth: 320,
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: '1px solid #cbd5e1',
                    background: isLocked ? '#f1f5f9' : '#fff'
                  }}
                >
                  <option value="">Select interval</option>
                  {[5, 10, 15, 20, 30].map((t) => (
                    <option key={t} value={t}>
                      {t} minutes
                    </option>
                  ))}
                </select>
                <small style={{ color: '#475569' }}>
                  AI will ask as many questions as possible within this selected time limit.
                </small>
              </div>
            )}

            {configMode === 'question' && (
              <>
                <div style={{ marginTop: 12, marginBottom: 12 }}>
                  <div style={{ fontSize: 14, color: '#334155', marginBottom: 6 }}>Mode Type</div>
                  <button
                    onClick={() => setPracticeType('practice')}
                    style={{
                      marginRight: 8,
                      padding: '8px 14px',
                      borderRadius: 6,
                      border: practiceType === 'practice' ? '2px solid #2563eb' : '1px solid #cbd5e1',
                      background: practiceType === 'practice' ? '#e0e7ff' : '#fff',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                    disabled={isLocked}
                  >
                    🔘 Practice Mode (no timer)
                  </button>
                  <button
                    onClick={() => setPracticeType('interview')}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 6,
                      border: practiceType === 'interview' ? '2px solid #2563eb' : '1px solid #cbd5e1',
                      background: practiceType === 'interview' ? '#e0e7ff' : '#fff',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                    disabled={isLocked}
                  >
                    🔘 Interview Mode (timer ON)
                  </button>
                </div>

                {practiceType === 'interview' && (
                  <div>
                    <label style={{ fontSize: 14, color: '#334155', marginBottom: 6, display: 'block' }}>
                      Interview duration (minutes):
                    </label>
                    <select
                      value={interviewTime}
                      onChange={(e) => setInterviewTime(Number(e.target.value))}
                      disabled={isLocked}
                      style={{
                        width: '100%',
                        maxWidth: 320,
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: '1px solid #cbd5e1',
                        background: isLocked ? '#f1f5f9' : '#fff'
                      }}
                    >
                      <option value="">Select interview duration</option>
                      {[5, 10, 15, 20, 30].map((t) => (
                        <option key={t} value={t}>
                          {t} minutes
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </>
            )}

            <button
              className="topic-action-btn"
              style={{
                marginTop: 14,
                opacity: isSetupReady ? 1 : 0.5,
                cursor: isSetupReady ? 'pointer' : 'not-allowed'
              }}
              disabled={!isSetupReady}
              onClick={handleConfirm}
            >
              Confirm Setup
            </button>

            {confirmedSelection && (
              <div style={{ marginTop: 14, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <div style={{ width: "100%", maxWidth: 600, background: "#eff6ff", borderRadius: 10, padding: "20px", border: "1px solid #bfdbfe", color: "#1e3a8a" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    {/* Selected Role */}
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Selected role:</div>
                      <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                        {confirmedSelection.role}
                      </div>
                    </div>

                    {/* Experience */}
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Experience</div>
                      <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                        {confirmedSelection.experience}
                      </div>
                    </div>

                    {/* Config Mode */}
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Config Mode</div>
                      <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                        {confirmedSelection.configMode === "question" ? "Question Mode" : "Time Mode"}
                      </div>
                    </div>

                    {/* Practice Type */}
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Practice Type</div>
                      <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                        {confirmedSelection.practiceType === "practice" ? "Practice Mode" : "Interview Mode"}
                      </div>
                    </div>

                    {/* Questions or Time Interval */}
                    {confirmedSelection.configMode === "question" ? (
                      <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Questions</div>
                        <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                          {confirmedSelection.questionCount}
                          {confirmedSelection.customQuestionCount
                            ? ` (custom: ${confirmedSelection.customQuestionCount})`
                            : ""}
                        </div>
                      </div>
                    ) : (
                      <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Time Mode Interval</div>
                        <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                          {confirmedSelection.timeModeInterval || "n/a"} minutes
                        </div>
                      </div>
                    )}

                    {/* Interview Timer */}
                    {confirmedSelection.practiceType === "interview" && (
                      <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Interview Timer</div>
                        <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                          {confirmedSelection.interviewModeTime || "n/a"} minutes
                        </div>
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", justifyContent: "center", marginTop: 18 }}>
                    <button
                      className="topic-action-btn secondary"
                      onClick={clearSelection}
                      style={{
                        borderRadius: 999,
                        padding: "8px 14px",
                        fontWeight: 700,
                        background: "#ec4899",
                        color: "#fff",
                        boxShadow: "0 8px 15px rgba(236,72,153,0.25)",
                      }}
                    >
                      Reset Selections
                    </button>
                  </div>
                </div>

                <button className="start-interview-confirm" onClick={() =>
                    navigate("/instructions", {
                      state: {
                        category: "mock",
                        selectedMode: "role",
                        selectedOptions: [confirmedSelection.role],
                        experience: confirmedSelection.experience,
                        configMode: confirmedSelection.configMode,
                        questionCount: confirmedSelection.questionCount,
                        customQuestionCount: confirmedSelection.customQuestionCount,
                        practiceType: confirmedSelection.practiceType,
                        interviewModeTime: confirmedSelection.interviewModeTime,
                        timeModeInterval: confirmedSelection.timeModeInterval,
                      }
                    })
                  }>
                  Proceed to Instructions
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* COMMON MISTAKES BOX */}
      <div className="mistake-box">
        <div>
          <h2>⚠ Common Mistakes</h2>
          <ul>
            <li>Giving generic answers without examples</li>
            <li>Not structuring responses clearly</li>
            <li>Missing key skills or achievements</li>
          </ul>
        </div>
        <img
          src={mistakeImg}
          alt="Common Mistakes Illustration"
          className="mistake-img"
        />
      </div>

      {/* FOOTER */}
      <div className="bottom-footer">
        Prepared by AI Powered Interview System
      </div>
    </div>
  );
}

export default MockInterview;
