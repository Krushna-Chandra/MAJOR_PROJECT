import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  ArrowUpRight,
  Brain,
  Briefcase,
  CheckCircle2,
  Gauge,
  Lightbulb,
  LineChart as LineChartIcon,
  MessagesSquare,
  Sparkles,
  Target,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import "../App.css";
import { normalizeReport, safeErrorText, safeScore, safeText } from "../utils/interviewReport";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

const CHART_WIDTH = 560;
const LINE_CHART_HEIGHT = 240;
const BAR_CHART_HEIGHT = 240;
const RESUME_ANALYZER_RESULT_KEY = "resumeAnalyzerResult";

const CATEGORY_DEFINITIONS = [
  { key: "technical", label: "Technical", shortLabel: "Tech", color: "#2563eb", softColor: "rgba(37, 99, 235, 0.12)" },
  { key: "behavioral", label: "Behavioral / HR", shortLabel: "HR", color: "#f97316", softColor: "rgba(249, 115, 22, 0.12)" },
  { key: "mock", label: "Mock", shortLabel: "Mock", color: "#7c3aed", softColor: "rgba(124, 58, 237, 0.12)" },
  { key: "resume", label: "Resume", shortLabel: "Resume", color: "#059669", softColor: "rgba(5, 150, 105, 0.12)" },
  { key: "aptitude", label: "Aptitude / Coding", shortLabel: "Code", color: "#0891b2", softColor: "rgba(8, 145, 178, 0.12)" },
];

function clampNumber(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function getPrimaryTrack(report) {
  const categorySource = safeText(report?.context?.category || report?.context?.selected_mode || report?.context?.practice_type || "").toLowerCase();

  if (categorySource.includes("behav") || categorySource.includes("hr")) return "hr";
  if (categorySource.includes("resume") || categorySource.includes("library")) return "mock";
  return "technical";
}

function inferSelectedMode(report) {
  return report?.context?.primary_language ? "language" : "role";
}

function getResumeAnalyzerActivity() {
  try {
    const payload = JSON.parse(sessionStorage.getItem(RESUME_ANALYZER_RESULT_KEY) || "null");
    if (payload?.resumeDataUrl || payload?.fileName || payload?.result) {
      return {
        count: 1,
        fileName: safeText(payload.fileName || "Resume analyzed"),
        createdAt: safeText(payload.analyzedAt || payload.createdAt),
      };
    }
  } catch {}

  return { count: 0, fileName: "", createdAt: "" };
}

function classifyReportCategory(report) {
  const context = report?.context || {};
  const source = safeText([
    context.category,
    context.selected_mode,
    context.practice_type,
    context.job_role,
    context.primary_language,
    context.config_mode,
  ]).toLowerCase();

  if (source.includes("resume")) return "resume";
  if (source.includes("aptitude") || source.includes("coding") || source.includes("code") || source.includes("challenge")) return "aptitude";
  if (source.includes("mock")) return "mock";
  if (source.includes("behav") || source.includes("hr")) return "behavioral";
  return "technical";
}

function buildCategoryStats(reports = [], resumeAnalyzerActivity = { count: 0 }) {
  const statsMap = CATEGORY_DEFINITIONS.reduce((accumulator, category) => {
    accumulator[category.key] = {
      ...category,
      average: 0,
      best: 0,
      count: 0,
      scores: [],
      total: 0,
    };
    return accumulator;
  }, {});

  reports.forEach((report) => {
    const key = classifyReportCategory(report);
    const bucket = statsMap[key] || statsMap.technical;
    const score = safeScore(report.overall_score);
    bucket.count += 1;
    bucket.total += score;
    bucket.best = Math.max(bucket.best, score);
    bucket.scores.push(score);
  });

  if (resumeAnalyzerActivity.count && !statsMap.resume.count) {
    statsMap.resume.count = resumeAnalyzerActivity.count;
  }

  return CATEGORY_DEFINITIONS.map((category) => {
    const bucket = statsMap[category.key];
    return {
      ...bucket,
      average: bucket.scores.length ? Math.round(bucket.total / bucket.scores.length) : 0,
    };
  });
}

function getConsistencyModel(scores = []) {
  if (scores.length < 2) {
    return {
      label: "Need more data",
      score: 0,
      summary: "Complete two or more sessions to measure score stability.",
    };
  }

  const average = scores.reduce((sum, score) => sum + score, 0) / scores.length;
  const variance = scores.reduce((sum, score) => sum + Math.pow(score - average, 2), 0) / scores.length;
  const deviation = Math.sqrt(variance);
  const score = clampNumber(Math.round(100 - deviation * 2), 0, 100);

  return {
    label: score >= 75 ? "Stable" : score >= 50 ? "Variable" : "Volatile",
    score,
    summary: score >= 75
      ? "Your scores are staying in a reliable range."
      : "Your scores are moving noticeably between sessions.",
  };
}

function countTopItems(items = [], limit = 3) {
  const counts = items.reduce((accumulator, item) => {
    const key = safeText(item).toLowerCase();
    if (!key) return accumulator;
    const existing = accumulator.get(key) || { label: safeText(item), value: 0 };
    existing.value += 1;
    accumulator.set(key, existing);
    return accumulator;
  }, new Map());

  return Array.from(counts.values())
    .sort((left, right) => right.value - left.value)
    .slice(0, limit);
}

function buildAdviceFromGap(gap, role, focus) {
  const lowerGap = safeText(gap).toLowerCase();
  const scopedFocus = safeText(focus || role || "your role");

  if (lowerGap.includes("communication") || lowerGap.includes("clarity")) {
    return `Practice concise spoken answers for ${scopedFocus} using a 3-part structure: context, action, and measurable result.`;
  }
  if (lowerGap.includes("confidence") || lowerGap.includes("hesitation")) {
    return `Run one timed mock interview for ${scopedFocus} and repeat your answer openings until they feel natural under pressure.`;
  }
  if (lowerGap.includes("system") || lowerGap.includes("design") || lowerGap.includes("architecture")) {
    return `Schedule a focused design round on ${scopedFocus} and explain tradeoffs, scale limits, and API boundaries out loud.`;
  }
  if (lowerGap.includes("algorithm") || lowerGap.includes("data structure") || lowerGap.includes("problem")) {
    return `Do a technical round centered on ${scopedFocus} and narrate your approach before giving the final solution.`;
  }
  if (lowerGap.includes("behavior") || lowerGap.includes("star") || lowerGap.includes("leadership") || lowerGap.includes("team")) {
    return `Prepare 3 STAR stories tailored to ${scopedFocus} so you can answer leadership and teamwork prompts with specific outcomes.`;
  }
  return `Review the repeated gap around "${safeText(gap)}" and practice one interview focused on ${scopedFocus} with stronger examples and clearer reasoning.`;
}

function buildRecommendationModel(reports = [], topicPerformance = []) {
  const latestReport = reports[0] || null;
  if (!latestReport) {
    return {
      coachSummary: "Complete one interview and the AI coach will generate role-aware improvement guidance, next-step drills, and a recommended interview plan.",
      focusAreas: [],
      nextInterview: null,
      plan: [],
      strengths: [],
    };
  }

  const role = safeText(latestReport.context?.job_role || latestReport.context?.primary_language || latestReport.context?.category || "General");
  const selectedOptions = Array.isArray(latestReport.context?.selected_options) ? latestReport.context.selected_options : [];
  const aggregateGaps = reports.flatMap((report) => [
    ...(report.improvement_areas || []),
    ...((report.evaluations || []).flatMap((item) => item.gaps || [])),
    ...((report.evaluations || []).flatMap((item) => item.missed_points || [])),
  ]);
  const aggregateStrengths = reports.flatMap((report) => [
    ...(report.top_strengths || []),
    ...((report.evaluations || []).flatMap((item) => item.strengths || [])),
    ...((report.evaluations || []).flatMap((item) => item.matched_points || [])),
  ]);

  const topGaps = countTopItems(aggregateGaps, 3);
  const topStrengths = countTopItems(aggregateStrengths, 3);
  const weakestTopic = [...topicPerformance].sort((left, right) => left.value - right.value)[0];
  const primaryFocus = topGaps[0]?.label || weakestTopic?.topic || selectedOptions[0] || role;
  const nextTrack = getPrimaryTrack(latestReport);
  const nextMode = inferSelectedMode(latestReport);
  const nextOption = nextMode === "language"
    ? safeText(latestReport.context?.primary_language || selectedOptions[0] || weakestTopic?.topic || role)
    : safeText(latestReport.context?.job_role || selectedOptions[0] || weakestTopic?.topic || role);
  const nextInterviewLabel = nextTrack === "hr"
    ? "Behavioral recovery round"
    : nextTrack === "mock"
      ? "Mock consolidation round"
      : "Technical recovery round";

  const plan = [
    {
      title: "Primary gap",
      description: topGaps[0]
        ? buildAdviceFromGap(topGaps[0].label, role, primaryFocus)
        : `Keep sharpening ${role} fundamentals and answer structure with one additional focused session this week.`,
    },
    {
      title: "Best skill-builder",
      description: weakestTopic
        ? `Your lowest-performing track is ${weakestTopic.topic} at ${weakestTopic.value}%. Make that the next focused interview topic before broadening out again.`
        : `Use the next interview to go deeper on ${primaryFocus} so the dashboard has enough signal to personalize your coaching further.`,
    },
    {
      title: "Retention move",
      description: topStrengths[0]
        ? `Keep ${topStrengths[0].label} as a strength by opening your next answer with the same level of clarity and evidence.`
        : `Preserve your strongest habits by keeping answers structured, specific, and outcome-oriented.`,
    },
  ];

  return {
    coachSummary: `Based on your recent ${role} interviews, the AI coach sees the biggest opportunity in ${primaryFocus}. The next round should be narrower and more intentional so you improve faster instead of repeating broad practice.`,
    focusAreas: topGaps,
    nextInterview: {
      category: nextTrack,
      description: `Recommended next session: a ${nextInterviewLabel.toLowerCase()} focused on ${nextOption}.`,
      label: nextInterviewLabel,
      mode: nextMode,
      option: nextOption,
      practiceType: topGaps.length ? "interview" : "practice",
      trackLabel: nextTrack === "hr" ? "HR / Behavioral" : nextTrack === "mock" ? "Mock" : "Technical",
    },
    plan,
    strengths: topStrengths,
  };
}

function getDashboardWelcomeState() {
  try {
    const storageKey = "dashboardHasVisited";
    const hasVisited = localStorage.getItem(storageKey) === "true";
    if (!hasVisited) {
      localStorage.setItem(storageKey, "true");
      return "Welcome";
    }
    return "Welcome back";
  } catch {
    return "Welcome";
  }
}

function getUserDisplayName() {
  try {
    const storedUser = JSON.parse(localStorage.getItem("user") || "null");
    if (storedUser?.first_name && storedUser?.last_name) {
      return `${storedUser.first_name} ${storedUser.last_name}`;
    }
    if (storedUser?.first_name) return storedUser.first_name;
    if (storedUser?.email) return storedUser.email.split("@")[0];
  } catch {}
  return "there";
}

function getStoredUserProfile() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
}

function getProfileLocationLabel(user) {
  const directLocation = safeText(
    user?.country ||
    user?.location ||
    user?.city ||
    user?.state
  );

  if (directLocation) return directLocation;

  try {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "";
    if (timeZone.includes("Kolkata") || timeZone.includes("Calcutta")) return "India";
  } catch {}

  return "Global";
}

function formatChange(value, suffix = "%") {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value)}${suffix}`;
}

function computeTrendDelta(values) {
  if (!Array.isArray(values) || values.length < 2) return 0;
  const latestWindow = values.slice(-3);
  const previousWindow = values.slice(-6, -3);
  const latestAverage = latestWindow.reduce((sum, value) => sum + value, 0) / latestWindow.length;
  const previousAverage = previousWindow.length
    ? previousWindow.reduce((sum, value) => sum + value, 0) / previousWindow.length
    : values[0];

  if (!Number.isFinite(previousAverage) || previousAverage === 0) {
    return Math.round(latestAverage);
  }

  return Math.round(((latestAverage - previousAverage) / previousAverage) * 100);
}

function buildSmoothPath(points) {
  if (points.length < 2) return "";

  return points.reduce((path, point, index, allPoints) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`;
    }

    const previous = allPoints[index - 1];
    const controlX = (previous.x + point.x) / 2;
    return `${path} C ${controlX} ${previous.y}, ${controlX} ${point.y}, ${point.x} ${point.y}`;
  }, "");
}

function createLineChartModel(data, width, height) {
  const padding = { top: 20, right: 18, bottom: 34, left: 18 };
  const max = Math.max(...data, 0);
  const min = Math.min(...data, max);
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const range = Math.max(max - min, 1);

  const points = data.map((value, index) => {
    const x = padding.left + (index / Math.max(data.length - 1, 1)) * chartWidth;
    const y = padding.top + ((max - value) / range) * chartHeight;
    return { x, y, value, label: `S${index + 1}` };
  });

  const linePath = buildSmoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${height - padding.bottom} L ${points[0].x} ${height - padding.bottom} Z`;

  const gridLines = Array.from({ length: 4 }, (_, index) => {
    const y = padding.top + (index / 3) * chartHeight;
    const label = Math.round(max - (index / 3) * (max - min || max));
    return { y, label };
  });

  return { areaPath, gridLines, linePath, points };
}

function LineChart({ data = [] }) {
  const [activeIndex, setActiveIndex] = useState(data.length - 1);

  useEffect(() => {
    setActiveIndex(data.length - 1);
  }, [data]);

  if (!data.length) return null;

  const { areaPath, gridLines, linePath, points } = createLineChartModel(data, CHART_WIDTH, LINE_CHART_HEIGHT);
  const activePoint = points[clampNumber(activeIndex, 0, points.length - 1)];

  return (
    <div className="dashboard-visual dashboard-line-chart">
      <svg viewBox={`0 0 ${CHART_WIDTH} ${LINE_CHART_HEIGHT}`} preserveAspectRatio="none" className="dashboard-chart-svg">
        <defs>
          <linearGradient id="dashboardLineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#6366f1" />
          </linearGradient>
          <linearGradient id="dashboardLineArea" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="rgba(99, 102, 241, 0.28)" />
            <stop offset="100%" stopColor="rgba(99, 102, 241, 0.02)" />
          </linearGradient>
        </defs>

        {gridLines.map((line, index) => (
          <g key={`line-${index}`}>
            <line
              x1="18"
              x2={CHART_WIDTH - 18}
              y1={line.y}
              y2={line.y}
              className="dashboard-chart-grid-line"
            />
            <text x={CHART_WIDTH - 12} y={line.y - 6} className="dashboard-chart-axis-label">
              {line.label}
            </text>
          </g>
        ))}

        <path d={areaPath} fill="url(#dashboardLineArea)" />
        <path d={linePath} fill="none" stroke="url(#dashboardLineGradient)" strokeWidth="4" strokeLinecap="round" />

        {points.map((point, index) => (
          <g key={point.label} onMouseEnter={() => setActiveIndex(index)} onFocus={() => setActiveIndex(index)}>
            <circle cx={point.x} cy={point.y} r={index === activeIndex ? 7 : 4.5} className="dashboard-chart-dot-glow" />
            <circle cx={point.x} cy={point.y} r={index === activeIndex ? 5 : 3.5} className="dashboard-chart-dot" />
            <text x={point.x} y={LINE_CHART_HEIGHT - 10} textAnchor="middle" className="dashboard-chart-axis-label">
              {point.label}
            </text>
          </g>
        ))}
      </svg>

      {activePoint ? (
        <div
          className="dashboard-chart-tooltip dashboard-chart-tooltip-floating"
          style={{
            left: `${(activePoint.x / CHART_WIDTH) * 100}%`,
            top: `${(activePoint.y / LINE_CHART_HEIGHT) * 100}%`,
          }}
        >
          <span>{activePoint.label}</span>
          <strong>{activePoint.value}%</strong>
        </div>
      ) : null}
    </div>
  );
}

function BarChart({ data = [] }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
  }, [data]);

  if (!data.length) return null;

  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const padding = { top: 18, right: 12, bottom: 54, left: 12 };
  const chartHeight = BAR_CHART_HEIGHT - padding.top - padding.bottom;
  const chartWidth = CHART_WIDTH - padding.left - padding.right;
  const gap = 18;
  const barWidth = (chartWidth - gap * (data.length - 1)) / Math.max(data.length, 1);
  const activeBar = data[clampNumber(activeIndex, 0, data.length - 1)];

  return (
    <div className="dashboard-visual dashboard-bar-chart">
      <svg viewBox={`0 0 ${CHART_WIDTH} ${BAR_CHART_HEIGHT}`} preserveAspectRatio="none" className="dashboard-chart-svg">
        <defs>
          <linearGradient id="dashboardBarGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>
        </defs>

        {data.map((item, index) => {
          const barHeight = (item.value / maxValue) * chartHeight;
          const x = padding.left + index * (barWidth + gap);
          const y = padding.top + (chartHeight - barHeight);
          const isActive = index === activeIndex;

          return (
            <g key={`${item.topic}-${index}`} onMouseEnter={() => setActiveIndex(index)} onFocus={() => setActiveIndex(index)}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                rx="18"
                className={isActive ? "dashboard-bar dashboard-bar-active" : "dashboard-bar"}
              />
              <text x={x + barWidth / 2} y={BAR_CHART_HEIGHT - 16} textAnchor="middle" className="dashboard-chart-axis-label">
                {safeText(item.topic).slice(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>

      {activeBar ? (
        <div className="dashboard-bar-summary">
          <span>{safeText(activeBar.topic)}</span>
          <strong>{activeBar.value}%</strong>
        </div>
      ) : null}
    </div>
  );
}

function DistributionMeter({ data = [], total = 0, score = 0 }) {
  const visibleData = data.filter((item) => item.count > 0);
  let cursor = 0;
  const segments = visibleData.map((item) => {
    const start = cursor;
    const end = cursor + (item.count / Math.max(total, 1)) * 100;
    cursor = end;
    return `${item.color} ${start}% ${end}%`;
  });
  const meterBackground = segments.length
    ? `conic-gradient(${segments.join(", ")}, #e2e8f0 ${cursor}% 100%)`
    : "conic-gradient(#e2e8f0 0% 100%)";

  return (
    <div className="dashboard-distribution">
      <div className="dashboard-distribution-meter" style={{ background: meterBackground }}>
        <div className="dashboard-distribution-core">
          <span>Readiness</span>
          <strong>{score}%</strong>
        </div>
      </div>

      <div className="dashboard-distribution-list">
        {data.map((item) => (
          <div key={item.key} className="dashboard-distribution-row">
            <span className="dashboard-distribution-dot" style={{ background: item.color }} />
            <div>
              <strong>{item.label}</strong>
              <span>{item.count} tracked</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetricCard({ eyebrow, title, value, trend, meta, icon: Icon, tone }) {
  const positive = trend >= 0;
  return (
    <article className={`saas-stat-card saas-stat-card-${tone}`}>
      <div className="saas-stat-card__glow" />
      <div className="saas-stat-card__header">
        <div>
          <span className="saas-eyebrow">{eyebrow}</span>
          <h3 className="saas-stat-card__title">{title}</h3>
        </div>
        <div className="saas-stat-card__icon">
          <Icon size={18} />
        </div>
      </div>

      <div className="saas-stat-card__value-row">
        <div className="saas-stat-card__value">{value}</div>
        <div className={`saas-stat-card__trend ${positive ? "is-positive" : "is-negative"}`}>
          {positive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {formatChange(trend)}
        </div>
      </div>

      <div className="saas-stat-card__footer">
        <span>{meta}</span>
        <span className="saas-stat-card__footer-pill">Live sync</span>
      </div>
    </article>
  );
}

function DashboardPage() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState({});
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = localStorage.getItem("token");

      if (!token) {
        navigate("/auth", { replace: true });
        return;
      }

      const response = await axios.get(`${API_BASE_URL}/interview-reports`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      const normalizedReports = Array.isArray(response.data?.reports)
        ? response.data.reports.map((item) => normalizeReport(item))
        : [];

      const scores = normalizedReports.map((item) => safeScore(item.overall_score));
      const topicMap = new Map();

      normalizedReports.forEach((item) => {
        const topic = safeText(item.context?.job_role || item.context?.primary_language || item.context?.category || "General");
        const current = topicMap.get(topic) || [];
        current.push(safeScore(item.overall_score));
        topicMap.set(topic, current);
      });

      const topicPerformance = Array.from(topicMap.entries())
        .slice(0, 6)
        .map(([topic, values]) => ({
          topic,
          value: Math.round(values.reduce((sum, score) => sum + score, 0) / Math.max(values.length, 1)),
        }));

      setReports(normalizedReports);
      setMetrics({
        totalInterviews: normalizedReports.length,
        avgScore: scores.length ? Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length) : 0,
        bestScore: scores.length ? Math.max(...scores) : 0,
        accuracyTrend: scores.length ? scores.slice(0, 9).reverse() : [],
        topicPerformance,
      });
    } catch (requestError) {
      const status = requestError.response?.status;
      if (status === 401 || status === 403) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        navigate("/auth", { replace: true });
        return;
      }

      setError(
        safeErrorText(
          requestError.response?.data?.detail ||
          requestError.response?.data ||
          requestError.message ||
          "Failed to load dashboard metrics."
        )
      );
      setMetrics({
        totalInterviews: 0,
        avgScore: 0,
        bestScore: 0,
        accuracyTrend: [],
        topicPerformance: [],
      });
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  const dashboardView = useMemo(() => {
    const accuracyTrend = metrics.accuracyTrend || [];
    const topicPerformance = metrics.topicPerformance || [];
    const resumeAnalyzerActivity = getResumeAnalyzerActivity();
    const categoryStats = buildCategoryStats(reports, resumeAnalyzerActivity);
    const storedUser = getStoredUserProfile();
    const userName = getUserDisplayName();
    const greeting = getDashboardWelcomeState();
    const latestReport = reports[0] || null;
    const latestScore = latestReport ? safeScore(latestReport.overall_score) : 0;
    const previousScore = reports[1] ? safeScore(reports[1].overall_score) : latestScore;
    const accuracyChange = computeTrendDelta(accuracyTrend);
    const bestVsAverage = Math.max(0, (metrics.bestScore || 0) - (metrics.avgScore || 0));
    const completionTrend = accuracyTrend.length > 1 ? Math.round(((accuracyTrend.length - 1) / accuracyTrend.length) * 100) : 0;
    const improvementRate = Math.min(100, Math.round((metrics.avgScore || 0) * 1.05));
    const improvementTrend = latestScore - previousScore;
    const totalMix = categoryStats.reduce((sum, item) => sum + item.count, 0);
    const categoryPerformance = categoryStats
      .filter((item) => item.scores.length)
      .map((item) => ({ ...item, topic: item.shortLabel, value: item.average }));
    const bestCategory = [...categoryStats].sort((left, right) => right.average - left.average || right.count - left.count)[0];
    const weakestCategory = [...categoryStats]
      .filter((item) => item.scores.length)
      .sort((left, right) => left.average - right.average)[0];
    const consistency = getConsistencyModel(accuracyTrend);
    const recentImprovement = accuracyTrend.length > 1
      ? accuracyTrend[accuracyTrend.length - 1] - accuracyTrend[accuracyTrend.length - 2]
      : 0;
    const profileSummary = {
      avatar: safeText(storedUser?.profile_image),
      email: safeText(storedUser?.email),
      initials: userName?.[0]?.toUpperCase() || "U",
      interviews: metrics.totalInterviews || 0,
      location: getProfileLocationLabel(storedUser),
      scoreOutOfTen: ((metrics.avgScore || 0) / 10).toFixed(1),
      status: (metrics.totalInterviews || 0) > 0 ? "Active" : "New",
      subtitle: (metrics.totalInterviews || 0) > 0 ? "Interview-ready candidate" : "Getting started",
    };
    const recommendation = buildRecommendationModel(reports, topicPerformance);

    const statCards = [
      {
        eyebrow: "Interview volume",
        title: "Completed interviews",
        value: `${metrics.totalInterviews || 0}`,
        trend: completionTrend,
        meta: "Sessions tracked across your workspace",
        icon: Briefcase,
        tone: "sky",
      },
      {
        eyebrow: "Quality signal",
        title: "Average score",
        value: `${metrics.avgScore || 0}%`,
        trend: accuracyChange,
        meta: "Rolling average across saved reports",
        icon: Gauge,
        tone: "indigo",
      },
      {
        eyebrow: "Peak outcome",
        title: "Best score",
        value: `${metrics.bestScore || 0}%`,
        trend: bestVsAverage,
        meta: "Headroom above your current average",
        icon: Target,
        tone: "violet",
      },
      {
        eyebrow: "Momentum",
        title: "Improvement rate",
        value: `${improvementRate}%`,
        trend: improvementTrend,
        meta: "Projected from recent session movement",
        icon: Sparkles,
        tone: "cyan",
      },
    ];

    const recentReports = reports.slice(0, 6).map((report, index) => {
      const score = safeScore(report.overall_score);
      const sessionLabel = safeText(report.context?.job_role || report.context?.primary_language || report.context?.category || "Interview");
      const modeLabel = safeText(report.context?.selected_mode || report.context?.category || "Interview");
      const duration = safeText(report.context?.interview_mode_time || report.context?.time_mode_interval || "10 min");
      const summary = safeText(report.summary) || "Review generated. Inspect the detailed feedback for strengths and focus areas.";
      const scoreTone = score >= 75 ? "success" : score >= 50 ? "warning" : "danger";

      return {
        id: report.session_id || `${sessionLabel}-${index}`,
        modeLabel,
        score,
        scoreTone,
        sessionLabel,
        summary,
        duration,
        report,
      };
    });
    const recentHeroReports = recentReports.slice(0, 3);

    return {
      accuracyTrend,
      greeting,
      bestCategory,
      categoryPerformance,
      categoryStats,
      consistency,
      recentHeroReports,
      latestReport,
      profileSummary,
      recommendation,
      recentImprovement,
      resumeAnalyzerActivity,
      statCards,
      totalMix,
      userName,
      weakestCategory,
    };
  }, [metrics, reports]);

  const {
    accuracyTrend,
    greeting,
    bestCategory,
    categoryPerformance,
    categoryStats,
    consistency,
    recentHeroReports,
    latestReport,
    profileSummary,
    recommendation,
    recentImprovement,
    resumeAnalyzerActivity,
    statCards,
    totalMix,
    userName,
    weakestCategory,
  } = dashboardView;

  const latestSnapshotSummary = latestReport
    ? safeText(latestReport.summary) || "Your latest interview report is ready to review."
    : "Finish your first interview and the latest snapshot will surface here automatically.";

  return (
    <>
      <div className="page-content reveal dashboard-shell">
        <section className="dashboard-hero-card">
          <div className="dashboard-hero-card__content">
            <span className="dashboard-badge">{greeting}</span>

            <div className="dashboard-profile-hero-card">
              <div className="dashboard-profile-hero-card__top">
                <div className="dashboard-profile-hero-avatar">
                  {profileSummary.avatar ? (
                    <img src={profileSummary.avatar} alt={userName} />
                  ) : (
                    <span>{profileSummary.initials}</span>
                  )}
                </div>

                <div className="dashboard-profile-hero-meta">
                  <span className="dashboard-profile-hero-label">Profile</span>
                  <h2>{userName}</h2>
                  <p>{profileSummary.subtitle}</p>

                  <div className="dashboard-profile-hero-tags">
                    <span>{profileSummary.email || "No email available"}</span>
                    <span>{profileSummary.location}</span>
                    <span>{profileSummary.interviews} interviews</span>
                  </div>
                </div>
              </div>

              <div className="dashboard-profile-hero-stats">
                <div className="dashboard-profile-hero-stat">
                  <span>Completed</span>
                  <strong>{profileSummary.interviews}</strong>
                </div>
                <div className="dashboard-profile-hero-stat">
                  <span>Average score</span>
                  <strong>{profileSummary.scoreOutOfTen}/10</strong>
                </div>
                <div className="dashboard-profile-hero-stat">
                  <span>Status</span>
                  <strong className="dashboard-profile-hero-status">
                    <span className="dashboard-profile-hero-status__dot" aria-hidden="true" />
                    {profileSummary.status}
                  </strong>
                </div>
              </div>
            </div>
          </div>
          <div className="dashboard-hero-card__aside">
            <div className="dashboard-hero-history">
              <div className="dashboard-hero-history__header">
                <span className="dashboard-panel__eyebrow">Recent history</span>
                <h3>Recent interviews</h3>
              </div>

              {recentHeroReports.length ? (
                <div className="dashboard-hero-history__list">
                  {recentHeroReports.map((row) => (
                    <button
                      key={`hero-${row.id}`}
                      type="button"
                      className="dashboard-hero-history__item"
                      onClick={() => navigate(`/reports/${row.report.session_id}`, { state: { report: row.report } })}
                    >
                      <div className="dashboard-hero-history__meta">
                        <span className="dashboard-chip dashboard-chip-primary">{row.modeLabel}</span>
                        <strong>{row.sessionLabel}</strong>
                      </div>
                      <div className="dashboard-hero-history__score">
                        <span className={`dashboard-score-pill dashboard-score-pill-${row.scoreTone}`}>{row.score}%</span>
                      </div>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="dashboard-hero-history__empty">
                  Complete an interview and your recent history will appear here.
                </div>
              )}
            </div>
          </div>
        </section>

        {error ? (
          <div className="dashboard-alert dashboard-alert-error">{error}</div>
        ) : null}

        {loading ? (
          <div className="dashboard-loading-card">
            <div className="dashboard-loading-shimmer" />
            <p>Loading your dashboard analytics...</p>
          </div>
        ) : (
          <>
            <section className="dashboard-stats-grid">
              {statCards.map((card) => (
                <MetricCard key={card.title} {...card} />
              ))}
            </section>

            <section className="dashboard-distribution-grid">
              <article className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <div>
                    <span className="dashboard-panel__eyebrow">Data distribution</span>
                    <h2>Category coverage</h2>
                  </div>
                  <div className="dashboard-panel__meta">
                    <Gauge size={16} />
                    {totalMix} tracked
                  </div>
                </div>
                <DistributionMeter data={categoryStats} total={totalMix} score={metrics.avgScore || 0} />
              </article>
            </section>

            <section className="dashboard-performance-grid">
              <article className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <div>
                    <span className="dashboard-panel__eyebrow">Trend overview</span>
                    <h2>Performance trajectory</h2>
                  </div>
                  <div className="dashboard-panel__meta">
                    <LineChartIcon size={16} />
                    Latest {accuracyTrend.length || 0} sessions
                  </div>
                </div>
                {accuracyTrend.length ? (
                  <LineChart data={accuracyTrend} />
                ) : (
                  <div className="dashboard-empty-state">No completed interviews yet. Your trendline will appear after your first scored report.</div>
                )}
              </article>

              <article className="dashboard-panel dashboard-panel-large">
                <div className="dashboard-panel__header">
                  <div>
                    <span className="dashboard-panel__eyebrow">Best category</span>
                    <h2>Where you perform best</h2>
                  </div>
                  <div className="dashboard-panel__meta dashboard-panel__meta-success">Updated now</div>
                </div>

                {categoryPerformance.length ? (
                  <BarChart data={categoryPerformance} />
                ) : (
                  <div className="dashboard-empty-state">Category scores will appear after your first evaluated interview.</div>
                )}
              </article>
            </section>

            <section className="dashboard-insights-grid">
              <article className="dashboard-panel dashboard-insight-panel">
                <div className="dashboard-panel__header">
                  <div>
                    <span className="dashboard-panel__eyebrow">Performance signals</span>
                    <h2>Quick insights</h2>
                  </div>
                  <div className="dashboard-panel__headline-value">
                    {bestCategory?.average || 0}%
                  </div>
                </div>

                <div className="dashboard-insight-stack">
                  <div className="dashboard-insight-card">
                    <span>Strongest category</span>
                    <strong>{bestCategory?.average ? bestCategory.label : "Waiting for data"}</strong>
                    <p>{bestCategory?.average ? `${bestCategory.average}% average across ${bestCategory.count} tracked session${bestCategory.count === 1 ? "" : "s"}.` : "Complete one evaluated session to calculate this."}</p>
                  </div>
                  <div className="dashboard-insight-card">
                    <span>Weakest category</span>
                    <strong>{weakestCategory ? weakestCategory.label : "Need more data"}</strong>
                    <p>{weakestCategory ? `${weakestCategory.average}% average. Keep the next practice round focused here.` : "The dashboard needs at least one scored category."}</p>
                  </div>
                  <div className="dashboard-insight-card">
                    <span>Consistency</span>
                    <strong>{consistency.label}</strong>
                    <p>{consistency.summary}</p>
                  </div>
                  <div className="dashboard-insight-card">
                    <span>Recent movement</span>
                    <strong>{formatChange(recentImprovement)}</strong>
                    <p>Latest session compared with the previous scored session.</p>
                  </div>
                </div>
              </article>
            </section>

            <section className="dashboard-category-grid">
              {categoryStats.map((category) => (
                <article key={category.key} className="dashboard-category-card" style={{ "--category-color": category.color, "--category-soft": category.softColor }}>
                  <div className="dashboard-category-card__top">
                    <span>{category.label}</span>
                    <strong>{category.count}</strong>
                  </div>
                  <div className="dashboard-category-card__meter">
                    <div style={{ width: `${category.average || (category.count ? 18 : 0)}%` }} />
                  </div>
                  <p>{category.average ? `${category.average}% average score` : category.count ? "Activity detected" : "No activity yet"}</p>
                </article>
              ))}
            </section>

            <section className="dashboard-results-grid">
              <article className="dashboard-panel dashboard-panel-large">
                <div className="dashboard-panel__header">
                  <div>
                    <span className="dashboard-panel__eyebrow">AI coach</span>
                    <h2>Performance recommendations</h2>
                  </div>
                  <div className="dashboard-panel__meta">
                    <Brain size={16} />
                    Adaptive guidance
                  </div>
                </div>

                <p className="dashboard-section-copy">{recommendation.coachSummary}</p>

                <div className="dashboard-coach-grid">
                  <div className="dashboard-coach-card">
                    <div className="dashboard-coach-card__icon">
                      <Lightbulb size={18} />
                    </div>
                    <div className="dashboard-coach-card__body">
                      <span>Focus areas</span>
                      {recommendation.focusAreas.length ? (
                        recommendation.focusAreas.map((item) => (
                          <div key={item.label} className="dashboard-coach-pill">
                            <strong>{item.label}</strong>
                            <span>{item.value} repeated signals</span>
                          </div>
                        ))
                      ) : (
                        <div className="dashboard-coach-empty">More reports will unlock repeated-gap detection.</div>
                      )}
                    </div>
                  </div>

                  <div className="dashboard-coach-card">
                    <div className="dashboard-coach-card__icon">
                      <CheckCircle2 size={18} />
                    </div>
                    <div className="dashboard-coach-card__body">
                      <span>Stable strengths</span>
                      {recommendation.strengths.length ? (
                        recommendation.strengths.map((item) => (
                          <div key={item.label} className="dashboard-coach-pill dashboard-coach-pill-success">
                            <strong>{item.label}</strong>
                            <span>{item.value} positive mentions</span>
                          </div>
                        ))
                      ) : (
                        <div className="dashboard-coach-empty">Strength trends will appear after more evaluated answers.</div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="dashboard-plan-list">
                  {recommendation.plan.map((item) => (
                    <div key={item.title} className="dashboard-plan-item">
                      <div className="dashboard-plan-item__bullet" />
                      <div>
                        <div className="dashboard-plan-item__title">{item.title}</div>
                        <div className="dashboard-plan-item__copy">{item.description}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <div className="dashboard-side-stack">
                <article className="dashboard-panel dashboard-highlight-panel">
                  <div className="dashboard-panel__header">
                    <div>
                      <span className="dashboard-panel__eyebrow">Latest snapshot</span>
                      <h2>Most recent round</h2>
                    </div>
                  </div>

                  <div className="dashboard-highlight-card">
                    <div className="dashboard-highlight-card__label">
                      <Brain size={14} />
                      {latestReport ? safeText(latestReport.context?.selected_mode || latestReport.context?.category || "Interview") : "Waiting for data"}
                    </div>
                    <h3>{latestReport ? safeText(latestReport.context?.job_role || latestReport.context?.primary_language || "General interview") : "No recent session yet"}</h3>
                    <p>{latestSnapshotSummary}</p>
                    <div className="dashboard-highlight-card__footer">
                      <span>{latestReport ? `${safeScore(latestReport.overall_score)}% score` : "Run a session to populate this card"}</span>
                      {latestReport ? <ArrowUpRight size={15} /> : null}
                    </div>
                  </div>
                </article>

                <article className="dashboard-panel dashboard-highlight-panel">
                  <div className="dashboard-panel__header">
                    <div>
                      <span className="dashboard-panel__eyebrow">Resume activity</span>
                      <h2>Resume signal</h2>
                    </div>
                  </div>

                  <div className="dashboard-highlight-card">
                    <div className="dashboard-highlight-card__label">
                      <MessagesSquare size={14} />
                      Resume tracker
                    </div>
                    <h3>{categoryStats.find((item) => item.key === "resume")?.count ? "Resume activity found" : "No resume activity yet"}</h3>
                    <p>
                      {resumeAnalyzerActivity.count
                        ? `${resumeAnalyzerActivity.fileName || "A resume"} was used in the resume analyzer. Resume interview activity is also counted when completed.`
                        : "Use resume interview or resume analyzer and this dashboard will mark resume activity without showing resume health scores."}
                    </p>
                    <div className="dashboard-highlight-card__footer">
                      <span>{categoryStats.find((item) => item.key === "resume")?.count || 0} tracked resume touchpoints</span>
                    </div>
                  </div>
                </article>

                <article className="dashboard-panel dashboard-tip-panel">
                  <div className="dashboard-panel__header">
                    <div>
                      <span className="dashboard-panel__eyebrow">Coaching signal</span>
                      <h2>Focus recommendation</h2>
                    </div>
                  </div>

                  <p className="dashboard-tip-copy">
                    Review the lowest-performing topic first, then compare your latest report against the previous one to spot repeat gaps in clarity, structure, and technical depth.
                  </p>
                </article>
              </div>
            </section>
          </>
        )}
      </div>
    </>
  );
}

export default DashboardPage;
