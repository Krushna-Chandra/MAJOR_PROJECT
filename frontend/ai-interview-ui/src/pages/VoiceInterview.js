import React, { useCallback, useEffect, useRef, useState } from "react";
import { useScrollToTop } from "../hooks/useScrollToTop";
import { useLocation, useNavigate } from "react-router-dom";
import { useInterviewFullscreenGuard } from "../hooks/useInterviewFullscreenGuard";
import { useRevealFullscreenWarning } from "../hooks/useRevealFullscreenWarning";
import {
  clearInterviewFullscreenGuard,
  isFullscreenActive,
  requestInterviewFullscreen,
} from "../utils/interviewFullscreenGuard";



import axios from "axios";



import "../App.css";
import interviewrWordmark from "../assets/Website Logo.png";







const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";



const EARLY_END_CLOSING_MESSAGE = "Thank you for your time today. The interview is now over. I am ending the session and preparing your report.";



const NATURAL_END_CLOSING_MESSAGE = "Thank you for your time today. This interview is now over. I am preparing your report.";



const TIMER_END_CLOSING_MESSAGE = "The interview time is now over. Thank you for your time today. I am preparing your report.";



const INTERVIEW_STORAGE_KEY = "voiceInterviewActiveSession";



const STARTUP_LAUNCH_COUNTDOWN_SECONDS = 3;

const STARTUP_CAMERA_TIMEOUT_MS = 2500;

const STARTUP_HANDOFF_STALL_MS = 6500;



const STARTUP_STAGE_MESSAGES = [



  "Setting up interview environment",



  "Preparing camera and microphone access",



  "Preparing your AI interviewer",



  "Loading your first question",



  "Starting your interview session",



];







const clean = (value) => (value || "").replace(/\s+/g, " ").trim();



const safeText = (value) => {



  if (value == null) return "";



  if (typeof value === "string" || typeof value === "number") return clean(String(value));



  if (Array.isArray(value)) return clean(value.map((item) => safeText(item)).filter(Boolean).join(", "));



  if (typeof value === "object") {



    return clean(



      String(



        value.text ||



        value.message ||



        value.msg ||



        value.question ||



        JSON.stringify(value)



      )



    );



  }



  return clean(String(value));



};







const safeTextList = (value) => {



  if (!Array.isArray(value)) return [];



  return value.map((item) => safeText(item)).filter(Boolean);



};







const safeErrorText = (value) => {



  if (Array.isArray(value)) {



    const normalized = value



      .map((item) => {



        if (item && typeof item === "object") {



          const location = Array.isArray(item.loc) ? item.loc.join(" > ") : safeText(item.loc);



          const message = safeText(item.msg || item.message || item.detail || item);



          return clean([location, message].filter(Boolean).join(": "));



        }



        return safeText(item);



      })



      .filter(Boolean);



    return normalized.join(" | ");



  }







  if (value && typeof value === "object" && value.detail) {



    return safeErrorText(value.detail);



  }







  return safeText(value);



};







const safeScore = (value) => {



  const numeric = Number(value);



  if (Number.isFinite(numeric)) {



    return Math.max(0, Math.min(100, Math.round(numeric)));



  }



  return 0;



};







const formatProviderName = (provider, stage = "") => {



  const value = safeText(provider).toLowerCase();



  const phase = safeText(stage).toLowerCase();







  if (!value) return "";



  if (value === "gemini") return "Google Gemini";



  if (value === "ollama") return "Ollama";







  if (value === "fallback") {



    if (phase === "generation") return "Built-in Question Generator";



    if (phase === "evaluation") return "Built-in Answer Evaluator";



    if (phase === "summary") return "Built-in Interview Summarizer";



    return "Built-in Backup Engine";



  }







  return value.replace(/\b\w/g, (char) => char.toUpperCase());



};







const formatRoundLabel = (value) => {



  const normalized = safeText(value);



  if (!normalized) return "";



  const lookup = {



    hr: "HR",



    behavioral: "Behavioral",



    hr_behavioral: "HR + Behavioral",



    technical: "HR + Behavioral",



    both: "HR + Behavioral",



  };



  return lookup[normalized.toLowerCase()] || normalized.replace(/_/g, " / ").replace(/\b\w/g, (char) => char.toUpperCase());



};







const detectInterviewControlCommand = (value) => {



  const normalized = clean(value).toLowerCase();



  if (!normalized) return null;



  const wordCount = normalized.split(" ").filter(Boolean).length;



  if (wordCount > 14) return null;







  const repeatPatterns = [



    /^repeat$/,



    /^repeat again$/,



    /^repeat question$/,



    /^repeat the question$/,



    /^repeat that question$/,



    /^repeat this question$/,



    /^repeat the question again$/,



    /^say again$/,



    /^say that again$/,



    /^say the question again$/,



    /^can you repeat$/,



    /^can you repeat that$/,



    /^can you repeat the question$/,



    /^can you repeat this question$/,



    /^can you repeat that question$/,



    /^can you please repeat$/,



    /^can you please repeat the question$/,



    /^please repeat$/,



    /^please repeat that$/,



    /^please repeat the question$/,



    /^please repeat this question$/,



    /^one more time$/,



    /^i did not catch that$/,



    /^i didn't catch that$/,



    /^pardon$/,



  ];







  const clarifyPatterns = [



    /^(i )?do not understand$/,



    /^(i )?do not understand the question$/,



    /^(i )?do not understand this question$/,



    /^(i )?don't understand$/,



    /^(i )?don't understand the question$/,



    /^(i )?don't understand this question$/,



    /^(i )?did not understand$/,



    /^(i )?did not understand the question$/,



    /^(i )?did not understand this question$/,



    /^(i )?didn't understand$/,



    /^(i )?didn't understand the question$/,



    /^(i )?didn't understand this question$/,



    /^(i )?didnt understand$/,



    /^(i )?didnt understand the question$/,



    /^(i )?didnt understand this question$/,



    /^(i )?cannot understand$/,



    /^(i )?cannot understand the question$/,



    /^(i )?cannot understand this question$/,



    /^(i )?can't understand$/,



    /^(i )?can't understand the question$/,



    /^(i )?can't understand this question$/,



    /^(i )?cant understand$/,



    /^(i )?cant understand the question$/,



    /^(i )?cant understand this question$/,



    /^can you explain$/,



    /^can you explain that$/,



    /^can you explain the question$/,



    /^can you explain this question$/,



    /^can you please explain$/,



    /^can you please explain the question$/,



    /^could you explain$/,



    /^could you explain that$/,



    /^could you explain the question$/,



    /^please explain$/,



    /^please explain that$/,



    /^please explain the question$/,



    /^please explain this question$/,



    /^clarify$/,



    /^clarify the question$/,



    /^clarify this question$/,



    /^simplify$/,



    /^simplify the question$/,



    /^simplify this question$/,



    /^make it simpler$/,



    /^what do you mean$/,



    /^what does that mean$/,



    /^i am confused$/,



    /^i'm confused$/,



  ];







  if (repeatPatterns.some((pattern) => pattern.test(normalized))) return "repeat";



  if (clarifyPatterns.some((pattern) => pattern.test(normalized))) return "clarify";



  if (



    [



      "repeat the question",



      "repeat that question",



      "repeat this question",



      "can you repeat",



      "could you repeat",



      "please repeat",



      "say that again",



      "one more time",



      "did not catch that",



      "didn't catch that",



    ].some((marker) => normalized.includes(marker))



  ) {



    return "repeat";



  }



  if (



    [



      "do not understand",



      "don't understand",



      "did not understand",



      "didn't understand",



      "didnt understand",



      "cannot understand",



      "can't understand",



      "cant understand",



      "explain the question",



      "explain this question",



      "clarify the question",



      "clarify this question",



      "simplify the question",



      "simplify this question",



      "make it simpler",



      "what do you mean",



      "what does that mean",



      "i am confused",



      "i'm confused",



    ].some((marker) => normalized.includes(marker))



  ) {



    return "clarify";



  }



  return null;



};







const buildQuestionClarification = (questionText) => {



  const normalized = safeText(questionText).toLowerCase();



  if (!normalized) {



    return "Sure. Let me make that simpler, then I will repeat the same question.";



  }



  if (/tell me about a time|describe a time|walk me through/.test(normalized)) {



    return "Sure. This is asking for a real example. Briefly explain the situation, what you did, and the result. I will repeat the same question.";



  }



  if (/what would you do|imagine|how would you handle/.test(normalized)) {



    return "Sure. This is a situational question. Explain what you would do first, how you would communicate, and why. I will repeat the same question.";



  }



  return "Sure. Answer directly, keep it structured, and add one clear example or outcome where possible. I will repeat the same question.";



};







const controlTurnStatus = (command) => {



  switch (safeText(command)) {



    case "repeat":



      return "Repeating the current question...";



    case "clarify":



      return "Clarifying the current question...";



    case "off_topic":



      return "Refocusing on the current question...";



    case "retry_answer":



      return "Waiting for a better answer on the same question...";



    case "end_confirm":



      return "Confirming whether to end the interview...";



    case "end_cancelled":



      return "Continuing the interview...";



    case "end_confirmed":



      return "Ending the interview...";



    default:



      return "Continuing the interview...";



  }



};







const controlTurnPrompt = (command, questionNumber, questionText) => {



  if (["end_confirm", "end_confirmed"].includes(safeText(command))) {



    return "";



  }



  return `Question ${questionNumber}. ${safeText(questionText) || "Please continue."}`;



};







const INTERVIEW_STATUS_STRIP_ITEMS = [



  { key: "mic-active", label: "Mic Active" },



  { key: "mic-muted", label: "Mic Muted" },



  { key: "ai-speaking", label: "AI Speaking" },



  { key: "evaluating", label: "Evaluating" },



];







const getInterviewPresenceMeta = ({



  started = false,



  aiSpeaking = false,



  listening = false,



  busy = false,



  fullscreenBlocked = false,



  speechRecognitionAvailable = false,



}) => {



  if (!started) {



    return {



      activeKey: "mic-muted",



      bubble: "Ready",



      headline: "AI interviewer ready",



      detail: "A live AI interviewer will guide the session, speak the questions, and react to each interview stage once you begin.",



    };



  }



  if (fullscreenBlocked) {



    return {



      activeKey: "mic-muted",



      bubble: "Paused",



      headline: "Interview paused",



      detail: "The session is waiting for fullscreen to be restored before the interviewer continues.",



    };



  }



  if (aiSpeaking) {



    return {



      activeKey: "ai-speaking",



      bubble: "Ask",



      headline: "Asking the current question",



      detail: "The interviewer is actively speaking, so you can focus on the wording before answering.",



    };



  }



  if (busy) {



    return {



      activeKey: "evaluating",



      bubble: "Thinking",



      headline: "Evaluating your answer",



      detail: "The interviewer is scoring your latest response and preparing the next step in the interview.",



    };



  }



  if (listening && speechRecognitionAvailable) {



    return {



      activeKey: "mic-active",



      bubble: "Listen",



      headline: "Mic active and listening",



      detail: "Your microphone is live right now, and the interviewer is waiting for your answer or command.",



    };



  }



  return {



    activeKey: "mic-muted",



    bubble: speechRecognitionAvailable ? "Standby" : "Type",



    headline: speechRecognitionAvailable ? "Mic muted between turns" : "Voice capture unavailable",



    detail: speechRecognitionAvailable



      ? "The interviewer is standing by until the next listen cycle, repeat request, or manual restart."



      : "Speech recognition is not available in this session, so you can type your answer and submit it manually.",



  };



};







const InterviewPresenceCard = ({ presence, showStatusStrip = true }) => (



  <div className={`voice-ai-presence-card is-${presence.activeKey}`}>



    <div className="voice-ai-presence-top">



      <div className={`voice-ai-character-stage is-${presence.activeKey}`}>



        <div className="voice-ai-character-halo" />



        <div className="voice-ai-character-bubble">{presence.bubble}</div>



        <div className="voice-ai-character-wave voice-ai-character-wave-left" />



        <div className="voice-ai-character-wave voice-ai-character-wave-right" />



        <div className="voice-ai-illustration-shell">



          <div className="voice-ai-illustration-backdrop" />



          <div className="voice-ai-illustration-orb">



            <div className="voice-ai-illustration-orb-ring" />



            <div className="voice-ai-illustration-orb-core" />



          </div>



          <div className="voice-ai-illustration-panel">



            <div className="voice-ai-illustration-panel-top">



              <span className="voice-ai-illustration-chip" />



              <span className="voice-ai-illustration-chip voice-ai-illustration-chip-muted" />



            </div>



            <div className="voice-ai-illustration-screen">



              <span className="voice-ai-illustration-line voice-ai-illustration-line-strong" />



              <span className="voice-ai-illustration-line" />



              <span className="voice-ai-illustration-line voice-ai-illustration-line-short" />



            </div>



            <div className="voice-ai-illustration-meter">



              <span className="voice-ai-illustration-meter-bar voice-ai-illustration-meter-bar-short" />



              <span className="voice-ai-illustration-meter-bar" />



              <span className="voice-ai-illustration-meter-bar voice-ai-illustration-meter-bar-tall" />



              <span className="voice-ai-illustration-meter-bar" />



              <span className="voice-ai-illustration-meter-bar voice-ai-illustration-meter-bar-short" />



            </div>



          </div>



        </div>



      </div>







      <div className="voice-ai-presence-copy">



        <div className="voice-ai-mini-label">AI Interviewer</div>



        <div className="voice-ai-presence-headline">{presence.headline}</div>



        <p className="voice-ai-copy voice-ai-presence-detail">{presence.detail}</p>



      </div>



    </div>







    {showStatusStrip ? (



      <div className="voice-ai-status-strip">



        {INTERVIEW_STATUS_STRIP_ITEMS.map((item) => (



          <div



            key={item.key}



            className={`voice-ai-status-pill ${presence.activeKey === item.key ? `is-active is-${item.key}` : ""}`}



          >



            <span className="voice-ai-status-dot" />



            <span>{item.label}</span>



          </div>



        ))}



      </div>



    ) : null}



  </div>



);







const preferredVoiceHints = [



  "google uk english female",



  "microsoft aria",



  "microsoft jenny",



  "microsoft libby",



  "microsoft sara",



  "microsoft zira",



  "samantha",



  "ava",



  "allison",



  "female",



];







const pickGentleVoice = (voices = []) => {



  if (!Array.isArray(voices) || !voices.length) return null;







  const scored = voices



    .filter((voice) => /en/i.test(`${voice.lang || ""} ${voice.name || ""}`))



    .map((voice) => {



      const name = safeText(voice.name).toLowerCase();



      const lang = safeText(voice.lang).toLowerCase();



      let score = 0;







      if (lang.startsWith("en")) score += 40;



      if (voice.localService) score += 10;



      if (/female|woman|girl/.test(name)) score += 18;







      preferredVoiceHints.forEach((hint, index) => {



        if (name.includes(hint)) {



          score += 30 - index;



        }



      });







      if (/male|man|david|mark|guy|gordon/.test(name)) score -= 8;



      return { voice, score };



    })



    .sort((left, right) => right.score - left.score);







  return scored[0]?.voice || voices[0] || null;



};







const normalizeEvaluation = (item) => ({



  ...item,



  question: safeText(item?.question),



  answer: safeText(item?.answer),



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



  count_towards_score: item?.count_towards_score !== false,



  is_control_turn: Boolean(item?.is_control_turn),



  control_command: safeText(item?.control_command),



});







function MetricTile({ label, value, tone = "#4338ca" }) {



  return (



    <div style={{ background: "white", borderRadius: 20, padding: 18, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



      <div style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", color: tone, marginBottom: 8 }}>



        {label}



      </div>



      <div style={{ fontSize: 28, fontWeight: 800, color: "#0f172a" }}>{value}</div>



    </div>



  );



}







function ScoreBars({ items = [] }) {



  if (!items.length) return null;



  return (



    <div style={{ display: "grid", gap: 12 }}>



      {items.map((item, index) => (



        <div key={`${item.question}-${index}`}>



          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 6, color: "#334155", fontSize: 14 }}>



            <span style={{ flex: 1 }}>{item.question}</span>



            <strong>{item.score}/100</strong>



          </div>



          <div style={{ height: 10, borderRadius: 999, background: "#e2e8f0", overflow: "hidden" }}>



            <div



              style={{



                width: `${Math.max(6, Math.min(100, item.score || 0))}%`,



                height: "100%",



                borderRadius: 999,



                background: item.score >= 75 ? "#10b981" : item.score >= 60 ? "#f59e0b" : "#ef4444",



              }}



            />



          </div>



        </div>



      ))}



    </div>



  );



}







function buildPayload(context) {



  let candidateName = "";



  try {



    const storedUser = JSON.parse(localStorage.getItem("user") || "{}");



    candidateName = storedUser?.first_name || "";



  } catch {



    candidateName = "";



  }



  const selectedOptions = Array.isArray(context.selectedOptions) ? context.selectedOptions.filter(Boolean) : [];



  const focusAreas = Array.isArray(context.focusAreas) ? context.focusAreas.filter(Boolean) : [];



  const effectiveOptions = focusAreas.length ? focusAreas : selectedOptions;



  const selectedMode = context.selectedMode || context.stage || "";







  return {



    category: context.category || (context.resumeText ? "resume" : "general"),



    selected_mode: selectedMode || "general",



    job_role: context.jobRole || (selectedMode !== "language" ? selectedOptions[0] : "") || "",



    primary_language:



      context.primaryLanguage ||



      context.primary_language ||



      (selectedMode === "language" ? selectedOptions[0] : "") ||



      "",



    selected_options: effectiveOptions,



    focus_areas: effectiveOptions,



    hr_round: context.hrRound || "",



    experience: context.experience || "Not specified",



    config_mode: context.configMode || "standard",



    question_count: context.customQuestionCount || context.questionCount || 10,



    practice_type: context.practiceType || "voice interview",



    interview_mode_time: context.interviewModeTime || null,



    time_mode_interval: context.timeModeInterval || null,



    resume_text: context.resumeText || "",



    resume_insights: context.resumeInsights || null,



    candidate_name: context.candidateName || candidateName || "",



  };



}







const isCanceledRequest = (error) =>



  Boolean(axios.isCancel?.(error)) ||



  error?.code === "ERR_CANCELED" ||



  error?.name === "CanceledError";







const readSavedInterview = () => {



  if (typeof window === "undefined") return null;







  try {



    const raw = window.localStorage.getItem(INTERVIEW_STORAGE_KEY);



    if (!raw) return null;



    const parsed = JSON.parse(raw);



    return parsed && typeof parsed === "object" ? parsed : null;



  } catch {



    return null;



  }



};







const clearSavedInterview = () => {



  if (typeof window === "undefined") return;



  try {



    window.localStorage.removeItem(INTERVIEW_STORAGE_KEY);



  } catch {}



};







const normalizeSavedSessionSnapshot = (snapshot) => {



  if (!snapshot || typeof snapshot !== "object") return null;







  return {



    sessionId: safeText(snapshot.sessionId || snapshot.session_id),



    providers: snapshot.providers && typeof snapshot.providers === "object" ? snapshot.providers : {},



    question: safeText(snapshot.question || snapshot.current_question),



    index: Number(snapshot.index ?? snapshot.current_index) || 0,



    total: Number(snapshot.total ?? snapshot.total_questions) || 0,



    draft: safeText(snapshot.draft),



    interim: safeText(snapshot.interim),



    latestEval: snapshot.latestEval || null,



    history: Array.isArray(snapshot.history) ? snapshot.history : Array.isArray(snapshot.evaluations) ? snapshot.evaluations : [],



    timeLeftSeconds:



      snapshot.timeLeftSeconds == null || Number(snapshot.timeLeftSeconds) < 0



        ? null



        : Number(snapshot.timeLeftSeconds),



    sessionMeta: snapshot.sessionMeta && typeof snapshot.sessionMeta === "object"



      ? snapshot.sessionMeta



      : snapshot.meta && typeof snapshot.meta === "object"



        ? snapshot.meta



        : {},



    summary: snapshot.summary && typeof snapshot.summary === "object" ? snapshot.summary : null,



  };



};







const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

const estimateSpeechTimeoutMs = (value) => {
  const wordCount = clean(value).split(" ").filter(Boolean).length;
  return Math.min(30000, Math.max(5000, wordCount * 420 + 1800));
};

const withTimeout = (promise, ms, fallbackValue) =>
  Promise.race([promise, wait(ms).then(() => fallbackValue)]);







function VoiceInterview({ embeddedContext = null, autoStart = false, startupOverlayMode = false } = {}) {



  const navigate = useNavigate();



  const location = useLocation();

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



  const effectiveState = embeddedContext || location.state;

  const forceFreshSession = Boolean(effectiveState?.forceFreshSession);

  const forceStartupFullscreenPrompt = Boolean(effectiveState?.forceStartupFullscreenPrompt);



  const savedInterviewRef = useRef(forceFreshSession ? null : readSavedInterview());



  const context = (effectiveState && Object.keys(effectiveState).length



    ? effectiveState



    : savedInterviewRef.current?.payload) || {};



  const payload = buildPayload(context);



  const SpeechRecognition =



    typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;







  const rootRef = useRef(null);



  const videoRef = useRef(null);



  const reportRef = useRef(null);



  const cameraRef = useRef(null);



  const recognitionRef = useRef(null);



  const timerRef = useRef(null);
const startupRunIdRef = useRef(0);
const pauseForFullscreenLossRef = useRef(() => {});



  const startupActiveRef = useRef(false);



  const startupPausedRef = useRef(false);



  const sessionIdRef = useRef("");



  const indexRef = useRef(0);



  const questionRef = useRef("");



  const draftRef = useRef("");



  const interimRef = useRef("");



  const busyRef = useRef(false);



  const summaryRef = useRef(null);



  const fullscreenBlockedRef = useRef(false);
  const autoStartedRef = useRef(false);
  const beginVoiceInterviewRef = useRef(null);
  const forcedStartupPromptShownRef = useRef(false);



  const dialogOpenRef = useRef(false);



  const startedRef = useRef(false);



  const autoListenRef = useRef(false);



  const speakingRef = useRef(false);



  const endRequestedRef = useRef(false);



  const finalizingRef = useRef(false);



  const preferredVoiceRef = useRef(null);



  const requestControllerRef = useRef(null);



  const flowTokenRef = useRef(0);



  const resumeModeRef = useRef("continue-answer");



  const interruptInterviewFlowRef = useRef(() => {});



  const finalizeEarlyExitRef = useRef(null);







  const [sessionId, setSessionId] = useState("");



  const [providers, setProviders] = useState({});



  const [question, setQuestion] = useState("");



  const [index, setIndex] = useState(0);



  const [total, setTotal] = useState(0);



  const [draft, setDraft] = useState("");



  const [interim, setInterim] = useState("");



  const [status, setStatus] = useState("Ready to begin.");



  const [error, setError] = useState("");



  const [started, setStarted] = useState(false);



  const [busy, setBusy] = useState(false);



  const [listening, setListening] = useState(false);



  const [aiSpeaking, setAiSpeaking] = useState(false);



  const [fullscreenBlocked, setFullscreenBlocked] = useState(false);



  const [latestEval, setLatestEval] = useState(null);



  const [history, setHistory] = useState([]);



  const [summary, setSummary] = useState(null);



  const [timeLeftSeconds, setTimeLeftSeconds] = useState(null);



  const [sessionMeta, setSessionMeta] = useState({});



  const [adaptiveData, setAdaptiveData] = useState({
    enabled: false,
    currentDifficulty: "medium",
    skillCount: 0,
    totalQuestions: 10,
    currentQuestionTimeLimit: 60,
    difficultyHistory: [],
  });

  const [currentSkill, setCurrentSkill] = useState("");



  const [showEndConfirm, setShowEndConfirm] = useState(false);



  const [showStartupCancelConfirm, setShowStartupCancelConfirm] = useState(false);



  const [showFullscreenPrompt, setShowFullscreenPrompt] = useState(false);



  const [restoreNotice, setRestoreNotice] = useState("");



  const [startupActive, setStartupActive] = useState(false);



  const [startupPaused, setStartupPaused] = useState(false);

  const [startupMessage, setStartupMessage] = useState(STARTUP_STAGE_MESSAGES[0]);



  const [interviewEntering, setInterviewEntering] = useState(false);



  const [startupMessageVisible, setStartupMessageVisible] = useState(true);



  const [startupCountdown, setStartupCountdown] = useState(null);



  const [viewportWidth, setViewportWidth] = useState(



    typeof window !== "undefined" ? window.innerWidth : 1440



  );



  const cancelSetupFullscreenGuard = useCallback(() => {
    navigate("/", { replace: true });
  }, [navigate]);



  const {
    fullscreenBlocked: setupFullscreenBlocked,
    restoreFullscreen: restoreSetupFullscreen,
    cancelFullscreenGuard: cancelSetupFullscreen,
  } = useInterviewFullscreenGuard({
    enabled: !autoStart && !started && !startupActive && !summary,
    onCancel: cancelSetupFullscreenGuard,
  });



  const dialogOpen = showEndConfirm || showStartupCancelConfirm || showFullscreenPrompt;
  useRevealFullscreenWarning(showFullscreenPrompt || (setupFullscreenBlocked && !dialogOpen));







  const applyRecoveredSession = (snapshot) => {



    const normalized = normalizeSavedSessionSnapshot(snapshot);



    if (!normalized?.sessionId) return false;







    setSessionId(normalized.sessionId);



    setProviders(normalized.providers);



    setQuestion(normalized.question);



    setIndex(normalized.index);



    setTotal(normalized.total);



    setDraft(normalized.draft);



    setInterim(normalized.interim);



    setStarted(true);



    setBusy(false);



    setListening(false);



    setAiSpeaking(false);



    setFullscreenBlocked(false);



    setLatestEval(normalized.latestEval ? normalizeEvaluation(normalized.latestEval) : null);



    setHistory(Array.isArray(normalized.history) ? normalized.history.map((item) => normalizeEvaluation(item)) : []);



    setSummary(normalized.summary ? normalized.summary : null);



    setTimeLeftSeconds(normalized.timeLeftSeconds);



    setSessionMeta(normalized.sessionMeta);



    setShowEndConfirm(false);



    setShowFullscreenPrompt(false);



    return true;



  };







  useEffect(() => {



    sessionIdRef.current = sessionId;



  }, [sessionId]);







  useEffect(() => {



    indexRef.current = index;



  }, [index]);







  useEffect(() => {



    questionRef.current = question;



  }, [question]);







  useEffect(() => {



    draftRef.current = draft;



  }, [draft]);







  useEffect(() => {



    interimRef.current = interim;



  }, [interim]);







  useEffect(() => {



    busyRef.current = busy;



  }, [busy]);







  useEffect(() => {



    summaryRef.current = summary;



  }, [summary]);







  useEffect(() => {



    fullscreenBlockedRef.current = fullscreenBlocked;



  }, [fullscreenBlocked]);







  useEffect(() => {



    startupActiveRef.current = startupActive;



  }, [startupActive, startupCountdown]);







  useEffect(() => {



    dialogOpenRef.current = dialogOpen;



  }, [dialogOpen]);







  useEffect(() => {



    startedRef.current = started;



  }, [started]);







  useEffect(() => {



    const handleResize = () => setViewportWidth(window.innerWidth);



    window.addEventListener("resize", handleResize);



    return () => window.removeEventListener("resize", handleResize);



  }, []);







  useEffect(() => {



    if (!forceFreshSession) return;



    clearSavedInterview();



    savedInterviewRef.current = null;



  }, [forceFreshSession]);







  useEffect(() => {



    const saved = savedInterviewRef.current;



    if (!saved || typeof saved !== "object") return;







    const normalized = normalizeSavedSessionSnapshot(saved);



    if (!normalized?.sessionId || normalized.summary) {



      clearSavedInterview();



      savedInterviewRef.current = null;



      return;



    }







    applyRecoveredSession(normalized);



    setStatus("Recovered your previous interview session.");



    setRestoreNotice("A saved interview session was recovered. Re-enter fullscreen to continue from where you left off.");



  }, [forceFreshSession]);







  useEffect(() => {



    const saved = savedInterviewRef.current;



    const normalized = normalizeSavedSessionSnapshot(saved);



    if (!normalized?.sessionId) return undefined;







    let cancelled = false;







    const syncSession = async () => {



      try {



        const response = await axios.get(`${API_BASE_URL}/ai-interview/session/${normalized.sessionId}`);



        if (cancelled) return;



        const remote = response.data || {};







        if (remote.is_complete && remote.summary) {



          clearSavedInterview();



          navigate(`/results/${normalized.sessionId}`, {



            replace: true,



            state: {



              report: {



                ...remote.summary,



                session_id: normalized.sessionId,



                ended_early: Boolean(remote.ended_early),



                providers: remote.providers || {},



                evaluations: Array.isArray(remote.evaluations) ? remote.evaluations.map((item) => normalizeEvaluation(item)) : [],



                answers: remote.answers || [],



                question_outline: remote.question_outline || [],



                questions_answered: Number(remote.questions_answered || 0),



                total_questions: Number(remote.total_questions || 0),



                context: remote.context || payload,



              },



              context: remote.context || payload,



            },



          });



          return;



        }







        applyRecoveredSession({



          ...remote,



          draft: normalized.draft,



          interim: normalized.interim,



          timeLeftSeconds: normalized.timeLeftSeconds,



        });



      } catch {}



    };







    void syncSession();



    return () => {



      cancelled = true;



    };



  }, [forceFreshSession, navigate, payload]);







  useEffect(() => {



    if (!started || summary || !sessionId) {



      if (summary || !started) {



        clearSavedInterview();



      }



      return;



    }







    try {



      window.localStorage.setItem(



        INTERVIEW_STORAGE_KEY,



        JSON.stringify({



          payload,



          sessionId,



          providers,



          question,



          index,



          total,



          draft,



          interim,



          status,



          history,



          latestEval,



          timeLeftSeconds,



          sessionMeta,



          savedAt: Date.now(),



        })



      );



    } catch {}



  }, [



    draft,



    history,



    index,



    interim,



    latestEval,



    payload,



    providers,



    question,



    sessionId,



    sessionMeta,



    started,



    status,



    summary,



    timeLeftSeconds,



    total,



  ]);







  useEffect(() => {



    if (!window.speechSynthesis) return undefined;







    const refreshVoices = () => {



      preferredVoiceRef.current = pickGentleVoice(window.speechSynthesis.getVoices());



    };







    refreshVoices();



    window.speechSynthesis.onvoiceschanged = refreshVoices;







    return () => {



      if (window.speechSynthesis.onvoiceschanged === refreshVoices) {



        window.speechSynthesis.onvoiceschanged = null;



      }



    };



  }, []);







  useEffect(() => {



    if (!startupActive || startupCountdown != null) return undefined;







    setStartupMessageVisible(true);



    let messageIndex = 0;



    const intervalId = window.setInterval(() => {



      setStartupMessageVisible(false);



      window.setTimeout(() => {



        messageIndex = (messageIndex + 1) % STARTUP_STAGE_MESSAGES.length;



        setStartupMessage(STARTUP_STAGE_MESSAGES[messageIndex]);



        setStartupMessageVisible(true);



      }, 260);



    }, 1700);







    return () => window.clearInterval(intervalId);



  }, [startupActive, startupCountdown]);







  const resolveTimerMinutes = () => {



    if (payload.config_mode === "time" && payload.time_mode_interval) {



      return Number(payload.time_mode_interval) || null;



    }



    if (payload.practice_type === "interview" && payload.interview_mode_time) {



      return Number(payload.interview_mode_time) || null;



    }



    return null;



  };







const isStartupLaunchActive = (runId) =>
  startupRunIdRef.current === runId &&
  startupActiveRef.current &&
  !startupPausedRef.current &&
  !fullscreenBlockedRef.current &&
  !dialogOpenRef.current &&
  !summaryRef.current &&
  !endRequestedRef.current &&
  !finalizingRef.current;

const isStartupLaunchCurrent = (runId) =>
  startupRunIdRef.current === runId &&
  startupActiveRef.current &&
  !startupPausedRef.current &&
  !summaryRef.current &&
  !endRequestedRef.current &&
  !finalizingRef.current;

const runStartupLaunchCountdown = async (runId) => {
  for (let remaining = STARTUP_LAUNCH_COUNTDOWN_SECONDS; remaining > 0; remaining -= 1) {
    if (!isStartupLaunchCurrent(runId)) return false;
    setStartupCountdown(remaining);
    await wait(1000);
    if (!isStartupLaunchCurrent(runId)) return false;
  }

  setStartupCountdown(null);
  return true;
};
  const buildLocalFallbackSummary = (endedEarly = false) => {



    const evaluations = history.map((item) => normalizeEvaluation(item));



    const scoredEvaluations = evaluations.filter((item) => item.count_towards_score !== false);



    const scores = scoredEvaluations.map((item) => safeScore(item.score));



    const overallScore = scores.length



      ? Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)



      : 0;







    return {



      overall_score: overallScore,



      ended_early: endedEarly,



      summary: evaluations.length



        ? "The interview was ended before the backend completion step finished, so this report was recovered from the answers already evaluated on this page."



        : "The interview ended before any evaluated answers were available for a full report.",



      top_strengths: Array.from(new Set(scoredEvaluations.flatMap((item) => item.strengths || []))).slice(0, 4),



      improvement_areas: Array.from(new Set(scoredEvaluations.flatMap((item) => item.gaps || []))).slice(0, 4),



      strongest_questions: scoredEvaluations.filter((item) => item.score >= 75).map((item) => item.question).slice(0, 3),



      needs_work_questions: scoredEvaluations.filter((item) => item.score < 60).map((item) => item.question).slice(0, 3),



      questions_answered: evaluations.length,



      total_questions: total || Math.max(evaluations.length, 1),



      question_outline: evaluations.map((item, index) => ({



        id: item.question_id || String(index + 1),



        question: item.question,



        question_type: item.question_type || "practical",



        score: safeScore(item.score),



      })),



      evaluations,



      providers,



      user: (() => {



        try {



          return JSON.parse(localStorage.getItem("user") || "null");



        } catch {



          return null;



        }



      })(),



      context: payload,



    };



  };







  const openResultsPage = async (reportData, sessionKey) => {



    const resolvedSessionId = safeText(sessionKey) || safeText(sessionIdRef.current) || `local-${Date.now()}`;

    summaryRef.current = reportData;
    endRequestedRef.current = true;
    clearInterviewFullscreenGuard();
    stopListening();
    stopSpeech();
    stopCamera();
    await exitFullscreenForResults();



    navigate(`/results/${resolvedSessionId}`, {



      replace: true,



      state: {



        report: {



          ...reportData,



          session_id: resolvedSessionId,



        },



        context: payload,



      },



    });



  };







  const cancelActiveRequest = () => {



    if (requestControllerRef.current) {



      requestControllerRef.current.abort();



      requestControllerRef.current = null;



    }



  };







  const stopSpeech = () => {



    if (window.speechSynthesis) window.speechSynthesis.cancel();



    speakingRef.current = false;



    setAiSpeaking(false);



  };







  const speak = (text, { flowToken = null } = {}) =>



    new Promise((resolve) => {



      const value = clean(text);



      if (!value || !window.speechSynthesis) return resolve(true);



      if (flowToken != null && flowToken !== flowTokenRef.current) {



        return resolve(false);



      }







      stopSpeech();



      const utterance = new SpeechSynthesisUtterance(value);



      const voice = preferredVoiceRef.current || pickGentleVoice(window.speechSynthesis.getVoices());



      if (voice) {



        utterance.voice = voice;



        utterance.lang = voice.lang || "en-US";



      } else {



        utterance.lang = "en-US";



      }



      utterance.rate = 0.94;



      utterance.pitch = 1.02;



      utterance.volume = 1;



      speakingRef.current = true;



      setAiSpeaking(true);



      let settled = false;
      let speechTimeoutId = null;

      const finishSpeech = (result) => {
        if (settled) return;
        settled = true;
        if (speechTimeoutId) window.clearTimeout(speechTimeoutId);
        speakingRef.current = false;
        setAiSpeaking(false);
        resolve(result);
      };



      utterance.onend = () => {



        finishSpeech(flowToken == null || flowToken === flowTokenRef.current);



      };



      utterance.onerror = () => finishSpeech(true);



      speechTimeoutId = window.setTimeout(() => finishSpeech(true), estimateSpeechTimeoutMs(value));



      try {
        window.speechSynthesis.speak(utterance);
      } catch {
        finishSpeech(true);
      }



    });







  const stopListening = ({ keepAutoListen = false } = {}) => {



    if (!keepAutoListen) autoListenRef.current = false;



    if (timerRef.current) clearTimeout(timerRef.current);



    timerRef.current = null;



    if (recognitionRef.current) {



      recognitionRef.current.onresult = null;



      recognitionRef.current.onerror = null;



      recognitionRef.current.onend = null;



      try {



        recognitionRef.current.stop();



      } catch {}



    }



    recognitionRef.current = null;



    setListening(false);



  };







  const interruptInterviewFlow = () => {



    flowTokenRef.current += 1;



    stopListening();



    stopSpeech();



  };







  const rememberResumeMode = () => {



    resumeModeRef.current = speakingRef.current ? "repeat-question" : "continue-answer";



  };







  const isVoiceFlowActive = (flowToken) =>



    flowToken === flowTokenRef.current &&



    !dialogOpenRef.current &&



    !fullscreenBlockedRef.current &&



    !summaryRef.current &&



    !endRequestedRef.current &&



    !finalizingRef.current;







  const ensureFullscreen = async () => {



    if (isFullscreenActive()) return true;



    await requestInterviewFullscreen(document.documentElement);



    if (!isFullscreenActive()) throw new Error("Fullscreen did not start.");



    return true;



  };







  const startCamera = async () => {



    if (cameraRef.current) {



      await attachCameraPreview();



      return true;



    }



    if (!navigator.mediaDevices?.getUserMedia) {



      throw new Error("Camera access is not supported in this browser.");



    }



    const stream = await navigator.mediaDevices.getUserMedia({



      video: {



        facingMode: "user",



        width: { ideal: 640 },



        height: { ideal: 360 },



      },



      audio: false,



    });



    cameraRef.current = stream;



    if (videoRef.current) {



      videoRef.current.srcObject = stream;



      videoRef.current.muted = true;



      videoRef.current.playsInline = true;



      void videoRef.current.play().catch(() => {});



    }



    return true;



  };







  const stopCamera = () => {



    if (cameraRef.current) cameraRef.current.getTracks().forEach((track) => track.stop());



    cameraRef.current = null;



  };



  const exitFullscreenForResults = async () => {



    try {



      const exitFullscreen =
        document.exitFullscreen ||
        document.webkitExitFullscreen ||
        document.msExitFullscreen;



      if (isFullscreenActive() && exitFullscreen) {



        await exitFullscreen.call(document);



      }



    } catch {}



  };







  const attachCameraPreview = async () => {



    if (!cameraRef.current || !videoRef.current) {



      return;



    }







    videoRef.current.srcObject = cameraRef.current;



    videoRef.current.muted = true;



    videoRef.current.playsInline = true;







    try {



      void videoRef.current.play().catch(() => {});



    } catch {}



  };







  const authHeaders = () => {



    const token = localStorage.getItem("token");



    return token ? { Authorization: `Bearer ${token}` } : {};



  };







  const runVoiceTurn = async ({ preface = "", prompt = "", restartListening = true } = {}) => {



    const flowToken = flowTokenRef.current + 1;



    flowTokenRef.current = flowToken;







    if (preface) {



      const prefaceFinished = await speak(preface, { flowToken });



      if (!prefaceFinished || !isVoiceFlowActive(flowToken)) return false;



    }







    if (prompt) {



      const promptFinished = await speak(prompt, { flowToken });



      if (!promptFinished || !isVoiceFlowActive(flowToken)) return false;



    }







    if (!restartListening) {



      return isVoiceFlowActive(flowToken);



    }







    if (!isVoiceFlowActive(flowToken)) return false;







    if (SpeechRecognition) {



      startListening();



    } else {



      setStatus("Speech recognition is unavailable. You can type and submit your answer.");



    }







    return true;



  };







  const startListening = () => {



    if (



      !SpeechRecognition ||



      fullscreenBlockedRef.current ||



      dialogOpenRef.current ||



      busyRef.current ||



      summaryRef.current ||



      endRequestedRef.current ||



      finalizingRef.current



    ) return;



    stopListening({ keepAutoListen: true });



    autoListenRef.current = true;



    const recognition = new SpeechRecognition();



    recognition.lang = "en-US";



    recognition.continuous = true;



    recognition.interimResults = true;







    recognition.onstart = () => {



      setListening(true);



      setStatus("Listening for your answer...");



    };







    recognition.onresult = (event) => {



      let finalText = "";



      let interimText = "";



      for (let i = event.resultIndex; i < event.results.length; i += 1) {



        const piece = event.results[i][0]?.transcript || "";



        if (event.results[i].isFinal) finalText += ` ${piece}`;



        else interimText += ` ${piece}`;



      }







      if (clean(finalText)) setDraft((prev) => clean(`${prev} ${finalText}`));



      setInterim(clean(interimText));



    };







    recognition.onerror = (event) => {



      setListening(false);



      if (event.error === "not-allowed") {



        autoListenRef.current = false;



        setError("Microphone access was blocked. Please allow microphone access.");



      }



      if (event.error === "audio-capture") {



        autoListenRef.current = false;



        setError("Microphone could not capture audio. Please check your device.");



      }



    };







    recognition.onend = () => {



      setListening(false);



      recognitionRef.current = null;



      if (



        autoListenRef.current &&



        !busyRef.current &&



        !summaryRef.current &&



        !fullscreenBlockedRef.current &&



        !dialogOpenRef.current &&



        !endRequestedRef.current &&



        !finalizingRef.current &&



        !speakingRef.current



      ) {



        window.setTimeout(() => startListening(), 250);



      }



    };



    recognitionRef.current = recognition;



    recognition.start();



  };







  const finishInterview = async (activeSessionId, { endedEarly = false } = {}) => {



    let controller = null;







    try {



      if (!activeSessionId) {



        const fallbackSummary = buildLocalFallbackSummary(endedEarly);



        setSummary(fallbackSummary);



        setStatus(endedEarly ? "Interview ended early." : "Interview completed.");



        await openResultsPage(fallbackSummary, fallbackSummary.session_id);



        return;



      }







      if (endedEarly && history.length) {



        const fallbackSummary = buildLocalFallbackSummary(true);



        setSummary(fallbackSummary);



        setStatus("Interview ended early.");



        await openResultsPage(fallbackSummary, activeSessionId);



        void axios.post(



          `${API_BASE_URL}/ai-interview/complete`,



          { session_id: activeSessionId, ended_early: true },



          { headers: authHeaders() }



        ).catch(() => {});



        return;



      }







      controller = new AbortController();



      requestControllerRef.current = controller;



      const response = await axios.post(



        `${API_BASE_URL}/ai-interview/complete`,



        { session_id: activeSessionId, ended_early: endedEarly },



        { headers: authHeaders(), signal: controller.signal }



      );



      const normalizedSummary = {



        ...response.data,



        overall_score: safeScore(response.data?.overall_score),



        summary: safeText(response.data?.summary),



        top_strengths: safeTextList(response.data?.top_strengths),



        improvement_areas: safeTextList(response.data?.improvement_areas),



        strongest_questions: safeTextList(response.data?.strongest_questions),



        needs_work_questions: safeTextList(response.data?.needs_work_questions),



        evaluations: Array.isArray(response.data?.evaluations)



          ? response.data.evaluations.map((item) => normalizeEvaluation(item))



          : [],



      };



      setSummary(normalizedSummary);



      setProviders((prev) => ({ ...prev, ...(response.data.providers || {}) }));



      setStatus(endedEarly ? "Interview ended early." : "Interview completed.");



      await openResultsPage(normalizedSummary, response.data?.session_id || activeSessionId);



    } catch (requestError) {



      if (isCanceledRequest(requestError)) return;







      const message = safeErrorText(



        requestError.response?.data?.detail ||



        requestError.response?.data ||



        requestError.message ||



        "Failed to complete the interview."



      );



      const fallbackSummary = {



        ...buildLocalFallbackSummary(endedEarly),



        summary: history.length



          ? `${buildLocalFallbackSummary(endedEarly).summary} Backend completion issue: ${message}`



          : "The interview ended before the backend completion step finished, so a local report was created from the information available on this page.",



      };



      setSummary(fallbackSummary);



      setStatus(endedEarly ? "Interview ended early." : "Interview completed.");



      await openResultsPage(fallbackSummary, fallbackSummary.session_id);



    } finally {



      if (requestControllerRef.current === controller) {



        requestControllerRef.current = null;



      }



      stopListening();



      stopSpeech();



      setTimeLeftSeconds(null);



    }



  };







  const resumeInterviewAfterPause = async ({ restoredFullscreen = false } = {}) => {



    if (



      summaryRef.current ||



      finalizingRef.current ||



      !startedRef.current ||



      dialogOpenRef.current ||



      fullscreenBlockedRef.current



    ) {



      return;



    }







    if (resumeModeRef.current === "repeat-question") {



      setStatus("Resuming interview...");



      await runVoiceTurn({



        preface: restoredFullscreen



          ? "Fullscreen restored. I will repeat the current question."



          : "Resuming the interview. I will repeat the current question.",



        prompt: `Question ${indexRef.current + 1}. ${safeText(questionRef.current) || "Please continue."}`,



      });



      return;



    }







    setStatus("Resuming interview...");



    await runVoiceTurn({



      preface: restoredFullscreen



        ? "Fullscreen restored. Please continue your answer."



        : "Resuming the interview. Please continue your answer.",



    });



  };







const cancelStartupPause = () => {
  startupRunIdRef.current += 1;
  startupPausedRef.current = false;
  startedRef.current = false;
  setStartupPaused(false);
  setStartupCountdown(null);
  setStartupActive(false);
  startupActiveRef.current = false;
  setShowStartupCancelConfirm(false);
  setShowFullscreenPrompt(false);
  setFullscreenBlocked(false);
  fullscreenBlockedRef.current = false;
  dialogOpenRef.current = false;
  stopSpeech();
  stopListening();
  stopCamera();
  setStarted(false);
  setBusy(false);
  setSessionId("");
  setProviders({});
  setQuestion("");
  setCurrentSkill("");
  setTotal(0);
  setIndex(0);
  setTimeLeftSeconds(null);
  setSessionMeta({});
  setError("");
  setStatus("Interview start cancelled.");
  clearInterviewFullscreenGuard();
  navigate("/", { replace: true });
};

const confirmStartupCancel = () => {
  setShowFullscreenPrompt(false);
  setShowStartupCancelConfirm(true);
  dialogOpenRef.current = true;
};

const pauseForFullscreenLoss = ({ duringStartup = false } = {}) => {
  if (summaryRef.current || endRequestedRef.current || finalizingRef.current) return;
  if (dialogOpenRef.current && fullscreenBlockedRef.current) return;

  cancelActiveRequest();

  if (duringStartup) {
    startupRunIdRef.current += 1;
    startupActiveRef.current = false;
    startupPausedRef.current = true;
    setStartupPaused(true);
    setStartupActive(false);
    setStartupCountdown(null);
    stopSpeech();
    stopListening();
    stopCamera();
    setStarted(false);
    setBusy(false);
    setQuestion("");
    setSessionId("");
    setProviders({});
    setSessionMeta({});
    setTotal(0);
    setIndex(0);
    setTimeLeftSeconds(null);
    setStatus("Interview start paused until fullscreen is restored.");
  } else {
    rememberResumeMode();
    interruptInterviewFlowRef.current?.();
    setStatus("Interview paused until fullscreen is restored.");
  }

  setFullscreenBlocked(true);
  fullscreenBlockedRef.current = true;
  dialogOpenRef.current = true;
  setShowEndConfirm(false);
  setShowStartupCancelConfirm(false);
  setShowFullscreenPrompt(true);
  setError("");
};

pauseForFullscreenLossRef.current = pauseForFullscreenLoss;

useEffect(() => {
  if (
    !startupActive ||
    started ||
    dialogOpen ||
    summary ||
    startupMessage !== STARTUP_STAGE_MESSAGES[4]
  ) {
    return undefined;
  }

  const timeoutId = window.setTimeout(() => {
    if (
      startupActiveRef.current &&
      !startedRef.current &&
      !dialogOpenRef.current &&
      !summaryRef.current &&
      !endRequestedRef.current &&
      !finalizingRef.current
    ) {
      pauseForFullscreenLossRef.current({ duringStartup: true });
    }
  }, STARTUP_HANDOFF_STALL_MS);

  return () => window.clearTimeout(timeoutId);
}, [startupActive, started, dialogOpen, summary, startupMessage]);

  const finalizeEarlyExit = async ({ closingMessage = EARLY_END_CLOSING_MESSAGE } = {}) => {



    if (finalizingRef.current || summaryRef.current) return;



    finalizingRef.current = true;



    endRequestedRef.current = true;



    dialogOpenRef.current = false;



    setShowEndConfirm(false);



    setShowFullscreenPrompt(false);



    setFullscreenBlocked(false);



    fullscreenBlockedRef.current = false;



    setBusy(true);



    setError("");



    setStatus("Ending interview and preparing your results...");







    try {



      interruptInterviewFlow();



      cancelActiveRequest();



      await speak(closingMessage);



      await finishInterview(sessionIdRef.current, { endedEarly: true });



    } catch (requestError) {



      if (isCanceledRequest(requestError)) return;







      setError(



        safeErrorText(



          requestError.response?.data?.detail ||



          requestError.response?.data ||



          requestError.message ||



          "Failed to end the interview."



        )



      );



      setStatus("Could not end the interview.");



      finalizingRef.current = false;



      endRequestedRef.current = false;



      setBusy(false);



    }



  };







  interruptInterviewFlowRef.current = interruptInterviewFlow;



  finalizeEarlyExitRef.current = finalizeEarlyExit;







  const submitAnswer = async () => {



    const answer = clean(`${draftRef.current} ${interimRef.current}`);



    if (!answer || !sessionIdRef.current || busyRef.current || summaryRef.current || finalizingRef.current) return;







    const controlCommand = detectInterviewControlCommand(answer);



    if (controlCommand) {



      stopListening();



      setDraft("");



      setInterim("");



      setError("");



      setIndex(indexRef.current);



      setQuestion(safeText(questionRef.current) || "");



      setStatus(controlCommand === "repeat" ? "Repeating the current question..." : "Clarifying the current question...");



      await runVoiceTurn({



        preface:



          controlCommand === "repeat"



            ? "Sure. I will repeat the same question."



            : buildQuestionClarification(questionRef.current),



        prompt: `Question ${indexRef.current + 1}. ${safeText(questionRef.current) || "Please continue."}`,



      });



      return;



    }







    stopListening();



    setBusy(true);



    setStatus("Evaluating your answer...");



    setError("");







    try {



      const controller = new AbortController();



      requestControllerRef.current = controller;



      const response = await axios.post(



        `${API_BASE_URL}/ai-interview/evaluate`,



        {



          session_id: sessionIdRef.current,



          question_index: indexRef.current,



          answer,



        },



        {



          signal: controller.signal,



        }



      );



      if (requestControllerRef.current === controller) {



        requestControllerRef.current = null;



      }



      if (



        finalizingRef.current ||



        summaryRef.current ||



        dialogOpenRef.current ||



        fullscreenBlockedRef.current ||



        endRequestedRef.current



      ) {



        return;



      }







      const result = {



        ...normalizeEvaluation(response.data),



        next_question: safeText(response.data?.next_question),



      };



      const isControlTurn = Boolean(response.data?.is_control_turn);



      const shouldEndInterview = Boolean(response.data?.should_end_interview);



      const progressCurrent = Number(response.data?.progress?.current);



      const progressTotal = Number(response.data?.progress?.total);



      setProviders((prev) => ({



        ...prev,



        ...(response.data?.providers || {}),



        evaluation_provider: isControlTurn ? prev.evaluation_provider : result.provider || prev.evaluation_provider,



      }));



      if (Number.isFinite(progressTotal) && progressTotal > 0) {



        setTotal(progressTotal);



      }







      setDraft("");



      setInterim("");







      if (isControlTurn) {



        const controlIndex = Number.isFinite(Number(response.data?.question_index))



          ? Number(response.data.question_index)



          : indexRef.current;



        const currentQuestionText =



          safeText(response.data?.question) ||



          result.next_question ||



          safeText(questionRef.current) ||



          "Please continue.";



        setIndex(controlIndex);



        setQuestion(currentQuestionText);



        setStatus(controlTurnStatus(result.control_command));



        if (shouldEndInterview) {



          await finalizeEarlyExitRef.current?.({



            closingMessage: result.assistant_reply || EARLY_END_CLOSING_MESSAGE,



          });



          return;



        }



        await runVoiceTurn({



          preface: result.assistant_reply || "Sure. I will repeat the same question.",



          prompt: controlTurnPrompt(



            result.control_command,



            controlIndex + 1,



            currentQuestionText



          ),



        });



        return;



      }







      setLatestEval(result);



      setHistory((prev) => [...prev, result]);



      // Update adaptive data if available
      if (adaptiveData.enabled && response.data?.difficulty_adjusted_to) {
        setAdaptiveData((prev) => {
          const newDifficulty = response.data.difficulty_adjusted_to;
          const timeMap = {
            "easy": 45,
            "medium": 60,
            "hard": 90,
          };
          return {
            ...prev,
            currentDifficulty: newDifficulty,
            currentQuestionTimeLimit: timeMap[newDifficulty] || 60,
            difficultyHistory: [...prev.difficultyHistory, newDifficulty],
          };
        });
        // Extract current skill from response
        if (response.data?.current_skill) {
          setCurrentSkill(response.data.current_skill);
        }
      }



      if (result.is_complete) {



        await speak(result.assistant_reply || NATURAL_END_CLOSING_MESSAGE);



        await finishInterview(sessionIdRef.current);



      } else {



        const nextIndex = Number.isFinite(progressCurrent) && progressCurrent >= 0



          ? progressCurrent



          : indexRef.current + 1;



        setIndex(nextIndex);



        setQuestion(result.next_question || "");



        await runVoiceTurn({



          preface: result.assistant_reply || "Thank you. Let us continue.",



          prompt: `Question ${nextIndex + 1}. ${result.next_question || "Please continue."}`,



        });



      }



    } catch (requestError) {



      if (requestControllerRef.current?.signal?.aborted) {



        requestControllerRef.current = null;



      }



      if (isCanceledRequest(requestError)) return;







      setError(



        safeErrorText(



          requestError.response?.data?.detail ||



          requestError.response?.data ||



          requestError.message ||



          "Failed to evaluate the answer."



        )



      );



      setStatus("Evaluation failed.");



    } finally {



      if (!finalizingRef.current) {



        setBusy(false);



      }



    }



  };







const beginVoiceInterview = async () => {
  const startupRunId = startupRunIdRef.current + 1;
  startupRunIdRef.current = startupRunId;

  setBusy(true);
  setError("");
  setLatestEval(null);
  setHistory([]);
  setSummary(null);
  setDraft("");
  setInterim("");
  endRequestedRef.current = false;
  finalizingRef.current = false;
  dialogOpenRef.current = false;
  setShowEndConfirm(false);
  setShowStartupCancelConfirm(false);
  setShowFullscreenPrompt(false);
  setFullscreenBlocked(false);
  fullscreenBlockedRef.current = false;
  startupPausedRef.current = false;
  setStartupPaused(false);
  setStartupActive(true);
  startupActiveRef.current = true;
  setStartupMessage(STARTUP_STAGE_MESSAGES[0]);
  setStartupMessageVisible(true);
  setStartupCountdown(null);
  setInterviewEntering(false);
  setStatus("Starting interview...");
  setQuestion("");
  setCurrentSkill("");
  startedRef.current = false;
  setStarted(false);

  try {
    if (autoStart && forceStartupFullscreenPrompt && !forcedStartupPromptShownRef.current) {
      forcedStartupPromptShownRef.current = true;
      setStartupMessage("Fullscreen confirmation required");
      await exitFullscreenForResults();
      pauseForFullscreenLossRef.current({ duringStartup: true });
      return;
    }

    if (!autoStart) {
      setStartupMessage("Entering fullscreen interview room");
      await ensureFullscreen();
    }
    clearInterviewFullscreenGuard();
    if (!isStartupLaunchActive(startupRunId)) return;

    setRestoreNotice("");
    setStartupMessage(STARTUP_STAGE_MESSAGES[1]);
    setStatus("Preparing your AI interviewer, first question, and interview room...");

    const cameraSetup = withTimeout(
      startCamera()
        .then(async () => {
          if (!isStartupLaunchActive(startupRunId)) {
            stopCamera();
            return new Error("Camera setup was interrupted.");
          }
          await attachCameraPreview();
          if (!isStartupLaunchActive(startupRunId)) {
            stopCamera();
            return new Error("Camera setup was interrupted.");
          }
          return null;
        })
        .catch((cameraError) => cameraError),
      STARTUP_CAMERA_TIMEOUT_MS,
      new Error("Camera setup timed out.")
    );

    const controller = new AbortController();
    requestControllerRef.current = controller;
    setStartupMessage(STARTUP_STAGE_MESSAGES[2]);
    const response = await axios.post(`${API_BASE_URL}/ai-interview/start`, payload, {
      headers: authHeaders(),
      signal: controller.signal,
    });
    if (requestControllerRef.current === controller) {
      requestControllerRef.current = null;
    }
    if (!isStartupLaunchActive(startupRunId)) {
      const cameraError = await cameraSetup;
      if (!cameraError) stopCamera();
      return;
    }

    const data = response.data;
    const cameraError = await cameraSetup;
    if (!isStartupLaunchActive(startupRunId)) {
      if (!cameraError) stopCamera();
      return;
    }

    setSessionId(data.session_id);
    setProviders(data.providers || {});
    setSessionMeta(data.meta || {});
    setQuestion(safeText(data.current_question));
    setTotal(data.total_questions || 0);
    setIndex(0);
    
    // Handle adaptive interview data
    if (data.adaptive_enabled) {
      setAdaptiveData({
        enabled: true,
        currentDifficulty: data.starting_difficulty || "medium",
        skillCount: data.skill_count || 0,
        totalQuestions: data.total_questions || 10,
        currentQuestionTimeLimit: data.time_limit_map?.[data.starting_difficulty] || 60,
        difficultyHistory: [data.starting_difficulty || "medium"],
      });
      // Extract current skill from initial response
      if (data.current_skill) {
        setCurrentSkill(data.current_skill);
      }
    }
    
    setStatus(
      cameraError
        ? "Interview ready. Camera preview is unavailable, but the voice interview will start shortly."
        : "Interview ready. Starting shortly."
    );
    setStartupMessage(STARTUP_STAGE_MESSAGES[3]);
    await wait(250);
    if (!isStartupLaunchActive(startupRunId)) return;

    setStartupMessage(STARTUP_STAGE_MESSAGES[4]);
    const countdownCompleted = await runStartupLaunchCountdown(startupRunId);
    if (!countdownCompleted || !isStartupLaunchCurrent(startupRunId)) return;

    if (!isFullscreenActive()) {
      pauseForFullscreenLossRef.current({ duringStartup: true });
      return;
    }

    dialogOpenRef.current = false;
    setShowEndConfirm(false);
    setShowStartupCancelConfirm(false);
    setShowFullscreenPrompt(false);

    startedRef.current = true;
    setStarted(true);
    setFullscreenBlocked(false);
    fullscreenBlockedRef.current = false;
    const timerMinutes = resolveTimerMinutes();
    setTimeLeftSeconds(timerMinutes ? timerMinutes * 60 : null);
    setStatus(
      cameraError
        ? "Interview ready. Camera preview is unavailable, but the voice interview is starting now."
        : "Interview ready. Starting now."
    );
    setStartupActive(false);
    startupActiveRef.current = false;
    busyRef.current = false;
    setBusy(false);
    setInterviewEntering(true);
    await wait(650);
    if (!startedRef.current && !isStartupLaunchActive(startupRunId)) return;
    setInterviewEntering(false);
    const firstTurnStarted = await runVoiceTurn({
      preface: safeText(data.assistant_intro) || "Hello. Let us begin.",
      prompt: `Question 1. ${safeText(data.current_question)}`,
    });
    if (!firstTurnStarted && isVoiceFlowActive(flowTokenRef.current)) {
      startListening();
    }
  } catch (requestError) {
    if (
      isCanceledRequest(requestError) ||
      startupRunId !== startupRunIdRef.current ||
      startupPausedRef.current ||
      fullscreenBlockedRef.current
    ) {
      return;
    }

    const mediaErrorName = requestError?.name || requestError?.cause?.name;
    const isMediaError =
      mediaErrorName === "NotAllowedError" ||
      mediaErrorName === "NotFoundError" ||
      mediaErrorName === "NotReadableError";
    setError(
      isMediaError
        ? "Camera or microphone access failed on the interview page. Please allow access and try again."
        : safeErrorText(
            requestError.response?.data?.detail ||
            requestError.response?.data ||
            requestError.message ||
            "Failed to start the interview."
          )
    );
    setStarted(false);
    setQuestion("");
    setStatus("Interview could not start.");
    setStartupActive(false);
    startupActiveRef.current = false;
    setStartupCountdown(null);
  } finally {
    if (startupRunId === startupRunIdRef.current) {
      setBusy(false);
    }
  }
};
beginVoiceInterviewRef.current = beginVoiceInterview;
  const restoreFullscreen = async () => {



    try {



      await ensureFullscreen();



      if (startupPausedRef.current) {



        dialogOpenRef.current = false;



        setShowFullscreenPrompt(false);
        setShowStartupCancelConfirm(false);



        setFullscreenBlocked(false);



        fullscreenBlockedRef.current = false;



        setError("");



        setRestoreNotice("");



        startupPausedRef.current = false;



        setStartupPaused(false);



        await beginVoiceInterview();



        return;



      }



      await startCamera();



      await attachCameraPreview();



      dialogOpenRef.current = false;



      setShowFullscreenPrompt(false);
      setShowStartupCancelConfirm(false);



      setFullscreenBlocked(false);



      fullscreenBlockedRef.current = false;



      setError("");



      setRestoreNotice("");



      await resumeInterviewAfterPause({ restoredFullscreen: true });



    } catch (requestError) {



      setError(safeErrorText(requestError.message || "Fullscreen is required to continue."));



    }



  };

  useEffect(() => {
    if (!autoStart || autoStartedRef.current || started || busy || summary) return;

    autoStartedRef.current = true;
    void beginVoiceInterviewRef.current?.();
  }, [autoStart, started, busy, summary]);







  const handleEndInterview = () => {



    if (summaryRef.current || finalizingRef.current) {



      return;



    }







    rememberResumeMode();



    interruptInterviewFlow();



    cancelActiveRequest();



    dialogOpenRef.current = true;



    setError("");



    setStatus("Interview paused while you confirm the next step.");



    setShowEndConfirm(true);



  };







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







    const reportTitle = safeText(title) || "Interview Report";



    const reportHtml = reportRef.current.innerHTML;







    printWindow.document.write(`



      <!doctype html>



      <html>



        <head>



          <title>${reportTitle} Report</title>



          <meta charset="utf-8" />



          <style>



            body {



              font-family: Arial, sans-serif;



              margin: 24px;



              color: #0f172a;



              background: #ffffff;



            }



            h1, h2, h3, h4 {



              color: #0f172a;



              margin-top: 0;



            }



            p, div, span {



              line-height: 1.6;



            }



            button {



              display: none !important;



            }



            svg {



              max-width: 100%;



            }



            .print-block {



              break-inside: avoid;



              page-break-inside: avoid;



            }



            @media print {



              body {



                margin: 12px;



              }



            }



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



    setTimeout(() => {



      printWindow.print();



    }, 300);



  };







useEffect(() => {
  const onFullscreenChange = () => {
    if (
      (!startedRef.current && !startupActiveRef.current) ||
      summaryRef.current ||
      endRequestedRef.current ||
      finalizingRef.current
    ) {
      return;
    }

    if (!isFullscreenActive()) {
      pauseForFullscreenLossRef.current({
        duringStartup: startupActiveRef.current && !startedRef.current,
      });
    }
  };

  document.addEventListener("fullscreenchange", onFullscreenChange);
  document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  document.addEventListener("MSFullscreenChange", onFullscreenChange);
  return () => {
    document.removeEventListener("fullscreenchange", onFullscreenChange);
    document.removeEventListener("webkitfullscreenchange", onFullscreenChange);
    document.removeEventListener("MSFullscreenChange", onFullscreenChange);
  };
}, []);

useEffect(() => {
  const onKeyDown = (event) => {
    if (event.key !== "Escape") return;
    if (
      (!startedRef.current && !startupActiveRef.current) ||
      summaryRef.current ||
      endRequestedRef.current ||
      finalizingRef.current ||
      (dialogOpenRef.current && fullscreenBlockedRef.current)
    ) {
      return;
    }

    const duringStartup = startupActiveRef.current && !startedRef.current;
    window.setTimeout(() => {
      if (!isFullscreenActive() || duringStartup) {
        pauseForFullscreenLossRef.current({ duringStartup });
      }
    }, 0);
  };

  window.addEventListener("keydown", onKeyDown, true);
  return () => window.removeEventListener("keydown", onKeyDown, true);
}, []);
  useEffect(() => {



    if (



      !started ||



      startupActive ||



      fullscreenBlocked ||



      dialogOpen ||



      summary ||



      endRequestedRef.current ||



      finalizingRef.current ||



      isFullscreenActive()



    ) {



      return;



    }







    dialogOpenRef.current = true;



    setShowEndConfirm(false);



    setShowFullscreenPrompt(true);



    setFullscreenBlocked(true);



    fullscreenBlockedRef.current = true;



    setStatus("Interview paused until fullscreen is restored.");



    setError("");



  }, [started, startupActive, fullscreenBlocked, dialogOpen, summary]);







  useEffect(() => {



    if (!started || summary || finalizingRef.current) return undefined;







    const handleBeforeUnload = (event) => {



      event.preventDefault();



      event.returnValue = "Your interview is still running. Leaving now may interrupt the session.";



      return event.returnValue;



    };







    window.addEventListener("beforeunload", handleBeforeUnload);



    return () => window.removeEventListener("beforeunload", handleBeforeUnload);



  }, [started, summary]);







  useEffect(() => {



    return () => {



      cancelActiveRequest();



      flowTokenRef.current += 1;



      stopListening();



      stopSpeech();



      stopCamera();



    };



  }, []);







  useEffect(() => {



    if (started && cameraRef.current && videoRef.current) {



      attachCameraPreview();



    }



  }, [started]);







  useEffect(() => {



    if (!started || busy || fullscreenBlocked || dialogOpen || summary || timeLeftSeconds == null || timeLeftSeconds <= 0) {



      return undefined;



    }







    const intervalId = window.setInterval(() => {



      setTimeLeftSeconds((previous) => {



        if (previous == null) return previous;



        if (previous <= 1) {



          window.clearInterval(intervalId);



          setStatus("Interview time completed.");



          if (sessionIdRef.current && !summaryRef.current && !finalizingRef.current) {



            finalizeEarlyExitRef.current?.({ closingMessage: TIMER_END_CLOSING_MESSAGE })?.catch(() => {



              setError("The interview timer ended, but the session summary could not be completed.");



            });



          }



          return 0;



        }



        return previous - 1;



      });



    }, 1000);







    return () => window.clearInterval(intervalId);



  }, [started, busy, fullscreenBlocked, dialogOpen, summary, timeLeftSeconds]);







  useEffect(() => {



    if (effectiveState || savedInterviewRef.current || started) return;







    setError("Interview setup was missing. Please start a new interview from the previous screen.");



    const timeoutId = window.setTimeout(() => {



      navigate("/instructions", { replace: true });



    }, 1600);







    return () => window.clearTimeout(timeoutId);



  }, [effectiveState, navigate, started]);







  const transcript = clean(`${draft} ${interim}`);



  const title = payload.job_role || payload.primary_language || payload.category || "Interview";



  const isCompactLayout = viewportWidth < 1180;



  const livePhase = fullscreenBlocked



    ? "Paused"



    : dialogOpen



      ? "Awaiting action"



      : aiSpeaking



          ? "AI speaking"



          : busy



            ? "Evaluating"



            : listening



            ? "Mic live"



            : started



              ? "Standing by"



              : "Ready";



  const livePresence = getInterviewPresenceMeta({



    started,



    aiSpeaking,



    listening,



    busy,



    fullscreenBlocked,



    speechRecognitionAvailable: Boolean(SpeechRecognition),



  });



  const reportEvaluations = summary?.evaluations || [];



  const answeredCount = reportEvaluations.length;



  const strongAnswerCount = reportEvaluations.filter((item) => (item.score || 0) >= 75).length;



  const needsWorkCount = reportEvaluations.filter((item) => (item.score || 0) < 60).length;



  const allMistakes = Array.from(



    new Set(reportEvaluations.flatMap((item) => safeTextList(item.gaps)))



  );



  const allMatchedPoints = reportEvaluations.flatMap((item) => safeTextList(item.matched_points));



  const allMissedPoints = reportEvaluations.flatMap((item) => safeTextList(item.missed_points));



  const performanceRatio = allMatchedPoints.length + allMissedPoints.length



    ? Math.round((allMatchedPoints.length / (allMatchedPoints.length + allMissedPoints.length)) * 100)



    : 0;



  const reportUser =



    summary?.user ||



    (() => {



      try {



        return JSON.parse(localStorage.getItem("user") || "null");



      } catch {



        return null;



      }



    })();



  const timerLabel = adaptiveData.enabled
    ? `${adaptiveData.currentDifficulty === "easy" ? "45 sec" : adaptiveData.currentDifficulty === "medium" ? "60 sec" : "90 sec"} (${adaptiveData.currentDifficulty})`
    : timeLeftSeconds == null
      ? "No active timer"
      : `${Math.floor(timeLeftSeconds / 60)
          .toString()
          .padStart(2, "0")}:${(timeLeftSeconds % 60).toString().padStart(2, "0")}`;



  const startupCountdownLabel =



    startupCountdown == null



      ? ""



      : `00:${Math.max(0, startupCountdown).toString().padStart(2, "0")}`;



  const selectionFocus = safeText(payload.focus_areas || payload.selected_options) || "General interview preparation";
  const isLiveTimeMode =
    safeText(sessionMeta.config_mode || payload.config_mode).toLowerCase() === "time" &&
    Boolean(sessionMeta.time_mode_interval || payload.time_mode_interval);



  const hrBreakdown = summary?.score_breakdown && typeof summary.score_breakdown === "object"



    ? Object.entries(summary.score_breakdown)



        .filter(([, value]) => value != null)



        .map(([key, value]) => ({



          key,



          label: key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),



          value: safeScore(value),



        }))



    : [];







  const hideAutoStartIntro = autoStart && !started && !summary;
  const isForcedStartupFullscreenPrompt =
    startupPaused && forceStartupFullscreenPrompt && forcedStartupPromptShownRef.current && !started;

  return (



    <div
      className={`voice-ai-root ${hideAutoStartIntro ? "voice-ai-root--launching" : ""} ${startupOverlayMode ? "voice-ai-root--hosted-startup" : ""}`}
      ref={rootRef}
    >



      <div className="voice-ai-orb voice-ai-orb-left" />



      <div className="voice-ai-orb voice-ai-orb-right" />



      <div className={`voice-ai-inner ${dialogOpen ? "voice-ai-inner-blurred" : ""} ${interviewEntering ? "voice-ai-inner-entering" : ""}`}>



        <div className="voice-ai-header">



          <div>



            <div className="voice-ai-badge">Live Interview</div>



            <h1 className="voice-ai-title">{safeText(title) || "Interview"}</h1>



            <p className="voice-ai-subtitle">



              An AI interviewer asks live technical questions, speaks them out loud, listens to your reply, and evaluates your response in real time.



            </p>



          </div>



          <div className="voice-ai-actions">



            {!started ? (



              <button className="go-back-btn" onClick={() => navigate(-1)}>



                Back



              </button>



            ) : null}



            {!started ? (



              <button className="mock-btn" onClick={() => navigate("/")}>



                Home



              </button>



            ) : null}



            {started && !summary ? (



              <button className="mock-btn" onClick={handleEndInterview} style={{ background: "linear-gradient(135deg, #dc2626, #f97316)" }}>



                End Interview



              </button>



            ) : null}



          </div>



        </div>







        {error ? (



          <div className="voice-ai-alert voice-ai-alert-error">{safeText(error)}</div>



        ) : null}







        {restoreNotice ? (



          <div className="voice-ai-alert voice-ai-alert-warn">{safeText(restoreNotice)}</div>



        ) : null}







        {!started ? (



          <div className="voice-ai-layout" style={{ gridTemplateColumns: isCompactLayout ? "1fr" : "minmax(0,1.08fr) minmax(320px,0.92fr)" }}>



            <div className="voice-ai-panel voice-ai-start-panel">



              <h2 className="voice-ai-section-title">Ready for your AI interview</h2>



              <p className="voice-ai-copy">



                The assistant will greet you, speak each question, capture your answer by voice, and keep the interview flowing with AI-powered feedback.



              </p>



              <div className="voice-ai-selection-box">



                <div className="voice-ai-mini-label">Interview Selections</div>



                <div className="voice-ai-selection-grid" style={{ gridTemplateColumns: isCompactLayout ? "1fr" : "repeat(2, minmax(0, 1fr))" }}>



                  <div className="voice-ai-selection-item"><strong>Category:</strong> {safeText(payload.category)}</div>



                  <div className="voice-ai-selection-item"><strong>Mode:</strong> {safeText(payload.selected_mode)}</div>



                  <div className="voice-ai-selection-item"><strong>Role:</strong> {safeText(payload.job_role) || "General"}</div>



                  <div className="voice-ai-selection-item"><strong>Language:</strong> {safeText(payload.primary_language) || "Not selected"}</div>



                  <div className="voice-ai-selection-item"><strong>Round:</strong> {formatRoundLabel(payload.hr_round) || "Standard"}</div>



                  <div className="voice-ai-selection-item"><strong>Experience:</strong> {safeText(payload.experience)}</div>



                  <div className="voice-ai-selection-item"><strong>Questions:</strong> {safeScore(payload.question_count)}</div>



                  <div className="voice-ai-selection-item"><strong>Config mode:</strong> {safeText(payload.config_mode)}</div>



                  <div className="voice-ai-selection-item"><strong>Timer:</strong> {resolveTimerMinutes() ? `${resolveTimerMinutes()} minutes` : "Off"}</div>



                  <div className="voice-ai-selection-item"><strong>Speech recognition:</strong> {SpeechRecognition ? "Automatic voice capture enabled" : "Unavailable, typed fallback enabled"}</div>



                  <div className="voice-ai-selection-item"><strong>Focus:</strong> {selectionFocus}</div>



                </div>



              </div>



              <button className="mock-btn" onClick={beginVoiceInterview} disabled={busy} style={{ marginTop: 24, background: "linear-gradient(135deg, #4338ca, #7c3aed)" }}>



                {busy ? "Starting..." : "Enter Fullscreen and Begin"}



              </button>



            </div>







            <div className="voice-ai-panel voice-ai-side-panel voice-ai-assistant-panel">



              <div className="voice-ai-assistant-shell">



                <div className="voice-ai-assistant-rings">



                  <div className="voice-ai-assistant-core" />



                </div>



              </div>



              <h3 className="voice-ai-section-title">AI Interview Assistant</h3>



              <p className="voice-ai-copy">



                This screen behaves like a live AI interview room with a dedicated assistant presence, live voice handling, and role-aware question flow.



              </p>



              <div className="voice-ai-steps">



                <div>1. Start the session and enter fullscreen.</div>



                <div>2. The assistant speaks the question from the active role focus.</div>



                <div>3. Your spoken answer is transcribed and evaluated by the AI models.</div>



                <div>4. The session continues until the full interview report is ready.</div>



              </div>



            </div>



          </div>



        ) : (



          <div className="voice-ai-layout voice-ai-live-layout" style={{ gridTemplateColumns: isCompactLayout ? "1fr" : "minmax(320px,0.86fr) minmax(0,1.14fr)" }}>



            <div className="voice-ai-column voice-ai-column-left">



              <div className="voice-ai-panel voice-ai-video-panel">



                <video className="voice-ai-video" ref={videoRef} autoPlay playsInline muted />



                <div className="voice-ai-meta-row">



                  <span>
                    {isLiveTimeMode
                      ? `Question ${Math.max(1, index + 1)} • Time mode`
                      : `Question ${Math.min(index + 1, total || 1)} of ${total || 1}`}
                  </span>



                  <strong>{safeText(listening ? "Listening automatically" : status)}</strong>



                </div>



                <div className="voice-ai-submeta-row">



                  <span>Difficulty: {adaptiveData.enabled ? `${adaptiveData.currentDifficulty.charAt(0).toUpperCase() + adaptiveData.currentDifficulty.slice(1)} (Adaptive)` : (safeText(sessionMeta.difficulty || payload.experience) || "Adaptive")}</span>



                  <span>Timer: {timerLabel}</span>



                </div>

                {adaptiveData.enabled && currentSkill && (
                  <div className="voice-ai-submeta-row">
                    <span style={{ color: "#2563eb", fontWeight: 600 }}>Current Skill: {currentSkill}</span>
                  </div>
                )}

                {adaptiveData.enabled && adaptiveData.difficultyHistory.length > 0 && (
                  <div className="voice-ai-submeta-row" style={{ gap: 8 }}>
                    <span style={{ fontSize: 13, color: "#64748b" }}>Progression:</span>
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      {adaptiveData.difficultyHistory.map((difficulty, idx) => (
                        <div key={idx} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <span style={{
                            padding: "4px 8px",
                            borderRadius: 4,
                            fontSize: 12,
                            fontWeight: 600,
                            background: difficulty === "easy" ? "rgba(34, 197, 94, 0.2)" : difficulty === "medium" ? "rgba(250, 204, 21, 0.2)" : "rgba(239, 68, 68, 0.2)",
                            color: difficulty === "easy" ? "#16a34a" : difficulty === "medium" ? "#d97706" : "#dc2626"
                          }}>
                            {difficulty.charAt(0).toUpperCase()}
                          </span>
                          {idx < adaptiveData.difficultyHistory.length - 1 && (
                            <span style={{ color: "#cbd5e1", fontSize: 12 }}>→</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {adaptiveData.enabled && (
                  <div className="voice-ai-submeta-row">
                    <span style={{ fontSize: 13, color: "#64748b" }}>Remaining Time:</span>
                    <span style={{
                      padding: "4px 12px",
                      borderRadius: 6,
                      fontSize: 14,
                      fontWeight: 700,
                      background: timeLeftSeconds && timeLeftSeconds <= 10 ? "rgba(239, 68, 68, 0.15)" : "rgba(59, 130, 246, 0.15)",
                      color: timeLeftSeconds && timeLeftSeconds <= 10 ? "#dc2626" : "#1d4ed8"
                    }}>
                      {timeLeftSeconds ?? adaptiveData.currentQuestionTimeLimit} sec
                    </span>
                  </div>
                )}

                {adaptiveData.enabled && (
                  <div className="voice-ai-submeta-row">
                    <span style={{ fontSize: 13, color: "#64748b" }}>Total Remaining:</span>
                    <span style={{ fontSize: 13, color: "#475569", fontWeight: 600 }}>
                      {(() => {
                        const remainingQuestions = adaptiveData.totalQuestions - (index + 1);
                        const remainingSeconds = remainingQuestions * adaptiveData.currentQuestionTimeLimit;
                        const minutes = Math.floor(remainingSeconds / 60);
                        const seconds = remainingSeconds % 60;
                        return `${minutes}:${seconds.toString().padStart(2, '0')} • ${remainingQuestions} question${remainingQuestions !== 1 ? 's' : ''}`;
                      })()}
                    </span>
                  </div>
                )}



                <div className="voice-ai-submeta-row">



                  <span>Session state: {livePhase}</span>



                  <span>{listening ? "Waiting for your response" : "No silence countdown active"}</span>



                </div>



              </div>







              <div className="voice-ai-panel voice-ai-mini-panel voice-ai-hud-panel">



                <InterviewPresenceCard presence={livePresence} />



                <h3 className="voice-ai-section-title">Interview HUD</h3>



                <div className="voice-ai-hud-grid">



                  <div className="voice-ai-hud-item"><span>Generation</span><strong>{formatProviderName(providers.generation_provider, "generation") || "Pending"}</strong></div>



                  <div className="voice-ai-hud-item"><span>Evaluation</span><strong>{formatProviderName(providers.evaluation_provider, "evaluation") || "Pending"}</strong></div>



                  <div className="voice-ai-hud-item"><span>Summary</span><strong>{formatProviderName(providers.summary_provider, "summary") || "Pending"}</strong></div>



                  <div className="voice-ai-hud-item"><span>Answers</span><strong>{history.length}</strong></div>



                  <div className="voice-ai-hud-item"><span>Listening</span><strong>{SpeechRecognition ? "Auto" : "Manual"}</strong></div>



                  <div className="voice-ai-hud-item"><span>Focus</span><strong>{selectionFocus}</strong></div>



                  <div className="voice-ai-hud-item"><span>Live state</span><strong>{livePhase}</strong></div>



                  <div className="voice-ai-hud-item"><span>Silence timer</span><strong>Off</strong></div>



                </div>



              </div>



            </div>







            <div className="voice-ai-column voice-ai-column-right">



              <div className="voice-ai-panel voice-ai-question-card">



                <div className="voice-ai-mini-label voice-ai-mini-label-light">Current question</div>



                <h2 className="voice-ai-question-text" style={{ fontSize: isCompactLayout ? 24 : 30 }}>



                  {safeText(question) || "Loading question..."}



                </h2>



                <div className="voice-ai-inline-actions">



                  <button



                    className="mock-btn"



                    onClick={() => {



                      interruptInterviewFlow();



                      void runVoiceTurn({



                        prompt: `Question ${index + 1}. ${safeText(question)}`,



                      });



                    }}



                    style={{ background: "rgba(255,255,255,0.16)" }}



                  >



                    Repeat Question



                  </button>



                  <button className="mock-btn" onClick={startListening} disabled={busy || fullscreenBlocked || Boolean(summary)} style={{ background: "rgba(255,255,255,0.16)" }}>



                    Restart Listening



                  </button>



                </div>



              </div>







              <div className="voice-ai-panel voice-ai-answer-card">



                <h3 className="voice-ai-section-title">Your answer</h3>



                <textarea



                  className="voice-ai-textarea"



                  value={draft}



                  onChange={(e) => setDraft(e.target.value)}



                  placeholder="Your spoken answer will appear here automatically. You can also refine it manually before submitting."



                />



                <div className="voice-ai-transcript-box">



                  Live transcript: {safeText(interim || transcript) || "Waiting for your answer..."}



                </div>



                <div className="voice-ai-inline-actions">



                  <button className="mock-btn" onClick={submitAnswer} disabled={!clean(transcript) || busy || aiSpeaking || fullscreenBlocked || Boolean(summary)} style={{ background: "linear-gradient(135deg, #059669, #10b981)" }}>



                    {aiSpeaking ? "Speaking..." : busy ? "Processing..." : "Submit Answer"}



                  </button>



                  <button className="go-back-btn" onClick={() => { stopListening(); setDraft(""); setInterim(""); }} disabled={busy}>



                    Clear



                  </button>



                </div>







                {latestEval ? (



                  <div className="voice-ai-eval-inline">



                    <div className="voice-ai-meta-row">



                      <h3 className="voice-ai-section-title" style={{ margin: 0 }}>Latest evaluation</h3>



                      <strong>



                        {latestEval.count_towards_score === false



                          ? "Discovery step"



                          : `Score ${safeScore(latestEval.score)}/100`}



                      </strong>



                    </div>



                    <p className="voice-ai-copy" style={{ marginTop: 10 }}>{safeText(latestEval.feedback)}</p>



                    <div className="voice-ai-mini-list" style={{ marginBottom: 12 }}>



                      <div>- Relevance: {safeText(latestEval.relevance) || "Pending"}</div>



                      <div>- Correctness: {safeText(latestEval.correctness) || "Pending"}</div>



                      <div>- Clarity: {safeText(latestEval.clarity) || "Pending"}</div>



                      <div>- Technical Depth: {safeText(latestEval.technical_depth) || "Pending"}</div>



                      <div>- Logic: {safeText(latestEval.logical_validity) || "Pending"}</div>



                      <div>- Real-world Fit: {safeText(latestEval.real_world_applicability) || "Pending"}</div>



                    </div>



                    <div className="voice-ai-mini-list">



                      {safeTextList(latestEval.strengths).map((item) => <div key={item}>- {item}</div>)}



                      {safeTextList(latestEval.gaps).map((item) => <div key={item}>- {item}</div>)}



                      {safeTextList(latestEval.suggestions).map((item) => <div key={item}>- Suggestion: {item}</div>)}



                    </div>



                  </div>



                ) : null}



              </div>



            </div>



          </div>



        )}







        {summary ? (



          <div ref={reportRef} style={{ background: "#ecfeff", borderRadius: 24, padding: 24, display: "grid", gap: 22, marginTop: 24 }}>



                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>



                    <h3 style={{ margin: 0, color: "#0f172a" }}>Final interview report</h3>



                    <strong>Overall score {safeScore(summary.overall_score)}/100</strong>



                  </div>







                  <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr 1fr" : "repeat(4, minmax(0, 1fr))", gap: 14 }}>



                    <MetricTile label="Questions answered" value={answeredCount} tone="#0f766e" />



                    <MetricTile label="Strong answers" value={strongAnswerCount} tone="#10b981" />



                    <MetricTile label="Need work" value={needsWorkCount} tone="#ef4444" />



                    <MetricTile label="Coverage ratio" value={`${performanceRatio}%`} tone="#2563eb" />



                  </div>







                  {hrBreakdown.length ? (



                    <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr 1fr" : "repeat(5, minmax(0, 1fr))", gap: 14 }}>



                      {hrBreakdown.map((item) => (



                        <MetricTile key={item.key} label={item.label} value={`${item.value}/100`} tone="#7c3aed" />



                      ))}



                    </div>



                  ) : null}







                  <div style={{ background: "white", borderRadius: 20, padding: 20, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



                    <h4 style={{ marginTop: 0, color: "#0f172a" }}>User details and selections</h4>



                    <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "repeat(2, minmax(0, 1fr))", gap: 12, color: "#334155" }}>



                      <div>Name: {safeText(`${reportUser?.first_name || ""} ${reportUser?.last_name || ""}`) || "Not available"}</div>



                      <div>Email: {safeText(reportUser?.email) || "Not available"}</div>



                      <div>Category: {safeText(summary.context?.category || payload.category)}</div>



                      <div>Mode: {safeText(summary.context?.selected_mode || payload.selected_mode)}</div>



                      <div>Role: {safeText(summary.context?.job_role || payload.job_role) || "Not selected"}</div>



                      <div>Language: {safeText(summary.context?.primary_language || payload.primary_language) || "Not selected"}</div>



                      <div>Round: {formatRoundLabel(summary.context?.hr_round || payload.hr_round) || "Standard"}</div>



                      <div>Focus: {safeText(summary.context?.focus_areas || payload.focus_areas) || selectionFocus}</div>



                      <div>Experience: {safeText(summary.context?.experience || payload.experience)}</div>



                      <div>Config mode: {safeText(summary.context?.config_mode || payload.config_mode)}</div>



                      <div>Practice type: {safeText(summary.context?.practice_type || payload.practice_type)}</div>



                      <div>Interview timer: {safeText(summary.context?.interview_mode_time) || "Off"}</div>



                      <div>Time mode interval: {safeText(summary.context?.time_mode_interval) || "Off"}</div>



                      <div>AI providers: {formatProviderName(summary.providers?.generation_provider, "generation")}, {formatProviderName(summary.providers?.evaluation_provider, "evaluation")}, {formatProviderName(summary.providers?.summary_provider, "summary")}</div>



                    </div>



                  </div>







                  <div style={{ background: "white", borderRadius: 20, padding: 20, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



                    <h4 style={{ marginTop: 0, color: "#0f172a" }}>Overall analysis</h4>



                    <p style={{ color: "#334155", lineHeight: 1.7 }}>{safeText(summary.summary)}</p>



                    <div style={{ display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "repeat(2, minmax(0, 1fr))", gap: 18 }}>



                      <div>



                        <div style={{ fontWeight: 800, color: "#0f766e", marginBottom: 8 }}>Top strengths</div>



                        <div style={{ display: "grid", gap: 8, color: "#334155" }}>



                          {(summary.top_strengths || []).map((item) => <div key={item}>- {item}</div>)}



                        </div>



                      </div>



                      <div>



                        <div style={{ fontWeight: 800, color: "#c2410c", marginBottom: 8 }}>Where to improve</div>



                        <div style={{ display: "grid", gap: 8, color: "#334155" }}>



                          {(summary.improvement_areas || []).map((item) => <div key={item}>- {item}</div>)}



                        </div>



                      </div>



                    </div>



                  </div>







                  <div style={{ background: "white", borderRadius: 20, padding: 20, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



                    <h4 style={{ marginTop: 0, color: "#0f172a" }}>Performance graph</h4>



                    <ScoreBars items={reportEvaluations.map((item) => ({ question: safeText(item.question), score: safeScore(item.score) }))} />



                  </div>







                  <div style={{ background: "white", borderRadius: 20, padding: 20, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



                    <h4 style={{ marginTop: 0, color: "#0f172a" }}>Common mistakes and missed areas</h4>



                    <div style={{ display: "grid", gap: 8, color: "#334155" }}>



                      {allMistakes.length



                        ? allMistakes.map((item) => <div key={item}>- {item}</div>)



                        : <div>No major repeated mistakes were detected.</div>}



                    </div>



                  </div>







                  <div style={{ background: "white", borderRadius: 20, padding: 20, boxShadow: "0 14px 34px rgba(88,107,176,0.10)" }}>



                    <h4 style={{ marginTop: 0, color: "#0f172a" }}>Question by question report</h4>



                    <div style={{ display: "grid", gap: 18 }}>



                      {reportEvaluations.map((item, itemIndex) => (



                        <div key={`${item.question}-${itemIndex}`} style={{ border: "1px solid #dbe4f0", borderRadius: 18, padding: 18, background: "#f8fbff" }}>



                          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap", alignItems: "center" }}>



                            <strong style={{ color: "#0f172a" }}>Question {itemIndex + 1}</strong>



                            <span style={{ fontWeight: 800, color: safeScore(item.score) >= 75 ? "#047857" : safeScore(item.score) >= 60 ? "#b45309" : "#b91c1c" }}>



                              Score {safeScore(item.score)}/100



                            </span>



                          </div>



                          <div style={{ marginTop: 10, color: "#0f172a", fontWeight: 700 }}>{safeText(item.question)}</div>



                          <div style={{ marginTop: 10, color: "#334155", lineHeight: 1.7 }}>



                            <strong>Your answer:</strong> {safeText(item.answer) || "Not captured"}



                          </div>



                          <div style={{ marginTop: 10, color: "#334155", lineHeight: 1.7 }}>



                            <strong>Analysis:</strong> {safeText(item.feedback)}



                          </div>



                          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "repeat(2, minmax(0, 1fr))", gap: 14 }}>



                            <div>



                              <div style={{ fontWeight: 800, color: "#0f766e", marginBottom: 6 }}>What went well</div>



                              <div style={{ display: "grid", gap: 6, color: "#334155" }}>



                                {(item.strengths || []).map((entry) => <div key={entry}>- {entry}</div>)}



                              </div>



                            </div>



                            <div>



                              <div style={{ fontWeight: 800, color: "#c2410c", marginBottom: 6 }}>Mistakes / gaps</div>



                              <div style={{ display: "grid", gap: 6, color: "#334155" }}>



                                {(item.gaps || []).map((entry) => <div key={entry}>- {entry}</div>)}



                              </div>



                            </div>



                          </div>



                          <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: isCompactLayout ? "1fr" : "repeat(2, minmax(0, 1fr))", gap: 14 }}>



                            <div>



                              <div style={{ fontWeight: 800, color: "#2563eb", marginBottom: 6 }}>Covered points</div>



                              <div style={{ display: "grid", gap: 6, color: "#334155" }}>



                                {(item.matched_points || []).map((entry) => <div key={entry}>- {entry}</div>)}



                              </div>



                            </div>



                            <div>



                              <div style={{ fontWeight: 800, color: "#7c2d12", marginBottom: 6 }}>Missed points</div>



                              <div style={{ display: "grid", gap: 6, color: "#334155" }}>



                                {(item.missed_points || []).map((entry) => <div key={entry}>- {entry}</div>)}



                              </div>



                            </div>



                          </div>



                          <div style={{ marginTop: 10, color: "#334155", lineHeight: 1.7 }}>



                            <strong>How you could answer better:</strong> {safeText(item.suggested_answer)}



                          </div>



                        </div>



                      ))}



                    </div>



                  </div>







                  <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 6 }}>



                    <button className="mock-btn" onClick={downloadReportPdf}>Download PDF</button>



                    <button className="mock-btn" onClick={() => navigate("/dashboard")}>View Dashboard</button>



                    <button className="go-back-btn" onClick={() => navigate("/")}>Return Home</button>



                  </div>



          </div>



        ) : null}



      </div>



      {dialogOpen ? (



        <div className="voice-ai-modal-overlay">



          {showEndConfirm ? (



            <div className="voice-ai-modal-card">



              <div className="voice-ai-modal-eyebrow">Confirm Exit</div>



              <h2 className="voice-ai-modal-title">Are you sure you want to end this interview?</h2>



              <p className="voice-ai-modal-copy">



                The interview will stop immediately, fullscreen will close, and your report will be generated from the answers captured so far.



              </p>



              <div className="voice-ai-modal-actions">



                <button



                  className="go-back-btn"



                  onClick={() => {



                    dialogOpenRef.current = false;



                    setShowEndConfirm(false);



                    void resumeInterviewAfterPause();



                  }}



                >



                  Cancel



                </button>



                <button



                  className="mock-btn"



                  onClick={() => {



                    void finalizeEarlyExit({ closingMessage: EARLY_END_CLOSING_MESSAGE });



                  }}



                  style={{ background: "linear-gradient(135deg, #dc2626, #f97316)" }}



                >



                  Confirm End Interview



                </button>



              </div>



            </div>



          ) : null}







          {showStartupCancelConfirm ? (
            <div className="voice-ai-modal-card" data-startup-cancel-confirmation>
              <div className="voice-ai-modal-eyebrow">Confirm Exit</div>
              <h2 className="voice-ai-modal-title">Cancel this interview setup?</h2>
              <p className="voice-ai-modal-copy">
                The interview has not started yet. You can resume the fullscreen launch, or cancel this setup and return to the home page.
              </p>
              <div className="voice-ai-modal-actions">
                <button className="mock-btn" onClick={restoreFullscreen}>
                  Resume Interview
                </button>
                <button
                  className="go-back-btn"
                  onClick={cancelStartupPause}
                  style={{ background: "linear-gradient(135deg, #dc2626, #f97316)", color: "#ffffff" }}
                >
                  Cancel Interview
                </button>
              </div>
            </div>
          ) : null}



          {showFullscreenPrompt ? (



            <div
              className="voice-ai-modal-card"
              data-fullscreen-warning
              data-startup-welcome={isForcedStartupFullscreenPrompt ? "true" : undefined}
              tabIndex="-1"
            >



              {isForcedStartupFullscreenPrompt ? (
                <img
                  src={interviewrWordmark}
                  alt="Interviewr - Your Path to Career Success"
                  className="voice-ai-startup-modal-logo"
                />
              ) : (
                <div className="voice-ai-modal-eyebrow">Fullscreen Required</div>
              )}



              <h2 className="voice-ai-modal-title">



                {isForcedStartupFullscreenPrompt

                  ? "Ready to start your interview?"

                  : startupPaused



                  ? "The interview start is paused because fullscreen mode was exited."



                  : "The interview is paused because fullscreen mode was exited."}



              </h2>



              <p className="voice-ai-modal-copy">



                {isForcedStartupFullscreenPrompt

                  ? "Start the interview in fullscreen mode when you are ready."

                  : startupPaused



                  ? "Stay in fullscreen to restart the interview launch sequence, or cancel this interview setup now."



                  : "Stay in fullscreen to resume from where the interview was paused, or end the interview and see your report."}



              </p>



              <div className="voice-ai-modal-actions">



                <button



                  className="go-back-btn"



                  onClick={() => {



                    if (startupPaused) {



                      confirmStartupCancel();



                      return;



                    }



                    void finalizeEarlyExit({ closingMessage: EARLY_END_CLOSING_MESSAGE });



                  }}



                >



                  {startupPaused ? "Cancel Interview" : "End Interview"}



                </button>



                <button className="mock-btn" onClick={restoreFullscreen}>



                  {isForcedStartupFullscreenPrompt ? "Start Interview" : "Stay in Fullscreen"}



                </button>



              </div>



            </div>



          ) : null}



        </div>



      ) : null}



      {setupFullscreenBlocked && !dialogOpen ? (
        <div className="voice-ai-modal-overlay">
          <div className="voice-ai-modal-card" data-fullscreen-warning tabIndex="-1">
            <div className="voice-ai-modal-eyebrow">Fullscreen Required</div>
            <h2 className="voice-ai-modal-title">
              The interview setup is paused because fullscreen mode was exited.
            </h2>
            <p className="voice-ai-modal-copy">
              Stay in fullscreen to continue the interview setup, or cancel this interview setup now.
            </p>
            <div className="voice-ai-modal-actions">
              <button className="go-back-btn" onClick={cancelSetupFullscreen}>
                Cancel Interview
              </button>
              <button className="mock-btn" onClick={restoreSetupFullscreen}>
                Stay in Fullscreen
              </button>
            </div>
          </div>
        </div>
      ) : null}



      {startupActive && !dialogOpen ? (



        <div className="voice-ai-startup-overlay">



          <div className="voice-ai-startup-orb voice-ai-startup-orb-one" />



          <div className="voice-ai-startup-orb voice-ai-startup-orb-two" />



          <div className="voice-ai-startup-minimal">



            <div className="voice-ai-startup-shell">



              <div className="voice-ai-startup-ring voice-ai-startup-ring-one" />



              <div className="voice-ai-startup-ring voice-ai-startup-ring-two" />



              <div className="voice-ai-startup-core">



                <div className="voice-ai-startup-eye voice-ai-startup-eye-left" />



                <div className="voice-ai-startup-eye voice-ai-startup-eye-right" />



                <div className="voice-ai-startup-mouth" />



              </div>



              <div className="voice-ai-startup-node voice-ai-startup-node-left" />



              <div className="voice-ai-startup-node voice-ai-startup-node-right" />



              <div className="voice-ai-startup-node voice-ai-startup-node-bottom" />



            </div>



            <div className={`voice-ai-startup-line ${startupMessageVisible ? "is-visible" : ""}`}>



              {startupMessage}



            </div>



            {startupCountdown != null ? (



              <div className="voice-ai-startup-timer">



                Interview session starts in <strong>{startupCountdownLabel}</strong>



              </div>



            ) : null}



          </div>



        </div>



      ) : null}



    </div>



  );



}







export default VoiceInterview;



