import React, { useMemo } from "react";
import {
  ArrowLeft,
  BadgeCheck,
  CheckCircle2,
  CircleAlert,
  FileBarChart2,
  FileSearch,
  FileText,
  Lightbulb,
  Radar,
  SearchCheck,
  Sparkles,
  Target,
  TrendingUp,
  Wrench,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import "../App.css";

const ANALYZER_RESULT_STORAGE_KEY = "resumeAnalyzerResult";

function formatFileSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function readStoredPayload(key) {
  try {
    const value = sessionStorage.getItem(key);
    return value ? JSON.parse(value) : null;
  } catch {
    return null;
  }
}

function normalizeResultPayload(payload) {
  if (!payload || typeof payload !== "object") return null;
  if (!payload.resumeDataUrl || !payload.result || typeof payload.result !== "object") {
    return null;
  }

  return {
    fileName: typeof payload.fileName === "string" ? payload.fileName : "",
    resumeDataUrl: typeof payload.resumeDataUrl === "string" ? payload.resumeDataUrl : "",
    resumeBytes: Number(payload.resumeBytes) || 0,
    jobDescription: typeof payload.jobDescription === "string" ? payload.jobDescription : "",
    createdAt: payload.createdAt || "",
    analyzedAt: payload.analyzedAt || "",
    result: payload.result,
  };
}

function clampScore(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(100, Math.round(numeric)));
}

function displayScore(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? Math.round(numeric) : "--";
}

function canonicalValue(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9+#.\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function smartUniqueList(items = []) {
  const seen = new Set();
  const output = [];

  (items || []).forEach((item) => {
    const cleaned = String(item || "").trim();
    const key = canonicalValue(cleaned);
    if (!cleaned || !key || seen.has(key)) return;
    seen.add(key);
    output.push(cleaned);
  });

  return output;
}

function averageScores(values = []) {
  const valid = values.filter((value) => Number.isFinite(value));
  if (!valid.length) return 0;
  return clampScore(valid.reduce((sum, value) => sum + value, 0) / valid.length);
}

function normalizeSections(result) {
  const rawDetected = smartUniqueList([
    ...(result.quality?.detected_sections || []),
    ...(result.analysis?.detected_sections || []),
    ...(result.analysis?.sections || []),
  ]);

  const detectedMap = new Map(rawDetected.map((item) => [canonicalValue(item), item]));
  const extractedSkills = smartUniqueList([
    ...(result.analysis?.skills || []),
    ...(result.analysis?.technical_skills || []),
    ...(result.analysis?.tools || []),
  ]);
  const projects = smartUniqueList(result.analysis?.project_highlights || []);
  const education = smartUniqueList(result.analysis?.education || []);
  const experience = smartUniqueList(result.analysis?.experience_highlights || []);

  if (extractedSkills.length) detectedMap.set("skills", "Skills");
  if (projects.length) detectedMap.set("projects", "Projects");
  if (education.length) detectedMap.set("education", "Education");
  if (experience.length) detectedMap.set("experience", "Experience");

  const canonicalDetected = new Set(detectedMap.keys());
  const canonicalTargets = ["skills", "projects", "experience", "education"];
  const detectedSections = canonicalTargets
    .filter((section) => canonicalDetected.has(section))
    .map((section) => detectedMap.get(section) || section.charAt(0).toUpperCase() + section.slice(1));

  const missingSections = smartUniqueList(
    canonicalTargets
      .filter((section) => !canonicalDetected.has(section))
      .map((section) => section.charAt(0).toUpperCase() + section.slice(1))
  );

  return { detectedSections, missingSections };
}

function buildRoleSummary(result, hasJobDescription, matchedKeywords, missingKeywords) {
  if (!hasJobDescription) {
    return "Attach a job description to get stronger role-fit and missing keyword guidance.";
  }
  if (result.match?.summary) {
    return result.match.summary;
  }
  if (matchedKeywords.length && missingKeywords.length) {
    return `Your resume already reflects ${matchedKeywords.length} role keywords, but ${missingKeywords.length} important skills or terms are still missing.`;
  }
  if (matchedKeywords.length) {
    return "Your resume is showing useful overlap with the target role. Strengthen that match with clearer project evidence.";
  }
  if (missingKeywords.length) {
    return "The resume has relevant content, but it is not clearly aligned to the language of the target job description yet.";
  }
  return "We found limited comparison information. Try using a fuller job description for a clearer match readout.";
}

function getScoreTone(score) {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "danger";
}

function formatProviderName(provider, model = "") {
  const normalized = String(provider || "").trim().toLowerCase();
  const modelName = String(model || "").trim();
  if (!normalized) return "Unknown provider";
  if (normalized === "gemini") return "Google Gemini";
  if (normalized === "ollama") {
    return modelName ? `Qwen via Ollama (${modelName})` : "Qwen via Ollama";
  }
  if (normalized === "fallback") return "Local fallback analyzer";
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase());
}

function getQualitySummary(score) {
  if (score >= 85) {
    return {
      label: "Excellent",
      copy: "Your resume already looks recruiter-ready with strong ATS and recruiter-facing signals.",
    };
  }
  if (score >= 70) {
    return {
      label: "Strong",
      copy: "This draft is in a good place. A few sharper edits can make it noticeably more competitive.",
    };
  }
  if (score >= 55) {
    return {
      label: "Fair",
      copy: "The base is there, but the resume still needs stronger proof, clearer structure, and tighter role alignment.",
    };
  }
  return {
    label: "Needs work",
    copy: "This draft needs more structure and stronger evidence before it will perform well in screening.",
  };
}

function ScoreMeter({ label, value = 0, tone = "ink", size = "default", detail }) {
  const safeValue = clampScore(value);

  return (
    <article className={`resume-report-meter-card is-${tone} ${size === "hero" ? "is-hero" : ""}`}>
      <div
        className="resume-report-meter-ring"
        style={{ "--meter-value": `${safeValue}%` }}
        aria-label={`${label} ${safeValue} out of 100`}
      >
        <div className="resume-report-meter-core">
          <strong>{safeValue}</strong>
          <span>/100</span>
        </div>
      </div>
      <div className="resume-report-meter-copy">
        <h3>{label}</h3>
        {detail ? <p>{detail}</p> : null}
      </div>
    </article>
  );
}

function ScoreProgressRow({ label, value, note, tone }) {
  const safeValue = clampScore(value);

  return (
    <div className="resume-report-progress-row">
      <div className="resume-report-progress-row__head">
        <div>
          <strong>{label}</strong>
          <span>{note}</span>
        </div>
        <b>{safeValue}/100</b>
      </div>
      <div className="resume-report-progress-track">
        <span
          className={`resume-report-progress-fill is-${tone || getScoreTone(safeValue)}`}
          style={{ width: `${Math.max(8, safeValue)}%` }}
        />
      </div>
    </div>
  );
}

function InsightList({ items = [], emptyText, tone = "soft", icon = "bullet" }) {
  if (!items.length) {
    return <div className="resume-report-list-empty">{emptyText}</div>;
  }

  return (
    <div className="resume-report-plan-list">
      {items.map((item) => (
        <div key={item} className={`resume-report-plan-item is-${tone}`}>
          <div className={`resume-report-plan-icon is-${icon}`} aria-hidden="true" />
          <div>{item}</div>
        </div>
      ))}
    </div>
  );
}

function HighlightBlock({ title, items = [], emptyText }) {
  return (
    <div className="resume-report-highlight-block">
      <strong>{title}</strong>
      <InsightList items={items} emptyText={emptyText} tone="soft" />
    </div>
  );
}

function ResumeAnalyzerWorkspace({ pageData, result, onAnalyzeAnother, onBackToAnalyzer }) {
  const view = useMemo(() => {
    const hasJobDescription = Boolean(result.match?.job_description_provided || pageData.jobDescription?.trim());
    const atsScore = clampScore(result.quality?.ats_score);

    const extractedSkills = smartUniqueList([
      ...(result.analysis?.skills || []),
      ...(result.analysis?.technical_skills || []),
      ...(result.analysis?.tools || []),
    ]);
    const requiredKeywords = smartUniqueList([
      ...(result.match?.missing_keywords || []),
      ...(result.role_focus?.missing_keywords || []),
      ...(result.job_requirements?.required_skills || []),
      ...(result.job_requirements?.preferred_skills || []),
    ]);
    const matchedKeywords = smartUniqueList([
      ...(result.match?.matched_keywords || []),
      ...extractedSkills.filter((skill) =>
        requiredKeywords.some((keyword) => canonicalValue(keyword) === canonicalValue(skill))
      ),
    ]).slice(0, 10);
    const skillsToAdd = smartUniqueList(
      requiredKeywords.filter(
        (keyword) =>
          !matchedKeywords.some((matched) => canonicalValue(matched) === canonicalValue(keyword))
      )
    ).slice(0, 12);

    const derivedResumeScore = averageScores([
      atsScore,
      result.scorecard?.resume_score,
      result.scorecard?.content_score,
      result.quality?.overall_score,
    ]);
    const structureSections = normalizeSections(result);
    const derivedStructure = clampScore(
      structureSections.detectedSections.length
        ? (structureSections.detectedSections.length / 4) * 100
        : result.quality?.section_coverage_score
    );
    const derivedContent = averageScores([
      result.scorecard?.content_score,
      extractedSkills.length ? 70 : 25,
      (result.analysis?.project_highlights || []).length ? 65 : 25,
    ]);
    const derivedImpact = averageScores([
      result.quality?.impact_score,
      result.quality?.numeric_mentions ? Math.min(100, result.quality.numeric_mentions * 12) : 20,
      result.quality?.quantified_achievements_found ? 72 : 28,
    ]);
    const derivedSpelling = clampScore(
      Number.isFinite(Number(result.spelling?.score))
        ? result.spelling.score
        : Math.max(40, 100 - ((result.spelling?.issues || []).length * 18))
    );
    const derivedMatch = hasJobDescription
      ? averageScores([
          result.match?.match_score,
          requiredKeywords.length
            ? (matchedKeywords.length / Math.max(1, requiredKeywords.length)) * 100
            : extractedSkills.length
              ? 60
              : 30,
        ])
      : 0;

    const resumeScore = derivedResumeScore;
    const structureScore = derivedStructure;
    const contentScore = derivedContent;
    const impactScore = derivedImpact;
    const spellingScore = derivedSpelling;
    const matchScore = derivedMatch;

    const averageQuality = clampScore(
      Math.round(
        (atsScore +
          resumeScore +
          structureScore +
          contentScore +
          impactScore +
          spellingScore +
          (hasJobDescription ? matchScore : 0)) /
          (hasJobDescription ? 7 : 6)
      )
    );

    const qualitySummary = getQualitySummary(averageQuality);
    const providerLabel = formatProviderName(
      result.providers?.analysis_provider || result.providers?.report_provider,
      result.providers?.report_model
    );
    const providerError = String(result.providers?.provider_error || "").trim();
    const providerNote = result.providers?.analysis_provider === "ollama"
      ? `Gemini failed for this run, so Qwen through Ollama generated the report instead.${providerError ? ` ${providerError}` : ""}`
      : result.providers?.analysis_provider === "fallback"
        ? `Gemini and Qwen/Ollama both failed for this run, so the local fallback analyzer was used.${providerError ? ` ${providerError}` : ""}`
        : "";

    const summaryCards = [
      { label: "ATS Score", value: `${atsScore}%`, note: "screening readiness" },
      { label: "Resume Score", value: `${resumeScore}%`, note: qualitySummary.label },
      {
        label: "Role Match",
        value: hasJobDescription ? `${matchScore}%` : "--",
        note: hasJobDescription ? "against target role" : "job description required",
      },
      { label: "Missing Sections", value: structureSections.missingSections.length, note: "important gaps" },
      { label: "Skills Found", value: extractedSkills.length, note: "extracted from resume" },
      { label: "Impact Signals", value: result.quality?.numeric_mentions ?? 0, note: "numbers and outcomes" },
    ];

    const scoreRows = [
      { label: "Resume strength", value: resumeScore, note: "overall quality of this draft" },
      { label: "Structure", value: structureScore, note: "document organization and scanability" },
      { label: "Content", value: contentScore, note: "skills, projects, and experience depth" },
      { label: "Impact", value: impactScore, note: "metrics, outcomes, and evidence" },
      { label: "Spelling", value: spellingScore, note: "surface polish and keyword accuracy" },
    ];

    if (hasJobDescription) {
      scoreRows.splice(1, 0, {
        label: "Job match",
        value: matchScore,
        note: "alignment with the description you provided",
      });
    }

    const fallbackRecommendations = [];
    if (skillsToAdd.length) {
      fallbackRecommendations.push(`Add or prove ${skillsToAdd.slice(0, 3).join(", ")} in projects or experience bullets.`);
    }
    if (structureSections.missingSections.length) {
      fallbackRecommendations.push(`Make these sections clearer for ATS: ${structureSections.missingSections.join(", ")}.`);
    }
    if (!(result.analysis?.project_highlights || []).length) {
      fallbackRecommendations.push("Add 1 to 2 strong projects with tools used, actions taken, and measurable outcomes.");
    } else if (!result.quality?.quantified_achievements_found) {
      fallbackRecommendations.push("Add measurable impact to project and experience bullets using numbers, results, or scale.");
    }

    const priorityActions = smartUniqueList([
      ...(result.quality?.must_add || []),
      ...(result.role_focus?.where_to_improve || []),
      ...(result.recommendations || []),
      ...fallbackRecommendations,
    ]).slice(0, 8);

    const signals = [
      {
        label: "Email",
        ok: Boolean(result.quality?.contact_checks?.email),
        note: result.quality?.contact_checks?.email ? "visible" : "missing",
      },
      {
        label: "Phone",
        ok: Boolean(result.quality?.contact_checks?.phone),
        note: result.quality?.contact_checks?.phone ? "visible" : "missing",
      },
      {
        label: "Profile link",
        ok: Boolean(result.quality?.contact_checks?.profile_link),
        note: result.quality?.contact_checks?.profile_link ? "present" : "missing",
      },
      {
        label: "Projects",
        ok: Boolean((result.analysis?.project_highlights || []).length),
        note: (result.analysis?.project_highlights || []).length ? "detected" : "not clear",
      },
      {
        label: "Numbers in bullets",
        ok: Boolean(result.quality?.quantified_achievements_found),
        note: result.quality?.quantified_achievements_found ? "found" : "needs more",
      },
      {
        label: "Target keywords",
        ok: Boolean(matchedKeywords.length),
        note: matchedKeywords.length
          ? "partly covered"
          : hasJobDescription
            ? "not reflected"
            : "job description not attached",
      },
    ];

    const signalStrengths = smartUniqueList([
      ...(result.quality?.strengths || []),
      extractedSkills.length ? `${extractedSkills.length} skill keywords were extracted from the resume.` : "",
      matchedKeywords.length ? `${matchedKeywords.length} target keywords already align with the job description.` : "",
      result.quality?.quantified_achievements_found ? "The resume includes quantified proof in bullets." : "",
    ]);

    const mustAdd = smartUniqueList([
      ...(result.quality?.must_add || []),
      ...(skillsToAdd.length ? [`Add evidence for: ${skillsToAdd.slice(0, 4).join(", ")}.`] : []),
      ...(structureSections.missingSections.length ? [`Clarify these sections: ${structureSections.missingSections.join(", ")}.`] : []),
    ]);

    const spellingIssues = (result.spelling?.issues || []).map(
      (item) => `Replace "${item.word}" with "${item.suggestion}".`
    );

    const roleSummary = buildRoleSummary(result, hasJobDescription, matchedKeywords, skillsToAdd);

    const weakAreas = (result.dashboard?.weak_areas || []).length
      ? result.dashboard.weak_areas
      : [
          { title: "Structure", score: structureScore, detail: structureSections.missingSections.length ? `Missing or unclear sections: ${structureSections.missingSections.join(", ")}.` : "Section structure is readable." },
          { title: "Role Alignment", score: hasJobDescription ? matchScore : 0, detail: hasJobDescription ? (skillsToAdd.length ? `Missing or weak alignment on ${skillsToAdd.slice(0, 3).join(", ")}.` : "Core job keywords are showing up well.") : "Attach a job description for direct role alignment." },
          { title: "Projects", score: impactScore, detail: (result.analysis?.project_highlights || []).length ? (result.quality?.quantified_achievements_found ? "Projects exist, but sharpen them with clearer outcomes where possible." : "Projects are present, but they need measurable impact.") : "No clear project evidence was extracted." },
        ];

    const meters = (result.dashboard?.meters || []).length
      ? result.dashboard.meters
      : [
          { label: "Resume Score", value: resumeScore, tone: getScoreTone(resumeScore) === "success" ? "teal" : getScoreTone(resumeScore) === "warning" ? "gold" : "slate" },
          { label: "Structure Score", value: structureScore, tone: getScoreTone(structureScore) === "success" ? "teal" : getScoreTone(structureScore) === "warning" ? "gold" : "slate" },
          { label: "Content Score", value: contentScore, tone: getScoreTone(contentScore) === "success" ? "teal" : getScoreTone(contentScore) === "warning" ? "gold" : "slate" },
          { label: "ATS Score", value: atsScore, tone: "ink" },
          { label: "Impact Score", value: impactScore, tone: getScoreTone(impactScore) === "success" ? "teal" : getScoreTone(impactScore) === "warning" ? "gold" : "slate" },
          { label: "Match Score", value: hasJobDescription ? matchScore : 0, tone: getScoreTone(matchScore) === "success" ? "teal" : getScoreTone(matchScore) === "warning" ? "gold" : "slate" },
        ];

    return {
      atsScore,
      averageQuality,
      detectedSections: structureSections.detectedSections,
      extractedSkills,
      meters,
      matchedKeywords,
      mustAdd,
      priorityActions,
      providerError,
      providerLabel,
      providerNote,
      qualitySummary,
      roleSummary,
      scoreRows,
      signals,
      skillsToAdd,
      spellingIssues,
      strengths: signalStrengths,
      summaryCards,
      weakAreas,
      missingSections: structureSections.missingSections,
    };
  }, [pageData.jobDescription, result]);

  return (
    <>
      <section className="resume-report-hero">
        <div className="resume-studio-kicker">Resume Analysis Report</div>
        <h1>{pageData.fileName || "Resume Analysis"}</h1>
        <p>
          Review ATS readiness, role alignment, structure, quality, and the exact
          edits that can strengthen the next draft of your resume.
        </p>

        <div className="resume-report-top-tags">
          <span>{view.providerLabel}</span>
          <span>{view.qualitySummary.label}</span>
          <span>
            {pageData.jobDescription?.trim() ? "job description attached" : "resume-only scan"}
          </span>
        </div>

        <div className="resume-report-hero-strip">
          {view.summaryCards.slice(0, 4).map((card) => (
            <article key={card.label} className="resume-report-hero-card">
              <div>
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="resume-report-layout">
        <aside className="resume-report-sidebar resume-report-sidebar-sticky">
          <div className="resume-report-sidebar-card resume-report-preview-card">
            <div className="resume-report-sidebar-top">
              <div>
                <span>Resume Preview</span>
                <h2>{pageData.fileName || "Uploaded resume"}</h2>
              </div>
              <div className="resume-report-sidebar-icon">
                <FileText size={20} />
              </div>
            </div>

            <div className="resume-report-sidebar-meta">
              <span>{formatFileSize(pageData.resumeBytes) || "PDF"}</span>
              <span>{result.analysis?.candidate_name || "Candidate not detected"}</span>
            </div>

            <iframe
              className="resume-report-frame"
              src={pageData.resumeDataUrl}
              title="Resume analysis preview"
            />

            <div className="resume-studio-actions">
              <button
                className="resume-studio-btn is-primary"
                type="button"
                onClick={onAnalyzeAnother}
              >
                <ArrowLeft size={16} />
                Analyze Another Resume
              </button>
              <button
                className="resume-studio-btn is-secondary"
                type="button"
                onClick={onBackToAnalyzer}
              >
                Back to Analyzer
              </button>
            </div>
          </div>

          <article className="resume-report-panel">
            <div className="resume-report-panel-head">
              <div>
                <span>ATS Illustration</span>
                <h3>Score meters</h3>
              </div>
              <FileBarChart2 size={18} />
            </div>

            {view.meters.length ? (
              <div className="resume-report-meter-grid">
                {view.meters.map((meter) => (
                  <ScoreMeter
                    key={meter.label}
                    label={meter.label}
                    value={meter.value}
                    tone={meter.tone}
                  />
                ))}
              </div>
            ) : (
              <div className="resume-report-dashboard-empty">
                Dashboard score meters are not available in this result yet.
              </div>
            )}
          </article>
        </aside>

        <div className="resume-report-main">
          <article className="resume-report-intro-card resume-report-command-card">
            <div className="resume-report-panel-head">
              <div>
                <span>Overview</span>
                <h2>How this resume is reading</h2>
              </div>
              <div className={`resume-report-score-badge is-${getScoreTone(view.averageQuality)}`}>
                {view.qualitySummary.label}
              </div>
            </div>

            <div className="resume-report-command-grid">
              <div className="resume-report-command-banner">
                <strong>{view.providerLabel}</strong>
                <p>{view.qualitySummary.copy}</p>

                {view.providerNote ? (
                  <div className="resume-report-dashboard-empty">
                    {view.providerNote}
                  </div>
                ) : null}

                {view.providerError && !view.providerNote ? (
                  <div className="resume-report-dashboard-empty">
                    Provider details: {view.providerError}
                  </div>
                ) : null}
              </div>

              <ScoreMeter
                label="ATS Score"
                value={view.atsScore}
                tone="ink"
                size="hero"
                detail="Use this score as a quick screening signal, then improve the weaker breakdown rows below."
              />
            </div>
          </article>

          <div className="resume-report-results">
            <div className="resume-report-dashboard-grid">
              <article className="resume-report-wide-panel resume-report-dashboard-grid-top">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Score breakdown</span>
                    <h3>How the resume is performing</h3>
                  </div>
                  <FileBarChart2 size={18} />
                </div>

                <div className="resume-report-progress-stack">
                  {view.scoreRows.map((item) => (
                    <ScoreProgressRow
                      key={item.label}
                      label={item.label}
                      value={item.value}
                      note={item.note}
                    />
                  ))}
                </div>
              </article>

              <article className="resume-report-panel resume-report-panel-featured">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Improve first</span>
                    <h3>Priority action plan</h3>
                  </div>
                  <Target size={18} />
                </div>

                <InsightList
                  items={view.priorityActions}
                  emptyText="No major action items were generated. Focus on polishing bullets and tailoring the final draft."
                  tone="priority"
                  icon="accent"
                />
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Weak areas</span>
                    <h3>Where the resume loses points</h3>
                  </div>
                  <Wrench size={18} />
                </div>

                {view.weakAreas.length ? (
                  <div className="resume-report-weak-grid">
                    {view.weakAreas.map((item) => (
                      <div key={item.title} className="resume-report-weak-card">
                        <strong>{item.title}</strong>
                        <span>{displayScore(item.score)}/100</span>
                        <p>{item.detail}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="resume-report-dashboard-empty">
                    Weak-area cards are not available in this result yet.
                  </div>
                )}
              </article>
            </div>

            <div className="resume-report-detail-grid">
              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Resume quality</span>
                    <h3>Signal check</h3>
                  </div>
                  <SearchCheck size={18} />
                </div>

                <p className="resume-report-copy">
                  Word count: {result.quality?.word_count ?? 0} words. Quantified
                  achievements found: {result.quality?.quantified_achievements_found ? " yes." : " no."}
                </p>

                <div className="resume-report-signal-grid">
                  {view.signals.map((signal) => (
                    <div
                      key={signal.label}
                      className={`resume-report-signal-card ${signal.ok ? "is-success" : "is-danger"}`}
                    >
                      <div className="resume-report-signal-card__icon">
                        {signal.ok ? <CheckCircle2 size={16} /> : <CircleAlert size={16} />}
                      </div>
                      <div>
                        <strong>{signal.label}</strong>
                        <span>{signal.note}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Section coverage</span>
                    <h3>Resume structure</h3>
                  </div>
                  <Radar size={18} />
                </div>

                <ScoreProgressRow
                  label="Section coverage"
                  value={result.quality?.section_coverage_score || clampScore((view.detectedSections.length / 4) * 100)}
                  note="how complete the resume structure appears"
                />

                <div className="resume-report-list-block">
                  <strong>Detected sections</strong>
                  <div className="resume-report-chip-row">
                    {view.detectedSections.length ? (
                      view.detectedSections.map((section) => (
                        <span key={section} className="resume-report-chip is-success">
                          {section}
                        </span>
                      ))
                    ) : (
                      <span className="resume-report-chip is-muted">
                        No sections detected clearly
                      </span>
                    )}
                  </div>
                </div>

                <div className="resume-report-list-block">
                  <strong>Missing sections</strong>
                  <div className="resume-report-chip-row">
                    {view.missingSections.length ? (
                      view.missingSections.map((section) => (
                        <span key={section} className="resume-report-chip is-missing">
                          {section}
                        </span>
                      ))
                    ) : (
                      <span className="resume-report-chip is-success">
                        No major section gaps detected
                      </span>
                    )}
                  </div>
                </div>
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Role alignment</span>
                    <h3>Keyword map</h3>
                  </div>
                  <TrendingUp size={18} />
                </div>

                <p className="resume-report-copy">
                  {view.roleSummary}
                </p>

                <div className="resume-report-list-block">
                  <strong>Matched keywords</strong>
                  <div className="resume-report-chip-row">
                    {view.matchedKeywords.length ? (
                      view.matchedKeywords.map((keyword) => (
                        <span key={keyword} className="resume-report-chip is-success">
                          {keyword}
                        </span>
                      ))
                    ) : (
                      <span className="resume-report-chip is-muted">
                        No strong keyword overlap detected yet
                      </span>
                    )}
                  </div>
                </div>

                <div className="resume-report-list-block">
                  <strong>Skills / keywords to add</strong>
                  <div className="resume-report-chip-row">
                    {view.skillsToAdd.length ? (
                      view.skillsToAdd.map((keyword) => (
                        <span key={keyword} className="resume-report-chip is-missing">
                          {keyword}
                        </span>
                      ))
                    ) : (
                      <span className="resume-report-chip is-success">
                        No urgent missing role keywords detected
                      </span>
                    )}
                  </div>
                </div>
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Suggestions</span>
                    <h3>Recommendations for the next draft</h3>
                  </div>
                  <Lightbulb size={18} />
                </div>

                <InsightList
                  items={view.priorityActions}
                  emptyText="We found limited information. Try improving formatting and adding clearer role keywords."
                  tone="soft"
                />

                <div className="resume-report-chip-row">
                  {(result.analysis?.suggested_roles || []).length ? (
                    result.analysis.suggested_roles.map((role) => (
                      <span key={role} className="resume-report-chip is-role">
                        {role}
                      </span>
                    ))
                  ) : (
                    <span className="resume-report-chip is-muted">
                      No role suggestions yet
                    </span>
                  )}
                </div>
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Strengths</span>
                    <h3>What is already working</h3>
                  </div>
                  <BadgeCheck size={18} />
                </div>

                <InsightList
                  items={view.strengths}
                  emptyText="No strong strengths were detected yet. Add clearer sections and measurable results."
                  tone="success"
                  icon="success"
                />
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Must add</span>
                    <h3>High-priority missing items</h3>
                  </div>
                  <Target size={18} />
                </div>

                <InsightList
                  items={view.mustAdd}
                  emptyText="No urgent missing items were detected."
                  tone="danger"
                  icon="accent"
                />

                <div className="resume-report-list-block">
                  <strong>Extracted skills</strong>
                  <div className="resume-report-chip-row">
                    {view.extractedSkills.length ? (
                      view.extractedSkills.map((skill) => (
                        <span key={skill} className="resume-report-chip">
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="resume-report-chip is-muted">
                        No skills extracted clearly
                      </span>
                    )}
                  </div>
                </div>
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Resume content</span>
                    <h3>What the analyzer extracted</h3>
                  </div>
                  <Sparkles size={18} />
                </div>

                <HighlightBlock
                  title="Experience"
                  items={result.analysis?.experience_highlights || []}
                  emptyText="No strong experience lines were extracted."
                />
                <HighlightBlock
                  title="Projects"
                  items={result.analysis?.project_highlights || []}
                  emptyText="No clear project lines were extracted."
                />
                <HighlightBlock
                  title="Education"
                  items={result.analysis?.education || []}
                  emptyText="No clear education lines were extracted."
                />
              </article>

              <article className="resume-report-panel">
                <div className="resume-report-panel-head">
                  <div>
                    <span>Polish check</span>
                    <h3>Spelling and quality notes</h3>
                  </div>
                  <CircleAlert size={18} />
                </div>

                <p className="resume-report-copy">{result.spelling?.summary}</p>

                <InsightList
                  items={view.spellingIssues}
                  emptyText="No obvious spelling issues were flagged."
                  tone="soft"
                />
              </article>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
function ResumeAnalyzerResults() {
  const navigate = useNavigate();
  const location = useLocation();
  const navigationPayload = normalizeResultPayload(location.state?.resultPayload);
  const storedResult = normalizeResultPayload(readStoredPayload(ANALYZER_RESULT_STORAGE_KEY));
  const pageData = navigationPayload || storedResult;
  const result = pageData?.result || null;

  const clearStoredAnalysis = () => {
    try {
      sessionStorage.removeItem(ANALYZER_RESULT_STORAGE_KEY);
    } catch {
      // Ignore browser storage cleanup issues.
    }
  };

  const goBackToAnalyzer = () => {
    clearStoredAnalysis();
    navigate("/resume-analyzer");
  };

  return (
    <div className="resume-studio-page resume-report-page">
      <main className="resume-studio-shell">
        {pageData && result ? (
          <ResumeAnalyzerWorkspace
            pageData={pageData}
            result={result}
            onAnalyzeAnother={goBackToAnalyzer}
            onBackToAnalyzer={() => navigate("/resume-analyzer")}
          />
        ) : (
          <section className="resume-report-layout">
            <div className="resume-report-empty">
              <div className="resume-report-empty-icon">
                <FileSearch size={24} />
              </div>
              <div>
                <span>Nothing to show yet</span>
                <h2>Upload a resume first</h2>
                <p>
                  Start from the Resume Analyzer page, upload your PDF, and then
                  come back to open the report.
                </p>
              </div>
              <button
                className="resume-studio-btn is-primary"
                type="button"
                onClick={() => navigate("/resume-analyzer")}
              >
                Go to Resume Analyzer
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default ResumeAnalyzerResults;
