import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import {
  ArrowRight,
  Brain,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Clock3,
  Download,
  Home,
  Layers3,
  Lightbulb,
  Radar,
  RefreshCcw,
  Sparkles,
  Target,
} from "lucide-react";
import "../App.css";
import {
  formatProviderName,
  normalizeReport,
  safeErrorText,
  safeScore,
  safeText,
  safeTextList,
} from "../utils/interviewReport";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

function countSignalMatches(sourceText, keywords) {
  return keywords.reduce((total, keyword) => total + (sourceText.includes(keyword) ? 1 : 0), 0);
}

function deriveSkillSignals(report) {
  const categories = [
    { label: "Communication", keywords: ["communication", "clarity", "explain", "articulate", "structure", "concise"] },
    { label: "Leadership", keywords: ["leadership", "ownership", "stakeholder", "team", "collaboration", "mentor"] },
    { label: "Problem Solving", keywords: ["problem", "algorithm", "debug", "solution", "approach", "analysis"] },
    { label: "Decision Making", keywords: ["decision", "tradeoff", "judgment", "priority", "choose", "impact"] },
    { label: "Time Mgmt", keywords: ["time", "deadline", "prioritize", "delivery", "planning", "schedule"] },
  ];

  const evaluations = (report?.evaluations || []).filter((item) => item?.count_towards_score !== false);
  const reportText = safeText([
    report?.summary,
    ...(report?.top_strengths || []),
    ...(report?.improvement_areas || []),
    ...evaluations.flatMap((item) => [
      item.feedback,
      ...(item.strengths || []),
      ...(item.gaps || []),
      ...(item.matched_points || []),
      ...(item.missed_points || []),
    ]),
  ]).toLowerCase();

  return categories.map((category) => {
    const rawScore = countSignalMatches(reportText, category.keywords);
    const importance = Math.max(2, Math.min(5, rawScore + 2));
    const actual = Math.max(
      1,
      Math.min(
        5,
        Math.round(((safeScore(report?.overall_score) / 100) * 3) + Math.max(0, importance - 2) * 0.35)
      )
    );

    return {
      label: category.label,
      actual,
      importance,
    };
  });
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
  const requiredPoints = buildRadarPoints(items.map((item) => item.importance), radius, centerX, centerY);
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

        <polygon points={requiredPoints} className="report-radar-required" />
        <polygon points={actualPoints} className="report-radar-actual" />
      </svg>

      <div className="report-radar-legend">
        <span><i className="report-radar-legend__required" /> Required skills</span>
        <span><i className="report-radar-legend__actual" /> Actual skills</span>
      </div>
    </div>
  );
}

function ScoreBars({ items = [] }) {
  if (!items.length) return null;
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

function buildRetryState(report) {
  if (!report) return null;

  return {
    category: safeText(report.context?.category) || "technical",
    selectedMode: report.context?.primary_language ? "language" : "role",
    selectedOptions: [safeText(report.context?.primary_language || report.context?.job_role || report.context?.category || "General")],
    experience: safeText(report.context?.experience) || "Fresher",
    configMode: "question",
    questionCount: 5,
    customQuestionCount: null,
    practiceType: safeText(report.context?.practice_type) === "interview" ? "interview" : "practice",
    interviewModeTime: report.context?.interview_mode_time ? Number(report.context.interview_mode_time) || 10 : 10,
    timeModeInterval: report.context?.time_mode_interval ? Number(report.context.time_mode_interval) || null : null,
  };
}

function Reports() {
  const navigate = useNavigate();
  const location = useLocation();
  const { sessionId } = useParams();
  const reportRef = useRef(null);
  const locationReport = location.state?.report ? normalizeReport(location.state.report, location.state?.context || {}) : null;

  const [report, setReport] = useState(locationReport);
  const [loading, setLoading] = useState(!locationReport);
  const [error, setError] = useState("");
  const [providerStatus, setProviderStatus] = useState(null);

  useEffect(() => {
    if (locationReport || !sessionId) return;

    const loadReport = async () => {
      setLoading(true);
      setError("");
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get(`${API_BASE_URL}/interview-reports/${sessionId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        setReport(normalizeReport(response.data?.report, location.state?.context || {}));
      } catch (requestError) {
        setError(
          safeErrorText(
            requestError.response?.data?.detail ||
            requestError.response?.data ||
            requestError.message ||
            "Failed to load the report."
          )
        );
      } finally {
        setLoading(false);
      }
    };

    loadReport();
  }, [location.state?.context, locationReport, sessionId]);

  useEffect(() => {
    let ignore = false;

    const loadProviderStatus = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/ai-interview/providers/status`);
        if (!ignore) {
          setProviderStatus(response.data || null);
        }
      } catch {
        if (!ignore) {
          setProviderStatus(null);
        }
      }
    };

    loadProviderStatus();

    return () => {
      ignore = true;
    };
  }, []);

  const reportView = useMemo(() => {
    const evaluations = (report?.evaluations || []).filter((item) => item?.count_towards_score !== false);
    const answeredCount = evaluations.length;
    const strongAnswerCount = evaluations.filter((item) => item.score >= 75).length;
    const needsWorkCount = evaluations.filter((item) => item.score < 60).length;
    const allMistakes = Array.from(new Set(evaluations.flatMap((item) => safeTextList(item.gaps))));
    const allMatchedPoints = evaluations.flatMap((item) => safeTextList(item.matched_points));
    const allMissedPoints = evaluations.flatMap((item) => safeTextList(item.missed_points));
    const performanceRatio = allMatchedPoints.length + allMissedPoints.length
      ? Math.round((allMatchedPoints.length / (allMatchedPoints.length + allMissedPoints.length)) * 100)
      : 0;
    const reportTitle = safeText(
      report?.context?.job_role || report?.context?.primary_language || report?.context?.category || "Interview"
    );
    const roleMode = safeText(report?.context?.selected_mode || report?.context?.category || "Interview");
    const experience = safeText(report?.context?.experience || "Not specified");
    const timer = safeText(report?.context?.interview_mode_time || report?.context?.time_mode_interval || "No timer");
    const skillSignals = deriveSkillSignals(report);
    const retryState = buildRetryState(report);
    const completedLabel = new Date().toLocaleDateString("en-GB");

    const questionCards = evaluations.map((item, itemIndex) => ({
      ...item,
      cardId: `${item.question}-${itemIndex}`,
      score: safeScore(item.score),
      idealAnswer:
        safeText(item.suggested_answer) ||
        "Use a clearer structure: explain the situation, your action, and the measurable result you created.",
    }));

    return {
      allMistakes,
      answeredCount,
      completedLabel,
      experience,
      performanceRatio,
      questionCards,
      reportTitle,
      retryState,
      roleMode,
      skillSignals,
      strongAnswerCount,
      needsWorkCount,
      timer,
    };
  }, [report]);

  const {
    allMistakes,
    answeredCount,
    completedLabel,
    experience,
    performanceRatio,
    questionCards,
    reportTitle,
    retryState,
    roleMode,
    skillSignals,
    strongAnswerCount,
    needsWorkCount,
    timer,
  } = reportView;
  const providerReadiness = useMemo(() => {
    if (!providerStatus?.providers || typeof providerStatus.providers !== "object") return [];

    return Object.entries(providerStatus.providers).map(([name, details]) => {
      const label = safeText(name).replace(/\b\w/g, (char) => char.toUpperCase());
      const configured = Boolean(details?.configured);
      const available = Boolean(details?.available);
      const connectionChecked = Boolean(details?.connection_checked);
      const model = safeText(details?.model);
      const detail = safeText(details?.detail);
      const status = connectionChecked
        ? available ? "Reachable" : configured ? "Needs attention" : "Not configured"
        : configured ? "Configured" : "Not configured";

      return {
        label,
        description: [status, model ? `model ${model}` : "", detail].filter(Boolean).join(" • "),
      };
    });
  }, [providerStatus]);

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

  return (
    <div className="report-page-shell">
      <div className="report-page-inner">
        <div className="report-topbar">
          <div>
            <span className="report-badge">AI interview report</span>
            <h1 className="report-page-title">{reportTitle} performance report</h1>
            <p className="report-page-subtitle">
              Analytical breakdown of this session, role-aligned coaching comments, and ideal answer guidance for the real interview.
            </p>
          </div>

          <div className="report-topbar-actions">
            <button className="report-secondary-button" onClick={() => navigate(-1)}>Back</button>
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
                  <span className="report-chip">{experience} difficulty</span>
                  <span className="report-chip">{timer}</span>
                </div>

                <div className="report-hero-grid">
                  <RadarChart items={skillSignals} />

                  <div className="report-side-panel-card">
                    <div className="report-side-panel-card__header">
                      <h2>Skill importance</h2>
                    </div>
                    <div className="report-skill-list">
                      {skillSignals.map((item) => (
                        <div key={item.label} className="report-skill-row">
                          <span>{item.label}</span>
                          <strong>{"*".repeat(item.importance)}</strong>
                        </div>
                      ))}
                    </div>
                  </div>
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
                  <MetricTile label="Strong answers" value={strongAnswerCount} tone="green" />
                  <MetricTile label="Need work" value={needsWorkCount} tone="orange" />
                  <MetricTile label="Coverage ratio" value={`${performanceRatio}%`} tone="blue" />
                </div>

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
                    <h2>Ideal answers for the real interview</h2>
                  </div>
                  <Brain size={18} />
                </div>

                <div className="report-question-list">
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
                          <p>{safeText(item.answer) || "No answer was captured for this question."}</p>
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
                              : <div>- The answer needs stronger positive signals in future attempts.</div>}
                          </div>
                        </div>

                        <div className="report-mini-panel report-mini-panel-warn">
                          <span>Mistakes / gaps</span>
                          <div className="report-bullet-list">
                            {(item.gaps || []).length
                              ? (item.gaps || []).map((entry) => <div key={entry}>- {entry}</div>)
                              : <div>- No clear gap tags were returned for this question.</div>}
                          </div>
                        </div>
                      </div>

                      <div className="report-ideal-answer-card">
                        <div className="report-ideal-answer-card__header">
                          <Target size={16} />
                          <span>Best answer to give in a real interview</span>
                        </div>
                        <p>{item.idealAnswer}</p>
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
                    <strong>{safeText(report.context?.selected_options) || "core"}</strong>
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
                      if (retryState) {
                        navigate("/instructions", { state: retryState });
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
                    <span className="report-card-eyebrow">Providers</span>
                    <h3>AI systems used</h3>
                  </div>
                </div>
                <div className="report-bullet-list">
                  <div>- Generation: {formatProviderName(report.providers?.generation_provider, "generation") || "Pending"}</div>
                  <div>- Evaluation: {formatProviderName(report.providers?.evaluation_provider, "evaluation") || "Pending"}</div>
                  <div>- Summary: {formatProviderName(report.providers?.summary_provider, "summary") || "Pending"}</div>
                  {providerReadiness.map((item) => <div key={item.label}>- {item.label}: {item.description}</div>)}
                  <div>- Mode: {safeText(report.context?.selected_mode) || "Interview"}</div>
                  <div>- Timer: {timer}</div>
                  <div>- Practice type: {safeText(report.context?.practice_type) || "practice"}</div>
                  <div>- Status: {report.ended_early ? "Ended early" : "Completed"}</div>
                  <div>- Duration tag: <Clock3 size={13} style={{ verticalAlign: "text-bottom" }} /> {timer}</div>
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
