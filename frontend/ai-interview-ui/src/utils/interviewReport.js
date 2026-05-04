export const clean = (value) => (value || "").replace(/\s+/g, " ").trim();

export const safeText = (value) => {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return clean(String(value));
  }
  if (Array.isArray(value)) {
    return clean(value.map((item) => safeText(item)).filter(Boolean).join(", "));
  }
  if (typeof value === "object") {
    return clean(
      String(
        value.text ||
        value.message ||
        value.msg ||
        value.question ||
        value.detail ||
        JSON.stringify(value)
      )
    );
  }
  return clean(String(value));
};

export const safeCodeText = (value) => {
  if (value == null) return "";
  const normalized = String(value).replace(/\r\n/g, "\n").trim();
  if (!normalized || normalized.includes("\n")) {
    return normalized;
  }

  const looksLikeCode =
    /(import |from |def |class |if __name__|print\(|return |const |let |var |function |public class |#include )/.test(normalized);
  if (!looksLikeCode) {
    return normalized;
  }

  let formatted = normalized
    .replace(/\s+(def\s+)/g, "\n$1")
    .replace(/\s+(class\s+)/g, "\n$1")
    .replace(/\s+(if __name__\s*==\s*)/g, "\n\n$1")
    .replace(/\s+(for\s+)/g, "\n    $1")
    .replace(/\s+(while\s+)/g, "\n    $1")
    .replace(/\s+(if\s+)/g, "\n    $1")
    .replace(/\s+(elif\s+)/g, "\n    $1")
    .replace(/\s+(else:)/g, "\n    $1")
    .replace(/\s+(return\s+)/g, "\n    $1")
    .replace(/\s+(print\()/g, "\n$1");

  return formatted.trim();
};

export const safeTextList = (value) => {
  if (!Array.isArray(value)) return [];
  return value.map((item) => safeText(item)).filter(Boolean);
};

export const safeErrorText = (value) => {
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (item && typeof item === "object") {
          const location = Array.isArray(item.loc) ? item.loc.join(" > ") : safeText(item.loc);
          const message = safeText(item.msg || item.message || item.detail || item);
          return clean([location, message].filter(Boolean).join(": "));
        }
        return safeText(item);
      })
      .filter(Boolean)
      .join(" | ");
  }

  if (value && typeof value === "object" && value.detail) {
    return safeErrorText(value.detail);
  }

  return safeText(value);
};

export const safeScore = (value) => {
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return Math.max(0, Math.min(100, Math.round(numeric)));
  }
  return 0;
};

export const safeOptionalScore = (value) => {
  const numeric = Number(value);
  if (Number.isFinite(numeric)) {
    return Math.max(0, Math.min(100, Math.round(numeric)));
  }
  return null;
};

export const formatProviderName = (provider, stage = "") => {
  const value = safeText(provider).toLowerCase();
  const phase = safeText(stage).toLowerCase();

  if (!value) return "";

  if (value === "gemini") return "Google Gemini";
  if (value === "ollama") return "Ollama";

  if (value === "fallback") {
    if (phase === "generation") return "Built-in Question Generator";
    if (phase === "evaluation") return "Built-in Answer Evaluator";
    if (phase === "summary") return "Built-in Interview Summarizer";
    if (phase === "analysis") return "Built-in Role Analyzer";
    return "Built-in Backup Engine";
  }

  return value.replace(/\b\w/g, (char) => char.toUpperCase());
};

const normalizeScoreBreakdown = (value) => {
  if (!value || typeof value !== "object") return null;

  const keys = [
    "communication",
    "confidence",
    "problem_solving",
    "teamwork",
    "leadership",
    "hr_readiness",
    "personality_attitude",
    "cultural_fit",
    "star_structure",
  ];

  const normalized = {};
  let hasAny = false;

  keys.forEach((key) => {
    const score = safeOptionalScore(value?.[key]);
    if (score != null) {
      normalized[key] = score;
      hasAny = true;
    }
  });

  return hasAny ? normalized : null;
};

export const normalizeEvaluation = (item) => ({
  question_id: safeText(item?.question_id),
  question: safeText(item?.question),
  question_type: safeText(item?.question_type) || "practical",
  interview_phase: safeText(item?.interview_phase),
  answer: safeCodeText(item?.answer),
  reference_answer: safeCodeText(item?.reference_answer),
  feedback: safeText(item?.feedback),
  strengths: safeTextList(item?.strengths),
  gaps: safeTextList(item?.gaps),
  matched_points: safeTextList(item?.matched_points),
  missed_points: safeTextList(item?.missed_points),
  suggested_answer: safeText(item?.suggested_answer),
  assistant_reply: safeText(item?.assistant_reply),
  relevance: safeText(item?.relevance),
  correctness: safeText(item?.correctness),
  clarity: safeText(item?.clarity),
  technical_depth: safeText(item?.technical_depth),
  logical_validity: safeText(item?.logical_validity),
  real_world_applicability: safeText(item?.real_world_applicability),
  suggestions: safeTextList(item?.suggestions),
  score: safeScore(item?.score),
  provider: safeText(item?.provider),
  count_towards_score: item?.count_towards_score !== false,
  communication_score: safeOptionalScore(item?.communication_score),
  confidence_score: safeOptionalScore(item?.confidence_score),
  problem_solving_score: safeOptionalScore(item?.problem_solving_score),
  teamwork_score: safeOptionalScore(item?.teamwork_score),
  leadership_score: safeOptionalScore(item?.leadership_score),
  hr_readiness_score: safeOptionalScore(item?.hr_readiness_score),
  personality_attitude_score: safeOptionalScore(item?.personality_attitude_score),
  cultural_fit_score: safeOptionalScore(item?.cultural_fit_score),
  star_score: safeOptionalScore(item?.star_score),
  is_control_turn: Boolean(item?.is_control_turn),
  control_command: safeText(item?.control_command),
});

export const normalizeQuestionOutline = (questions) => {
  if (!Array.isArray(questions)) return [];
  return questions.map((item, index) => ({
    id: safeText(item?.id || index + 1),
    question: safeText(item?.question),
    question_type: safeText(item?.question_type) || "practical",
    score: safeScore(item?.score),
  }));
};

export const getStoredUser = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem("user") || "null");
    if (parsed && typeof parsed === "object") {
      return {
        id: safeText(parsed.id),
        email: safeText(parsed.email),
        first_name: safeText(parsed.first_name),
        last_name: safeText(parsed.last_name),
      };
    }
  } catch {}
  return null;
};

export const normalizeReport = (report, fallbackContext = {}, fallbackUser = null) => {
  const storedUser = fallbackUser || getStoredUser();
  const context = {
    ...(fallbackContext || {}),
    ...(report || {}),
    ...((report?.context && typeof report.context === "object") ? report.context : {}),
  };
  const user = report?.user && typeof report.user === "object" ? report.user : storedUser;
  const evaluations = Array.isArray(report?.evaluations) ? report.evaluations.map((item) => normalizeEvaluation(item)) : [];
  const providerFromEvaluations = evaluations
    .map((item) => safeText(item?.provider))
    .find((value) => value && value !== "fallback");
  const evaluationProvider = safeText(report?.providers?.evaluation_provider);

  return {
    session_id: safeText(report?.session_id),
    interview_type: safeText(report?.interview_type || report?.type),
    created_at: safeText(report?.created_at || report?.createdAt || report?.timestamp),
    completed_at: safeText(report?.completed_at || report?.completedAt || report?.ended_at || report?.endedAt),
    overall_score: safeScore(report?.overall_score ?? report?.score),
    summary: safeText(report?.summary),
    ended_early: Boolean(report?.ended_early),
    questions_answered: Number(report?.questions_answered || 0),
    total_questions: Number(report?.total_questions || report?.question_count || 0),
    top_strengths: safeTextList(report?.top_strengths),
    improvement_areas: safeTextList(report?.improvement_areas),
    strongest_questions: safeTextList(report?.strongest_questions),
    needs_work_questions: safeTextList(report?.needs_work_questions),
    score_breakdown: normalizeScoreBreakdown(report?.score_breakdown),
    skills_breakdown: report?.skills_breakdown && typeof report.skills_breakdown === "object" ? report.skills_breakdown : null,
    top_skills: safeTextList(report?.top_skills),
    weakest_skills: safeTextList(report?.weakest_skills),
    avg_difficulty_reached: safeText(report?.avg_difficulty_reached),
    adaptive_insights: report?.adaptive_insights && typeof report.adaptive_insights === "object" ? report.adaptive_insights : null,
    answers: safeTextList(report?.answers),
    evaluations,
    question_outline: normalizeQuestionOutline(report?.question_outline || report?.questions),
    providers: {
      generation_provider: safeText(report?.providers?.generation_provider),
      evaluation_provider: evaluationProvider && evaluationProvider !== "fallback"
        ? evaluationProvider
        : providerFromEvaluations || evaluationProvider,
      summary_provider: safeText(report?.providers?.summary_provider),
    },
    context: {
      category: safeText(context?.category),
      selected_mode: safeText(context?.selected_mode),
      job_role: safeText(context?.job_role),
      primary_language: safeText(context?.primary_language),
      experience: safeText(context?.experience),
      config_mode: safeText(context?.config_mode),
      mode: safeText(context?.mode),
      practice_type: safeText(context?.practice_type),
      interview_mode_time: safeText(context?.interview_mode_time),
      time_mode_interval: safeText(context?.time_mode_interval),
      selected_options: safeTextList(context?.selected_options),
      focus_areas: safeTextList(context?.focus_areas || context?.selected_options),
      hr_round: safeText(context?.hr_round),
      aptitude_type: safeText(context?.aptitude_type),
      section_id: safeText(context?.section_id || context?.sectionId),
      section_title: safeText(context?.section_title || context?.sectionTitle),
      test_type: safeText(context?.test_type || context?.testType),
      coding_level: safeText(context?.coding_level || context?.codingLevel),
    },
    user: user
      ? {
          id: safeText(user?.id),
          email: safeText(user?.email),
          first_name: safeText(user?.first_name),
          last_name: safeText(user?.last_name),
        }
      : null,
  };
};
