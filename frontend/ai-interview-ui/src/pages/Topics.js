import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import "../App.css";
import MiniNavbar from "../components/MiniNavbar";
import {
  TECHNICAL_JOB_ROLES,
  NON_TECHNICAL_JOB_ROLES,
  getResolvedJobRole,
  getRoleSuggestions,
} from "../utils/roleSearch";

const LANGUAGE_OPTIONS = [
  "JavaScript",
  "Python",
  "Java",
  "C#",
  "C++",
  "TypeScript",
  "Go",
  "Ruby",
  "PHP",
  "Swift",
  "Kotlin",
  "Rust",
  "Scala",
  "Perl",
  "R",
  "Dart",
  "Haskell",
  "Elixir",
  "C",
  "MATLAB",
  "SQL",
  "HTML",
  "CSS",
  "Shell",
];

const HR_FOCUS_AREAS = [
  "Communication",
  "Leadership",
  "Problem-solving",
  "Teamwork",
  "Confidence",
];

const HR_ROUND_OPTIONS = [
  {
    id: "hr",
    label: "HR Interview",
    description: "Classic HR questions around motivation, role fit, strengths, and workplace approach.",
  },
  {
    id: "behavioral",
    label: "Behavioral Interview",
    description: "STAR-based teamwork, leadership, conflict, and situational experience questions.",
  },
  {
    id: "hr_behavioral",
    label: "HR + Behavioral Interview",
    description: "Classic HR, STAR-based behavioral, communication, and personality questions.",
  },
];

const INTERVIEW_TIME_OPTIONS = [5, 10, 15, 20, 30];

const PAGE_CONTENT = {
  hr: {
    title: "HR Interview Topics",
    description: "Configure a personalized HR round with role, experience, focus areas, and adaptive follow-up logic.",
    heroClass: "beh-hero",
    startButtonLabel: "Start Your HR Interview ->",
    cards: [
      {
        key: "hr",
        title: "HR Interview",
        description: "Warm-up, motivation, role-fit, strengths, and workplace communication questions.",
        actionLabel: "Build HR Round ->",
        selectionMode: "hr",
        defaultRound: "hr",
      },
      {
        key: "behavioral",
        title: "Behavioral Interview",
        description: "STAR-based leadership, teamwork, conflict handling, ownership, and situational prompts.",
        actionLabel: "Build Behavioral Round ->",
        selectionMode: "hr",
        defaultRound: "behavioral",
      },
      {
        key: "hr_behavioral",
        title: "HR + Behavioral Interview",
        description: "Blend HR and behavioral prompts in one adaptive interview flow.",
        actionLabel: "Build Combined Round ->",
        selectionMode: "hr",
        defaultRound: "hr_behavioral",
      },
    ],
  },
  technical: {
    title: "Technical Interview Topics",
    description: "Choose a role or language path, then configure the interview length, mode, and difficulty style.",
    heroClass: "tech-hero",
    startButtonLabel: "Start Your Technical Interview ->",
    cards: [
      {
        key: "role",
        title: "Role-based Interview",
        description: "Practice role-aware questions tailored to the job title and your experience level.",
        actionLabel: "Select Roles ->",
        selectionMode: "role",
      },
      {
        key: "language",
        title: "Language-based Interview",
        description: "Focus on language fundamentals, concepts, debugging, and practical problem solving.",
        actionLabel: "Select Languages ->",
        selectionMode: "language",
      },
    ],
  },
};

function Topics() {
  const { category } = useParams();
  const navigate = useNavigate();
  const pageConfig = PAGE_CONTENT[category] || PAGE_CONTENT.hr;
  const isHrCategory = category === "hr";

  const [selectedMode, setSelectedMode] = React.useState(() => (isHrCategory ? "hr" : null));
  const [searchTerm, setSearchTerm] = React.useState("");
  const [selectedOptions, setSelectedOptions] = React.useState([]);
  const [jobRole, setJobRole] = React.useState("");
  const [selectedRound, setSelectedRound] = React.useState("hr_behavioral");
  const [selectedFocusAreas, setSelectedFocusAreas] = React.useState([]);
  const [experience, setExperience] = React.useState("");
  const [confirmedSelection, setConfirmedSelection] = React.useState(null);
  const [isLocked, setIsLocked] = React.useState(false);
  const [configMode, setConfigMode] = React.useState(null);
  const [questionCount, setQuestionCount] = React.useState(10);
  const [customQuestionCount, setCustomQuestionCount] = React.useState("");
  const [practiceType, setPracticeType] = React.useState("practice");
  const [interviewTime, setInterviewTime] = React.useState(5);
  const [timeModeValue, setTimeModeValue] = React.useState("");
  const selectionRef = React.useRef(null);

  const modeOptions =
    selectedMode === "language"
      ? LANGUAGE_OPTIONS
      : selectedMode === "role"
        ? TECHNICAL_JOB_ROLES
        : selectedMode === "hr"
          ? NON_TECHNICAL_JOB_ROLES
        : [];

  const suggestedOptions = searchTerm.trim()
    ? getRoleSuggestions(searchTerm, modeOptions)
    : [];

  const resolveSearchSelection = React.useCallback(() => {
    if (!searchTerm.trim()) return;
    const resolvedOption = getResolvedJobRole(searchTerm, modeOptions);
    if (!resolvedOption) return;
    toggleSelectionOption(resolvedOption);
    setSearchTerm("");
  }, [modeOptions, searchTerm, selectedMode]);

  const resetConfiguration = React.useCallback((nextRound = "hr_behavioral") => {
    setSearchTerm("");
    setSelectedOptions([]);
    setJobRole("");
    setSelectedFocusAreas([]);
    setExperience("");
    setConfirmedSelection(null);
    setIsLocked(false);
    setConfigMode(null);
    setQuestionCount(10);
    setCustomQuestionCount("");
    setPracticeType("practice");
    setInterviewTime(5);
    setTimeModeValue("");
    setSelectedRound(nextRound);
  }, []);

  React.useEffect(() => {
    if (isHrCategory) {
      setSelectedMode("hr");
      resetConfiguration("hr_behavioral");
      return;
    }

    setSelectedMode(null);
    resetConfiguration();
  }, [isHrCategory, resetConfiguration]);

  const closeSelectionPanel = () => {
    if (isHrCategory) {
      resetConfiguration(selectedRound);
      return;
    }

    setSelectedMode(null);
    resetConfiguration();
  };

  const openSelectionPanel = (mode, round = "hr_behavioral") => {
    setSelectedMode(mode);
    resetConfiguration(round);
  };

  const toggleSelectionOption = (item) => {
    if (selectedMode === "role") {
      setSelectedOptions([item]);
      return;
    }
    if (selectedMode === "language") {
      setSelectedOptions((previous) => {
        // If item is already selected, remove it
        if (previous.includes(item)) {
          return previous.filter((value) => value !== item);
        }
        // If item is not selected and we haven't reached limit of 3, add it
        if (previous.length < 3) {
          return [...previous, item];
        }
        // If we've reached the limit, don't add
        return previous;
      });
      return;
    }
    if (selectedMode === "hr") {
      setJobRole(item);
    }
  };

  const toggleFocusArea = (area) => {
    setSelectedFocusAreas((previous) =>
      previous.includes(area)
        ? previous.filter((value) => value !== area)
        : [...previous, area]
    );
  };

  const questionModeValid =
    configMode !== "question" ||
    (questionCount === "custom"
      ? Number(customQuestionCount) >= 10 && Number(customQuestionCount) <= 30
      : Number(questionCount) >= 10 && Number(questionCount) <= 30);

  const timeModeValid = configMode !== "time" || Number(timeModeValue) > 0;
  const interviewTimerValid = practiceType !== "interview" || Number(interviewTime) > 0;

  const technicalSelectionReady =
    selectedOptions.length > 0 &&
    Boolean(experience) &&
    Boolean(configMode) &&
    questionModeValid &&
    timeModeValid &&
    interviewTimerValid;

  const hrSelectionReady =
    Boolean(jobRole) &&
    Boolean(selectedRound) &&
    selectedFocusAreas.length > 0 &&
    Boolean(experience) &&
    Boolean(configMode) &&
    questionModeValid &&
    timeModeValid &&
    interviewTimerValid;

  const isSelectionReady = isHrCategory ? hrSelectionReady : technicalSelectionReady;

  const resolvedQuestionCount =
    questionCount === "custom"
      ? Number(customQuestionCount || 0)
      : Number(questionCount || 0);

  const focusSummary =
    selectedFocusAreas.length === HR_FOCUS_AREAS.length
      ? "All focus areas selected"
      : selectedFocusAreas.join(", ") || "None";

  const roundLabel =
    HR_ROUND_OPTIONS.find((option) => option.id === selectedRound)?.label || "HR / Behavioral Interview";

  const handleConfirmSelection = () => {
    if (!isSelectionReady) return;

    const baseSelection = {
      experience,
      configMode,
      questionCount: configMode === "question" ? (resolvedQuestionCount || 10) : null,
      customQuestionCount:
        configMode === "question" && questionCount === "custom"
          ? customQuestionCount
          : null,
      practiceType,
      interviewModeTime: practiceType === "interview" ? interviewTime : null,
      timeModeInterval: configMode === "time" ? timeModeValue : null,
    };

    if (isHrCategory) {
      setConfirmedSelection({
        ...baseSelection,
        mode: "hr",
        jobRole,
        hrRound: selectedRound,
        hrRoundLabel: roundLabel,
        focusAreas: selectedFocusAreas,
        options: selectedFocusAreas,
      });
    } else {
      setConfirmedSelection({
        ...baseSelection,
        mode: selectedMode,
        jobRole: selectedMode === "role" ? selectedOptions[0] : "",
        options: selectedOptions,
      });
    }

    setIsLocked(true);
  };

  const proceedToInstructions = () => {
    if (!confirmedSelection) return;

    navigate("/instructions", {
      state: {
        category,
        selectedMode: confirmedSelection.mode,
        selectedOptions: confirmedSelection.options,
        focusAreas: confirmedSelection.focusAreas || confirmedSelection.options,
        hrRound: confirmedSelection.hrRound || "",
        jobRole: confirmedSelection.jobRole || "",
        experience: confirmedSelection.experience,
        configMode: confirmedSelection.configMode,
        questionCount: confirmedSelection.questionCount,
        customQuestionCount: confirmedSelection.customQuestionCount,
        practiceType: confirmedSelection.practiceType,
        interviewModeTime: confirmedSelection.interviewModeTime,
        timeModeInterval: confirmedSelection.timeModeInterval,
      },
    });
  };

  const currentSelectionLabel = isHrCategory
    ? jobRole || "None"
    : selectedOptions.join(", ") || "None";

  return (
    <div className="mock-page reveal">
      <MiniNavbar />

      <div className={`mock-hero ${pageConfig.heroClass}`}>
        <div>
          <h1>{pageConfig.title}</h1>
          <p>{pageConfig.description}</p>
          <button
            className="mock-btn"
            onClick={() => {
              selectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            }}
          >
            {pageConfig.startButtonLabel}
          </button>
        </div>
      </div>

      <div className="mock-section selection-layout-section" ref={selectionRef}>
        <div className="section-title">
          {isHrCategory
            ? "Build Your HR Interview"
            : !selectedMode
              ? "Available interviews"
              : selectedMode === "role"
                ? "Choose Job Roles"
                : "Choose Languages"}
        </div>

        {!selectedMode && !isHrCategory ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
            {pageConfig.cards.map((topic) => (
              <div key={topic.key} className="mock-card pro-card">
                <div className="card-top">
                  <div>
                    <h4>{topic.title}</h4>
                    <p style={{ marginTop: 6 }}>{topic.description}</p>
                  </div>
                  <div className="icon-circle">AI</div>
                </div>

                <button
                  className="topic-action-btn"
                  style={{ width: "100%", marginTop: 12 }}
                  onClick={() => openSelectionPanel(topic.selectionMode, topic.defaultRound || "hr_behavioral")}
                >
                  {topic.actionLabel}
                </button>

                <div className="card-footer">Adaptive AI interview planning enabled</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="selection-window">
            <div className="selection-window-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              {isHrCategory ? <div /> : (
                <button className="selection-window-back" onClick={closeSelectionPanel}>
                  &lt;- Back
                </button>
              )}
              <h3 style={{ margin: 0 }}>
                {isHrCategory
                  ? "HR Interview Builder"
                  : selectedMode === "role"
                    ? "Choose Job Roles"
                    : "Choose Languages"}
              </h3>
              <button
                className="selection-window-refresh"
                title="Reset selections"
                onClick={() => resetConfiguration(selectedRound)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  color: "#0f172a",
                  fontSize: "1rem",
                  padding: 0,
                }}
              >
                Reset
              </button>
            </div>

            <div style={{ marginBottom: 18, border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fafbff" }}>
              <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>
                {isHrCategory ? "Step 1: Role Selection" : selectedMode === "role" ? "Role Selection" : "Language Selection"}
              </div>
              <div style={{ marginBottom: 12, position: "relative" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder={selectedMode === "language" ? "Search languages..." : "Search job roles..."}
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
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #cbd5e1",
                      background: isLocked ? "#f1f5f9" : "#fff",
                    }}
                  />
                  {searchTerm ? (
                    <button
                      onClick={() => setSearchTerm("")}
                      title="Clear"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        border: "1px solid #cbd5e1",
                        background: "#fff",
                        cursor: "pointer",
                      }}
                    >
                      x
                    </button>
                  ) : null}
                </div>

                {searchTerm.trim() ? (
                  <div
                    style={{
                      position: "absolute",
                      top: 46,
                      left: 0,
                      right: 0,
                      background: "#fff",
                      border: "1px solid #cbd5e1",
                      borderRadius: 8,
                      zIndex: 10,
                      maxHeight: 200,
                      overflowY: "auto",
                      boxShadow: "0 10px 30px rgba(0,0,0,0.12)",
                    }}
                  >
                    {suggestedOptions.length > 0 ? (
                      suggestedOptions.map((option) => (
                        <div
                          key={option}
                          onClick={() => {
                            toggleSelectionOption(option);
                            setSearchTerm("");
                          }}
                          style={{
                            padding: "8px 10px",
                            borderBottom: "1px solid #e2e8f0",
                            cursor: "pointer",
                          }}
                        >
                          {option}
                        </div>
                      ))
                    ) : (
                      <div style={{ padding: "8px 10px", color: "#718096" }}>
                        No matching options for "{searchTerm}"
                      </div>
                    )}
                  </div>
                ) : null}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                {modeOptions.map((option) => {
                  const checked = isHrCategory ? jobRole === option : selectedOptions.includes(option);
                  const inputType = selectedMode === "language" ? "checkbox" : "radio";
                  const isLimitReached = selectedMode === "language" && selectedOptions.length >= 3 && !checked;
                  const canSelect = !isLimitReached && !isLocked;

                  return (
                    <label
                      key={option}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        padding: 12,
                        borderRadius: 10,
                        border: checked ? "2px solid #2563eb" : isLimitReached ? "1px solid #cbd5e1" : "1px solid #d1d5db",
                        background: checked ? "rgba(37,99,235,0.08)" : isLimitReached ? "rgba(0,0,0,0.03)" : "#fff",
                        cursor: canSelect ? "pointer" : "not-allowed",
                        opacity: isLimitReached ? 0.6 : 1,
                      }}
                    >
                      <input
                        type={inputType}
                        name={selectedMode === "language" ? `select-${option}` : "select-option"}
                        checked={checked}
                        onChange={() => !isLocked && !isLimitReached && toggleSelectionOption(option)}
                        disabled={isLocked || isLimitReached}
                      />
                      <span>{option}</span>
                    </label>
                  );
                })}
              </div>

              <div style={{ marginTop: 14, fontSize: 14, color: "#334155", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>Selected: {currentSelectionLabel}</div>
                {selectedMode === "language" && (
                  <div style={{ fontWeight: 600, color: selectedOptions.length >= 3 ? "#dc2626" : "#0f172a" }}>
                    {selectedOptions.length}/3 languages
                  </div>
                )}
              </div>
            </div>

            {isHrCategory ? (
              <>
                <div style={{ marginBottom: 18, border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fff" }}>
                  <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>
                    Step 2: HR Round Selection
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                    {HR_ROUND_OPTIONS.map((option) => (
                      <button
                        key={option.id}
                        onClick={() => !isLocked && setSelectedRound(option.id)}
                        disabled={isLocked}
                        style={{
                          textAlign: "left",
                          padding: 14,
                          borderRadius: 12,
                          border: selectedRound === option.id ? "2px solid #7c3aed" : "1px solid #d1d5db",
                          background: selectedRound === option.id ? "rgba(124,58,237,0.10)" : "#fff",
                          cursor: "pointer",
                        }}
                      >
                        <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: 6 }}>{option.label}</div>
                        <div style={{ color: "#475569", fontSize: 14 }}>{option.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ marginBottom: 18, border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fff" }}>
                  <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>
                    Step 3: Experience Level
                  </div>
                  <select
                    value={experience}
                    onChange={(event) => !isLocked && setExperience(event.target.value)}
                    disabled={isLocked}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #cbd5e1",
                      width: "100%",
                      maxWidth: 420,
                      background: isLocked ? "#f1f5f9" : "#fff",
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
                <div style={{ marginBottom: 18, border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", marginBottom: 10, flexWrap: "wrap" }}>
                    <div>
                      <div style={{ fontWeight: 700, color: "#0f172a" }}>Step 4: Focus Areas</div>
                      <div style={{ fontSize: 14, color: "#475569", marginTop: 4 }}>
                        Select one or more areas. Choosing all makes the HR round feel fully personalized.
                      </div>
                    </div>
                    <button
                      onClick={() => !isLocked && setSelectedFocusAreas(HR_FOCUS_AREAS)}
                      disabled={isLocked}
                      style={{
                        padding: "8px 12px",
                        borderRadius: 999,
                        border: "1px solid #cbd5e1",
                        background: "#fff",
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      Include all
                    </button>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
                    {HR_FOCUS_AREAS.map((area) => (
                      <label
                        key={area}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          padding: 12,
                          borderRadius: 10,
                          border: selectedFocusAreas.includes(area) ? "2px solid #0f766e" : "1px solid #d1d5db",
                          background: selectedFocusAreas.includes(area) ? "rgba(15,118,110,0.08)" : "#fff",
                          cursor: "pointer",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedFocusAreas.includes(area)}
                          onChange={() => !isLocked && toggleFocusArea(area)}
                          disabled={isLocked}
                        />
                        <span>{area}</span>
                      </label>
                    ))}
                  </div>

                  <div style={{ marginTop: 14, fontSize: 14, color: "#334155" }}>
                    Focus summary: {focusSummary}
                  </div>
                </div>
              </>
            ) : null}

            <div style={{ marginBottom: 18, border: "1px solid #e2e8f0", borderRadius: 12, padding: 16, background: "#fafbff" }}>
              <div style={{ fontWeight: 700, color: "#0f172a", marginBottom: 10 }}>
                {isHrCategory ? "Step 5: Interview Setup" : "Interview Setup"}
              </div>

              {!isHrCategory ? (
                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 14, color: "#334155", marginBottom: 6, display: "block" }}>
                    Select experience:
                  </label>
                  <select
                    value={experience}
                    onChange={(event) => !isLocked && setExperience(event.target.value)}
                    disabled={isLocked}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #cbd5e1",
                      width: "100%",
                      maxWidth: 420,
                      background: isLocked ? "#f1f5f9" : "#fff",
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
              ) : null}

              <div style={{ fontSize: 14, fontWeight: 600, color: "#334155", marginBottom: 8 }}>
                Select Mode
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                <button
                  onClick={() => !isLocked && setConfigMode("question")}
                  disabled={isLocked}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 6,
                    border: configMode === "question" ? "2px solid #2563eb" : "1px solid #cbd5e1",
                    background: configMode === "question" ? "#e0e7ff" : "#fff",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Question Mode
                </button>
                <button
                  onClick={() => !isLocked && setConfigMode("time")}
                  disabled={isLocked}
                  style={{
                    padding: "8px 14px",
                    borderRadius: 6,
                    border: configMode === "time" ? "2px solid #2563eb" : "1px solid #cbd5e1",
                    background: configMode === "time" ? "#e0e7ff" : "#fff",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Time Mode
                </button>
              </div>

              {configMode === "question" ? (
                <div style={{ marginBottom: 16 }}>
                  <label style={{ fontSize: 14, color: "#334155", marginBottom: 6, display: "block" }}>
                    Number of questions:
                  </label>
                  <select
                    value={questionCount || "custom"}
                    onChange={(event) => {
                      if (event.target.value === "custom") {
                        setQuestionCount("custom");
                        setCustomQuestionCount("");
                        return;
                      }
                      setQuestionCount(Number(event.target.value));
                      setCustomQuestionCount("");
                    }}
                    disabled={isLocked}
                    style={{
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #cbd5e1",
                      width: "100%",
                      maxWidth: 420,
                      background: isLocked ? "#f1f5f9" : "#fff",
                    }}
                  >
                    <option value={10}>10</option>
                    <option value={15}>15</option>
                    <option value={20}>20</option>
                    <option value={25}>25</option>
                    <option value={30}>30</option>
                    <option value="custom">Custom</option>
                  </select>

                  {questionCount === "custom" ? (
                    <input
                      type="number"
                      min={10}
                      max={30}
                      value={customQuestionCount}
                      onChange={(event) => setCustomQuestionCount(event.target.value)}
                      disabled={isLocked}
                      placeholder="Enter 10 to 30 questions"
                      style={{
                        marginTop: 8,
                        width: "100%",
                        maxWidth: 420,
                        padding: "10px 12px",
                        borderRadius: 8,
                        border: "1px solid #cbd5e1",
                      }}
                    />
                  ) : null}

                  {questionCount === "custom" && customQuestionCount && !questionModeValid ? (
                    <div style={{ marginTop: 8, color: "#b91c1c", fontSize: 13 }}>
                      Enter a custom question count between 10 and 30.
                    </div>
                  ) : null}

                  {isHrCategory && selectedFocusAreas.length > 0 ? (
                    <div style={{ marginTop: 10, color: "#475569", fontSize: 13 }}>
                      The interview will distribute questions across your {selectedFocusAreas.length} selected focus area{selectedFocusAreas.length > 1 ? "s" : ""}.
                    </div>
                  ) : null}

                  <div style={{ marginTop: 16, marginBottom: 12 }}>
                    <div style={{ fontSize: 14, color: "#334155", marginBottom: 6 }}>Mode Type</div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <button
                        onClick={() => !isLocked && setPracticeType("practice")}
                        disabled={isLocked}
                        style={{
                          padding: "8px 14px",
                          borderRadius: 6,
                          border: practiceType === "practice" ? "2px solid #2563eb" : "1px solid #cbd5e1",
                          background: practiceType === "practice" ? "#e0e7ff" : "#fff",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Practice Mode
                      </button>
                      <button
                        onClick={() => !isLocked && setPracticeType("interview")}
                        disabled={isLocked}
                        style={{
                          padding: "8px 14px",
                          borderRadius: 6,
                          border: practiceType === "interview" ? "2px solid #2563eb" : "1px solid #cbd5e1",
                          background: practiceType === "interview" ? "#e0e7ff" : "#fff",
                          fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        Interview Mode
                      </button>
                    </div>
                  </div>

                  {practiceType === "interview" ? (
                    <div>
                      <label style={{ fontSize: 14, color: "#334155", marginBottom: 6, display: "block" }}>
                        Interview duration (minutes):
                      </label>
                      <select
                        value={interviewTime}
                        onChange={(event) => setInterviewTime(Number(event.target.value))}
                        disabled={isLocked}
                        style={{
                          width: "100%",
                          maxWidth: 420,
                          padding: "10px 12px",
                          borderRadius: 8,
                          border: "1px solid #cbd5e1",
                          background: isLocked ? "#f1f5f9" : "#fff",
                        }}
                      >
                        <option value="">Select interview duration</option>
                        {INTERVIEW_TIME_OPTIONS.map((time) => (
                          <option key={time} value={time}>
                            {time} minutes
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {configMode === "time" ? (
                <div>
                  <label style={{ fontSize: 14, color: "#334155", marginBottom: 6, display: "block" }}>
                    Choose sample time (minutes):
                  </label>
                  <select
                    value={timeModeValue}
                    onChange={(event) => setTimeModeValue(Number(event.target.value))}
                    disabled={isLocked}
                    style={{
                      width: "100%",
                      maxWidth: 420,
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: "1px solid #cbd5e1",
                      background: isLocked ? "#f1f5f9" : "#fff",
                    }}
                  >
                    <option value="">Select interval</option>
                    {INTERVIEW_TIME_OPTIONS.map((time) => (
                      <option key={time} value={time}>
                        {time} minutes
                      </option>
                    ))}
                  </select>
                  <small style={{ color: "#475569" }}>
                    AI will ask as many questions as possible within this selected time limit.
                  </small>
                </div>
              ) : null}
            </div>
            <button
              className="topic-action-btn"
              style={{
                marginTop: 6,
                opacity: isSelectionReady && !confirmedSelection ? 1 : 0.5,
                cursor: isSelectionReady && !confirmedSelection ? "pointer" : "not-allowed",
              }}
              disabled={!isSelectionReady || confirmedSelection !== null}
              onClick={handleConfirmSelection}
            >
              Confirm Selection
            </button>

            {confirmedSelection ? (
              <div style={{ marginTop: 14, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                <div style={{ width: "100%", maxWidth: 600, background: "#eff6ff", borderRadius: 10, padding: "20px", border: "1px solid #bfdbfe", color: "#1e3a8a" }}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                    {/* Selected Role/Languages */}
                    <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>
                        {isHrCategory ? "Selected role:" : confirmedSelection.mode === "role" ? "Selected role:" : "Selected language(s):"}
                      </div>
                      <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>
                        {isHrCategory ? confirmedSelection.jobRole : confirmedSelection.options.join(", ")}
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

                    {/* Interview Round (HR only) */}
                    {isHrCategory && (
                      <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Interview Round</div>
                        <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>{confirmedSelection.hrRoundLabel}</div>
                      </div>
                    )}

                    {/* Focus Areas (HR only) */}
                    {isHrCategory && (
                      <div style={{ background: "#fff", borderRadius: 8, padding: 12, border: "1px solid #bfdbfe", textAlign: "center" }}>
                        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.85rem", color: "#1e3a8a" }}>Focus Areas</div>
                        <div style={{ color: "#0f172a", fontSize: "0.95rem" }}>{confirmedSelection.focusAreas.join(", ")}</div>
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", justifyContent: "center", marginTop: 18 }}>
                    <button
                      className="topic-action-btn secondary"
                      onClick={() => resetConfiguration(selectedRound)}
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

                <button className="start-interview-confirm" onClick={proceedToInstructions}>
                  Proceed to Instructions
                </button>
              </div>
            ) : null}
          </div>
        )}
      </div>

      <div style={{ textAlign: "center", marginTop: 40, paddingBottom: 40, display: "flex", justifyContent: "center", gap: 12 }}>
        <button className="go-back-btn" onClick={() => navigate(-1)}>
          &lt;- Go Back
        </button>

        <button className="topic-action-btn" onClick={() => navigate("/")}>
          Home
        </button>
      </div>

      <div className="bottom-footer">
        Tailored interview setup for {pageConfig.cards.length} guided pathways
      </div>
    </div>
  );
}

export default Topics;
