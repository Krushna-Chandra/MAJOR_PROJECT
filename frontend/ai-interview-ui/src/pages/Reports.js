import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import {
  ArrowRight,
  Brain,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Download,
  Home,
  Layers3,
  Lightbulb,
  Radar,
  RefreshCcw,
  Sparkles,
  Star,
  Target,
} from "lucide-react";
import "../App.css";
import { useScrollToTop } from "../hooks/useScrollToTop";
import {
  normalizeReport,
  safeCodeText,
  safeErrorText,
  safeScore,
  safeText,
  safeTextList,
} from "../utils/interviewReport";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

function averageScores(values) {
  const scores = values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value));
  if (!scores.length) return null;
  return safeScore(scores.reduce((total, value) => total + value, 0) / scores.length);
}

function percentScore(numerator, denominator) {
  const top = Number(numerator);
  const bottom = Number(denominator);
  if (!Number.isFinite(top) || !Number.isFinite(bottom) || bottom <= 0) return 0;
  return safeScore((top / bottom) * 100);
}

function buildPerformanceDimensions(report) {
  const evaluations = (report?.evaluations || []).filter((item) => item?.count_towards_score !== false);
  const dimensions = [
    { label: "Communication", reportKey: "communication", evaluationKey: "communication_score" },
    { label: "Confidence", reportKey: "confidence", evaluationKey: "confidence_score" },
    { label: "Problem Solving", reportKey: "problem_solving", evaluationKey: "problem_solving_score" },
    { label: "Teamwork", reportKey: "teamwork", evaluationKey: "teamwork_score" },
    { label: "Leadership", reportKey: "leadership", evaluationKey: "leadership_score" },
    { label: "Readiness", reportKey: "hr_readiness", evaluationKey: "hr_readiness_score" },
  ];

  const directDimensions = dimensions
    .map((dimension) => {
      const score = report?.score_breakdown?.[dimension.reportKey] != null
        ? safeScore(report.score_breakdown[dimension.reportKey])
        : averageScores(evaluations.map((item) => item?.[dimension.evaluationKey]));
      return score == null
        ? null
        : {
            label: dimension.label,
            score,
            actual: Math.max(0, Math.min(5, score / 20)),
          };
    })
    .filter(Boolean);

  if (directDimensions.length >= 3) {
    return directDimensions;
  }

  const reportedAnswered = Number(report?.questions_answered);
  const answeredCount = Number.isFinite(reportedAnswered) && reportedAnswered >= 0 ? reportedAnswered : evaluations.length;
  const totalQuestions = Number(report?.total_questions || report?.question_outline?.length || answeredCount);
  const strongAnswerCount = evaluations.filter((item) => safeScore(item?.score) >= 75).length;
  const matchedPoints = evaluations.flatMap((item) => safeTextList(item?.matched_points));
  const missedPoints = evaluations.flatMap((item) => safeTextList(item?.missed_points));
  const pointTotal = matchedPoints.length + missedPoints.length;

  const groundedDimensions = [
    { label: "Score Average", score: safeScore(report?.overall_score) },
    { label: "Strong Answers", score: percentScore(strongAnswerCount, answeredCount) },
    { label: "Completion", score: percentScore(answeredCount, totalQuestions) },
  ];

  if (pointTotal > 0) {
    groundedDimensions.push({ label: "Covered Points", score: percentScore(matchedPoints.length, pointTotal) });
  }

  return groundedDimensions.map((item) => ({
    ...item,
    actual: Math.max(0, Math.min(5, item.score / 20)),
  }));
}

function buildRadarPoints(values, radius, centerX, centerY) {
  return values
    .map((value, index) => {
      const angle = ((Math.PI * 2) / values.length) * index - Math.PI / 2;
      const pointRadius = (value / 5) * radius;
      const x = centerX + Math.cos(angle) * pointRadius;
      const y = centerY + Math.sin(angle) * pointRadius;
      return `${x},${y}`;
    })
    .join(" ");
}

function RadarChart({ items = [] }) {
  if (!items.length) return null;

  const centerX = 170;
  const centerY = 160;
  const radius = 110;
  const actualPoints = buildRadarPoints(items.map((item) => item.actual), radius, centerX, centerY);

  return (
    <div className="report-radar-card">
      <svg viewBox="0 0 340 320" className="report-radar-chart">
        {[1, 2, 3, 4, 5].map((step) => {
          const stepRadius = (radius / 5) * step;
          const points = buildRadarPoints(new Array(items.length).fill(5), stepRadius, centerX, centerY);
          return <polygon key={step} points={points} className="report-radar-grid" />;
        })}

        {items.map((item, index) => {
          const angle = ((Math.PI * 2) / items.length) * index - Math.PI / 2;
          const x = centerX + Math.cos(angle) * (radius + 18);
          const y = centerY + Math.sin(angle) * (radius + 18);
          const axisX = centerX + Math.cos(angle) * radius;
          const axisY = centerY + Math.sin(angle) * radius;

          return (
            <g key={item.label}>
              <line x1={centerX} y1={centerY} x2={axisX} y2={axisY} className="report-radar-axis" />
              <text x={x} y={y} textAnchor="middle" className="report-radar-label">
                {item.label}
              </text>
            </g>
          );
        })}

        <polygon points={actualPoints} className="report-radar-actual" />
      </svg>

      <div className="report-radar-legend">
        <span><i className="report-radar-legend__actual" /> Evaluated performance</span>
      </div>
    </div>
  );
}

function ScoreBars({ items = [] }) {
  if (!items.length) {
    return <div className="report-bullet-list">- No question-level scores were saved for this report.</div>;
  }
  return (
    <div className="report-score-list">
      {items.map((item, index) => (
        <div key={`${item.question}-${index}`} className="report-score-row">
          <div className="report-score-row__meta">
            <span>{item.question}</span>
            <strong>{item.score}/100</strong>
          </div>
          <div className="report-score-track">
            <div
              className={`report-score-fill ${item.score >= 75 ? "is-strong" : item.score >= 60 ? "is-mid" : "is-low"}`}
              style={{ width: `${Math.max(8, Math.min(100, item.score || 0))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function MetricTile({ label, value, tone = "indigo" }) {
  return (
    <div className={`report-metric-tile report-metric-tile-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatReportDate(report) {
  const rawDate = safeText(report?.completed_at || report?.created_at || report?.timestamp);
  if (!rawDate) return "Not recorded";

  const numeric = Number(rawDate);
  const parsed = Number.isFinite(numeric)
    ? new Date(numeric < 10000000000 ? numeric * 1000 : numeric)
    : new Date(rawDate);

  return Number.isNaN(parsed.getTime()) ? "Not recorded" : parsed.toLocaleDateString("en-GB");
}

function formatBreakdownLabel(key) {
  const labels = {
    communication: "Communication",
    confidence: "Confidence",
    problem_solving: "Problem-solving",
    teamwork: "Teamwork",
    leadership: "Leadership",
    hr_readiness: "HR Readiness",
    personality_attitude: "Personality",
    cultural_fit: "Cultural Fit",
    star_structure: "STAR",
  };

  return labels[key] || safeText(key).replace(/_/g, " ");
}

function formatRoundLabel(value) {
  const normalized = safeText(value);
  if (!normalized) return "";
  const lookup = {
    hr: "HR",
    behavioral: "Behavioral",
    hr_behavioral: "HR + Behavioral",
    technical: "HR + Behavioral",
    both: "HR + Behavioral",
  };
  return lookup[normalized.toLowerCase()] || normalized
    .replace(/_/g, " / ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getReportCategory(report) {
  return safeText(report?.context?.category || report?.category || report?.interview_type || report?.type).toLowerCase();
}

function getReportTitle(report) {
  return safeText(
    report?.context?.job_role ||
    report?.context?.primary_language ||
    report?.context?.section_title ||
    report?.context?.test_type ||
    report?.context?.category ||
    report?.interview_type ||
    "Interview"
  );
}

function getRetryTarget(report, retryState) {
  const category = getReportCategory(report);
  const interviewType = safeText(report?.interview_type).toLowerCase();

  if (category === "aptitude" || interviewType === "aptitude") {
    return { path: "/aptitude-test", state: null };
  }
  if (category === "resume" || interviewType.includes("resume")) {
    return { path: "/resume-interview", state: null };
  }
  if (category === "hr") {
    return { path: "/permissions", state: retryState };
  }
  if (category === "technical" || category === "mock" || category === "general") {
    return { path: "/permissions", state: retryState };
  }
  return { path: "/dashboard", state: null };
}

function buildRetryState(report) {
  if (!report) return null;

  const category = safeText(report.context?.category) || "technical";
  const isHrCategory = category.toLowerCase() === "hr";
  const selectedOptions = isHrCategory
    ? (safeTextList(report.context?.focus_areas || report.context?.selected_options).length
        ? safeTextList(report.context?.focus_areas || report.context?.selected_options)
        : ["Communication", "Leadership", "Problem-solving", "Teamwork", "Confidence"])
    : [safeText(report.context?.primary_language || report.context?.job_role || report.context?.category || "General")];

  return {
    category,
    selectedMode: isHrCategory ? "hr" : report.context?.primary_language ? "language" : "role",
    selectedOptions,
    focusAreas: isHrCategory ? selectedOptions : [],
    hrRound: isHrCategory ? safeText(report.context?.hr_round) : "",
    jobRole: safeText(report.context?.job_role),
    experience: safeText(report.context?.experience) || "Fresher",
    configMode: "question",
    questionCount: 10,
    customQuestionCount: null,
    practiceType: safeText(report.context?.practice_type) === "interview" ? "interview" : "practice",
    interviewModeTime: report.context?.interview_mode_time ? Number(report.context.interview_mode_time) || 10 : 10,
    timeModeInterval: report.context?.time_mode_interval ? Number(report.context.time_mode_interval) || null : null,
  };
}

function buildQuestionCards(report, evaluations) {
  if (evaluations.length) {
    return evaluations.map((item, itemIndex) => ({
      ...item,
      cardId: `${item.question || item.question_id || "question"}-${itemIndex}`,
      score: safeScore(item.score),
      suggestedAnswer: safeText(item.suggested_answer),
      referenceAnswer: safeCodeText(item.reference_answer),
      hasEvaluation: true,
    }));
  }

  return (report?.question_outline || []).map((item, itemIndex) => ({
    question_id: safeText(item.id || itemIndex + 1),
    question: safeText(item.question) || `Question ${itemIndex + 1}`,
    question_type: safeText(item.question_type),
    answer: "",
    feedback: "No evaluated answer was captured for this question.",
    reference_answer: "",
    strengths: [],
    gaps: [],
    matched_points: [],
    missed_points: [],
    suggestions: [],
    score: safeScore(item.score),
    suggestedAnswer: "",
    referenceAnswer: "",
    cardId: `${item.id || item.question || "outline"}-${itemIndex}`,
    hasEvaluation: false,
  }));
}

function isCodingQuestion(item) {
  return safeText(item?.question_type).toLowerCase() === "coding";
}

function Reports() {
  useScrollToTop();
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionId } = useParams();
  const reportRef = useRef(null);
  const locationReport = location.state?.report ? normalizeReport(location.state.report, location.state?.context || {}) : null;

  const [report, setReport] = useState(locationReport);
  const [loading, setLoading] = useState(!locationReport);
  const [error, setError] = useState("");
  const [userRating, setUserRating] = useState(0);
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [ratingMessage, setRatingMessage] = useState("");

  useEffect(() => {
    if (!sessionId) return;

    const loadReport = async () => {
      if (!locationReport) {
        setLoading(true);
      }
      setError("");
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get(`${API_BASE_URL}/interview-reports/${sessionId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        setReport(normalizeReport(response.data?.report, location.state?.context || {}));
      } catch (requestError) {
        if (!locationReport) {
          setError(
            safeErrorText(
              requestError.response?.data?.detail ||
              requestError.response?.data ||
              requestError.message ||
              "Failed to load the report."
            )
          );
        }
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, [location.state?.context, locationReport, sessionId]);

  useEffect(() => {
    if (!sessionId) return;

    let ignore = false;

    const loadRating = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        const response = await axios.get(`${API_BASE_URL}/report-ratings/${sessionId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!ignore) {
          setUserRating(Number(response.data?.rating) || 0);
        }
      } catch {
        if (!ignore) {
          setUserRating(0);
        }
      }
    };

    loadRating();

    return () => {
      ignore = true;
    };
  }, [sessionId]);

  const reportView = useMemo(() => {
    const evaluations = (report?.evaluations || []).filter((item) => item?.count_towards_score !== false);
    const reportedAnswered = Number(report?.questions_answered);
    const answeredCount = Number.isFinite(reportedAnswered) && reportedAnswered >= 0 ? reportedAnswered : evaluations.length;
    const strongAnswerCount = evaluations.filter((item) => item.score >= 75).length;
    const needsWorkCount = evaluations.filter((item) => item.score < 60).length;
    const allMistakes = Array.from(new Set(evaluations.flatMap((item) => safeTextList(item.gaps))));
    const allMatchedPoints = evaluations.flatMap((item) => safeTextList(item.matched_points));
    const allMissedPoints = evaluations.flatMap((item) => safeTextList(item.missed_points));
    const hasPointCoverage = allMatchedPoints.length + allMissedPoints.length > 0;
    const performanceRatio = hasPointCoverage
      ? Math.round((allMatchedPoints.length / (allMatchedPoints.length + allMissedPoints.length)) * 100)
      : null;
    const reportTitle = getReportTitle(report);
    const roleMode = safeText(report?.context?.selected_mode || report?.context?.category || "Interview");
    const roundLabel = formatRoundLabel(report?.context?.hr_round || roleMode || "Interview");
    const experience = safeText(report?.context?.experience || "Not specified");
    const timer = safeText(report?.context?.interview_mode_time || report?.context?.time_mode_interval || "No timer");
    const focusAreaLabel = safeText(report?.context?.focus_areas || report?.context?.selected_options) || reportTitle;
    const performanceDimensions = buildPerformanceDimensions(report);
    const reportCategory = getReportCategory(report);
    const isHrReport = reportCategory === "hr";
    const isAptitudeReport = reportCategory === "aptitude" || safeText(report?.interview_type).toLowerCase() === "aptitude";
    const isResumeAdaptive = safeText(report?.interview_type).toLowerCase() === "resume_adaptive";
    const scoreBreakdown = report?.score_breakdown && typeof report.score_breakdown === "object"
      ? Object.entries(report.score_breakdown)
          .filter(([, value]) => value != null)
          .map(([key, value], index) => ({
            key,
            label: formatBreakdownLabel(key),
            value: safeScore(value),
            tone: ["teal", "green", "blue", "orange", "indigo"][index % 5],
          }))
      : [];
    
    // Process skill-wise breakdown for adaptive resume interviews
    const skillsBreakdown = isResumeAdaptive && report?.skills_breakdown && typeof report.skills_breakdown === "object"
      ? Object.entries(report.skills_breakdown)
          .map(([skillName, skillData]) => ({
            name: skillName,
            score: safeScore(skillData?.score),
            proficiency: safeText(skillData?.proficiency),
            performance: safeText(skillData?.performance),
            difficulty_progression: safeTextList(skillData?.difficulty_progression),
            questions_count: Number(skillData?.questions_count) || 0,
            strengths: safeTextList(skillData?.strengths),
            weaknesses: safeTextList(skillData?.weaknesses),
            recommendation: safeText(skillData?.recommendation),
          }))
          .sort((a, b) => b.score - a.score)
      : [];
    
    const topSkills = isResumeAdaptive ? safeTextList(report?.top_skills) : [];
    const weakestSkills = isResumeAdaptive ? safeTextList(report?.weakest_skills) : [];
    const avgDifficultyReached = isResumeAdaptive ? safeText(report?.avg_difficulty_reached) : "";
    
    const retryState = buildRetryState(report);
    const retryTarget = getRetryTarget(report, retryState);
    const completedLabel = formatReportDate(report);
    const questionCards = buildQuestionCards(report, evaluations);

    return {
      allMistakes,
      answeredCount,
      avgDifficultyReached,
      completedLabel,
      experience,
      focusAreaLabel,
      hasPointCoverage,
      isAptitudeReport,
      isHrReport,
      isResumeAdaptive,
      performanceRatio,
      questionCards,
      roundLabel,
      reportTitle,
      retryTarget,
      roleMode,
      scoreBreakdown,
      performanceDimensions,
      skillsBreakdown,
      strongAnswerCount,
      topSkills,
      weakestSkills,
      needsWorkCount,
      timer,
    };
  }, [report]);

  const {
    allMistakes,
    answeredCount,
    avgDifficultyReached,
    completedLabel,
    experience,
    focusAreaLabel,
    hasPointCoverage,
    isAptitudeReport,
    isHrReport,
    isResumeAdaptive,
    performanceDimensions,
    performanceRatio,
    questionCards,
    roundLabel,
    reportTitle,
    retryTarget,
    roleMode,
    scoreBreakdown,
    skillsBreakdown,
    strongAnswerCount,
    topSkills,
    weakestSkills,
    needsWorkCount,
    timer,
  } = reportView;
  const downloadReportPdf = () => {
    if (!reportRef.current) {
      setError("The report is not ready to export yet.");
      return;
    }

    const printWindow = window.open("", "_blank", "width=1200,height=900");
    if (!printWindow) {
      setError("Popup blocked. Please allow popups to export the report as PDF.");
      return;
    }

    const reportHtml = reportRef.current.innerHTML;
    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <title>${reportTitle} Report</title>
          <meta charset="utf-8" />
          <style>
            body { font-family: Arial, sans-serif; margin: 24px; color: #0f172a; background: #ffffff; }
            h1, h2, h3, h4 { color: #0f172a; margin-top: 0; }
            p, div, span { line-height: 1.6; }
            button { display: none !important; }
          </style>
        </head>
        <body>
          <h1>${reportTitle} Report</h1>
          ${reportHtml}
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 300);
  };

  const handleRatingSubmit = async (ratingValue) => {
    if (!sessionId || ratingSubmitting) return;

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        setRatingMessage("Please log in again to submit your rating.");
        return;
      }

      setRatingSubmitting(true);
      setRatingMessage("");

      const response = await axios.post(
        `${API_BASE_URL}/report-ratings/${sessionId}`,
        { rating: ratingValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setUserRating(Number(response.data?.rating) || ratingValue);
      setRatingMessage("Thanks for rating this interview report.");
    } catch (requestError) {
      setRatingMessage(
        safeErrorText(
          requestError.response?.data?.detail ||
          requestError.response?.data ||
          requestError.message ||
          "Unable to save your rating right now."
        )
      );
    } finally {
      setRatingSubmitting(false);
    }
  };

  return (
    <div className="report-page-shell">
      <div className="report-page-inner">
        <div className="report-topbar">
          <div>
            <span className="report-badge">AI interview report</span>
            <h1 className="report-page-title">{reportTitle} performance report</h1>
            <p className="report-page-subtitle">
              Grounded breakdown of this session using the answers, scores, and feedback captured during the attempt.
            </p>
          </div>

          <div className="report-topbar-actions">
            <button className="report-secondary-button" onClick={() => navigate(-1)}>Back</button>
            <button className="report-secondary-button" onClick={() => navigate("/")}>Home</button>
            <button className="report-primary-button" onClick={() => navigate("/dashboard")}>Dashboard</button>
          </div>
        </div>

        {error ? <div className="report-alert report-alert-error">{safeText(error)}</div> : null}
        {loading ? <div className="report-loading-card">Loading report...</div> : null}

        {!loading && report ? (
          <div ref={reportRef} className="report-grid-layout">
            <section className="report-main-column">
              <article className="report-hero-card">
                <div className="report-tag-row">
                  <span className="report-chip">{roleMode}</span>
                  <span className="report-chip">{reportTitle}</span>
                  {isHrReport ? <span className="report-chip">{roundLabel}</span> : null}
                  <span className="report-chip">{experience}</span>
                  <span className="report-chip">{timer}</span>
                </div>

                <div className="report-hero-grid">
                  <RadarChart items={performanceDimensions} />

                  <div className="report-side-panel-card">
                    <div className="report-side-panel-card__header">
                      <h2>Evaluated dimensions</h2>
                    </div>
                    <div className="report-skill-list">
                      {performanceDimensions.map((item) => (
                        <div key={item.label} className="report-skill-row">
                          <span>{item.label}</span>
                          <strong>{item.score}/100</strong>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </article>

              <article className="report-rating-card">
                <div className="report-card-header report-card-header-tight">
                  <div>
                    <span className="report-card-eyebrow">Session feedback</span>
                    <h3>Rate this interview report</h3>
                  </div>
                  <Star size={18} />
                </div>

                <p className="report-rating-copy">
                  Your rating helps us improve the report quality and updates the average rating shown on the home page.
                </p>

                <div className="report-rating-stars" aria-label="Rate this report from 1 to 5 stars">
                  {[1, 2, 3, 4, 5].map((value) => {
                    const active = value <= userRating;
                    return (
                      <button
                        key={value}
                        type="button"
                        className={`report-rating-star ${active ? "is-active" : ""}`}
                        onClick={() => handleRatingSubmit(value)}
                        disabled={ratingSubmitting}
                        aria-label={`Rate ${value} star${value > 1 ? "s" : ""}`}
                      >
                        <Star size={22} fill={active ? "currentColor" : "none"} />
                      </button>
                    );
                  })}
                </div>

                <div className="report-rating-meta">
                  <span>{userRating ? `Your rating: ${userRating}/5` : "Select a star rating"}</span>
                  {ratingMessage ? <span>{ratingMessage}</span> : null}
                </div>
              </article>

              <article className="report-analytics-card">
                <div className="report-card-header">
                  <div>
                    <span className="report-card-eyebrow">Session analytics</span>
                    <h2>Performance metrics</h2>
                  </div>
                  <div className="report-score-badge">{safeScore(report.overall_score)}/100</div>
                </div>

                <div className="report-metrics-grid">
                  <MetricTile label="Questions answered" value={answeredCount} tone="teal" />
                  <MetricTile label={isAptitudeReport ? "Correct answers" : "Strong answers"} value={strongAnswerCount} tone="green" />
                  <MetricTile label={isAptitudeReport ? "Incorrect / skipped" : "Need work"} value={needsWorkCount} tone="orange" />
                  <MetricTile label="Covered points" value={hasPointCoverage ? `${performanceRatio}%` : "Not recorded"} tone="blue" />
                </div>

                {isResumeAdaptive && skillsBreakdown.length ? (
                  <div className="report-score-card">
                    <div className="report-card-header report-card-header-tight">
                      <div>
                        <span className="report-card-eyebrow">Skills assessment</span>
                        <h3>Per-skill performance breakdown</h3>
                      </div>
                      <Layers3 size={18} />
                    </div>
                    <div className="skills-breakdown-container">
                      {skillsBreakdown.map((skill) => {
                        const proficiencyColors = {
                          "Beginner": "is-beginner",
                          "Intermediate": "is-intermediate",
                          "Expert": "is-expert",
                        };
                        const performanceColors = {
                          "Strong": "is-strong",
                          "Moderate": "is-mid",
                          "Needs Work": "is-low",
                        };
                        
                        return (
                          <div key={skill.name} className="skill-breakdown-card">
                            <div className="skill-header">
                              <div className="skill-title">
                                <h4>{skill.name}</h4>
                                <span className={`skill-proficiency-badge ${proficiencyColors[skill.proficiency] || "is-intermediate"}`}>
                                  {skill.proficiency}
                                </span>
                              </div>
                              <div className={`skill-score ${performanceColors[skill.performance] || "is-mid"}`}>
                                {skill.score}/100
                              </div>
                            </div>

                            <div className="skill-content">
                              <div className="skill-metric">
                                <span>Questions: {skill.questions_count}</span>
                              </div>

                              <div className="skill-difficulty">
                                <span className="difficulty-label">Difficulty progression:</span>
                                <div className="difficulty-badges">
                                  {skill.difficulty_progression.map((diff, idx) => {
                                    const diffColor = {
                                      "Easy": "diff-easy",
                                      "Medium": "diff-medium",
                                      "Hard": "diff-hard",
                                    };
                                    return (
                                      <span key={idx} className={`difficulty-badge ${diffColor[diff] || "diff-medium"}`}>
                                        {diff}
                                      </span>
                                    );
                                  })}
                                </div>
                              </div>

                              {skill.strengths.length > 0 && (
                                <div className="skill-section">
                                  <span className="section-label">Strengths:</span>
                                  <ul className="skill-list is-strengths">
                                    {skill.strengths.map((str, idx) => (
                                      <li key={idx}>{str}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {skill.weaknesses.length > 0 && (
                                <div className="skill-section">
                                  <span className="section-label">Areas to improve:</span>
                                  <ul className="skill-list is-weaknesses">
                                    {skill.weaknesses.map((weak, idx) => (
                                      <li key={idx}>{weak}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {skill.recommendation && (
                                <div className="skill-recommendation">
                                  <Lightbulb size={14} />
                                  <span>{skill.recommendation}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {(topSkills.length > 0 || weakestSkills.length > 0) && (
                      <div className="skill-summary">
                        {topSkills.length > 0 && (
                          <div className="skill-summary-item">
                            <span className="summary-label">Top skills:</span>
                            <span className="summary-value">{topSkills.join(", ")}</span>
                          </div>
                        )}
                        {weakestSkills.length > 0 && (
                          <div className="skill-summary-item">
                            <span className="summary-label">Areas to focus:</span>
                            <span className="summary-value">{weakestSkills.join(", ")}</span>
                          </div>
                        )}
                        {avgDifficultyReached && (
                          <div className="skill-summary-item">
                            <span className="summary-label">Adaptive difficulty:</span>
                            <span className="summary-value">{avgDifficultyReached}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : null}

                {isHrReport && scoreBreakdown.length ? (
                  <div className="report-score-card">
                    <div className="report-card-header report-card-header-tight">
                      <div>
                        <span className="report-card-eyebrow">HR score breakdown</span>
                        <h3>Communication and readiness</h3>
                      </div>
                      <Target size={18} />
                    </div>
                    <div className="report-metrics-grid">
                      {scoreBreakdown.map((item) => (
                        <MetricTile key={item.key} label={item.label} value={`${item.value}/100`} tone={item.tone} />
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="report-score-card">
                  <div className="report-card-header report-card-header-tight">
                    <div>
                      <span className="report-card-eyebrow">Question score trend</span>
                      <h3>Per-question performance</h3>
                    </div>
                    <Radar size={18} />
                  </div>
                  <ScoreBars items={questionCards.map((item) => ({ question: safeText(item.question), score: safeScore(item.score) }))} />
                </div>
              </article>

              <article className="report-comments-card">
                <div className="report-card-header">
                  <div>
                    <span className="report-card-eyebrow">Coach comments</span>
                    <h2>Session comments</h2>
                  </div>
                  <Sparkles size={18} />
                </div>

                <div className="report-comment-list">
                  {(report.improvement_areas || []).length ? (
                    (report.improvement_areas || []).map((item) => (
                      <div key={item} className="report-comment-item">
                        <CircleAlert size={16} />
                        <span>{item}</span>
                      </div>
                    ))
                  ) : (
                    <div className="report-comment-item">
                      <CheckCircle2 size={16} />
                      <span>No major repeated improvement areas were detected in this round.</span>
                    </div>
                  )}

                  <div className="report-comment-item report-comment-item-highlight">
                    <Lightbulb size={16} />
                    <span>{safeText(report.summary) || "Use the per-question guidance below to sharpen the answers for a real interview."}</span>
                  </div>
                </div>
              </article>

              <article className="report-question-section">
                <div className="report-card-header">
                  <div>
                    <span className="report-card-eyebrow">Question review</span>
                    <h2>Question-by-question analysis</h2>
                  </div>
                  <Brain size={18} />
                </div>

                <div className="report-question-list">
                  {!questionCards.length ? (
                    <article className="report-question-card">
                      <div className="report-question-card__top">
                        <div>
                          <span className="report-question-card__index">No question details</span>
                          <h3>No evaluated questions were saved for this report.</h3>
                        </div>
                      </div>
                      <div className="report-question-block">
                        <span>Report status</span>
                        <p>The summary above is limited because this attempt did not include question-level evaluation data.</p>
                      </div>
                    </article>
                  ) : null}

                  {questionCards.map((item, index) => (
                    <article key={item.cardId} className="report-question-card">
                      <div className="report-question-card__top">
                        <div>
                          <span className="report-question-card__index">Question {index + 1}</span>
                          <h3>{safeText(item.question)}</h3>
                        </div>
                        <div className={`report-question-score ${item.score >= 75 ? "is-strong" : item.score >= 60 ? "is-mid" : "is-low"}`}>
                          {item.score}/100
                        </div>
                      </div>

                      <div className="report-question-grid">
                        <div className="report-question-block">
                          <span>Your answer</span>
                          {isCodingQuestion(item) ? (
                            <pre className="aptitude-code-summary-text">{safeCodeText(item.answer) || "No code was captured for this question."}</pre>
                          ) : (
                            <p>{safeText(item.answer) || "No answer was captured for this question."}</p>
                          )}
                        </div>

                        <div className="report-question-block">
                          <span>AI analysis</span>
                          <p>{safeText(item.feedback) || "No analysis available."}</p>
                        </div>
                      </div>

                      <div className="report-question-grid">
                        <div className="report-mini-panel">
                          <span>What went well</span>
                          <div className="report-bullet-list">
                            {(item.strengths || []).length
                              ? (item.strengths || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- {item.hasEvaluation ? "No specific strength was recorded for this answer." : "No evaluated answer was captured for this question."}</div>}
                          </div>
                        </div>

                        <div className="report-mini-panel report-mini-panel-warn">
                          <span>Mistakes / gaps</span>
                          <div className="report-bullet-list">
                            {(item.gaps || []).length
                              ? (item.gaps || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- {item.hasEvaluation ? "No clear gap tags were returned for this question." : "No gap analysis is available without an evaluated answer."}</div>}
                          </div>
                        </div>
                      </div>

                      <div className="report-ideal-answer-card">
                        <div className="report-ideal-answer-card__header">
                          <Target size={16} />
                          <span>{isCodingQuestion(item) ? "Correct answer" : "Suggested answer guidance"}</span>
                        </div>
                        {isCodingQuestion(item) ? (
                          <pre className="aptitude-code-summary-text">
                            {safeCodeText(item.referenceAnswer) ||
                              (item.hasEvaluation
                                ? "No reference answer was saved for this coding question."
                                : "A correct answer can be shown after a coding submission is evaluated.")}
                          </pre>
                        ) : (
                          <p>
                            {item.suggestedAnswer ||
                              (item.hasEvaluation
                                ? "No suggested answer was returned for this question."
                                : "Suggested guidance is available after an answer is evaluated.")}
                          </p>
                        )}
                      </div>

                      <div className="report-question-grid">
                        <div className="report-mini-panel">
                          <span>Covered points</span>
                          <div className="report-bullet-list">
                            {(item.matched_points || []).length
                              ? (item.matched_points || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- No matched points were recorded.</div>}
                          </div>
                        </div>

                        <div className="report-mini-panel report-mini-panel-warn">
                          <span>Missed points</span>
                          <div className="report-bullet-list">
                            {(item.missed_points || []).length
                              ? (item.missed_points || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- No missed points were recorded.</div>}
                          </div>
                        </div>
                      </div>

                      <div className="report-question-grid">
                        <div className="report-mini-panel">
                          <span>Structured feedback</span>
                          <div className="report-bullet-list">
                            <div>- Relevance: {safeText(item.relevance) || "Pending"}</div>
                            <div>- Correctness: {safeText(item.correctness) || "Pending"}</div>
                            <div>- Clarity: {safeText(item.clarity) || "Pending"}</div>
                            <div>- Technical Depth: {safeText(item.technical_depth) || "Pending"}</div>
                            <div>- Logic: {safeText(item.logical_validity) || "Pending"}</div>
                            <div>- Real-world Fit: {safeText(item.real_world_applicability) || "Pending"}</div>
                          </div>
                        </div>

                        <div className="report-mini-panel">
                          <span>{isCodingQuestion(item) ? "Suggestions" : "Suggestions"}</span>
                          <div className="report-bullet-list">
                            {(item.suggestions || []).length
                              ? (item.suggestions || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- No specific improvement suggestions were returned.</div>}
                          </div>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </article>
            </section>

            <aside className="report-sidebar">
              <article className="report-snapshot-card">
                <h2>Session snapshot</h2>

                <div className="report-snapshot-stack">
                  <div className="report-snapshot-tile">
                    <span><Layers3 size={14} /> Questions answered</span>
                    <strong>{answeredCount}</strong>
                  </div>
                  <div className="report-snapshot-tile">
                    <span><Target size={14} /> Focus area</span>
                    <strong>{focusAreaLabel}</strong>
                  </div>
                  <div className="report-snapshot-tile">
                    <span><CalendarDays size={14} /> Completed</span>
                    <strong>{completedLabel}</strong>
                  </div>
                </div>

                <div className="report-sidebar-actions">
                  <button className="report-secondary-button" onClick={() => navigate("/")}>
                    <Home size={15} />
                    Home
                  </button>
                  <button
                    className="report-primary-button"
                    onClick={() => {
                      if (retryTarget?.path) {
                        navigate(retryTarget.path, retryTarget.state ? { state: retryTarget.state } : undefined);
                      }
                    }}
                  >
                    <RefreshCcw size={15} />
                    Practice again
                  </button>
                  <button className="report-secondary-button" onClick={() => navigate("/dashboard")}>
                    <ArrowRight size={15} />
                    Back to dashboard
                  </button>
                  <button className="report-secondary-button" onClick={downloadReportPdf}>
                    <Download size={15} />
                    Download PDF
                  </button>
                </div>
              </article>

              <article className="report-sidebar-card">
                <div className="report-card-header report-card-header-tight">
                  <div>
                    <span className="report-card-eyebrow">Top strengths</span>
                    <h3>What to keep</h3>
                  </div>
                </div>
                <div className="report-bullet-list">
                  {(report.top_strengths || []).length
                    ? (report.top_strengths || []).map((item) => <div key={item}>- {item}</div>)
                    : <div>- More completed sessions will reveal stable strengths.</div>}
                </div>
              </article>

              <article className="report-sidebar-card">
                <div className="report-card-header report-card-header-tight">
                  <div>
                    <span className="report-card-eyebrow">Repeated misses</span>
                    <h3>Focus next</h3>
                  </div>
                </div>
                <div className="report-bullet-list">
                  {allMistakes.length
                    ? allMistakes.map((item) => <div key={item}>- {item}</div>)
                    : <div>- No major repeated mistakes were detected.</div>}
                </div>
              </article>

              <article className="report-sidebar-card">
                <div className="report-card-header report-card-header-tight">
                  <div>
                    <span className="report-card-eyebrow">Report basis</span>
                    <h3>Session data used</h3>
                  </div>
                </div>
                <div className="report-bullet-list">
                  <div>- Mode: {safeText(report.context?.selected_mode) || "Interview"}</div>
                  <div>- Timer: {timer}</div>
                  <div>- Practice type: {safeText(report.context?.practice_type) || "practice"}</div>
                  <div>- Status: {report.ended_early ? "Ended early" : "Completed"}</div>
                  <div>- Evaluated answers: {answeredCount}</div>
                </div>
              </article>
            </aside>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default Reports;
