import asyncio
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from config import load_backend_env
from database import interview_sessions_collection

load_backend_env()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
OLLAMA_TIMEOUT_SECONDS = max(30, int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")))
LIVE_AI_TIMEOUT_SECONDS = max(8, int(os.getenv("LIVE_AI_TIMEOUT_SECONDS", "12")))
STARTUP_AI_TIMEOUT_SECONDS = max(LIVE_AI_TIMEOUT_SECONDS, int(os.getenv("STARTUP_AI_TIMEOUT_SECONDS", "20")))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

INTERVIEW_SESSIONS: Dict[str, Dict[str, Any]] = {}
ACTIVE_SESSION_TTL_SECONDS = max(3600, int(os.getenv("ACTIVE_SESSION_TTL_SECONDS", "86400")))

ROLE_PROFILES: List[Dict[str, Any]] = [
    {
        "aliases": ["software developer", "software engineer", "backend", "backend developer", "full stack", "full-stack", "fullstack"],
        "label": "Software Developer / Backend / Full Stack",
        "core_fields": [
            "Data Structures and Algorithms",
            "arrays, linked lists, trees, graphs",
            "sorting and searching",
            "Python, Java, C++, or JavaScript fundamentals",
            "database management and SQL",
            "operating systems concepts",
            "computer networks basics",
            "system design for experienced roles",
        ],
        "question_seeds": [
            "How would you reverse a linked list, and what are the time and space trade-offs?",
            "What is the difference between a process and a thread?",
            "Write or explain an SQL query to fetch the top 3 salaries from an employee table.",
            "How do HTTP requests flow between client, server, and database in a typical web application?",
            "How would you design a scalable API service for a growing product?",
        ],
    },
    {
        "aliases": ["frontend", "frontend developer", "front end", "ui developer", "react developer"],
        "label": "Frontend Developer",
        "core_fields": [
            "HTML, CSS, and JavaScript fundamentals",
            "React, Angular, or Vue",
            "DOM, browser rendering, and events",
            "responsive design and accessibility",
            "API integration and state handling",
        ],
        "question_seeds": [
            "What is the virtual DOM in React, and why is it useful?",
            "What is the difference between == and === in JavaScript?",
            "How does event bubbling work in the browser?",
            "How would you make a complex UI responsive across devices?",
            "How do you fetch and manage API data safely in a frontend application?",
        ],
    },
    {
        "aliases": ["backend developer", "api developer", "server side", "server-side", "fastapi", "django", "node", "spring"],
        "label": "Backend Developer",
        "core_fields": [
            "server-side programming with Python, Java, or Node.js",
            "REST APIs and authentication with JWT",
            "SQL and NoSQL databases",
            "system design basics",
            "scalability and backend architecture",
        ],
        "question_seeds": [
            "How would you design a login system using JWT authentication?",
            "What is a REST API and what makes it RESTful?",
            "When would you choose SQL over NoSQL, or vice versa?",
            "How would you structure a FastAPI or Node.js backend for maintainability?",
            "What steps would you take to secure a backend API?",
        ],
    },
    {
        "aliases": ["data science", "data scientist", "machine learning", "ml engineer", "ai engineer", "artificial intelligence"],
        "label": "Data Science / AI / ML",
        "core_fields": [
            "linear algebra, probability, and statistics",
            "regression, classification, and clustering",
            "NumPy, Pandas, TensorFlow, or PyTorch",
            "Python for data workflows",
            "data cleaning, visualization, and model evaluation",
        ],
        "question_seeds": [
            "What is overfitting and how do you reduce it?",
            "What is the difference between supervised and unsupervised learning?",
            "How would you evaluate a classification model?",
            "Why is data cleaning important before training a model?",
            "How would you explain bias-variance trade-off?",
        ],
    },
    {
        "aliases": ["devops", "cloud engineer", "site reliability", "sre", "platform engineer"],
        "label": "DevOps / Cloud Engineer",
        "core_fields": [
            "AWS, Azure, or GCP basics",
            "CI/CD pipelines",
            "Docker and Kubernetes",
            "Linux fundamentals",
            "networking and deployment workflows",
        ],
        "question_seeds": [
            "What is a Docker container and how is it different from a virtual machine?",
            "Explain a CI/CD pipeline from commit to deployment.",
            "What role does Kubernetes play in modern deployments?",
            "How would you troubleshoot a Linux service that fails after deployment?",
            "How do load balancers and DNS fit into cloud architecture?",
        ],
    },
    {
        "aliases": ["qa", "quality assurance", "testing", "test engineer", "automation tester", "qa engineer"],
        "label": "Testing / QA Engineer",
        "core_fields": [
            "manual testing concepts",
            "test cases and bug lifecycle",
            "automation testing with Selenium or similar tools",
            "API testing",
            "regression and integration testing",
        ],
        "question_seeds": [
            "How would you write test cases for a login page?",
            "What is regression testing and when should it be run?",
            "How do you decide what to automate in a test suite?",
            "How would you validate an API endpoint?",
            "What information makes a bug report actionable for developers?",
        ],
    },
    {
        "aliases": ["cybersecurity", "security engineer", "information security", "cyber security"],
        "label": "Cybersecurity",
        "core_fields": [
            "network security fundamentals",
            "cryptography basics",
            "ethical hacking basics",
            "OWASP vulnerabilities",
            "threat analysis and secure practices",
        ],
        "question_seeds": [
            "What is SQL injection and how do you prevent it?",
            "What is encryption and how is it different from hashing?",
            "How would you explain the OWASP Top 10 to a developer?",
            "What are common ways to secure authentication systems?",
            "How would you approach vulnerability assessment in a web app?",
        ],
    },
]


class ProviderError(Exception):
    pass


async def _persist_session(session: Dict[str, Any]) -> None:
    session_id = _normalize_text(session.get("session_id") or "")
    if not session_id:
        return
    await interview_sessions_collection.replace_one(
        {"session_id": session_id},
        session,
        upsert=True,
    )


async def _load_persisted_session(session_id: str) -> Optional[Dict[str, Any]]:
    normalized_session_id = _normalize_text(session_id)
    if not normalized_session_id:
        return None
    session = await interview_sessions_collection.find_one(
        {"session_id": normalized_session_id},
        {"_id": 0},
    )
    if not isinstance(session, dict):
        return None

    created_at = float(session.get("created_at") or 0)
    if created_at and (time.time() - created_at) > ACTIVE_SESSION_TTL_SECONDS:
        await interview_sessions_collection.delete_one({"session_id": normalized_session_id})
        return None
    return session if isinstance(session, dict) else None


async def _get_session(session_id: str) -> Optional[Dict[str, Any]]:
    session = INTERVIEW_SESSIONS.get(session_id)
    if session:
        return session
    session = await _load_persisted_session(session_id)
    if session:
        INTERVIEW_SESSIONS[session_id] = session
    return session


def _json_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if extra:
        headers.update(extra)
    return headers


def _http_post_json(
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 60
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_json_headers(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {exc.code} calling {url}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Failed to reach {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ProviderError(f"Timed out calling {url}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Invalid JSON response from {url}") from exc


def _http_get_json(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20
) -> Dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        headers=_json_headers(headers),
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {exc.code} calling {url}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"Failed to reach {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ProviderError(f"Timed out calling {url}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError(f"Invalid JSON response from {url}") from exc


def _extract_json_block(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ProviderError("Provider returned an empty response.")

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ProviderError("Provider did not return valid JSON.")


def _extract_gemini_text(data: Dict[str, Any]) -> str:
    candidates = data.get("candidates") or []
    collected = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            if isinstance(part, dict) and part.get("text"):
                collected.append(str(part["text"]))

    text = "".join(collected).strip()
    if text:
        return text

    prompt_feedback = data.get("promptFeedback") or {}
    block_reason = prompt_feedback.get("blockReason")
    if block_reason:
        raise ProviderError(f"Gemini blocked the request: {block_reason}")

    raise ProviderError("Gemini returned no text content.")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _candidate_first_name(payload: Dict[str, Any]) -> str:
    raw = _normalize_text(payload.get("candidate_name") or "")
    if not raw:
        return ""
    first = raw.split(" ")[0].strip(" ,.;:-")
    if not first:
        return ""
    if len(first) > 24:
        return ""
    return first


def _clamp_question_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 10
    return max(10, min(count, 30))


def _payload_uses_time_mode(payload: Dict[str, Any]) -> bool:
    config_mode = _normalize_text(payload.get("config_mode") or "").lower()
    time_limit = payload.get("time_mode_interval") or payload.get("interview_mode_time")
    return config_mode == "time" and bool(time_limit)


def _payload_time_mode_minutes(payload: Dict[str, Any]) -> Optional[int]:
    interval = payload.get("time_mode_interval") or payload.get("interview_mode_time")
    try:
        minutes = int(interval)
    except (TypeError, ValueError):
        return None
    return minutes if minutes > 0 else None


def _safe_list(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    cleaned = []
    for item in values:
        if isinstance(item, dict):
            preferred = (
                item.get("text")
                or item.get("message")
                or item.get("msg")
                or item.get("question")
                or json.dumps(item, ensure_ascii=False)
            )
            item = preferred
        item = _normalize_text(str(item))
        if item:
            cleaned.append(item)
    return cleaned


def _context_summary(payload: Dict[str, Any]) -> str:
    selected_options = _safe_list(payload.get("selected_options") or [])
    focus_areas = _safe_list(payload.get("focus_areas") or []) or selected_options
    primary_focus = ", ".join(focus_areas) if focus_areas else "general interview preparation"
    config_mode = payload.get("config_mode") or "question"
    time_mode_interval = payload.get("time_mode_interval")
    interview_mode_time = payload.get("interview_mode_time")
    role_profile = _match_role_profile(payload.get("job_role") or "")
    hr_round = _normalize_text(payload.get("hr_round") or "")
    selected_mode = payload.get("selected_mode") or (
        "language" if payload.get("primary_language") else "role" if payload.get("job_role") else "general"
    )
    parts = [
        f"Category: {payload.get('category') or 'general'}",
        f"Selected mode: {selected_mode}",
        f"Job role: {payload.get('job_role') or 'Not specified'}",
        f"Primary language: {payload.get('primary_language') or 'Not specified'}",
        f"Experience level: {payload.get('experience') or 'Not specified'}",
        f"Focus areas: {primary_focus}",
        f"Configuration mode: {config_mode}",
        f"Practice type: {payload.get('practice_type') or 'interview'}",
    ]
    if _payload_uses_time_mode(payload):
        parts.append("Question pacing: Keep asking questions until the selected timer ends")
    else:
        parts.append(f"Question count: {_clamp_question_count(payload.get('question_count'))}")
    if hr_round:
        parts.append(f"HR round: {hr_round}")
    if config_mode == "time" and time_mode_interval:
        parts.append(f"Time mode interval: {time_mode_interval} minutes")
    if payload.get("practice_type") == "interview" and interview_mode_time:
        parts.append(f"Interview duration: {interview_mode_time} minutes")
    if role_profile:
        parts.append(f"Role profile: {role_profile['label']}")
        parts.append(f"Role core fields: {', '.join(role_profile['core_fields'])}")
    resume_text = _normalize_text(payload.get("resume_text") or "")
    if resume_text:
        parts.append(f"Resume snippet: {resume_text[:700]}")
    resume_insights = payload.get("resume_insights") if isinstance(payload.get("resume_insights"), dict) else {}
    extracted = resume_insights.get("extracted") if isinstance(resume_insights.get("extracted"), dict) else {}
    education = _safe_list(extracted.get("educational_qualifications") or [])
    resume_projects = _safe_list(extracted.get("projects") or [])
    resume_skills = _safe_list(extracted.get("technical_skills") or [])
    resume_experience = _safe_list(extracted.get("experience") or [])
    resume_hobbies = _safe_list(extracted.get("hobbies") or [])
    if education:
        parts.append(f"Resume education: {', '.join(education[:4])}")
    if resume_skills:
        parts.append(f"Resume extracted skills: {', '.join(resume_skills[:8])}")
    if resume_projects:
        parts.append(f"Resume extracted projects: {', '.join(resume_projects[:4])}")
    if resume_experience:
        parts.append(f"Resume extracted experience: {', '.join(resume_experience[:4])}")
    if resume_hobbies:
        parts.append(f"Resume hobbies/interests: {', '.join(resume_hobbies[:4])}")
    return "\n".join(parts)


def _difficulty_from_experience(experience: str) -> str:
    value = (experience or "").strip().lower()
    if "fresh" in value or "entry" in value or "beginner" in value:
        return "introductory to moderate"
    if "mid" in value:
        return "moderate to advanced"
    if "experien" in value or "senior" in value:
        return "advanced and scenario-based"
    return "moderate"


def _difficulty_band(difficulty_guidance: str) -> str:
    value = _normalize_text(difficulty_guidance).lower()
    if "introductory" in value:
        return "introductory"
    if "advanced" in value:
        return "advanced"
    return "moderate"


def _language_bank_key(language: str) -> str:
    value = _normalize_text(language)
    aliases = {
        "Node.js": "JavaScript",
        ".NET": "C#",
    }
    return aliases.get(value, value)


def _language_phase_defaults(phase: str) -> Tuple[List[str], List[str]]:
    if phase == "warmup":
        return (
            [
                "correct basic concept",
                "clear explanation in plain terms",
                "when or why it is used",
                "small practical example when helpful",
            ],
            ["fundamentals", "clarity", "correctness"],
        )
    if phase == "concept_deep_dive":
        return (
            [
                "clear conceptual explanation",
                "important trade-off or caveat",
                "real-world relevance",
                "structured reasoning",
            ],
            ["conceptual depth", "trade-offs", "clarity"],
        )
    return (
        [
            "real project or debugging context",
            "specific actions or technical choices",
            "reasoning behind the approach",
            "result, learning, or resolution",
        ],
        ["specificity", "practical understanding", "clarity"],
    )


def _pick_language_phase_question(
    language: str,
    phase: str,
    difficulty_guidance: str,
    variation_seed: str = "",
    rotation_index: int = 0,
) -> Dict[str, Any]:
    key = _language_bank_key(language)
    phase_key = _normalize_text(phase) or "warmup"
    bank = LANGUAGE_PHASE_QUESTION_BANK.get(key, LANGUAGE_PHASE_QUESTION_BANK["default"])
    options = list(bank.get(phase_key) or LANGUAGE_PHASE_QUESTION_BANK["default"].get(phase_key) or [])
    if not options:
        options = list(LANGUAGE_PHASE_QUESTION_BANK["default"]["warmup"])

    shuffler = random.Random(
        _normalize_text(f"{variation_seed}|{key}|{phase_key}|{difficulty_guidance}|{rotation_index}")
    )
    selected = dict(shuffler.choice(options))
    question_text = _normalize_text(selected.get("question") or "").format(language=language)
    topic_tag = _normalize_text(selected.get("topic_tag") or language).format(language=language)
    band = _difficulty_band(difficulty_guidance)

    if phase_key == "warmup":
        if band == "introductory":
            question_text = f"{question_text} Keep the explanation simple and concrete."
        elif band == "advanced":
            question_text = f"{question_text} Also mention one caveat, edge case, or mistake if relevant."
    elif phase_key == "concept_deep_dive":
        if band == "introductory":
            question_text = f"{question_text} Explain it step by step."
        elif band == "advanced":
            question_text = f"{question_text} Also include any production trade-off, pitfall, or edge case that matters."
    elif phase_key == "language_discovery":
        if band == "introductory":
            question_text = f"{question_text} Keep it to one clear example."
        elif band == "advanced":
            question_text = f"{question_text} Include the deeper technical decision or trade-off if it mattered."

    expected_points, evaluation_focus = _language_phase_defaults(phase_key)
    question_type = "practical" if phase_key == "language_discovery" else ("conceptual" if phase_key == "concept_deep_dive" else "fundamental")
    return {
        "question": question_text,
        "topic_tag": topic_tag,
        "expected_points": expected_points,
        "evaluation_focus": evaluation_focus,
        "question_type": question_type,
    }


def _resolve_question_count(payload: Dict[str, Any]) -> int:
    config_mode = payload.get("config_mode")
    if config_mode == "time":
        interval = payload.get("time_mode_interval") or payload.get("interview_mode_time") or 5
        try:
            minutes = int(interval)
        except (TypeError, ValueError):
            minutes = 5
        derived_count = max(10, min(30, minutes * 3))
        return derived_count
    return _clamp_question_count(payload.get("question_count"))


def _selected_focus_areas(payload: Dict[str, Any]) -> List[str]:
    return _safe_list(payload.get("focus_areas") or []) or _safe_list(payload.get("selected_options") or [])


def _hr_round_mode(payload: Dict[str, Any]) -> str:
    value = _normalize_text(payload.get("hr_round") or "").lower()
    if value in {"hr", "behavioral", "hr_behavioral"}:
        return value
    if value in {"technical", "both"}:
        return "hr_behavioral"
    return "hr_behavioral"


def _hr_round_label(value: str) -> str:
    normalized = _normalize_text(value).lower()
    mapping = {
        "hr": "HR",
        "behavioral": "Behavioral",
        "hr_behavioral": "HR + Behavioral",
        "technical": "HR + Behavioral",
        "both": "HR + Behavioral",
    }
    return mapping.get(normalized, "HR + Behavioral")


def _hr_adaptive_interview_enabled(payload: Dict[str, Any]) -> bool:
    return _normalize_text(payload.get("category") or "").lower() == "hr"


def _target_subject(payload: Dict[str, Any]) -> str:
    selected_mode = payload.get("selected_mode") or ""
    if selected_mode == "language" and payload.get("primary_language"):
        return payload["primary_language"]
    return (
        payload.get("job_role")
        or payload.get("primary_language")
        or "the selected interview focus"
    )


def _build_interview_variation(payload: Dict[str, Any]) -> Dict[str, str]:
    chooser = random.SystemRandom()
    role = _normalize_text(payload.get("job_role") or payload.get("primary_language") or "the selected role")
    return {
        "seed": uuid.uuid4().hex[:10],
        "opening_style": chooser.choice([
            "warm but crisp technical screening",
            "curious hands-on technical conversation",
            "practical engineer-to-engineer discussion",
            "focused real-world backend assessment",
        ]),
        "technical_lens": chooser.choice([
            "debugging and troubleshooting",
            "practical implementation details",
            "real-world architecture and trade-offs",
            "backend fundamentals with production thinking",
            "API design and maintainability",
            "performance, reliability, and scalability",
        ]),
        "scenario_lens": chooser.choice([
            "a production incident",
            "a feature launch under deadline pressure",
            "a scaling bottleneck",
            "a debugging-heavy support case",
            "a maintainability refactor",
        ]),
        "follow_up_style": chooser.choice([
            "go deeper after strong answers",
            "simplify and clarify after weak answers",
            "alternate between concept and example",
            "mix direct questions with small scenarios",
        ]),
        "freshness_rule": (
            f"Make this {role} interview feel fresh for seed {uuid.uuid4().hex[:6]} "
            "and avoid reusing stock boilerplate wording."
        ),
    }


def _variation_summary(variation: Optional[Dict[str, str]]) -> str:
    data = variation or {}
    return "\n".join(
        [
            f"Variation seed: {_normalize_text(data.get('seed') or 'default')}",
            f"Opening style: {_normalize_text(data.get('opening_style') or 'standard technical interview')}",
            f"Technical lens: {_normalize_text(data.get('technical_lens') or 'general technical depth')}",
            f"Scenario lens: {_normalize_text(data.get('scenario_lens') or 'real-world backend scenario')}",
            f"Follow-up style: {_normalize_text(data.get('follow_up_style') or 'balanced follow-up')}",
            f"Freshness directive: {_normalize_text(data.get('freshness_rule') or 'Keep the interview wording fresh and non-repetitive.')}",
        ]
    )


def _safe_question_type(value: Any) -> str:
    allowed = {
        "discovery",
        "introduction",
        "fundamental",
        "conceptual",
        "practical",
        "scenario",
        "behavioral",
    }
    normalized = _normalize_text(str(value or "")).lower().replace(" ", "_")
    normalized = normalized.replace("_based", "").replace("technical_", "")
    if normalized in allowed:
        return normalized
    return "practical"


def _match_role_profile(job_role: str) -> Optional[Dict[str, Any]]:
    role_text = _normalize_text(job_role).lower()
    if not role_text:
        return None

    for profile in ROLE_PROFILES:
        for alias in profile["aliases"]:
            if alias in role_text:
                return profile
    return None


def _role_keyword_terms(job_role: str) -> List[str]:
    role_text = _normalize_text(job_role).lower()
    ignore = {
        "developer", "engineer", "specialist", "associate", "intern", "trainee", "lead",
        "manager", "architect", "consultant", "analyst", "staff", "principal", "junior",
        "senior", "expert", "head", "full", "stack",
    }
    terms = []
    for token in re.findall(r"[a-zA-Z0-9+#.]+", role_text):
        if len(token) > 2 and token not in ignore and token not in terms:
            terms.append(token)
    return terms[:6]


def _generic_role_focus(job_role: str, primary_language: str, selected_options: List[str]) -> Dict[str, List[str]]:
    role_label = _normalize_text(job_role) or "Technical Role"
    role_terms = _role_keyword_terms(role_label)
    option_terms = _safe_list(selected_options)[:6]
    tech_stack = _merge_unique([primary_language] if primary_language else [], option_terms)
    tech_stack = _merge_unique(tech_stack, [term.title() for term in role_terms[:3]])

    core_areas = []
    if primary_language:
        core_areas.append(f"{primary_language} fundamentals for {role_label}")
    core_areas.extend(option_terms[:4])
    core_areas.extend(
        [
            f"core responsibilities of a {role_label}",
            f"real-world workflows in {role_label}",
            f"debugging and troubleshooting for {role_label}",
            f"design and trade-offs for {role_label}",
            f"testing, reliability, or quality expectations for {role_label}",
        ]
    )
    for term in role_terms[:3]:
        core_areas.append(f"{term.title()} concepts relevant to {role_label}")

    question_focus = [
        f"Ask practical questions that mirror real {role_label} work",
        f"Ask what tools, systems, or workflows a strong {role_label} candidate should know",
        f"Ask debugging, design, trade-off, and implementation questions for {role_label}",
        f"Ask scenario-based questions grounded in day-to-day {role_label} responsibilities",
    ]
    if primary_language:
        question_focus.append(f"Ask how {primary_language} is used effectively in {role_label}")
    for option in option_terms[:3]:
        question_focus.append(f"Ask role-specific questions using {option}")

    return {
        "core_areas": list(dict.fromkeys(core_areas))[:8],
        "question_focus": list(dict.fromkeys(question_focus))[:7],
        "tech_stack": tech_stack[:6],
    }


def _fallback_role_blueprint(payload: Dict[str, Any]) -> Dict[str, Any]:
    job_role = _normalize_text(payload.get("job_role") or "")
    primary_language = _normalize_text(payload.get("primary_language") or "")
    selected_options = _safe_list(payload.get("selected_options") or [])
    role_profile = _match_role_profile(job_role)

    if role_profile:
        return {
            "role_label": role_profile["label"],
            "core_areas": role_profile["core_fields"][:6],
            "tech_stack": [primary_language] if primary_language else [],
            "question_focus": role_profile["question_seeds"][:5],
            "language_focus": primary_language or "",
        }

    inferred_stack = []
    if primary_language:
        inferred_stack.append(primary_language)
    inferred_stack.extend(selected_options[:4])
    generic_focus = _generic_role_focus(job_role, primary_language, selected_options)
    core_areas = generic_focus["core_areas"] or (
        selected_options[:6] if selected_options else [
            "programming fundamentals",
            "core concepts",
            "problem solving",
            "debugging",
            "system understanding",
        ]
    )

    return {
        "role_label": job_role or primary_language or "Technical Role",
        "core_areas": core_areas,
        "tech_stack": generic_focus["tech_stack"] or inferred_stack,
        "question_focus": generic_focus["question_focus"] or [
            f"Ask technical fundamentals for {job_role or primary_language or 'the selected role'}",
            "Ask conceptual questions based on selected topics",
            "Ask practical implementation questions",
            "Ask debugging or architecture questions where relevant",
        ],
        "language_focus": primary_language or "",
    }


async def _call_gemini_json(
    prompt: str,
    temperature: float = 0.35,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise ProviderError("GEMINI_API_KEY is not configured.")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    attempts = [
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        },
        {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"{prompt}\n\nReturn one JSON object only. No markdown, no comments, no prose."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": min(temperature, 0.2),
            },
        },
    ]

    errors = []
    for payload in attempts:
        try:
            data = await asyncio.to_thread(_http_post_json, url, payload, None, timeout_seconds or 80)
            text = _extract_gemini_text(data)
            return _extract_json_block(text)
        except ProviderError as exc:
            errors.append(str(exc))

    raise ProviderError(" | ".join(errors))


async def _call_ollama_json(
    prompt: str,
    temperature: float = 0.2,
    timeout_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    url = f"{OLLAMA_BASE_URL}/api/generate"
    effective_prompt = prompt
    if OLLAMA_MODEL.lower().startswith("qwen3") and not prompt.lstrip().startswith("/no_think"):
        # Qwen3 defaults to thinking mode, which is too slow for this app on CPU-only laptops.
        effective_prompt = f"/no_think\n{prompt}"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": effective_prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
    }
    data = await asyncio.to_thread(
        _http_post_json,
        url,
        payload,
        None,
        timeout_seconds or OLLAMA_TIMEOUT_SECONDS,
    )
    text = data.get("response", "")
    return _extract_json_block(text)


async def _generate_json_with_fallback(
    prompt: str,
    order: List[str],
    temperature: float = 0.3,
    timeout_seconds: Optional[int] = None,
) -> Tuple[Dict[str, Any], str]:
    errors = []
    for provider in order:
        try:
            if provider == "gemini":
                return await _call_gemini_json(prompt, temperature, timeout_seconds), "gemini"
            if provider == "ollama":
                return await _call_ollama_json(prompt, temperature, timeout_seconds), "ollama"
        except ProviderError as exc:
            errors.append(f"{provider}: {exc}")

    raise ProviderError(" | ".join(errors) if errors else "No provider available.")


def get_ai_provider_status() -> Dict[str, Any]:
    ollama_status = {
        "configured": bool(OLLAMA_BASE_URL and OLLAMA_MODEL),
        "available": False,
        "connection_checked": True,
        "model": OLLAMA_MODEL,
        "base_url": OLLAMA_BASE_URL,
        "detail": "",
    }

    if ollama_status["configured"]:
        try:
            tags = _http_get_json(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            models = tags.get("models") or []
            installed = [
                _normalize_text(model.get("name") or model.get("model") or "")
                for model in models
                if isinstance(model, dict)
            ]
            ollama_status["available"] = True
            if OLLAMA_MODEL and installed:
                has_model = any(
                    item == OLLAMA_MODEL or item.startswith(f"{OLLAMA_MODEL}:")
                    for item in installed
                )
                ollama_status["detail"] = (
                    f"Connected. Model '{OLLAMA_MODEL}' is installed."
                    if has_model
                    else f"Connected, but model '{OLLAMA_MODEL}' is not installed."
                )
            else:
                ollama_status["detail"] = "Connected."
        except ProviderError as exc:
            ollama_status["detail"] = str(exc)
    else:
        ollama_status["detail"] = "OLLAMA_BASE_URL or OLLAMA_MODEL is missing."

    gemini_configured = bool(GEMINI_API_KEY)
    return {
        "providers": {
            "gemini": {
                "configured": gemini_configured,
                "available": gemini_configured,
                "connection_checked": False,
                "model": GEMINI_MODEL,
                "detail": "API key loaded." if gemini_configured else "GEMINI_API_KEY is missing.",
            },
            "ollama": ollama_status,
        },
        "stage_order": {
            "analysis": ["gemini", "ollama"],
            "generation": ["gemini", "ollama"],
            "evaluation": ["gemini", "ollama"],
            "summary": ["gemini", "ollama"],
        },
    }


COMPUTER_FUNDAMENTALS_TOPICS = [
    "DBMS",
    "Computer Networks",
    "Operating Systems",
    "Programming Concepts",
    "Data Structures",
    "Computer Fundamentals",
    "OOP (Object-Oriented Programming)",
    "Software Engineering",
    "Basics of Algorithms",
]


APTITUDE_TOPICS = [
    "Clocks & Calendar",
    "Series and Progressions",
    "Equations",
    "Averages",
    "Area, Shapes & Perimeter",
    "Numbers & Decimal Fractions",
    "Number System",
    "LCM & HCF",
    "Percentages",
    "Allegations and Mixtures",
    "Probability",
    "Ratios",
    "Proportion",
    "Work and Time",
    "Geometry",
    "Divisibility",
    "Profit and Loss",
    "Ages",
    "Speed Distance and Time",
    "Pie Charts",
    "Mean, Median, Mode, Variance and Standard Deviation",
]


REASONING_TOPICS = [
    "Blood Relations",
    "Seating Arrangement",
    "Coding-Decoding",
    "Data Sufficiency",
    "Data Arrangements",
    "Distance and Directions",
    "Statement and Conclusion",
    "Data Interpretation",
    "Syllogism",
    "Word Pattern",
    "Letter Series",
    "Number Series",
    "Directional Sense",
    "Figure-Based Reasoning",
    "Cube Folding, Paper Cuts and Folds",
]


VERBAL_TOPICS = [
    "Sentence Completion",
    "Words Completion",
    "Reading Comprehension",
    "Para jumbles",
    "Error Detection",
    "Sentence Building",
    "Idioms & Phrases",
]


ADVANCED_QUANT_TOPICS = [
    "HCF & LCM and Number System",
    "Geometry",
    "Ages",
    "Allegations and Mixtures",
    "Averages",
    "Clocks and Calendars",
    "Equations",
    "Percentages",
    "Permutations and Combinations",
    "Probability",
    "Profit and Loss",
    "Ratios and Proportion",
    "Series and Progressions",
    "Time, Speed and Distance",
    "Time and Work",
    "Mean, Median, Mode, Standard Deviation, and Variance",
    "Data Interpretation",
    "Graphical Data Interpretation",
    "Pie Charts",
    "Tabular Data Interpretation",
    "Simple Arithmetic Operations",
]


APTITUDE_FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "What is 15% of 240?", "options": ["24", "30", "36", "42"], "answer": "36", "topic": "Percentages"},
    {"question": "If 25% of a number is 75, the number is:", "options": ["250", "275", "300", "325"], "answer": "300", "topic": "Percentages"},
    {"question": "The average of 12, 18, 20, and 30 is:", "options": ["18", "20", "22", "24"], "answer": "20", "topic": "Averages"},
    {"question": "The mean of 5, 7, 9, 11, and 13 is:", "options": ["8", "9", "10", "11"], "answer": "9", "topic": "Mean, Median, Mode, Variance and Standard Deviation"},
    {"question": "A train travels 180 km in 3 hours. What is its speed?", "options": ["50 km/h", "55 km/h", "60 km/h", "65 km/h"], "answer": "60 km/h", "topic": "Speed Distance and Time"},
    {"question": "If a worker completes a job in 10 days, what fraction of the work is done in 1 day?", "options": ["1/5", "1/10", "1/12", "1/15"], "answer": "1/10", "topic": "Work and Time"},
    {"question": "What is the area of a rectangle with length 15 cm and breadth 8 cm?", "options": ["100", "110", "120", "130"], "answer": "120", "topic": "Area, Shapes & Perimeter"},
    {"question": "The perimeter of a square is 36 cm. What is the side length?", "options": ["6 cm", "8 cm", "9 cm", "12 cm"], "answer": "9 cm", "topic": "Area, Shapes & Perimeter"},
    {"question": "Which of the following numbers is divisible by 3?", "options": ["124", "153", "172", "190"], "answer": "153", "topic": "Divisibility"},
    {"question": "What is the HCF of 18 and 24?", "options": ["3", "6", "9", "12"], "answer": "6", "topic": "LCM & HCF"},
    {"question": "What is the LCM of 6 and 8?", "options": ["12", "24", "36", "48"], "answer": "24", "topic": "LCM & HCF"},
    {"question": "What is 3/4 of 84?", "options": ["56", "60", "63", "66"], "answer": "63", "topic": "Numbers & Decimal Fractions"},
    {"question": "0.75 is equal to:", "options": ["3/2", "3/4", "4/3", "7/5"], "answer": "3/4", "topic": "Numbers & Decimal Fractions"},
    {"question": "Which of the following is a prime number?", "options": ["21", "29", "33", "39"], "answer": "29", "topic": "Number System"},
    {"question": "If the ratio of boys to girls is 3:2 and there are 30 boys, how many girls are there?", "options": ["18", "20", "22", "24"], "answer": "20", "topic": "Ratios"},
    {"question": "If x : y = 4 : 5 and x = 20, then y = ?", "options": ["22", "24", "25", "28"], "answer": "25", "topic": "Proportion"},
    {"question": "A shopkeeper gains 20% on an item sold for Rs. 240. What was the cost price?", "options": ["Rs. 180", "Rs. 190", "Rs. 200", "Rs. 210"], "answer": "Rs. 200", "topic": "Profit and Loss"},
    {"question": "A and B can complete a work in 6 days together. If A alone can do it in 10 days, how many days will B alone take?", "options": ["12", "15", "18", "20"], "answer": "15", "topic": "Work and Time"},
    {"question": "The sum of present ages of a father and son is 50. If the father is 20 years older, what is the son's age?", "options": ["10", "15", "20", "25"], "answer": "15", "topic": "Ages"},
    {"question": "In a pie chart, a sector of 90 degrees represents what fraction of the whole?", "options": ["1/2", "1/3", "1/4", "1/5"], "answer": "1/4", "topic": "Pie Charts"},
    {"question": "A bag contains 3 red and 2 blue balls. What is the probability of drawing a red ball?", "options": ["1/5", "2/5", "3/5", "4/5"], "answer": "3/5", "topic": "Probability"},
    {"question": "In the mixture 2 liters milk and 3 liters water, the ratio of milk to water is:", "options": ["2:3", "3:2", "5:2", "2:5"], "answer": "2:3", "topic": "Allegations and Mixtures"},
    {"question": "What comes next in the series 2, 4, 8, 16, ?", "options": ["24", "30", "32", "36"], "answer": "32", "topic": "Series and Progressions"},
    {"question": "Solve: 2x + 5 = 17", "options": ["4", "5", "6", "7"], "answer": "6", "topic": "Equations"},
    {"question": "How many odd days are there in 2 ordinary years?", "options": ["0", "1", "2", "3"], "answer": "2", "topic": "Clocks & Calendar"},
    {"question": "The sum of angles in a triangle is:", "options": ["90 degrees", "120 degrees", "180 degrees", "360 degrees"], "answer": "180 degrees", "topic": "Geometry"},
]


REASONING_FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "Pointing to a man, Riya says, 'He is the son of my mother's brother.' How is the man related to Riya?", "options": ["Brother", "Cousin", "Uncle", "Nephew"], "answer": "Cousin", "topic": "Blood Relations"},
    {"question": "Five people sit in a row. A is to the left of B, and C is to the right of B. Who sits in the middle among A, B, and C?", "options": ["A", "B", "C", "Cannot be determined"], "answer": "B", "topic": "Seating Arrangement"},
    {"question": "If CAT is coded as DBU, then DOG is coded as:", "options": ["EPH", "EPG", "DOH", "FPH"], "answer": "EPH", "topic": "Coding-Decoding"},
    {"question": "Statement: All pens are books. Some books are bags. Conclusion: Some pens are bags. Choose the correct option.", "options": ["Conclusion definitely follows", "Conclusion does not follow", "Conclusion may follow", "Both statement and conclusion are false"], "answer": "Conclusion does not follow", "topic": "Syllogism"},
    {"question": "Which number comes next in the series 2, 5, 10, 17, 26, ?", "options": ["35", "36", "37", "38"], "answer": "37", "topic": "Number Series"},
    {"question": "Which letter comes next in the series A, C, F, J, ?", "options": ["M", "N", "O", "P"], "answer": "O", "topic": "Letter Series"},
    {"question": "If SOUTH is written as HTUOS, then which of the following is a similar word pattern for TRAIN?", "options": ["NIART", "TRAINI", "TARIN", "RAINT"], "answer": "NIART", "topic": "Word Pattern"},
    {"question": "A person walks 5 km north and then 3 km east. In which direction is the person from the starting point?", "options": ["North-East", "South-East", "North-West", "West"], "answer": "North-East", "topic": "Distance and Directions"},
    {"question": "A person walks 10 m south, then 10 m west. Which direction is the final position from the start?", "options": ["South-East", "South-West", "North-West", "North-East"], "answer": "South-West", "topic": "Directional Sense"},
    {"question": "Statement: All students should revise daily. Conclusion: Revision helps students prepare better. Choose the best option.", "options": ["Conclusion follows", "Conclusion does not follow", "Both are unrelated", "Statement is false"], "answer": "Conclusion follows", "topic": "Statement and Conclusion"},
    {"question": "A table shows sales of 10, 20, 30, and 40 units in four months. What is the average monthly sales?", "options": ["20", "25", "30", "35"], "answer": "25", "topic": "Data Interpretation"},
    {"question": "Question: Is x greater than y? Statements: 1. x = 12  2. y = 10. Choose the correct option.", "options": ["Statement 1 alone is sufficient", "Statement 2 alone is sufficient", "Both together are sufficient", "Data insufficient"], "answer": "Both together are sufficient", "topic": "Data Sufficiency"},
    {"question": "In a line arrangement, P is between Q and R. If Q is at one end, where is R?", "options": ["At the other end", "In the middle", "Next to Q", "Cannot be determined"], "answer": "At the other end", "topic": "Data Arrangements"},
    {"question": "A figure sequence shows: 1 triangle, then 2 triangles, then 3 triangles. If the pattern continues, how many triangles will be in the 6th figure?", "options": ["5", "6", "7", "8"], "answer": "6", "topic": "Figure-Based Reasoning"},
    {"question": "A square is rotated 90 degrees clockwise in each step. If it starts with a dot at the top-left corner, where will the dot be after 2 rotations?", "options": ["Top-right", "Bottom-right", "Bottom-left", "Top-left"], "answer": "Bottom-right", "topic": "Figure-Based Reasoning"},
    {"question": "In a shape pattern, the number of sides goes 3, 4, 5, 6. Which shape should come next?", "options": ["Triangle", "Hexagon", "Heptagon", "Octagon"], "answer": "Heptagon", "topic": "Figure-Based Reasoning"},
    {"question": "A paper is folded once and a hole is punched near the folded edge. After unfolding, how many holes will appear?", "options": ["1", "2", "3", "4"], "answer": "2", "topic": "Figure-Based Reasoning"},
    {"question": "A cube has all faces painted. If it is cut into 27 smaller equal cubes, how many small cubes will have paint on exactly 2 faces?", "options": ["8", "12", "6", "24"], "answer": "12", "topic": "Cube Folding, Paper Cuts and Folds"},
]


VERBAL_FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "Choose the correct word to complete the sentence: She was tired, ____ she finished the work.", "options": ["but", "yet", "although", "because"], "answer": "yet", "topic": "Sentence Completion"},
    {"question": "Fill in the blank: The manager asked the team to work with great ____.", "options": ["diligence", "diligent", "diligently", "dilute"], "answer": "diligence", "topic": "Words Completion"},
    {"question": "Read the sentence and find the error: 'He do not like coffee.'", "options": ["He", "do", "not", "coffee"], "answer": "do", "topic": "Error Detection"},
    {"question": "Choose the correctly arranged sentence: 1. to 2. school 3. every day 4. She goes", "options": ["She school goes to every day", "She goes to school every day", "To school she every day goes", "Every day school she goes to"], "answer": "She goes to school every day", "topic": "Sentence Building"},
    {"question": "Choose the correct meaning of the idiom 'break the ice'.", "options": ["To crack frozen water", "To start a conversation comfortably", "To stop talking", "To become angry"], "answer": "To start a conversation comfortably", "topic": "Idioms & Phrases"},
    {"question": "Arrange the following into a meaningful paragraph order: P: It started raining heavily. Q: We opened our umbrellas. R: Dark clouds gathered. S: We hurried home.", "options": ["R, P, Q, S", "P, R, Q, S", "Q, R, P, S", "R, Q, P, S"], "answer": "R, P, Q, S", "topic": "Para jumbles"},
    {"question": "Choose the best word to complete the sentence: The new policy will ____ better communication between teams.", "options": ["foster", "fostersly", "fostering", "fostered"], "answer": "foster", "topic": "Words Completion"},
    {"question": "Sentence Completion: If you study regularly, you ____ improve your vocabulary.", "options": ["will", "would", "shall be", "had"], "answer": "will", "topic": "Sentence Completion"},
    {"question": "Read the passage: 'Mina reads every day. She enjoys stories about science and discovery.' What does Mina like to read about?", "options": ["History", "Sports", "Science and discovery", "Travel only"], "answer": "Science and discovery", "topic": "Reading Comprehension"},
    {"question": "Find the error: 'Neither of the boys were present.'", "options": ["Neither", "boys", "were", "present"], "answer": "were", "topic": "Error Detection"},
    {"question": "Choose the correct meaning of the idiom 'once in a blue moon'.", "options": ["Very often", "Very rarely", "At night", "Without warning"], "answer": "Very rarely", "topic": "Idioms & Phrases"},
    {"question": "Arrange the words into a meaningful sentence: 1. honesty 2. the best policy 3. is 4.", "options": ["Honesty is the best policy", "The best honesty is policy", "Policy is honesty the best", "Is honesty best the policy"], "answer": "Honesty is the best policy", "topic": "Sentence Building"},
    {"question": "Choose the best completion: The speaker paused for a moment ____ continuing the lecture.", "options": ["before", "after", "during", "through"], "answer": "before", "topic": "Sentence Completion"},
    {"question": "Read the passage: 'The library was silent, so everyone spoke softly.' Why did everyone speak softly?", "options": ["They were afraid", "The library was silent", "They were outside", "They were singing"], "answer": "The library was silent", "topic": "Reading Comprehension"},
]


ADVANCED_QUANT_FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "Find the HCF of 84, 126, and 210.", "options": ["14", "21", "28", "42"], "answer": "42", "topic": "HCF & LCM and Number System"},
    {"question": "The LCM of 18, 24, and 30 is:", "options": ["120", "180", "240", "360"], "answer": "360", "topic": "HCF & LCM and Number System"},
    {"question": "The radius of a circle is increased by 20%. By what percent does the area increase?", "options": ["20%", "36%", "40%", "44%"], "answer": "44%", "topic": "Geometry"},
    {"question": "Ten years ago, the ratio of ages of A and B was 3:2. Ten years from now it will be 5:4. What is A's present age?", "options": ["30", "35", "40", "45"], "answer": "40", "topic": "Ages"},
    {"question": "In what ratio should water be mixed with milk costing Rs. 30 per liter so that the mixture sold at Rs. 24 per liter gives no profit and no loss?", "options": ["1:4", "1:5", "2:5", "3:7"], "answer": "1:4", "topic": "Allegations and Mixtures"},
    {"question": "The average of 15 numbers is 24. If one number is excluded, the average becomes 23. What is the excluded number?", "options": ["32", "36", "38", "40"], "answer": "38", "topic": "Averages"},
    {"question": "If 15th August 2021 was a Sunday, what day was 15th August 2022?", "options": ["Sunday", "Monday", "Tuesday", "Wednesday"], "answer": "Monday", "topic": "Clocks and Calendars"},
    {"question": "Solve for x: 3x + 5 = 2x + 17", "options": ["10", "11", "12", "13"], "answer": "12", "topic": "Equations"},
    {"question": "A number is increased by 25% and then decreased by 20%. The net change is:", "options": ["0%", "4% increase", "5% increase", "5% decrease"], "answer": "0%", "topic": "Percentages"},
    {"question": "How many different 4-letter arrangements can be made from the letters of the word MATH if repetition is not allowed?", "options": ["12", "18", "24", "36"], "answer": "24", "topic": "Permutations and Combinations"},
    {"question": "Two dice are thrown together. What is the probability of getting a sum of 9?", "options": ["1/6", "1/8", "1/9", "1/12"], "answer": "1/9", "topic": "Probability"},
    {"question": "A trader marks his goods 25% above cost price and allows a discount of 10%. His profit percent is:", "options": ["10%", "12.5%", "15%", "20%"], "answer": "12.5%", "topic": "Profit and Loss"},
    {"question": "If x : y = 7 : 9 and y : z = 3 : 5, then x : y : z is:", "options": ["7:9:15", "7:3:5", "21:27:45", "14:18:15"], "answer": "21:27:45", "topic": "Ratios and Proportion"},
    {"question": "Find the next term in the series: 3, 8, 15, 24, 35, ?", "options": ["44", "46", "48", "50"], "answer": "48", "topic": "Series and Progressions"},
    {"question": "A car covers 360 km in 4.5 hours. What is its average speed?", "options": ["72 km/h", "76 km/h", "80 km/h", "84 km/h"], "answer": "80 km/h", "topic": "Time, Speed and Distance"},
    {"question": "A can do a piece of work in 12 days and B in 18 days. In how many days can they finish it together?", "options": ["6.2", "7.2", "7.5", "8"], "answer": "7.2", "topic": "Time and Work"},
    {"question": "The mean of five observations is 18. If four observations are 12, 16, 20, and 24, the fifth observation is:", "options": ["14", "16", "18", "20"], "answer": "18", "topic": "Mean, Median, Mode, Standard Deviation, and Variance"},
    {"question": "If the median of 3, 5, 7, x, 11 is 7, which of the following can be x?", "options": ["1", "6", "7", "13"], "answer": "6", "topic": "Mean, Median, Mode, Standard Deviation, and Variance"},
    {"question": "Sales in four quarters are 120, 150, 180, and 210 units. What is the percentage increase from the first to the last quarter?", "options": ["60%", "65%", "70%", "75%"], "answer": "75%", "topic": "Data Interpretation"},
    {"question": "A line graph shows values rising from 40 to 70. What is the percentage increase?", "options": ["60%", "65%", "75%", "80%"], "answer": "75%", "topic": "Graphical Data Interpretation"},
    {"question": "In a pie chart, if a sector measures 72 degrees, what percent of the total does it represent?", "options": ["18%", "20%", "22%", "25%"], "answer": "20%", "topic": "Pie Charts"},
    {"question": "A table shows monthly profits of Rs. 20k, 25k, 30k, and 35k. What is the average monthly profit?", "options": ["Rs. 25k", "Rs. 27.5k", "Rs. 28k", "Rs. 30k"], "answer": "Rs. 27.5k", "topic": "Tabular Data Interpretation"},
    {"question": "Evaluate: 18 + 6 x 3 - 12 / 4", "options": ["32", "33", "34", "35"], "answer": "33", "topic": "Simple Arithmetic Operations"},
]


COMPUTER_FUNDAMENTALS_FALLBACK_QUESTIONS: List[Dict[str, Any]] = [
    {"question": "Which SQL command is used to retrieve data from a database?", "options": ["GET", "SELECT", "OPEN", "FETCHROW"], "answer": "SELECT", "topic": "DBMS"},
    {"question": "Which normal form removes partial dependency in a relation?", "options": ["1NF", "2NF", "3NF", "BCNF"], "answer": "2NF", "topic": "DBMS"},
    {"question": "Which SQL clause is used to filter rows after grouping?", "options": ["WHERE", "HAVING", "ORDER BY", "DISTINCT"], "answer": "HAVING", "topic": "DBMS"},
    {"question": "Which device operates mainly at the network layer to forward packets?", "options": ["Hub", "Switch", "Router", "Repeater"], "answer": "Router", "topic": "Computer Networks"},
    {"question": "Which protocol is commonly used to transfer web pages?", "options": ["FTP", "SMTP", "HTTP", "SNMP"], "answer": "HTTP", "topic": "Computer Networks"},
    {"question": "Which topology connects all devices to a central hub or switch?", "options": ["Ring", "Bus", "Star", "Mesh"], "answer": "Star", "topic": "Computer Networks"},
    {"question": "Which scheduling algorithm gives the CPU first to the process that arrives earliest?", "options": ["Round Robin", "Priority", "First Come First Serve", "Shortest Job First"], "answer": "First Come First Serve", "topic": "Operating Systems"},
    {"question": "What is the main purpose of an operating system?", "options": ["Design websites", "Manage hardware and software resources", "Create databases only", "Compile programs only"], "answer": "Manage hardware and software resources", "topic": "Operating Systems"},
    {"question": "Which memory stores data temporarily while a program is running?", "options": ["ROM", "RAM", "Hard Disk", "Plotter memory"], "answer": "RAM", "topic": "Operating Systems"},
    {"question": "Which statement about a compiler is correct?", "options": ["It translates the whole program before execution", "It executes SQL queries", "It only formats code", "It stores programs permanently"], "answer": "It translates the whole program before execution", "topic": "Programming Concepts"},
    {"question": "Which loop is guaranteed to execute at least once in many programming languages?", "options": ["for loop", "while loop", "do-while loop", "foreach loop"], "answer": "do-while loop", "topic": "Programming Concepts"},
    {"question": "Which data type is commonly used to store true or false values?", "options": ["float", "boolean", "char", "array"], "answer": "boolean", "topic": "Programming Concepts"},
    {"question": "Which data structure follows the Last In First Out principle?", "options": ["Queue", "Stack", "Linked List", "Tree"], "answer": "Stack", "topic": "Data Structures"},
    {"question": "Which traversal of a Binary Search Tree returns values in sorted order?", "options": ["Preorder", "Postorder", "Inorder", "Level order"], "answer": "Inorder", "topic": "Data Structures"},
    {"question": "Which of the following is not a linear data structure?", "options": ["Array", "Stack", "Queue", "Tree"], "answer": "Tree", "topic": "Data Structures"},
    {"question": "CPU stands for:", "options": ["Central Process Unit", "Central Processing Unit", "Control Program Unit", "Computer Primary Unit"], "answer": "Central Processing Unit", "topic": "Computer Fundamentals"},
    {"question": "Which number system uses only 0 and 1?", "options": ["Decimal", "Binary", "Octal", "Hexadecimal"], "answer": "Binary", "topic": "Computer Fundamentals"},
    {"question": "Which of these is an input device?", "options": ["Monitor", "Printer", "Keyboard", "Speaker"], "answer": "Keyboard", "topic": "Computer Fundamentals"},
    {"question": "Which OOP concept allows one class to acquire the properties of another class?", "options": ["Polymorphism", "Encapsulation", "Inheritance", "Abstraction"], "answer": "Inheritance", "topic": "OOP (Object-Oriented Programming)"},
    {"question": "Which principle hides internal implementation details from the user?", "options": ["Inheritance", "Abstraction", "Compilation", "Recursion"], "answer": "Abstraction", "topic": "OOP (Object-Oriented Programming)"},
    {"question": "What is meant by polymorphism in OOP?", "options": ["Storing data in private fields", "Using one interface with many forms", "Creating only one object", "Combining hardware devices"], "answer": "Using one interface with many forms", "topic": "OOP (Object-Oriented Programming)"},
    {"question": "Which phase of the software development life cycle focuses on gathering requirements?", "options": ["Testing", "Maintenance", "Requirement Analysis", "Deployment"], "answer": "Requirement Analysis", "topic": "Software Engineering"},
    {"question": "Which testing type checks individual functions or modules?", "options": ["System Testing", "Integration Testing", "Unit Testing", "Acceptance Testing"], "answer": "Unit Testing", "topic": "Software Engineering"},
    {"question": "A software bug is best described as:", "options": ["A finished feature", "An error or flaw in the program", "A database backup", "A network cable"], "answer": "An error or flaw in the program", "topic": "Software Engineering"},
    {"question": "What is the time complexity of binary search on a sorted array?", "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "answer": "O(log n)", "topic": "Basics of Algorithms"},
    {"question": "Which algorithmic technique solves a problem by dividing it into smaller subproblems and combining results?", "options": ["Brute force", "Divide and conquer", "Greedy only", "Backtracking only"], "answer": "Divide and conquer", "topic": "Basics of Algorithms"},
    {"question": "Which notation is commonly used to describe algorithm efficiency?", "options": ["SQL notation", "Big O notation", "Binary notation", "Flowchart notation"], "answer": "Big O notation", "topic": "Basics of Algorithms"},
]


def _normalize_mcq_option(value: Any) -> str:
    return _normalize_text(str(value or ""))


def _normalize_generated_mcq(raw_question: Dict[str, Any], index: int) -> Dict[str, Any]:
    question = _normalize_text(raw_question.get("question") or raw_question.get("prompt") or raw_question.get("text") or "")
    if not question:
        raise ProviderError("Generated MCQ question text was empty.")

    raw_options = raw_question.get("options") or raw_question.get("choices") or []
    options: List[str] = []
    seen_options = set()
    for option in raw_options:
        normalized_option = _normalize_mcq_option(option)
        if normalized_option and normalized_option.lower() not in seen_options:
            seen_options.add(normalized_option.lower())
            options.append(normalized_option)

    answer = _normalize_mcq_option(raw_question.get("answer") or raw_question.get("correct_answer"))
    if answer and answer.lower() not in seen_options:
        options.append(answer)
        seen_options.add(answer.lower())

    if len(options) != 4:
        raise ProviderError("Generated MCQ did not contain exactly four unique options.")
    if not answer:
        raise ProviderError("Generated MCQ answer was empty.")
    if answer.lower() not in {item.lower() for item in options}:
        raise ProviderError("Generated MCQ answer was not included in options.")

    topic = _normalize_text(raw_question.get("topic") or raw_question.get("category") or "Computer Fundamentals")
    return {
        "question": question,
        "options": options,
        "answer": next(item for item in options if item.lower() == answer.lower()),
        "topic": topic,
        "sessionId": f"computer-fundamentals-generated-{index + 1}",
    }


def _build_computer_fundamentals_fallback_questions(count: int) -> List[Dict[str, Any]]:
    shuffled = [dict(item) for item in COMPUTER_FUNDAMENTALS_FALLBACK_QUESTIONS]
    random.shuffle(shuffled)
    questions: List[Dict[str, Any]] = []
    round_number = 0
    while len(questions) < count:
        for item in shuffled:
            questions.append({
                **item,
                "sessionId": f"computer-fundamentals-fallback-{round_number}-{len(questions) + 1}",
            })
            if len(questions) >= count:
                break
        round_number += 1
        random.shuffle(shuffled)
    return questions[:count]


def _build_aptitude_fallback_questions(count: int) -> List[Dict[str, Any]]:
    shuffled = [dict(item) for item in APTITUDE_FALLBACK_QUESTIONS]
    random.shuffle(shuffled)
    questions: List[Dict[str, Any]] = []
    round_number = 0
    while len(questions) < count:
        for item in shuffled:
            questions.append({
                **item,
                "sessionId": f"aptitude-fallback-{round_number}-{len(questions) + 1}",
            })
            if len(questions) >= count:
                break
        round_number += 1
        random.shuffle(shuffled)
    return questions[:count]


def _build_reasoning_fallback_questions(count: int) -> List[Dict[str, Any]]:
    shuffled = [dict(item) for item in REASONING_FALLBACK_QUESTIONS]
    random.shuffle(shuffled)
    questions: List[Dict[str, Any]] = []
    round_number = 0
    while len(questions) < count:
        for item in shuffled:
            questions.append({
                **item,
                "sessionId": f"reasoning-fallback-{round_number}-{len(questions) + 1}",
            })
            if len(questions) >= count:
                break
        round_number += 1
        random.shuffle(shuffled)
    return questions[:count]


def _build_verbal_fallback_questions(count: int) -> List[Dict[str, Any]]:
    shuffled = [dict(item) for item in VERBAL_FALLBACK_QUESTIONS]
    random.shuffle(shuffled)
    questions: List[Dict[str, Any]] = []
    round_number = 0
    while len(questions) < count:
        for item in shuffled:
            questions.append({
                **item,
                "sessionId": f"verbal-fallback-{round_number}-{len(questions) + 1}",
            })
            if len(questions) >= count:
                break
        round_number += 1
        random.shuffle(shuffled)
    return questions[:count]


def _build_advanced_quant_fallback_questions(count: int) -> List[Dict[str, Any]]:
    shuffled = [dict(item) for item in ADVANCED_QUANT_FALLBACK_QUESTIONS]
    random.shuffle(shuffled)
    questions: List[Dict[str, Any]] = []
    round_number = 0
    while len(questions) < count:
        for item in shuffled:
            questions.append({
                **item,
                "sessionId": f"advanced-quant-fallback-{round_number}-{len(questions) + 1}",
            })
            if len(questions) >= count:
                break
        round_number += 1
        random.shuffle(shuffled)
    return questions[:count]


async def generate_computer_fundamentals_questions(count: int = 10) -> List[Dict[str, Any]]:
    normalized_count = max(10, min(int(count or 10), 50))
    prompt = f"""
You are generating multiple-choice questions for a Computer Fundamentals practice test.

Return valid JSON with this exact shape:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "answer": "one exact option from the list",
      "topic": "one of the allowed topics"
    }}
  ]
}}

Rules:
- Generate exactly {normalized_count} questions.
- Difficulty must stay easy to moderate, not advanced and not tricky for the sake of being tricky.
- Cover these topics with a healthy mix: {json.dumps(COMPUTER_FUNDAMENTALS_TOPICS, ensure_ascii=False)}.
- Focus on interview-style fundamentals for students and entry-level candidates.
- Each question must have exactly 4 distinct options.
- Only one option can be correct.
- The answer must exactly match one of the options.
- Avoid duplicate or near-duplicate questions.
- Avoid markdown fences.
- Freshness seed: {uuid.uuid4().hex}
"""

    try:
        payload, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            30,
        )
        raw_questions = payload.get("questions") or []
        normalized_questions = [
            _normalize_generated_mcq(item, index)
            for index, item in enumerate(raw_questions)
            if isinstance(item, dict)
        ]
        deduped_questions: List[Dict[str, Any]] = []
        seen_questions = set()
        for item in normalized_questions:
            key = item["question"].strip().lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            deduped_questions.append(item)
            if len(deduped_questions) >= normalized_count:
                break
        if len(deduped_questions) >= normalized_count:
            return deduped_questions[:normalized_count]
        raise ProviderError("Generated MCQ set was incomplete.")
    except ProviderError:
        return _build_computer_fundamentals_fallback_questions(normalized_count)


async def generate_aptitude_questions(count: int = 10) -> List[Dict[str, Any]]:
    normalized_count = max(10, min(int(count or 10), 50))
    prompt = f"""
You are generating multiple-choice questions for an aptitude practice test.

Return valid JSON with this exact shape:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "answer": "one exact option from the list",
      "topic": "one of the allowed topics"
    }}
  ]
}}

Rules:
- Generate exactly {normalized_count} questions.
- Difficulty must stay easy to moderate, suitable for real aptitude test practice.
- Cover these topics with a healthy mix: {json.dumps(APTITUDE_TOPICS, ensure_ascii=False)}.
- Prefer calculation, logic, interpretation, and formula-based aptitude questions.
- Do not include verbal grammar, computer fundamentals, or coding questions here.
- Each question must have exactly 4 distinct options.
- Only one option can be correct.
- The answer must exactly match one of the options.
- Avoid duplicate or near-duplicate questions.
- Avoid markdown fences.
- Freshness seed: {uuid.uuid4().hex}
"""

    try:
        payload, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            30,
        )
        raw_questions = payload.get("questions") or []
        normalized_questions = [
            _normalize_generated_mcq(item, index)
            for index, item in enumerate(raw_questions)
            if isinstance(item, dict)
        ]
        deduped_questions: List[Dict[str, Any]] = []
        seen_questions = set()
        for item in normalized_questions:
            key = item["question"].strip().lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            deduped_questions.append({
                **item,
                "sessionId": f"aptitude-generated-{len(deduped_questions) + 1}",
            })
            if len(deduped_questions) >= normalized_count:
                break
        if len(deduped_questions) >= normalized_count:
            return deduped_questions[:normalized_count]
        raise ProviderError("Generated aptitude MCQ set was incomplete.")
    except ProviderError:
        return _build_aptitude_fallback_questions(normalized_count)


async def generate_reasoning_questions(count: int = 10) -> List[Dict[str, Any]]:
    normalized_count = max(10, min(int(count or 10), 50))
    prompt = f"""
You are generating multiple-choice questions for a reasoning practice test.

Return valid JSON with this exact shape:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "answer": "one exact option from the list",
      "topic": "one of the allowed topics"
    }}
  ]
}}

Rules:
- Generate exactly {normalized_count} questions.
- Difficulty must stay easy to moderate, suitable for aptitude and placement reasoning practice.
- Cover these topics with a healthy mix: {json.dumps(REASONING_TOPICS, ensure_ascii=False)}.
- Do not include verbal grammar, coding, or computer fundamentals questions.
- Prefer short, clear reasoning MCQs with one definite correct answer.
- Include some non-verbal or figure-based reasoning questions, but describe the visual pattern fully in words so the question works without actual images.
- Each question must have exactly 4 distinct options.
- Only one option can be correct.
- The answer must exactly match one of the options.
- Avoid duplicate or near-duplicate questions.
- Avoid markdown fences.
- Freshness seed: {uuid.uuid4().hex}
"""

    try:
        payload, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            30,
        )
        raw_questions = payload.get("questions") or []
        normalized_questions = [
            _normalize_generated_mcq(item, index)
            for index, item in enumerate(raw_questions)
            if isinstance(item, dict)
        ]
        deduped_questions: List[Dict[str, Any]] = []
        seen_questions = set()
        for item in normalized_questions:
            key = item["question"].strip().lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            deduped_questions.append({
                **item,
                "sessionId": f"reasoning-generated-{len(deduped_questions) + 1}",
            })
            if len(deduped_questions) >= normalized_count:
                break
        if len(deduped_questions) >= normalized_count:
            return deduped_questions[:normalized_count]
        raise ProviderError("Generated reasoning MCQ set was incomplete.")
    except ProviderError:
        return _build_reasoning_fallback_questions(normalized_count)


async def generate_verbal_questions(count: int = 10) -> List[Dict[str, Any]]:
    normalized_count = max(10, min(int(count or 10), 50))
    prompt = f"""
You are generating multiple-choice questions for a verbal ability practice test.

Return valid JSON with this exact shape:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "answer": "one exact option from the list",
      "topic": "one of the allowed topics"
    }}
  ]
}}

Rules:
- Generate exactly {normalized_count} questions.
- Difficulty must stay easy to moderate, suitable for placement-style verbal practice.
- Cover these topics with a healthy mix: {json.dumps(VERBAL_TOPICS, ensure_ascii=False)}.
- Do not include coding, computer fundamentals, or quantitative aptitude questions.
- Prefer short, clear MCQs with one definite correct answer.
- For Reading Comprehension, keep the passage short and include the needed context inside the question.
- Each question must have exactly 4 distinct options.
- Only one option can be correct.
- The answer must exactly match one of the options.
- Avoid duplicate or near-duplicate questions.
- Avoid markdown fences.
- Freshness seed: {uuid.uuid4().hex}
"""

    try:
        payload, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            30,
        )
        raw_questions = payload.get("questions") or []
        normalized_questions = [
            _normalize_generated_mcq(item, index)
            for index, item in enumerate(raw_questions)
            if isinstance(item, dict)
        ]
        deduped_questions: List[Dict[str, Any]] = []
        seen_questions = set()
        for item in normalized_questions:
            key = item["question"].strip().lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            deduped_questions.append({
                **item,
                "sessionId": f"verbal-generated-{len(deduped_questions) + 1}",
            })
            if len(deduped_questions) >= normalized_count:
                break
        if len(deduped_questions) >= normalized_count:
            return deduped_questions[:normalized_count]
        raise ProviderError("Generated verbal MCQ set was incomplete.")
    except ProviderError:
        return _build_verbal_fallback_questions(normalized_count)


async def generate_advanced_quant_questions(count: int = 10) -> List[Dict[str, Any]]:
    normalized_count = max(10, min(int(count or 10), 50))
    prompt = f"""
You are generating multiple-choice questions for an advanced quantitative ability practice test.

Return valid JSON with this exact shape:
{{
  "questions": [
    {{
      "question": "question text",
      "options": ["option 1", "option 2", "option 3", "option 4"],
      "answer": "one exact option from the list",
      "topic": "one of the allowed topics"
    }}
  ]
}}

Rules:
- Generate exactly {normalized_count} questions.
- Difficulty must be intermediate to hard, but still solvable in a placement-style timed test.
- Cover these topics with a healthy mix: {json.dumps(ADVANCED_QUANT_TOPICS, ensure_ascii=False)}.
- Do not include verbal, reasoning, coding, or computer fundamentals questions.
- Prefer quantitative problem-solving MCQs with one definite correct answer.
- Each question must have exactly 4 distinct options.
- Only one option can be correct.
- The answer must exactly match one of the options.
- Avoid duplicate or near-duplicate questions.
- Avoid markdown fences.
- Freshness seed: {uuid.uuid4().hex}
"""

    try:
        payload, _provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.35,
            30,
        )
        raw_questions = payload.get("questions") or []
        normalized_questions = [
            _normalize_generated_mcq(item, index)
            for index, item in enumerate(raw_questions)
            if isinstance(item, dict)
        ]
        deduped_questions: List[Dict[str, Any]] = []
        seen_questions = set()
        for item in normalized_questions:
            key = item["question"].strip().lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)
            deduped_questions.append({
                **item,
                "sessionId": f"advanced-quant-generated-{len(deduped_questions) + 1}",
            })
            if len(deduped_questions) >= normalized_count:
                break
        if len(deduped_questions) >= normalized_count:
            return deduped_questions[:normalized_count]
        raise ProviderError("Generated advanced quantitative MCQ set was incomplete.")
    except ProviderError:
        return _build_advanced_quant_fallback_questions(normalized_count)


async def _infer_role_blueprint(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    selected_mode = payload.get("selected_mode") or "general"
    category = payload.get("category") or "general"
    selected_options = _safe_list(payload.get("selected_options") or [])
    fallback_blueprint = _fallback_role_blueprint(payload)

    prompt = f"""
You are analyzing a user's selected interview role and topics.

Input:
- Category: {category}
- Selected mode: {selected_mode}
- Job role: {payload.get("job_role") or "Not specified"}
- Primary language: {payload.get("primary_language") or "Not specified"}
- Experience: {payload.get("experience") or "Not specified"}
- Selected options: {json.dumps(selected_options, ensure_ascii=False)}

Return valid JSON in this exact shape:
{{
  "role_label": "normalized role label",
  "core_areas": ["6 to 8 technical domains that this role should be interviewed on"],
  "tech_stack": ["languages, frameworks, databases, tools, cloud, testing, or infra items relevant to the role"],
  "question_focus": ["5 to 7 specific areas the interview should ask from"],
  "language_focus": "primary language if relevant, otherwise empty string"
}}

Rules:
- Infer the likely tech stack and concepts from the selected role and options.
- Keep this technical only.
- Do not include HR, behavioral, motivation, strengths, or self-introduction topics.
- If the role suggests backend, frontend, full stack, data science, AI/ML, DevOps, QA, or security, infer the most relevant stacks and concepts automatically.
- Support any technical job title, even if it is niche, uncommon, or not in a predefined list.
- If the role is uncommon, infer the interview focus from the actual role title words, selected options, and language.
- If selected options are provided, use them strongly.
- If a language is provided, include it where relevant.
- Avoid markdown.
"""

    try:
        blueprint, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            STARTUP_AI_TIMEOUT_SECONDS,
        )
        normalized = {
            "role_label": _normalize_text(blueprint.get("role_label") or fallback_blueprint["role_label"]),
            "core_areas": _safe_list(blueprint.get("core_areas")) or fallback_blueprint["core_areas"],
            "tech_stack": _safe_list(blueprint.get("tech_stack")) or fallback_blueprint["tech_stack"],
            "question_focus": _safe_list(blueprint.get("question_focus")) or fallback_blueprint["question_focus"],
            "language_focus": _normalize_text(blueprint.get("language_focus") or fallback_blueprint["language_focus"]),
        }
        return normalized, provider
    except ProviderError:
        return fallback_blueprint, "fallback"


def _default_questions(payload: Dict[str, Any], variation: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    variation = variation or _build_interview_variation(payload)
    shuffler = random.Random(_normalize_text(variation.get("seed") or "default"))
    role = payload.get("job_role") or "candidate"
    language = payload.get("primary_language")
    focus = payload.get("selected_options") or []
    category = payload.get("category") or "general"
    selected_mode = payload.get("selected_mode") or ("language" if language else "role")
    experience = payload.get("experience") or "Not specified"
    difficulty = _difficulty_from_experience(experience)
    question_count = _resolve_question_count(payload)
    config_mode = payload.get("config_mode") or "question"
    time_hint = payload.get("time_mode_interval") or payload.get("interview_mode_time")
    target_subject = _target_subject(payload)
    role_profile = _match_role_profile(role)
    base_questions: List[Dict[str, Any]] = []

    if role_profile:
        role_field_points = role_profile["core_fields"][:4]
        base_questions.extend(
            [
                {
                    "question": f"For a {role_profile['label']} role, which core technical areas should a strong {experience} candidate be confident in, and why?",
                    "question_type": "fundamental",
                    "expected_points": role_field_points,
                    "evaluation_focus": ["fundamentals", "technical awareness", "clarity"],
                },
                {
                    "question": role_profile["question_seeds"][0],
                    "question_type": "practical",
                    "expected_points": [
                        "clear step-by-step technical explanation",
                        "correct use of core concepts",
                        "time or space complexity or trade-off reasoning",
                        "practical implementation approach",
                    ],
                    "evaluation_focus": ["problem solving", "technical depth", "clarity"],
                },
                {
                    "question": role_profile["question_seeds"][1],
                    "question_type": "conceptual",
                    "expected_points": [
                        "correct definition of the concept",
                        "difference from related concept",
                        "practical significance",
                    ],
                    "evaluation_focus": ["conceptual depth", "accuracy", "clarity"],
                },
                {
                    "question": role_profile["question_seeds"][2],
                    "question_type": "practical",
                    "expected_points": [
                        "role-relevant technical reasoning",
                        "correct syntax or structured explanation",
                        "clear practical outcome",
                    ],
                    "evaluation_focus": ["applied skills", "accuracy", "clarity"],
                },
                {
                    "question": role_profile["question_seeds"][3],
                    "question_type": "scenario",
                    "expected_points": [
                        "clear architecture or solution flow",
                        "relevant tools or components",
                        "trade-offs and scalability or maintainability considerations",
                    ],
                    "evaluation_focus": ["system thinking", "practical design", "technical reasoning"],
                },
                {
                    "question": role_profile["question_seeds"][4],
                    "question_type": "scenario",
                    "expected_points": [
                        "real-world technical constraints",
                        "structured problem-solving approach",
                        "relevant stack choices and reasoning",
                    ],
                    "evaluation_focus": ["architecture", "decision making", "technical fit"],
                },
            ]
        )

    if language:
        base_questions.insert(
            min(2, len(base_questions)),
            {
                "question": f"How have you used {language} in real projects, and what makes you effective with it?",
                "question_type": "practical",
                "expected_points": [
                    "hands-on use of the language",
                    "specific tools or frameworks",
                    "strengths and best practices",
                ],
                "evaluation_focus": ["technical depth", "practical experience", "clarity"],
            },
        )
        base_questions.insert(
            min(1, len(base_questions)),
            {
                "question": f"What core fundamentals of {language} should a strong {experience} candidate understand before solving advanced problems?",
                "question_type": "fundamental",
                "expected_points": [
                    "language fundamentals and syntax",
                    "runtime or execution understanding",
                    "memory, errors, or debugging basics",
                    "why fundamentals matter in real work",
                ],
                "evaluation_focus": ["fundamentals", "conceptual clarity", "relevance"],
            },
        )

    if category == "technical":
        technical_question = {
            "question": (
                f"For a {experience} candidate, explain a {difficulty} technical challenge you would expect "
                f"in a {role or language or 'technical'} interview and how you would solve it."
            ),
            "question_type": "scenario",
            "expected_points": [
                "clear technical context",
                "step-by-step approach",
                "trade-offs or reasoning",
                "practical outcome",
            ],
            "evaluation_focus": ["technical depth", "problem solving", "clarity"],
        }
        base_questions.insert(min(1, len(base_questions)), technical_question)
        base_questions.insert(
            min(1, len(base_questions)),
            {
                "question": f"What core concepts and fundamentals should every {target_subject} candidate be comfortable explaining confidently?",
                "question_type": "conceptual",
                "expected_points": [
                    "important foundational concepts",
                    "why those concepts matter",
                    "real interview relevance",
                    "clear structured explanation",
                ],
                "evaluation_focus": ["fundamentals", "conceptual depth", "clarity"],
            },
        )

    if selected_mode == "language" and language:
        base_questions.insert(
            min(1, len(base_questions)),
            {
                "question": (
                    f"As a {experience} {language} candidate, what topics should you be strongest in, "
                    "and how would you demonstrate that in an interview?"
                ),
                "question_type": "conceptual",
                "expected_points": [
                    "language fundamentals",
                    "real project usage",
                    "best practices",
                    "confidence with examples",
                ],
                "evaluation_focus": ["language depth", "examples", "confidence"],
            },
        )

    if focus:
        base_questions.insert(
            min(1, len(base_questions)),
            {
                "question": f"You selected {', '.join(focus[:3])}. Which of these best matches your strengths and why?",
                "question_type": "conceptual",
                "expected_points": [
                    "clear choice with justification",
                    "evidence from past work",
                    "fit with target interview",
                ],
                "evaluation_focus": ["role alignment", "specificity", "confidence"],
            },
        )
        if category == "technical" or selected_mode == "language":
            base_questions.insert(
                min(2, len(base_questions)),
                {
                    "question": f"Pick one of these focus areas: {', '.join(focus[:3])}. Explain its core fundamentals and where it is applied in practice.",
                    "question_type": "fundamental",
                    "expected_points": [
                        "clear explanation of the chosen topic",
                        "key fundamentals or building blocks",
                        "real-world usage",
                        "practical trade-offs or examples",
                    ],
                    "evaluation_focus": ["fundamentals", "application", "clarity"],
                },
            )

    if not base_questions:
        base_questions = [
            {
                "question": f"What are the most important technical fundamentals for a {role} candidate?",
                "question_type": "fundamental",
                "expected_points": [
                    "role-relevant technical fundamentals",
                    "clear explanation of why they matter",
                    "practical usage in interviews or projects",
                ],
                "evaluation_focus": ["fundamentals", "clarity", "technical relevance"],
            },
            {
                "question": f"Explain a technical problem you might solve as a {role} and how you would approach it.",
                "question_type": "scenario",
                "expected_points": [
                    "clear technical context",
                    "step-by-step approach",
                    "relevant tools or concepts",
                    "trade-offs or result",
                ],
                "evaluation_focus": ["problem solving", "technical depth", "clarity"],
            },
            {
                "question": f"What concepts should every {role} candidate understand before working on real projects?",
                "question_type": "conceptual",
                "expected_points": [
                    "important concepts listed clearly",
                    "why each concept matters",
                    "connection to real implementation",
                ],
                "evaluation_focus": ["conceptual clarity", "technical awareness", "relevance"],
            },
        ]

    supplemental_topics = _merge_unique([], _safe_list(focus))
    if role_profile:
        supplemental_topics = _merge_unique(supplemental_topics, role_profile.get("core_fields") or [])
    supplemental_topics = _merge_unique(supplemental_topics, [target_subject, language or "", role or ""])
    if not supplemental_topics:
        supplemental_topics = [target_subject or "core fundamentals"]

    while len(base_questions) < question_count:
        topic = supplemental_topics[(len(base_questions) - 1) % len(supplemental_topics)]
        rotation = len(base_questions) % 4
        if rotation == 0:
            base_questions.append(
                {
                    "question": f"For {topic}, what fundamentals, best practices, or common mistakes should a strong {experience} candidate know well?",
                    "question_type": "fundamental",
                    "expected_points": [
                        "clear fundamentals",
                        "best practices",
                        "common mistakes or pitfalls",
                        "practical relevance",
                    ],
                    "evaluation_focus": ["fundamentals", "clarity", "relevance"],
                }
            )
        elif rotation == 1:
            base_questions.append(
                {
                    "question": f"Describe a practical example where you would apply {topic} in a real project or interview scenario.",
                    "question_type": "practical",
                    "expected_points": [
                        "clear use case",
                        "specific implementation or workflow",
                        "relevant trade-offs",
                        "result or value",
                    ],
                    "evaluation_focus": ["application", "specificity", "clarity"],
                }
            )
        elif rotation == 2:
            base_questions.append(
                {
                    "question": f"What trade-offs, edge cases, or debugging issues do you watch for when working with {topic}?",
                    "question_type": "scenario",
                    "expected_points": [
                        "important trade-offs",
                        "edge cases or failure modes",
                        "debugging or mitigation steps",
                        "practical judgment",
                    ],
                    "evaluation_focus": ["problem solving", "real-world awareness", "clarity"],
                }
            )
        else:
            base_questions.append(
                {
                    "question": f"How would you explain {topic} clearly to an interviewer while proving you have hands-on understanding?",
                    "question_type": "conceptual",
                    "expected_points": [
                        "clear explanation",
                        "hands-on experience reference",
                        "structured communication",
                    ],
                    "evaluation_focus": ["conceptual clarity", "examples", "confidence"],
                }
            )

    first_block = base_questions[:1]
    remaining = base_questions[1:]
    shuffler.shuffle(remaining)
    trimmed = (first_block + remaining)[:question_count]
    intro_style = _normalize_text(variation.get("opening_style") or "technical interview")
    technical_lens = _normalize_text(variation.get("technical_lens") or "real-world engineering")
    return {
        "assistant_intro": (
            f"Hello, I am your AI interview assistant. "
            f"This will be a {intro_style}. "
            f"I will ask you {len(trimmed)} {difficulty} questions tailored for "
            f"{language if selected_mode == 'language' and language else role}. "
            f"This interview is configured in {config_mode} mode"
            f"{f' for about {time_hint} minutes' if time_hint else ''}. "
            f"Expect a fresh mix focused on {technical_lens}. Answer naturally and clearly."
        ),
        "questions": trimmed,
    }


def _keyword_set(values: List[str]) -> List[str]:
    stop_words = {
        "the", "and", "for", "with", "that", "this", "have", "your", "from",
        "into", "about", "what", "when", "where", "which", "will", "would",
        "been", "were", "they", "them", "their", "then", "than", "just",
        "very", "into", "able", "also", "only", "role", "work", "used",
    }
    tokens: List[str] = []
    for value in values:
        for token in re.findall(r"[a-zA-Z0-9]+", value.lower()):
            if len(token) > 2 and token not in stop_words:
                tokens.append(token)
    return list(dict.fromkeys(tokens))


def _normalize_enum_label(value: Any, allowed: List[str], fallback: str) -> str:
    normalized = _normalize_text(str(value or ""))
    if not normalized:
        return fallback
    lowered = normalized.lower()
    for option in allowed:
        if lowered == option.lower():
            return option
    for option in allowed:
        option_lower = option.lower()
        if lowered in option_lower or option_lower in lowered:
            return option
    return fallback


def _normalize_evaluation_payload(evaluation: Dict[str, Any], fallback_defaults: Dict[str, Any]) -> Dict[str, Any]:
    suggestions = _safe_list(evaluation.get("suggestions"))[:3] or _safe_list(fallback_defaults.get("suggestions"))[:3]
    normalized = {
        "score": int(evaluation.get("score", fallback_defaults["score"])),
        "feedback": _normalize_text(evaluation.get("feedback") or fallback_defaults["feedback"]),
        "strengths": _safe_list(evaluation.get("strengths"))[:3] or fallback_defaults["strengths"],
        "gaps": _safe_list(evaluation.get("gaps"))[:3] or fallback_defaults["gaps"],
        "matched_points": _safe_list(evaluation.get("matched_points"))[:4] or fallback_defaults["matched_points"],
        "missed_points": _safe_list(evaluation.get("missed_points"))[:4] or fallback_defaults["missed_points"],
        "suggested_answer": _normalize_text(evaluation.get("suggested_answer") or fallback_defaults["suggested_answer"]),
        "assistant_reply": _normalize_text(evaluation.get("assistant_reply") or fallback_defaults["assistant_reply"]),
        "relevance": _normalize_enum_label(
            evaluation.get("relevance"),
            ["Relevant", "Partially Relevant", "Not Relevant"],
            fallback_defaults["relevance"],
        ),
        "correctness": _normalize_enum_label(
            evaluation.get("correctness"),
            ["Correct", "Partially Correct", "Incorrect"],
            fallback_defaults["correctness"],
        ),
        "clarity": _normalize_enum_label(
            evaluation.get("clarity"),
            ["Clear", "Needs Improvement"],
            fallback_defaults["clarity"],
        ),
        "technical_depth": _normalize_enum_label(
            evaluation.get("technical_depth"),
            ["Good", "Moderate", "Weak"],
            fallback_defaults["technical_depth"],
        ),
        "logical_validity": _normalize_enum_label(
            evaluation.get("logical_validity"),
            ["Logical", "Partially Logical", "Illogical"],
            fallback_defaults["logical_validity"],
        ),
        "real_world_applicability": _normalize_enum_label(
            evaluation.get("real_world_applicability"),
            ["Applicable", "Partially Applicable", "Not Applicable"],
            fallback_defaults["real_world_applicability"],
        ),
        "suggestions": suggestions,
    }
    for key in [
        "communication_score",
        "confidence_score",
        "problem_solving_score",
    ]:
        normalized[key] = _normalize_score_value(
            evaluation.get(key),
            fallback_defaults.get(key),
        )
    normalized["score"] = max(0, min(100, normalized["score"]))
    return normalized


def _normalize_score_value(value: Any, fallback: Optional[int] = None) -> Optional[int]:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = fallback
    if score is None:
        return None
    return max(0, min(100, score))


def _answer_quality_signals(answer_text: str) -> Dict[str, Any]:
    normalized = _normalize_text(answer_text)
    lowered = normalized.lower()
    words = re.findall(r"[a-zA-Z0-9']+", lowered)
    unique_words = list(dict.fromkeys(words))
    word_count = len(words)
    unique_ratio = (len(unique_words) / word_count) if word_count else 0.0
    alpha_words = [word for word in words if re.fullmatch(r"[a-z']+", word)]

    filler_phrases = {
        "nothing",
        "no idea",
        "i don't know",
        "i dont know",
        "dont know",
        "don't know",
        "not sure",
        "nothing much",
        "anything",
        "something",
        "whatever",
        "random",
        "blah",
        "ok",
        "okay",
        "hmm",
        "umm",
        "um",
        "uh",
    }
    filler_hits = sum(1 for phrase in filler_phrases if phrase in lowered)
    explicit_no_idea_patterns = (
        r"^i don't know$",
        r"^i dont know$",
        r"^i don't know about (it|this|that|the question|this question)$",
        r"^i dont know about (it|this|that|the question|this question)$",
        r"^dont know$",
        r"^don't know$",
        r"^i have no idea$",
        r"^i don't have any idea$",
        r"^i dont have any idea$",
        r"^no idea$",
        r"^i have no idea about (it|this|that|the question)$",
        r"^i have no idea about this question$",
        r"^i don't have any idea about (it|this|that|the question|this question)$",
        r"^i dont have any idea about (it|this|that|the question|this question)$",
        r"^i do not know$",
        r"^i can't say$",
        r"^i cant say$",
        r"^cannot say$",
        r"^can't say$",
        r"^not sure$",
        r"^i am not sure$",
        r"^i'm not sure$",
        r"^i am not sure about (it|this|that|the question|this question)$",
        r"^i'm not sure about (it|this|that|the question|this question)$",
    )
    explicit_no_idea = any(re.fullmatch(pattern, lowered) for pattern in explicit_no_idea_patterns) or (
        (
            "no idea" in lowered
            or "don't know" in lowered
            or "dont know" in lowered
            or "do not know" in lowered
            or "can't say" in lowered
            or "cant say" in lowered
            or "not sure" in lowered
        )
        and any(marker in lowered for marker in ("question", "this", "that", "about"))
    )
    repeated_word = bool(word_count >= 2 and len(unique_words) == 1)
    repeated_phrase = bool(word_count >= 4 and unique_ratio <= 0.35)
    has_sentence_shape = any(token in lowered for token in (" because ", " when ", " where ", " so ", " but ", " and ", " i "))
    has_example_shape = any(
        token in lowered
        for token in ("for example", "for instance", "in my project", "i worked", "i used", "i handled", "my role")
    )
    consonant_heavy_words = [
        word for word in alpha_words
        if len(word) >= 5 and sum(1 for char in word if char in "aeiou") <= 1
    ]
    hard_to_pronounce_words = [
        word for word in alpha_words
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", word)
    ]
    gibberish_like = (
        bool(alpha_words)
        and len(alpha_words) <= 4
        and len(consonant_heavy_words) >= max(1, len(alpha_words) - 1)
        and len(hard_to_pronounce_words) >= max(1, len(alpha_words) - 1)
        and not has_sentence_shape
        and not has_example_shape
    )
    likely_nonsense = (
        ((repeated_word or repeated_phrase) and not has_sentence_shape and not has_example_shape)
        or gibberish_like
    )

    return {
        "word_count": word_count,
        "unique_ratio": unique_ratio,
        "filler_hits": filler_hits,
        "explicit_no_idea": explicit_no_idea,
        "repeated_word": repeated_word,
        "repeated_phrase": repeated_phrase,
        "gibberish_like": gibberish_like,
        "likely_nonsense": likely_nonsense,
        "has_sentence_shape": has_sentence_shape,
        "has_example_shape": has_example_shape,
    }


def _feedback_style(session: Dict[str, Any], question: Optional[Dict[str, Any]] = None) -> str:
    context = session.get("context", {}) or {}
    category = _normalize_text(context.get("category") or "").lower()
    round_mode = _normalize_text(context.get("hr_round") or "").lower()
    question_type = _normalize_text((question or {}).get("question_type") or "").lower()
    interview_phase = _normalize_text((question or {}).get("interview_phase") or "").lower()

    if category == "hr":
        if question_type == "behavioral" or interview_phase in {"behavioral", "conflict", "situational", "communication"} or round_mode == "behavioral":
            return "behavioral"
        return "hr"
    if question_type == "behavioral" or interview_phase == "behavioral_bridge":
        return "behavioral"
    return "technical"


def _tone_feedback(
    style: str,
    evaluation: Dict[str, Any],
    question: Optional[Dict[str, Any]] = None,
    answer_text: str = "",
) -> Dict[str, Any]:
    score = max(0, min(100, int(evaluation.get("score", 0))))
    relevance = _normalize_text(evaluation.get("relevance") or "")
    clarity = _normalize_text(evaluation.get("clarity") or "")
    correctness = _normalize_text(evaluation.get("correctness") or "")
    strengths = _safe_list(evaluation.get("strengths"))[:2]
    gaps = _safe_list(evaluation.get("gaps"))[:2]
    topic = _normalize_text((question or {}).get("topic_tag") or (question or {}).get("question_type") or "the question")
    quality = _answer_quality_signals(answer_text)

    if quality["explicit_no_idea"]:
        if style == "technical":
            feedback = (
                "It is okay not to know every answer in a technical interview. "
                "Be honest, review this topic later, and treat it as something to learn rather than something to guess."
            )
            assistant_reply = "No problem. It is okay not to know every technical answer. Please review this topic later, and let us move to the next question."
            suggested_answer = "If you are unsure in a real interview, be honest, say what you do know, and mention how you would learn or approach it."
        elif style == "behavioral":
            feedback = (
                "That is an honest response, and honesty is better than inventing an example. "
                "Try to reflect on this kind of situation later so you can answer with a real story next time."
            )
            assistant_reply = "No problem. Think through an example like this later, and let us continue."
            suggested_answer = "For behavioral questions, prepare a few real examples in STAR format so you are not forced to guess."
        else:
            feedback = (
                "That is an honest response. "
                "You should review this area before your next interview so you can answer with more confidence and role relevance."
            )
            assistant_reply = "No problem. Please learn a bit more about this area, and let us continue."
            suggested_answer = "If you do not know an answer in an HR round, be honest, stay calm, and connect to what you would do or learn next."

        evaluation["score"] = min(score, 25)
        evaluation["feedback"] = _normalize_text(feedback)
        evaluation["assistant_reply"] = _normalize_text(assistant_reply)
        evaluation["suggested_answer"] = _normalize_text(suggested_answer)
        evaluation["relevance"] = "Partially Relevant"
        evaluation["correctness"] = "Incorrect"
        evaluation["clarity"] = "Clear"
        evaluation["honest_uncertainty"] = True
        return evaluation

    if style == "technical":
        if relevance == "Not Relevant":
            feedback = (
                f"This answer did not really engage with {topic}. "
                "In a technical round, I would expect you to answer the prompt directly, then anchor it with one concrete example, decision, or trade-off."
            )
            assistant_reply = f"Let us reset and answer the actual technical question about {topic}."
        elif score >= 80:
            feedback = (
                "This felt like a strong technical answer. "
                "You stayed on the problem, explained the reasoning clearly, and sounded closer to how an engineer would defend a decision in a real interview."
            )
            assistant_reply = "Good. That was clear and technically grounded."
        elif score >= 60:
            feedback = (
                "There is a solid technical base here. "
                "To make it interview-strong, tighten the structure and make the implementation detail or trade-off more explicit."
            )
            assistant_reply = "Reasonable direction. I would just want a little more technical precision."
        else:
            feedback = (
                "I can see the direction you were trying to take, but this would still feel weak in a real technical interview. "
                "You need a clearer explanation, a more direct answer, and at least one concrete technical detail."
            )
            assistant_reply = "You are not far off, but I need a sharper technical answer."
        suggested_answer = (
            "Start with the direct technical answer, explain how or why it works, then add one example, edge case, or trade-off."
        )
    elif style == "behavioral":
        if relevance == "Not Relevant":
            feedback = (
                "This did not really answer the behavioral prompt. "
                "In a behavioral round, I would expect a specific situation, what you personally did, and the result or learning."
            )
            assistant_reply = "Let us come back to the actual situation and your role in it."
        elif score >= 80:
            feedback = (
                "This sounded strong for a behavioral interview. "
                "You gave enough context, made your action visible, and showed outcome or ownership in a way that feels believable."
            )
            assistant_reply = "Good. That felt like a credible real example."
        elif score >= 60:
            feedback = (
                "The answer is moving in the right direction for a behavioral round. "
                "It would be stronger with clearer STAR structure so your action and impact stand out more."
            )
            assistant_reply = "Good base. I would just want the story and your action to be a bit clearer."
        else:
            feedback = (
                "This would still feel underdeveloped in a behavioral interview. "
                "Give me the situation, what you specifically did, and what changed because of your action."
            )
            assistant_reply = "Please make it more specific and more ownership-focused."
        suggested_answer = (
            "Use a STAR-style flow: situation, task, action, and result, with clear ownership and one concrete outcome."
        )
    else:
        if relevance == "Not Relevant":
            feedback = (
                "This answer did not really connect to the question I asked. "
                "In an HR round, I would expect a direct response that shows motivation, professionalism, self-awareness, or role fit."
            )
            assistant_reply = "Let us come back to the actual question and answer it directly."
        elif score >= 80:
            feedback = (
                "This sounded interview-ready for an HR round. "
                "You were clear, relevant, and human, and the answer gave a believable sense of your motivation and professional judgment."
            )
            assistant_reply = "Good. That felt clear and professional."
        elif score >= 60:
            feedback = (
                "This is a decent HR answer with the right intent. "
                "To make it stronger, be a little more specific and connect the answer more clearly to the role or workplace situation."
            )
            assistant_reply = "Fair answer. I would just want a clearer connection to the role."
        else:
            feedback = (
                "This would still feel weak in an HR conversation. "
                "I need a clearer point, a little more substance, and a stronger connection to how you work or why you fit the role."
            )
            assistant_reply = "Please make that more specific and role-relevant."
        suggested_answer = (
            "Answer directly, keep it professional, and connect your point to motivation, work style, role fit, or a real example."
        )

    if clarity == "Needs Improvement" and score < 80:
        feedback = f"{feedback} The structure also needs to be cleaner so the listener can follow your point quickly."
    if correctness == "Incorrect" and style == "technical":
        feedback = f"{feedback} I would also revisit the underlying concept because the explanation was not technically reliable yet."

    if strengths and score >= 60:
        feedback = f"{feedback} What worked best was {strengths[0].rstrip('.').lower()}."
    elif gaps and score < 60:
        feedback = f"{feedback} The main issue was {gaps[0].rstrip('.').lower()}."

    evaluation["feedback"] = _normalize_text(feedback)
    evaluation["assistant_reply"] = _normalize_text(assistant_reply)
    if not _normalize_text(evaluation.get("suggested_answer") or "") or score < 80:
        evaluation["suggested_answer"] = _normalize_text(suggested_answer)
    evaluation["honest_uncertainty"] = False
    return evaluation


def _normalize_hr_evaluation_payload(evaluation: Dict[str, Any], fallback_defaults: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_evaluation_payload(evaluation, fallback_defaults)
    for key in [
        "communication_score",
        "confidence_score",
        "problem_solving_score",
        "teamwork_score",
        "leadership_score",
        "hr_readiness_score",
        "personality_attitude_score",
        "cultural_fit_score",
        "star_score",
    ]:
        normalized[key] = _normalize_score_value(
            evaluation.get(key),
            fallback_defaults.get(key),
        )
    return normalized


def _reconcile_evaluation_with_heuristic(
    evaluation: Dict[str, Any],
    heuristic_defaults: Dict[str, Any],
) -> Dict[str, Any]:
    reconciled = dict(evaluation)
    current_score = max(0, min(100, int(reconciled.get("score", 0))))
    heuristic_score = max(0, min(100, int(heuristic_defaults.get("score", 0))))
    current_matched = _safe_list(reconciled.get("matched_points"))
    heuristic_matched = _safe_list(heuristic_defaults.get("matched_points"))
    current_relevance = _normalize_text(reconciled.get("relevance") or "")
    heuristic_relevance = _normalize_text(heuristic_defaults.get("relevance") or "")
    current_correctness = _normalize_text(reconciled.get("correctness") or "")
    heuristic_correctness = _normalize_text(heuristic_defaults.get("correctness") or "")

    # Do not let one overly strict model judgment mark a meaningfully related answer as irrelevant.
    if current_relevance == "Not Relevant" and (heuristic_relevance != "Not Relevant" or heuristic_matched or heuristic_score >= 50):
        reconciled["relevance"] = heuristic_relevance or "Partially Relevant"
        reconciled["logical_validity"] = _normalize_text(
            heuristic_defaults.get("logical_validity") or reconciled.get("logical_validity") or "Partially Logical"
        )

    if current_correctness == "Incorrect" and (heuristic_correctness != "Incorrect" or heuristic_matched or heuristic_score >= 55):
        reconciled["correctness"] = heuristic_correctness or "Partially Correct"

    if not current_matched and heuristic_matched:
        reconciled["matched_points"] = heuristic_matched[:4]
    if not _safe_list(reconciled.get("strengths")) and _safe_list(heuristic_defaults.get("strengths")):
        reconciled["strengths"] = _safe_list(heuristic_defaults.get("strengths"))[:3]
    if current_score < 45 and heuristic_score >= 55:
        reconciled["score"] = min(100, max(current_score, int(round((current_score + heuristic_score) / 2))))
    if heuristic_score <= 25:
        cap = max(12, heuristic_score + 12)
        reconciled["score"] = min(current_score, cap)
        reconciled["relevance"] = heuristic_relevance or "Not Relevant"
        reconciled["correctness"] = heuristic_correctness or "Incorrect"
        reconciled["clarity"] = _normalize_text(heuristic_defaults.get("clarity") or "Needs Improvement")
        reconciled["logical_validity"] = _normalize_text(heuristic_defaults.get("logical_validity") or "Illogical")
        reconciled["feedback"] = _normalize_text(heuristic_defaults.get("feedback") or reconciled.get("feedback") or "")
        reconciled["gaps"] = _safe_list(heuristic_defaults.get("gaps"))[:3] or _safe_list(reconciled.get("gaps"))[:3]
        reconciled["suggestions"] = _safe_list(heuristic_defaults.get("suggestions"))[:3] or _safe_list(reconciled.get("suggestions"))[:3]
        reconciled["matched_points"] = _safe_list(heuristic_defaults.get("matched_points"))[:4]
        reconciled["missed_points"] = _safe_list(heuristic_defaults.get("missed_points"))[:4] or _safe_list(reconciled.get("missed_points"))[:4]
        for metric_key in [
            "communication_score",
            "confidence_score",
            "problem_solving_score",
            "teamwork_score",
            "leadership_score",
            "hr_readiness_score",
            "personality_attitude_score",
            "cultural_fit_score",
            "star_score",
        ]:
            heuristic_metric = _normalize_score_value(heuristic_defaults.get(metric_key))
            current_metric = _normalize_score_value(reconciled.get(metric_key))
            if heuristic_metric is not None or current_metric is not None:
                reconciled[metric_key] = min(
                    current_metric if current_metric is not None else 100,
                    max(0, (heuristic_metric if heuristic_metric is not None else heuristic_score) + 8),
                )

    return reconciled


def _heuristic_evaluation(question: Dict[str, Any], answer: str) -> Dict[str, Any]:
    answer_text = _normalize_text(answer)
    expected_points = _safe_list(question.get("expected_points"))
    keywords = _keyword_set(expected_points)
    answer_lower = answer_text.lower()
    quality = _answer_quality_signals(answer_text)

    matched_keywords = [kw for kw in keywords if kw in answer_lower]
    coverage = len(matched_keywords) / max(len(keywords), 1)
    length_bonus = min(quality["word_count"] / 80, 1.0)
    score = int(round(min(100, 35 + coverage * 45 + length_bonus * 20)))

    matched_points = []
    missed_points = []
    for point in expected_points:
        point_keywords = _keyword_set([point])
        if any(keyword in answer_lower for keyword in point_keywords):
            matched_points.append(point)
        else:
            missed_points.append(point)

    strengths = []
    if answer_text:
        strengths.append("You provided a direct spoken response to the question.")
    if matched_points:
        strengths.append("You covered some of the expected interview points.")
    if len(answer_text.split()) > 35:
        strengths.append("Your answer had a reasonable level of detail.")

    gaps = []
    if not answer_text:
        gaps.append("No meaningful answer was captured.")
    if missed_points:
        gaps.append("Some expected points were not clearly addressed.")
    if len(answer_text.split()) < 18:
        gaps.append("Your answer did not give enough detail to assess your thinking clearly.")

    suggested_answer = (
        "A stronger answer would briefly give context, explain your actions clearly, "
        "and end with the result or lesson learned."
    )

    word_count = quality["word_count"]
    project_markers = ("example", "project", "production", "real", "client", "api", "service", "system", "deployed")
    structure_markers = ("first", "second", "then", "finally", "approach", "step", "start by", "walk through")
    complexity_markers = ("time complexity", "space complexity", "big o", "o(", "complexity")
    tradeoff_markers = ("trade-off", "tradeoff", "optimiz", "latency", "throughput", "scal", "memory")
    uncertainty_markers = ("maybe", "i think", "probably", "not sure", "guess", "kind of")
    has_real_world_marker = any(marker in answer_lower for marker in project_markers)
    has_structure = any(marker in answer_lower for marker in structure_markers)
    has_complexity = any(marker in answer_lower for marker in complexity_markers)
    has_tradeoff = any(marker in answer_lower for marker in tradeoff_markers)
    uncertainty_hits = sum(1 for marker in uncertainty_markers if marker in answer_lower)
    off_topic = bool(answer_text) and coverage < 0.12 and not matched_points
    vague_but_related = bool(answer_text) and not off_topic and coverage < 0.28 and word_count < 20

    if quality["likely_nonsense"]:
        score = min(score, 12)
    elif quality["filler_hits"] and word_count < 10:
        score = min(score, 22)
    elif vague_but_related:
        score = min(score, 45)

    communication_score = max(
        30,
        min(100, score + (8 if word_count >= 30 else -8 if word_count < 12 else 0) + (6 if has_structure else -3)),
    )
    confidence_score = max(
        25,
        min(100, score + (6 if word_count >= 22 else -6 if word_count < 10 else 0) - min(12, uncertainty_hits * 4)),
    )
    problem_solving_score = max(
        30,
        min(100, score + (10 if has_structure else -4) + (6 if has_complexity or has_tradeoff else 0)),
    )

    relevance = "Not Relevant" if off_topic or quality["likely_nonsense"] else ("Partially Relevant" if coverage < 0.45 else "Relevant")
    correctness = "Incorrect" if quality["likely_nonsense"] or coverage < 0.18 else ("Partially Correct" if coverage < 0.65 else "Correct")
    clarity = "Needs Improvement" if word_count < 16 or quality["repeated_phrase"] else "Clear"
    technical_depth = "Weak" if word_count < 18 or coverage < 0.25 or quality["likely_nonsense"] else ("Moderate" if coverage < 0.7 else "Good")
    logical_validity = "Illogical" if off_topic or quality["likely_nonsense"] else ("Partially Logical" if coverage < 0.55 else "Logical")
    real_world_applicability = (
        "Applicable" if has_real_world_marker and coverage >= 0.45
        else "Partially Applicable" if has_real_world_marker or coverage >= 0.28
        else "Not Applicable"
    )

    topic_label = _normalize_text(question.get("topic_tag") or question.get("question_type") or "the topic")
    suggestions = []
    if quality["likely_nonsense"] or (quality["filler_hits"] and word_count < 10):
        suggestions.append("Answer with one clear idea instead of filler words or repeated phrases.")
    if off_topic:
        suggestions.append(f"Focus directly on {topic_label} before adding extra context.")
    if word_count < 16:
        suggestions.append("Expand your answer with one concrete example or implementation detail.")
    if missed_points:
        suggestions.append("Cover the main expected points in a clearer order.")
    if not has_real_world_marker:
        suggestions.append("Tie your answer to a real project, trade-off, or production scenario.")
    suggestions = suggestions[:3]

    if quality["explicit_no_idea"]:
        assistant_reply = "That is okay. If you do not know, say it honestly and review this topic later. Let us continue."
    elif quality["gibberish_like"]:
        assistant_reply = "I could not understand that response as a real answer. Please answer the question clearly."
    elif quality["likely_nonsense"]:
        assistant_reply = "I did not get a meaningful answer there. Please answer the question directly."
    elif quality["filler_hits"] and word_count < 10:
        assistant_reply = "I need a real answer here. Please explain your point a little more clearly."
    elif off_topic:
        assistant_reply = f"That is slightly off-topic. Let us focus on {topic_label}."
    elif word_count < 10:
        assistant_reply = "I heard a response, but not enough to judge your actual answer yet."
    elif word_count < 18 or coverage < 0.28:
        assistant_reply = "You are in the right area, but I need a clearer and more specific answer."
    elif score >= 80:
        assistant_reply = "Interesting. Let us explore that a little further."
    else:
        assistant_reply = "Alright, let us continue."

    if not answer_text:
        feedback = "I could not capture a clear answer. Please answer directly, stay on the topic, and add one real example."
    elif quality["explicit_no_idea"]:
        feedback = (
            "It is okay to say you do not know. "
            "Use this as a topic to learn after the interview, and try to answer honestly without guessing."
        )
    elif quality["gibberish_like"]:
        feedback = (
            "Your response did not sound like a recognizable answer to the question. "
            "Please answer in clear words or sentences so I can evaluate your actual thinking."
        )
    elif quality["likely_nonsense"]:
        feedback = (
            "Your response did not contain a clear idea I could evaluate. "
            "Answer the question directly in one or two complete sentences, then add a brief example."
        )
    elif quality["filler_hits"] and word_count < 10:
        feedback = (
            "Your answer sounded more like filler than a complete response. "
            "Give one clear point, explain it briefly, and connect it to the question."
        )
    elif off_topic:
        feedback = (
            f"Your response drifted away from {topic_label}. Start by answering the exact question, "
            "then support it with one relevant technical example."
        )
    elif vague_but_related:
        feedback = (
            "Your answer is in the right direction, but it is still too general. "
            "A stronger response would explain your main point more clearly and include one concrete example."
        )
    elif score >= 75:
        feedback = (
            "Your answer was relevant and mostly correct. To make it stronger, add one real-world trade-off "
            "or production consideration."
        )
    else:
        feedback = (
            "Your answer has some relevant points, but it needs clearer structure, better technical precision, "
            "and a more practical example."
        )

    return {
        "score": score,
        "feedback": feedback,
        "strengths": strengths[:3],
        "gaps": gaps[:3],
        "matched_points": matched_points[:4],
        "missed_points": missed_points[:4],
        "suggested_answer": suggested_answer,
        "assistant_reply": assistant_reply,
        "relevance": relevance,
        "correctness": correctness,
        "clarity": clarity,
        "technical_depth": technical_depth,
        "logical_validity": logical_validity,
        "real_world_applicability": real_world_applicability,
        "suggestions": suggestions,
        "communication_score": communication_score,
        "confidence_score": confidence_score,
        "problem_solving_score": problem_solving_score,
    }


def _hr_heuristic_evaluation(question: Dict[str, Any], answer: str) -> Dict[str, Any]:
    base = _heuristic_evaluation(question, answer)
    answer_text = _normalize_text(answer)
    answer_lower = answer_text.lower()
    quality = _answer_quality_signals(answer_text)
    word_count = quality["word_count"]

    teamwork_markers = ("team", "collabor", "together", "support", "stakeholder")
    leadership_markers = ("lead", "owned", "initiative", "mentor", "guided", "responsible")
    problem_markers = ("problem", "challenge", "resolved", "solution", "decided", "trade-off", "deadline")
    result_markers = ("result", "outcome", "impact", "learned", "improved", "delivered", "achieved")
    star_markers = ("situation", "task", "action", "result")

    has_teamwork = any(marker in answer_lower for marker in teamwork_markers)
    has_leadership = any(marker in answer_lower for marker in leadership_markers)
    has_problem = any(marker in answer_lower for marker in problem_markers)
    has_result = any(marker in answer_lower for marker in result_markers)
    star_hits = sum(1 for marker in star_markers if marker in answer_lower)

    communication_score = max(35, min(100, base["score"] + (8 if word_count >= 35 else -6 if word_count < 14 else 0)))
    confidence_score = max(30, min(100, base["score"] + (6 if word_count >= 25 else -8 if word_count < 12 else 0)))
    teamwork_score = max(25, min(100, base["score"] + (10 if has_teamwork else -5)))
    leadership_score = max(20, min(100, base["score"] + (10 if has_leadership else -8)))
    problem_solving_score = max(30, min(100, base["score"] + (8 if has_problem else -4)))
    personality_attitude_score = max(35, min(100, base["score"] + (6 if has_result else 0)))
    cultural_fit_score = max(35, min(100, int(round((communication_score + teamwork_score + personality_attitude_score) / 3))))
    star_score = max(25, min(100, int(round(base["score"] + star_hits * 8 + (8 if has_result else 0) - (8 if word_count < 16 else 0)))))
    hr_readiness_score = max(
        30,
        min(
            100,
            int(round((communication_score + confidence_score + problem_solving_score + cultural_fit_score + star_score) / 5)),
        ),
    )

    if quality["likely_nonsense"]:
        base["feedback"] = (
            "That did not sound like a meaningful interview answer yet. "
            "Please answer like you would to a real interviewer: explain the situation, what you did, and the result."
        )
        base["assistant_reply"] = "Please answer that again in a more direct and meaningful way."
    elif quality["filler_hits"] and word_count < 10:
        base["feedback"] = (
            "I need a clearer HR-style answer here. "
            "Share a real situation or motivation, describe your action, and explain the result or learning."
        )
        base["assistant_reply"] = "Please try that again with a real example or a clearer explanation."
    elif word_count < 14:
        base["feedback"] = (
            "Your answer was understandable, but it needs more detail and a clearer example. "
            "Try using a situation, the action you took, and the final result."
        )
    elif star_score >= 75 and hr_readiness_score >= 75:
        base["feedback"] = (
            "This answer felt interview-ready. You gave useful context, explained your action clearly, "
            "and showed a meaningful result or lesson."
        )
    else:
        base["feedback"] = (
            "Your answer had the right direction, but it would be stronger with clearer structure, "
            "more specific actions, and a sharper outcome."
        )

    base["suggested_answer"] = (
        "Open with the situation, explain the exact action you took, and close with the outcome, learning, "
        "or business impact."
    )
    base["communication_score"] = communication_score
    base["confidence_score"] = confidence_score
    base["problem_solving_score"] = problem_solving_score
    base["teamwork_score"] = teamwork_score
    base["leadership_score"] = leadership_score
    base["hr_readiness_score"] = hr_readiness_score
    base["personality_attitude_score"] = personality_attitude_score
    base["cultural_fit_score"] = cultural_fit_score
    base["star_score"] = star_score
    return base


KNOWN_LANGUAGES = {
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "go": "Go",
    "golang": "Go",
    "c#": "C#",
    "dotnet": ".NET",
    ".net": ".NET",
    "php": "PHP",
    "ruby": "Ruby",
    "rust": "Rust",
    "kotlin": "Kotlin",
}

KNOWN_FRAMEWORKS = {
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "spring boot": "Spring Boot",
    "spring": "Spring",
    "express": "Express.js",
    "nestjs": "NestJS",
    "nest": "NestJS",
    "laravel": "Laravel",
    "asp.net": "ASP.NET",
    "gin": "Gin",
}

KNOWN_DATABASES = {
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "oracle": "Oracle",
    "sql server": "SQL Server",
}

KNOWN_TOOLS = {
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "rabbitmq": "RabbitMQ",
    "kafka": "Kafka",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
}

KNOWN_LANGUAGE_FOCUS_AREAS = {
    "fundamentals": "fundamentals",
    "basic concepts": "fundamentals",
    "core concepts": "fundamentals",
    "debugging": "debugging",
    "troubleshooting": "debugging",
    "problem solving": "problem solving",
    "problem-solving": "problem solving",
    "algorithms": "problem solving",
    "api": "APIs",
    "apis": "APIs",
    "project experience": "project experience",
    "projects": "project experience",
    "real project": "project experience",
    "performance": "performance",
    "optimization": "performance",
    "testing": "testing",
}

LANGUAGE_PHASE_QUESTION_BANK = {
    "Python": {
        "warmup": [
            {"question": "In Python, what is the difference between a list and a tuple, and when would you choose one over the other?", "topic_tag": "Python collections"},
            {"question": "In Python, what is the difference between a dictionary and a set, and when is each the better choice?", "topic_tag": "Python dicts and sets"},
            {"question": "In Python, how does variable scope work inside functions, and what do global or nonlocal change?", "topic_tag": "Python scope"},
        ],
        "concept_deep_dive": [
            {"question": "In Python, how do shallow copy and deep copy differ, and when can choosing the wrong one create bugs?", "topic_tag": "Python copy behavior"},
            {"question": "In Python, how do iterators and generators differ, and why does that difference matter in real programs?", "topic_tag": "Python iterators and generators"},
            {"question": "In Python, what is the difference between mutable and immutable objects, and how can that affect function behavior?", "topic_tag": "Python mutability"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Python bug or debugging issue you handled. What was happening, and how did you fix it?", "topic_tag": "Python debugging"},
            {"question": "Tell me about one Python project where a core language feature made a real difference. What was the situation, and why did that feature help?", "topic_tag": "Python project experience"},
        ],
    },
    "JavaScript": {
        "warmup": [
            {"question": "In JavaScript, what is the difference between let, const, and var, and why does it matter in real code?", "topic_tag": "JavaScript variables"},
            {"question": "In JavaScript, what is the difference between == and ===, and when can using the wrong one cause problems?", "topic_tag": "JavaScript equality"},
            {"question": "In JavaScript, how do arrays and plain objects differ, and when is each the right choice?", "topic_tag": "JavaScript data structures"},
        ],
        "concept_deep_dive": [
            {"question": "In JavaScript, what is a closure, and when does it become especially useful or risky?", "topic_tag": "JavaScript closures"},
            {"question": "In JavaScript, how do the event loop, call stack, and task queues work together?", "topic_tag": "JavaScript event loop"},
            {"question": "In JavaScript, how do async and await relate to promises, and what mistakes commonly appear around them?", "topic_tag": "JavaScript async"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real JavaScript bug or async issue you had to debug. What was happening, and how did you resolve it?", "topic_tag": "JavaScript debugging"},
            {"question": "Tell me about one JavaScript feature or project where scope, closures, async flow, or data handling mattered in practice.", "topic_tag": "JavaScript project experience"},
        ],
    },
    "TypeScript": {
        "warmup": [
            {"question": "In TypeScript, what is the difference between any and unknown, and when should each be avoided or preferred?", "topic_tag": "TypeScript types"},
            {"question": "In TypeScript, how do interface and type differ, and when do those differences matter?", "topic_tag": "TypeScript interface vs type"},
            {"question": "In TypeScript, what are union types, and how does narrowing help you use them safely?", "topic_tag": "TypeScript unions"},
        ],
        "concept_deep_dive": [
            {"question": "In TypeScript, how do generics improve code quality, and when can they become too loose or too complex?", "topic_tag": "TypeScript generics"},
            {"question": "In TypeScript, what is the difference between compile-time safety and runtime behavior, and why does that distinction matter?", "topic_tag": "TypeScript runtime vs compile time"},
            {"question": "In TypeScript, how do discriminated unions work, and why are they useful in larger codebases?", "topic_tag": "TypeScript discriminated unions"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real TypeScript issue or refactor where types helped you catch or prevent a bug.", "topic_tag": "TypeScript debugging"},
            {"question": "Tell me about one TypeScript project where strong typing, generics, or narrowing made a meaningful difference.", "topic_tag": "TypeScript project experience"},
        ],
    },
    "Java": {
        "warmup": [
            {"question": "In Java, what is the difference between primitive types and reference types, and why does that matter?", "topic_tag": "Java types"},
            {"question": "In Java, how do ArrayList and arrays differ, and when would you choose one over the other?", "topic_tag": "Java collections"},
            {"question": "In Java, what is the difference between checked and unchecked exceptions?", "topic_tag": "Java exceptions"},
        ],
        "concept_deep_dive": [
            {"question": "In Java, why do equals and hashCode need to stay consistent, and what can go wrong if they do not?", "topic_tag": "Java equals and hashCode"},
            {"question": "In Java, how do interface and abstract class differ, and when would you choose one over the other?", "topic_tag": "Java abstraction"},
            {"question": "In Java, how does garbage collection affect real applications, and what should developers still manage carefully?", "topic_tag": "Java garbage collection"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Java debugging issue, exception problem, or performance issue you handled. What happened, and how did you solve it?", "topic_tag": "Java debugging"},
            {"question": "Tell me about one Java project where core language behavior or the standard library strongly influenced your design or implementation.", "topic_tag": "Java project experience"},
        ],
    },
    "Go": {
        "warmup": [
            {"question": "In Go, what is the difference between an array and a slice, and why do developers usually work with slices more often?", "topic_tag": "Go arrays and slices"},
            {"question": "In Go, how does error handling usually work, and why is it intentionally different from exception-based models?", "topic_tag": "Go error handling"},
            {"question": "In Go, how do structs and interfaces differ, and when is each central to good design?", "topic_tag": "Go types"},
        ],
        "concept_deep_dive": [
            {"question": "In Go, how do goroutines and channels work together, and what mistakes often appear around them?", "topic_tag": "Go concurrency"},
            {"question": "In Go, how do pointer semantics affect function behavior and performance?", "topic_tag": "Go pointers"},
            {"question": "In Go, what is the difference between buffered and unbuffered channels, and when does that difference matter?", "topic_tag": "Go channels"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Go bug, concurrency issue, or debugging problem you handled. What was happening, and how did you resolve it?", "topic_tag": "Go debugging"},
            {"question": "Tell me about one Go project where slices, interfaces, concurrency, or error handling mattered in practice.", "topic_tag": "Go project experience"},
        ],
    },
    "C#": {
        "warmup": [
            {"question": "In C#, what is the difference between value types and reference types, and why does that matter in practice?", "topic_tag": "C# value vs reference types"},
            {"question": "In C#, how do IEnumerable and List differ, and when is each the better fit?", "topic_tag": "C# collections"},
            {"question": "In C#, what do async and await do, and what problem do they solve?", "topic_tag": "C# async"},
        ],
        "concept_deep_dive": [
            {"question": "In C#, how do interface and abstract class differ, and when would you choose one instead of the other?", "topic_tag": "C# abstraction"},
            {"question": "In C#, how do delegates and events differ, and when does that distinction matter?", "topic_tag": "C# delegates and events"},
            {"question": "In C#, how do nullable reference types improve code safety, and what limits do they still have?", "topic_tag": "C# nullability"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real C# debugging issue, async problem, or production bug you handled. What happened, and how did you fix it?", "topic_tag": "C# debugging"},
            {"question": "Tell me about one C# project where core language behavior or framework usage affected your implementation decisions.", "topic_tag": "C# project experience"},
        ],
    },
    "Rust": {
        "warmup": [
            {"question": "In Rust, what problem do ownership and borrowing solve, and how would you explain them simply?", "topic_tag": "Rust ownership"},
            {"question": "In Rust, what is the difference between Option and Result, and when is each used?", "topic_tag": "Rust option and result"},
            {"question": "In Rust, how do mutable and immutable bindings differ, and why is that important?", "topic_tag": "Rust mutability"},
        ],
        "concept_deep_dive": [
            {"question": "In Rust, how do moves, borrows, and clones differ, and when does choosing the wrong one hurt correctness or performance?", "topic_tag": "Rust moves and borrows"},
            {"question": "In Rust, what role do lifetimes play, and when do developers really need to think about them?", "topic_tag": "Rust lifetimes"},
            {"question": "In Rust, how do traits compare to interfaces or protocols in other languages, and why are they powerful?", "topic_tag": "Rust traits"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Rust error, borrow-checker issue, or debugging problem you worked through. What was happening, and how did you solve it?", "topic_tag": "Rust debugging"},
            {"question": "Tell me about one Rust project where ownership, lifetimes, error handling, or performance trade-offs mattered in practice.", "topic_tag": "Rust project experience"},
        ],
    },
    "Kotlin": {
        "warmup": [
            {"question": "In Kotlin, what is the difference between val and var, and why does that matter for code quality?", "topic_tag": "Kotlin val vs var"},
            {"question": "In Kotlin, how does null safety work, and what problem is it designed to reduce?", "topic_tag": "Kotlin null safety"},
            {"question": "In Kotlin, what is a data class, and when is it more useful than a regular class?", "topic_tag": "Kotlin data classes"},
        ],
        "concept_deep_dive": [
            {"question": "In Kotlin, how do higher-order functions and collection transformations improve readability, and where can they be overused?", "topic_tag": "Kotlin functional style"},
            {"question": "In Kotlin, how do coroutines differ from thread-based approaches, and why does that matter?", "topic_tag": "Kotlin coroutines"},
            {"question": "In Kotlin, how do sealed classes help model state and control flow?", "topic_tag": "Kotlin sealed classes"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Kotlin bug, nullability issue, coroutine problem, or debugging case you handled.", "topic_tag": "Kotlin debugging"},
            {"question": "Tell me about one Kotlin project where null safety, coroutines, or collection handling mattered in practice.", "topic_tag": "Kotlin project experience"},
        ],
    },
    "PHP": {
        "warmup": [
            {"question": "In PHP, how do associative arrays differ from indexed arrays, and when does that matter in real code?", "topic_tag": "PHP arrays"},
            {"question": "In PHP, what is the difference between == and ===, and when can mixing them up cause bugs?", "topic_tag": "PHP equality"},
            {"question": "In PHP, how do include, require, and autoloading differ at a high level?", "topic_tag": "PHP loading"},
        ],
        "concept_deep_dive": [
            {"question": "In PHP, how do object references and copy behavior work, and when can they surprise developers?", "topic_tag": "PHP object behavior"},
            {"question": "In PHP, how do exceptions improve error handling compared with older patterns?", "topic_tag": "PHP exceptions"},
            {"question": "In PHP, how do traits help code reuse, and when can using too many of them become messy?", "topic_tag": "PHP traits"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real PHP bug, debugging issue, or framework problem you handled. What happened, and how did you fix it?", "topic_tag": "PHP debugging"},
            {"question": "Tell me about one PHP project where arrays, object behavior, framework conventions, or request handling mattered in practice.", "topic_tag": "PHP project experience"},
        ],
    },
    "Ruby": {
        "warmup": [
            {"question": "In Ruby, what is the difference between a symbol and a string, and when does that distinction matter?", "topic_tag": "Ruby symbols and strings"},
            {"question": "In Ruby, how do blocks differ from procs and lambdas at a practical level?", "topic_tag": "Ruby blocks and lambdas"},
            {"question": "In Ruby, how do arrays and hashes differ, and when is each the better fit?", "topic_tag": "Ruby collections"},
        ],
        "concept_deep_dive": [
            {"question": "In Ruby, how do mixins and inheritance differ, and when would you choose one approach over the other?", "topic_tag": "Ruby mixins"},
            {"question": "In Ruby, how do Enumerable methods improve code clarity, and where can they hide performance costs?", "topic_tag": "Ruby enumerable"},
            {"question": "In Ruby, how does object mutability affect method behavior and debugging?", "topic_tag": "Ruby mutability"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real Ruby bug, debugging issue, or Rails-related problem you handled. What happened, and how did you solve it?", "topic_tag": "Ruby debugging"},
            {"question": "Tell me about one Ruby project where blocks, mixins, collections, or object behavior mattered in practice.", "topic_tag": "Ruby project experience"},
        ],
    },
    "default": {
        "warmup": [
            {"question": "In {language}, what basic data types or core collections do developers use most often, and when does each make sense?", "topic_tag": "{language} core types"},
            {"question": "In {language}, how do functions or methods usually work, and what basics should a strong developer understand clearly?", "topic_tag": "{language} functions"},
            {"question": "In {language}, how does basic control flow and error handling work, and where do beginners commonly make mistakes?", "topic_tag": "{language} basics"},
        ],
        "concept_deep_dive": [
            {"question": "In {language}, what language behavior, trade-off, or edge case should a strong developer understand beyond the basics?", "topic_tag": "{language} deeper concepts"},
            {"question": "In {language}, what core behavior becomes especially important in larger or more realistic codebases?", "topic_tag": "{language} real-world behavior"},
            {"question": "In {language}, what concept looks simple at first but causes real bugs if misunderstood?", "topic_tag": "{language} common pitfalls"},
        ],
        "language_discovery": [
            {"question": "Tell me about one real bug, debugging issue, or implementation problem you handled while working in {language}.", "topic_tag": "{language} debugging"},
            {"question": "Tell me about one project or feature where a core part of {language} mattered in practice.", "topic_tag": "{language} project experience"},
        ],
    },
}


def _merge_unique(existing: List[str], new_items: List[str]) -> List[str]:
    merged = list(existing or [])
    for item in new_items or []:
        value = _normalize_text(item)
        if value and value not in merged:
            merged.append(value)
    return merged


def _extract_known_terms(text: str, vocabulary: Dict[str, str]) -> List[str]:
    lowered = text.lower()
    matches: List[str] = []
    for needle, label in vocabulary.items():
        if needle in lowered and label not in matches:
            matches.append(label)
    return matches


def _extract_preferred_language(text: str, languages: List[str]) -> str:
    lowered = text.lower()
    preference_markers = (
        "prefer",
        "preferred",
        "most comfortable with",
        "comfortable with",
        "mainly",
        "mostly",
        "focus on",
        "worked mostly with",
        "use mostly",
    )
    for language in languages:
        value = language.lower()
        if any(f"{marker} {value}" in lowered for marker in preference_markers):
            return language
    return languages[0] if len(languages) == 1 else ""


def _build_hr_phase_plan(question_count: int, round_mode: str) -> List[str]:
    normalized_mode = _normalize_text(round_mode).lower() or "hr_behavioral"

    mode_configs = {
        "hr": {
            "base": ["introduction", "background", "motivation", "strengths", "role_fit", "workplace", "closing"],
            "extras": ["workplace", "role_fit", "strengths", "motivation"],
        },
        "behavioral": {
            "base": ["introduction", "behavioral", "conflict", "behavioral", "situational", "communication", "closing"],
            "extras": ["behavioral", "conflict", "situational", "communication"],
        },
        "hr_behavioral": {
            "base": ["introduction", "background", "motivation", "strengths", "behavioral", "conflict", "situational", "workplace", "closing"],
            "extras": ["behavioral", "role_fit", "strengths", "situational", "workplace"],
        },
    }

    config = mode_configs.get(normalized_mode, mode_configs["hr_behavioral"])
    if question_count <= 1:
        return ["introduction"]

    if question_count <= len(config["base"]):
        return config["base"][: question_count - 1] + ["closing"]

    plan = list(config["base"])
    extra_index = 0
    while len(plan) < question_count:
        plan.insert(-1, config["extras"][extra_index % len(config["extras"])])
        extra_index += 1
    return plan[: question_count - 1] + ["closing"]


def _build_focus_plan(focus_areas: List[str], question_count: int) -> List[str]:
    cleaned = [item for item in _safe_list(focus_areas) if item]
    if not cleaned:
        cleaned = ["Communication", "Leadership", "Problem-solving", "Teamwork", "Confidence"]

    base_questions_per_area = question_count // len(cleaned)
    remainder = question_count % len(cleaned)
    plan: List[str] = []

    for index, area in enumerate(cleaned):
        allocation = base_questions_per_area + (1 if index < remainder else 0)
        plan.extend([area] * allocation)

    return plan[:question_count]


def _build_hr_adaptive_state(payload: Dict[str, Any], question_count: int) -> Dict[str, Any]:
    focus_areas = _selected_focus_areas(payload)
    resolved_focus_areas = focus_areas or ["Communication", "Leadership", "Problem-solving", "Teamwork", "Confidence"]
    round_mode = _hr_round_mode(payload)
    return {
        "enabled": True,
        "mode": "hr",
        "scored_question_target": question_count,
        "discovery_questions_asked": 0,
        "clarification_turns": 0,
        "discovery_complete": True,
        "focus_areas": resolved_focus_areas,
        "focus_plan": _build_focus_plan(resolved_focus_areas, question_count),
        "covered_topics": [],
        "scored_questions_answered": 0,
        "technical_questions_answered": 0,
        "hr_questions_answered": 0,
        "hr_question_target": question_count,
        "role_label": _normalize_text(payload.get("job_role") or "Candidate"),
        "confidence_summary": "",
        "round_mode": round_mode,
        "phase_plan": _build_hr_phase_plan(question_count, round_mode),
    }


def _next_hr_phase(state: Dict[str, Any]) -> str:
    plan = state.get("phase_plan") or ["behavioral"]
    index = min(int(state.get("scored_questions_answered", 0)), max(len(plan) - 1, 0))
    return _normalize_text(plan[index] or "behavioral") or "behavioral"


def _next_hr_focus(state: Dict[str, Any], last_question: Optional[Dict[str, Any]] = None) -> str:
    focus_plan = [item for item in _safe_list(state.get("focus_plan") or []) if item]
    question_index = int(state.get("scored_questions_answered", 0))
    if focus_plan:
        return focus_plan[min(question_index, len(focus_plan) - 1)]
    focus_areas = [item for item in _safe_list(state.get("focus_areas") or []) if item]
    covered = {item.lower() for item in state.get("covered_topics") or []}
    last_topic = _normalize_text((last_question or {}).get("topic_tag") or "")
    for focus in focus_areas:
        lowered = focus.lower()
        if lowered not in covered and lowered != last_topic.lower():
            return focus
    return last_topic or (focus_areas[0] if focus_areas else "Communication")


def _adaptive_role_interview_enabled(payload: Dict[str, Any]) -> bool:
    category = _normalize_text(payload.get("category") or "").lower()
    if category not in {"technical", "mock", "resume"}:
        return False
    selected_mode = payload.get("selected_mode") or (
        "language" if payload.get("primary_language") else "role" if payload.get("job_role") else "general"
    )
    selected_mode = _normalize_text(selected_mode).lower()
    if selected_mode == "role":
        return bool(_normalize_text(payload.get("job_role") or ""))
    if selected_mode == "language":
        return bool(_normalize_text(payload.get("primary_language") or ""))
    return False


def _build_technical_phase_plan(question_count: int, selected_mode: str = "") -> List[str]:
    if _normalize_text(selected_mode).lower() == "language":
        if question_count <= 1:
            return ["warmup"]
        if question_count == 2:
            return ["warmup", "concept_deep_dive"]
        if question_count == 3:
            return ["warmup", "concept_deep_dive", "language_discovery"]
        if question_count == 4:
            return ["warmup", "concept_deep_dive", "language_discovery", "real_world_scenario"]

        plan = ["warmup", "concept_deep_dive", "language_discovery", "structured_thinking", "real_world_scenario"]
        extra_cycle = ["concept_deep_dive", "structured_thinking", "real_world_scenario"]
        cycle_index = 0
        while len(plan) < question_count:
            plan.insert(-1, extra_cycle[cycle_index % len(extra_cycle)])
            cycle_index += 1
        return plan[:question_count]

    if question_count <= 1:
        return ["warmup"]
    if question_count == 2:
        return ["warmup", "real_world_scenario"]
    if question_count == 3:
        return ["warmup", "concept_deep_dive", "real_world_scenario"]
    if question_count == 4:
        return ["warmup", "concept_deep_dive", "structured_thinking", "real_world_scenario"]

    plan = ["warmup", "concept_deep_dive", "structured_thinking", "real_world_scenario"]
    extra_cycle = ["concept_deep_dive", "structured_thinking", "real_world_scenario"]
    cycle_index = 0
    while len(plan) < question_count:
        plan.insert(-1, extra_cycle[cycle_index % len(extra_cycle)])
        cycle_index += 1
    return plan[:question_count]


def _next_adaptive_phase(state: Dict[str, Any], desired_track: str) -> str:
    if desired_track == "hr":
        return "behavioral_bridge"
    plan = [item for item in _safe_list(state.get("technical_phase_plan") or []) if item]
    if not plan:
        return "concept_deep_dive"
    index = min(int(state.get("technical_questions_answered", 0)), max(len(plan) - 1, 0))
    return _normalize_text(plan[index] or "concept_deep_dive") or "concept_deep_dive"


def _detect_interview_control_command(value: str) -> Optional[str]:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return None
    word_count = len([word for word in normalized.split() if word])
    if word_count > 14:
        return None

    repeat_patterns = [
        r"^repeat$",
        r"^repeat again$",
        r"^repeat question$",
        r"^repeat the question$",
        r"^repeat that question$",
        r"^repeat this question$",
        r"^repeat the question again$",
        r"^repeat that question again$",
        r"^say again$",
        r"^say that again$",
        r"^say the question again$",
        r"^can you repeat$",
        r"^can you repeat that$",
        r"^can you repeat the question$",
        r"^can you repeat this question$",
        r"^can you repeat that question$",
        r"^can you please repeat$",
        r"^can you please repeat that$",
        r"^can you please repeat the question$",
        r"^could you repeat that$",
        r"^could you repeat the question$",
        r"^could you please repeat that$",
        r"^could you please repeat the question$",
        r"^please repeat$",
        r"^please repeat that$",
        r"^please repeat the question$",
        r"^please repeat this question$",
        r"^one more time$",
        r"^sorry repeat$",
        r"^i did not catch that$",
        r"^i didn't catch that$",
        r"^pardon$",
    ]
    clarify_patterns = [
        r"^(i )?do not understand$",
        r"^(i )?do not understand the question$",
        r"^(i )?don't understand$",
        r"^(i )?don't understand the question$",
        r"^(i )?did not understand$",
        r"^(i )?did not understand the question$",
        r"^(i )?didn't understand$",
        r"^(i )?didn't understand the question$",
        r"^(i )?cannot understand$",
        r"^(i )?cannot understand the question$",
        r"^(i )?cannot understand this question$",
        r"^(i )?can't understand$",
        r"^(i )?can't understand the question$",
        r"^(i )?can't understand this question$",
        r"^(i )?cant understand$",
        r"^(i )?cant understand the question$",
        r"^(i )?cant understand this question$",
        r"^can you explain$",
        r"^can you explain that$",
        r"^can you explain the question$",
        r"^can you explain this question$",
        r"^can you please explain the question$",
        r"^could you explain$",
        r"^could you explain that$",
        r"^could you explain the question$",
        r"^could you explain this question$",
        r"^please explain$",
        r"^please explain the question$",
        r"^please explain this question$",
        r"^clarify$",
        r"^clarify the question$",
        r"^clarify this question$",
        r"^simplify$",
        r"^simplify the question$",
        r"^simplify this question$",
        r"^make it simpler$",
        r"^what do you mean$",
        r"^what does that mean$",
        r"^i am confused$",
        r"^i'm confused$",
    ]

    if any(re.fullmatch(pattern, normalized) for pattern in repeat_patterns):
        return "repeat"
    if any(re.fullmatch(pattern, normalized) for pattern in clarify_patterns):
        return "clarify"
    if any(
        marker in normalized
        for marker in (
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
        )
    ):
        return "repeat"
    if any(
        marker in normalized
        for marker in (
            "do not understand",
            "don't understand",
            "did not understand",
            "didn't understand",
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
        )
    ):
        return "clarify"
    return None


def _detect_end_interview_request(value: str) -> bool:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return False
    patterns = [
        r"^end interview$",
        r"^end the interview$",
        r"^please end the interview$",
        r"^i want to end the interview$",
        r"^i want to stop the interview$",
        r"^stop the interview$",
        r"^finish the interview$",
        r"^can we end the interview$",
        r"^let us end the interview$",
        r"^let's end the interview$",
        r"^please stop the interview$",
    ]
    return any(re.fullmatch(pattern, normalized) for pattern in patterns)


def _detect_confirmation_reply(value: str) -> Optional[str]:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return None
    word_count = len([word for word in normalized.split() if word])
    if word_count > 8:
        return None

    yes_patterns = [
        r"^yes$",
        r"^yes please$",
        r"^yes end it$",
        r"^yes end the interview$",
        r"^please end it$",
        r"^please end the interview$",
        r"^end the interview$",
        r"^confirm$",
        r"^okay end it$",
        r"^ok end it$",
        r"^sure$",
        r"^yep$",
        r"^yeah$",
    ]
    no_patterns = [
        r"^no$",
        r"^no please$",
        r"^no continue$",
        r"^continue$",
        r"^continue interview$",
        r"^do not end it$",
        r"^don't end it$",
        r"^dont end it$",
        r"^keep going$",
        r"^let us continue$",
        r"^let's continue$",
        r"^resume$",
        r"^not now$",
    ]

    if any(re.fullmatch(pattern, normalized) for pattern in yes_patterns):
        return "yes"
    if any(re.fullmatch(pattern, normalized) for pattern in no_patterns):
        return "no"
    return None


def _detect_off_topic_small_talk(value: str) -> Optional[str]:
    normalized = _normalize_text(value).lower()
    if not normalized:
        return None
    word_count = len([word for word in normalized.split() if word])
    if word_count > 18:
        return None

    patterns = {
        "greeting": [
            r"^hi$",
            r"^hello$",
            r"^hey$",
            r"^good morning$",
            r"^good afternoon$",
            r"^good evening$",
            r"^nice to meet you$",
            r"^howdy$",
        ],
        "identity": [
            r"^what(?:'s| is) your name.*$",
            r"^who are you.*$",
            r"^tell me your name.*$",
            r"^what are you.*$",
        ],
        "wellbeing": [
            r"^how are you.*$",
            r"^how(?:'s| is) it going.*$",
            r"^are you okay.*$",
            r"^how have you been.*$",
        ],
        "personal_life": [
            r"^are you married.*$",
            r"^are you single.*$",
            r"^do you have (?:a )?(?:wife|husband|girlfriend|boyfriend).*$",
            r"^do you have children.*$",
            r"^do you have kids.*$",
            r"^tell me about your family.*$",
            r"^what do you think about marriage.*$",
            r"^tell me about marriage.*$",
        ],
        "background": [
            r"^where are you from.*$",
            r"^how old are you.*$",
            r"^what is your age.*$",
            r"^what religion are you.*$",
            r"^what is your religion.*$",
            r"^what caste are you.*$",
            r"^what nationality are you.*$",
        ],
        "meta": [
            r"^are you (?:an )?ai.*$",
            r"^are you human.*$",
            r"^are you real.*$",
            r"^are you a robot.*$",
            r"^which model are you.*$",
            r"^what model are you.*$",
            r"^are you chatgpt.*$",
            r"^who made you.*$",
            r"^who created you.*$",
            r"^what can you do.*$",
        ],
        "casual": [
            r"^what is your favorite .*",
            r"^what's your favorite .*",
            r"^do you like .*",
            r"^what do you like .*",
            r"^tell me a joke.*$",
            r"^say a joke.*$",
            r"^what is the weather.*$",
            r"^how is the weather.*$",
            r"^can we be friends.*$",
            r"^do you love me.*$",
        ],
    }

    for label, label_patterns in patterns.items():
        if any(re.fullmatch(pattern, normalized) for pattern in label_patterns):
            return label
    return None


def _build_question_clarification(
    question_text: str,
    question_type: str = "",
    topic_tag: str = "",
) -> str:
    normalized = _normalize_text(question_text).lower()
    question_type = _normalize_text(question_type).lower()
    topic = _normalize_text(topic_tag)

    if not normalized:
        return "Sure. Let me make that simpler, then I will repeat the same question."
    if question_type in {"fundamental", "conceptual"} or normalized.startswith("what is") or normalized.startswith("explain"):
        focus = topic or "the concept"
        return (
            f"Sure. Keep it simple: define {focus}, explain how it works in plain language, "
            "and give one small example. I will repeat the same question."
        )
    if question_type == "scenario" or any(marker in normalized for marker in ("imagine", "production", "slowing", "failure", "incident")):
        return (
            "Sure. Start with what you would check first, how you would narrow the issue down, "
            "and what trade-offs you would consider. I will repeat the same question."
        )
    if question_type == "practical" or any(marker in normalized for marker in ("walk me through", "approach", "how would you", "what data structure")):
        return (
            "Sure. Answer step by step. Explain your approach first, mention the main data structure or components you would use, "
            "and then add the key trade-offs or complexity. I will repeat the same question."
        )
    if any(marker in normalized for marker in ("tell me about a time", "describe a time")):
        return (
            "Sure. Briefly explain the situation, what you did, and the result. "
            "I will repeat the same question."
        )
    return "Sure. Answer directly, keep it structured, and add one clear example or outcome where possible. I will repeat the same question."


def _build_control_turn_response(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    command: str,
    assistant_reply: Optional[str] = None,
    feedback: str = "",
    suggestions: Optional[List[str]] = None,
    next_question: Optional[str] = None,
    next_question_type: Optional[str] = None,
    answer_text: str = "",
    should_end_interview: bool = False,
) -> Dict[str, Any]:
    prompt = _normalize_text(question.get("question") or "")
    question_type = _normalize_text(question.get("question_type") or "practical")
    topic_tag = _normalize_text(question.get("topic_tag") or "")
    spoken_reply = _normalize_text(
        assistant_reply
        or (
            "Sure. I will repeat the same question."
            if command == "repeat"
            else _build_question_clarification(prompt, question_type, topic_tag)
        )
    )
    next_prompt = prompt if next_question is None else _normalize_text(next_question)
    next_prompt_type = _normalize_text(next_question_type or question_type) or "practical"

    return {
        "question_id": question["id"],
        "question": prompt,
        "question_type": question_type or "practical",
        "interview_phase": _normalize_text(question.get("interview_phase") or ""),
        "answer": _normalize_text(answer_text),
        "score": 0,
        "feedback": _normalize_text(feedback),
        "strengths": [],
        "gaps": [],
        "matched_points": [],
        "missed_points": [],
        "suggested_answer": "",
        "assistant_reply": spoken_reply,
        "relevance": "",
        "correctness": "",
        "clarity": "",
        "technical_depth": "",
        "logical_validity": "",
        "real_world_applicability": "",
        "suggestions": _safe_list(suggestions)[:3],
        "provider": "command",
        "count_towards_score": False,
        "communication_score": None,
        "confidence_score": None,
        "problem_solving_score": None,
        "teamwork_score": None,
        "leadership_score": None,
        "hr_readiness_score": None,
        "personality_attitude_score": None,
        "cultural_fit_score": None,
        "star_score": None,
        "question_index": question_index,
        "is_complete": False,
        "next_question": next_prompt,
        "next_question_type": next_prompt_type,
        "next_interview_phase": _normalize_text(question.get("interview_phase") or ""),
        "progress": {
            "current": question_index,
            "total": _session_total_questions(session),
        },
        "providers": dict(session.get("providers", {})),
        "question_outline": session.get("question_outline", []),
        "is_control_turn": True,
        "control_command": command,
        "should_end_interview": bool(should_end_interview),
        # Include adaptive state for skill-based interviews
        "current_skill": question.get("skill", ""),
        "difficulty_adjusted_to": question.get("difficulty", "medium"),
        "difficulty_progression": session.get("meta", {}).get("adaptive_state", {}).get("state", {}).get("difficulty_history", []),
    }


def _build_off_topic_control_response(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str,
    off_topic_kind: str,
) -> Dict[str, Any]:
    topic_label = _normalize_text(question.get("topic_tag") or question.get("question_type") or "this topic")
    if off_topic_kind == "greeting":
        opener = "We can skip the small talk and stay with the interview."
    elif off_topic_kind == "identity":
        opener = "My role here is to interview you, not to discuss me."
    elif off_topic_kind == "wellbeing":
        opener = "I appreciate that, but we need to stay with the interview."
    elif off_topic_kind == "personal_life":
        opener = "That is not appropriate for the current interview question, so let us keep this professional."
    elif off_topic_kind == "background":
        opener = "That is not relevant to this interview question."
    elif off_topic_kind == "meta":
        opener = "Questions about the interviewer or the system are not relevant to your answer."
    else:
        opener = "That is not related to the question I asked."

    assistant_reply = (
        f"Irrelevant answer. {opener} "
        f"Please answer the current question about {topic_label} directly."
    )
    feedback = (
        f"Irrelevant answer. Your response was not relevant to the question. In a real interview, this would be treated as poor focus and a weak answer. "
        f"Stay on {topic_label}, answer the prompt directly, and avoid unrelated personal or casual conversation."
    )
    suggestions = [
        f"Answer the question directly about {topic_label} before saying anything else.",
        "If you need help, ask me to repeat or clarify the question instead of changing the topic.",
        "Add one relevant example only after you have addressed the actual prompt.",
    ]
    return _build_control_turn_response(
        session,
        question_index,
        question,
        "off_topic",
        assistant_reply=assistant_reply,
        feedback=feedback,
        suggestions=suggestions,
        next_question=_normalize_text(question.get("question") or ""),
        next_question_type=_normalize_text(question.get("question_type") or "practical"),
        answer_text=answer_text,
    )


def _normalize_known_language(value: str) -> str:
    normalized = _normalize_text(value).lower()
    return KNOWN_LANGUAGES.get(normalized, _normalize_text(value))


def _detect_answer_language_mismatch(session: Dict[str, Any], answer_text: str) -> str:
    state = session.get("meta", {}).get("adaptive_state") or {}
    selected_mode = _normalize_text(
        state.get("selected_mode") or session.get("context", {}).get("selected_mode") or ""
    ).lower()
    target_language = _normalize_known_language(
        state.get("preferred_language")
        or session.get("context", {}).get("primary_language")
        or ""
    )
    if selected_mode != "language" or not target_language:
        return ""

    mentioned_languages = _extract_known_terms(answer_text, KNOWN_LANGUAGES)
    if not mentioned_languages:
        return ""

    normalized_target = _normalize_text(target_language).lower()
    normalized_mentions = {
        _normalize_text(language).lower()
        for language in mentioned_languages
        if _normalize_text(language)
    }
    if normalized_target in normalized_mentions:
        return ""
    if len(normalized_mentions) == 1:
        return next(iter(normalized_mentions))
    return ""


def _build_retry_answer_control_response(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str,
    evaluation: Dict[str, Any],
) -> Dict[str, Any]:
    topic_label = _normalize_text(question.get("topic_tag") or question.get("question_type") or "this topic")
    expected_language = _normalize_known_language(
        session.get("meta", {}).get("adaptive_state", {}).get("preferred_language")
        or session.get("context", {}).get("primary_language")
        or ""
    )
    detected_language = _detect_answer_language_mismatch(session, answer_text)
    quality = _answer_quality_signals(answer_text)
    word_count = quality["word_count"]
    relevance = _normalize_text(evaluation.get("relevance") or "")
    style = _feedback_style(session, question)

    if style == "behavioral":
        topic_noun = "example"
    elif style == "hr":
        topic_noun = "answer"
    else:
        topic_noun = "technical answer"

    if detected_language and expected_language:
        assistant_reply = (
            f"You switched away from {expected_language}. Please answer this question in {expected_language} so I can assess the right topic."
        )
        feedback = (
            f"Your response focused on {detected_language.title()} instead of {expected_language}. "
            f"This interview is currently testing {expected_language}, so the same question will stay active."
        )
        suggestions = [
            f"Answer using {expected_language} concepts, syntax, or examples.",
            "If you need the question repeated, ask me to repeat it instead of switching technologies.",
            "Give one direct example that clearly matches the selected language.",
        ]
    elif quality["gibberish_like"]:
        assistant_reply = (
            "Sorry, I do not understand what you said. Please answer the same question clearly."
            if style == "technical"
            else "Sorry, I do not understand what you said. Please answer the same question clearly in normal words."
        )
        feedback = (
            f"Your response was not understandable enough to evaluate {topic_label}. "
            f"The interview will stay on the same question until you give a clear {topic_noun} in normal words."
        )
        suggestions = [
            "Answer in clear words or sentences.",
            "State your actual point directly.",
            "Add one simple explanation or example.",
        ]
    elif quality["likely_nonsense"]:
        assistant_reply = (
            "I did not get a meaningful answer there. Please answer the same question clearly."
            if style == "technical"
            else "I did not get a meaningful answer there. Please answer the same question clearly, like you would to a real interviewer."
        )
        feedback = (
            f"Your response did not contain enough meaningful information to evaluate {topic_label}. "
            f"The interview will stay on the same question until you give a direct {topic_noun} with at least one clear idea."
        )
        suggestions = [
            "Start with one direct point that answers the question.",
            "Add one brief explanation or example from your work, project, or learning.",
            "Avoid repeated words, filler, or unrelated phrases.",
        ]
    elif quality["filler_hits"] and word_count < 10:
        assistant_reply = (
            "That still sounds too vague. Please give me one clear answer with a short explanation."
            if style != "behavioral"
            else "That still sounds too vague. Please give me one clear example with a short explanation."
        )
        feedback = (
            f"Your response sounded more like filler than a complete answer about {topic_label}. "
            f"A human interviewer would expect one clear point, a short explanation, and a relevant {'example' if style == 'behavioral' else 'detail'}."
        )
        suggestions = [
            "Answer in one or two complete sentences first.",
            "Explain why that point matters.",
            "Add one simple example if you can.",
        ]
    elif word_count < 8:
        assistant_reply = (
            "I heard a response, but there is not enough there yet for me to assess your actual answer."
            if style != "behavioral"
            else "I heard a response, but there is not enough there yet for me to assess the example properly."
        )
        feedback = (
            f"Your response did not give me enough substance to assess {topic_label} properly. "
            "Give a direct answer, then add one clear explanation, example, or outcome."
        )
        suggestions = [
            "Start with a direct answer to the question.",
            "Add one specific example, action, or implementation detail.",
            "Finish with the result, trade-off, or why it mattered.",
        ]
    elif relevance == "Not Relevant":
        assistant_reply = "Irrelevant answer. Please try to give an appropriate answer to the question."
        feedback = (
            f"Your response did not stay relevant to {topic_label}, so the interview will keep the current question active. "
            "Answer the prompt directly before adding extra context."
        )
        suggestions = [
            f"Focus directly on {topic_label}.",
            "Answer the exact question before adding background details.",
            "Use one relevant technical or practical example.",
        ]
    else:
        assistant_reply = (
            "That answer still needs more specificity before we move on. Please try the same question again with a clearer explanation."
            if style == "technical"
            else "That answer still needs more specificity before we move on. Please try the same question again with a clearer and more complete response."
        )
        feedback = (
            f"Your response was not strong enough to move forward yet. "
            f"It needs clearer relevance, structure, or {'ownership and impact' if style == 'behavioral' else 'role connection' if style == 'hr' else 'technical detail'} on {topic_label}."
        )
        suggestions = [
            "Answer in a clear order: main point, brief explanation, then example.",
            "Use the exact topic from the question instead of a related topic.",
            "Add one practical detail that shows real understanding.",
        ]

    return _build_control_turn_response(
        session,
        question_index,
        question,
        "retry_answer",
        assistant_reply=assistant_reply,
        feedback=feedback,
        suggestions=suggestions,
        next_question=_normalize_text(question.get("question") or ""),
        next_question_type=_normalize_text(question.get("question_type") or "practical"),
        answer_text=answer_text,
    )


def _should_retry_answer(
    session: Dict[str, Any],
    question: Dict[str, Any],
    answer_text: str,
    evaluation: Dict[str, Any],
) -> bool:
    normalized_answer = _normalize_text(answer_text)
    if not normalized_answer:
        return False

    if _detect_answer_language_mismatch(session, normalized_answer):
        return True

    quality = _answer_quality_signals(normalized_answer)
    word_count = quality["word_count"]
    relevance = _normalize_text(evaluation.get("relevance") or "")
    correctness = _normalize_text(evaluation.get("correctness") or "")
    clarity = _normalize_text(evaluation.get("clarity") or "")
    logical_validity = _normalize_text(evaluation.get("logical_validity") or "")
    matched_points = _safe_list(evaluation.get("matched_points"))
    score = max(0, min(100, int(evaluation.get("score", 0))))

    if quality["explicit_no_idea"]:
        return False
    if quality["likely_nonsense"]:
        return True
    if quality["filler_hits"] and word_count < 10:
        return True
    if relevance == "Not Relevant" and not matched_points and score < 45:
        return True
    if logical_validity == "Illogical" and not matched_points and score < 45:
        return True
    if word_count < 6:
        return True
    if score < 35 and not matched_points:
        return True
    if correctness == "Incorrect" and clarity == "Needs Improvement" and word_count < 16:
        return True
    return False


def _adaptive_closing_message(
    session: Dict[str, Any],
    question: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> str:
    role_label = _normalize_text(session.get("meta", {}).get("adaptive_state", {}).get("role_label") or session.get("context", {}).get("job_role") or "this role")
    topic = _normalize_text(question.get("topic_tag") or question.get("question_type") or "the discussion")
    score = int(evaluation.get("score") or 0)

    if score >= 80:
        performance_note = f"You handled the discussion around {topic} confidently."
    elif score >= 60:
        performance_note = f"You showed a solid base in {topic}."
    else:
        performance_note = f"You stayed engaged through some challenging {role_label} questions."

    return (
        "That brings us to the end of the interview. "
        f"{performance_note} "
        "If this were a live round, this is where I would ask: do you have any questions for me?"
    )


def _adaptive_intro_legacy(payload: Dict[str, Any], question_count: int) -> str:
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    role = _normalize_text(payload.get("job_role") or "the selected role")
    language = _normalize_text(payload.get("primary_language") or "the selected language")
    category = _normalize_text(payload.get("category") or "").lower()
    subject = language if selected_mode == "language" and language else role
    if category == "mock":
        return (
            f"Hello, I’m your AI interviewer for this {role} mock interview. "
            "I’ll start by understanding the technologies you feel most comfortable with, and then I’ll ask one question at a time like a real interviewer. "
            "Because this is a mock interview, I may include a small HR or behavioral section near the end as well."
        )
    return (
        f"Hello, I’m your AI interviewer for this {role} technical round. "
        "I’ll first confirm the stack you’d like to focus on, and then I’ll ask one question at a time and adapt based on your answers. "
        f"I’ll keep the interview technical and tailor the next {question_count} scored questions to your strengths."
    )


def _adaptive_discovery_question_legacy(payload: Dict[str, Any], variation: Optional[Dict[str, str]] = None) -> str:
    role = _normalize_text(payload.get("job_role") or "this role")
    role_lower = role.lower()
    shuffler = random.Random(_normalize_text((variation or {}).get("seed") or role or "adaptive"))
    if any(keyword in role_lower for keyword in ("backend", "full stack", "full-stack", "fullstack", "software engineer", "software developer")):
        options = [
            f"To start, which backend languages, frameworks, databases, or tools are you most comfortable with for this {role} role?",
            f"Before we go deeper, which backend stack do you actually feel strongest with for this {role} role?",
            f"To get the interview aligned properly, which backend technologies have you used most confidently in real work for this {role} role?",
        ]
    else:
        options = [
            f"To start, which languages, frameworks, tools, or technical areas are you most comfortable with for this {role} role?",
            f"Before we dive in, which technical stack or problem areas would you like me to focus on first for this {role} role?",
            f"To tailor this interview properly, which technologies or technical areas do you feel strongest with for this {role} role?",
        ]
    return shuffler.choice(options)


def _build_adaptive_state(payload: Dict[str, Any], role_blueprint: Dict[str, Any], question_count: int) -> Dict[str, Any]:
    category = _normalize_text(payload.get("category") or "").lower()
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    primary_language = _normalize_text(payload.get("primary_language") or role_blueprint.get("language_focus") or "")
    include_hr = category in {"mock", "resume"}
    hr_target = 0 if not include_hr else (1 if question_count <= 5 else 2 if category == "mock" else max(2, min(3, question_count // 3 or 2)))
    technical_target = max(1, question_count - hr_target)
    language_mode = (selected_mode or ("language" if primary_language else "role")) == "language" and bool(primary_language)
    return {
        "enabled": True,
        "include_hr": include_hr,
        "selected_mode": selected_mode or ("language" if primary_language else "role"),
        "scored_question_target": question_count,
        "technical_question_target": technical_target,
        "discovery_questions_asked": 0 if language_mode else 1,
        "clarification_turns": 0,
        "discovery_complete": language_mode,
        "preferred_language": primary_language,
        "languages": [primary_language] if primary_language else [],
        "frameworks": [],
        "databases": [],
        "tools": [],
        "focus_areas": _safe_list(role_blueprint.get("core_areas"))[:6],
        "covered_topics": [],
        "scored_questions_answered": 0,
        "technical_questions_answered": 0,
        "hr_questions_answered": 0,
        "hr_question_target": hr_target,
        "role_label": _normalize_text(
            payload.get("job_role")
            or role_blueprint.get("role_label")
            or (f"{primary_language} technical focus" if primary_language else "Technical Role")
        ),
        "confidence_summary": "",
        "difficulty_guidance": _difficulty_from_experience(payload.get("experience") or ""),
        "technical_phase_plan": _build_technical_phase_plan(technical_target, selected_mode or ("language" if primary_language else "role")),
        "last_phase": "",
    }


def _adaptive_intro(payload: Dict[str, Any], question_count: int) -> str:
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    role = _normalize_text(payload.get("job_role") or "the selected role")
    language = _normalize_text(payload.get("primary_language") or "the selected language")
    category = _normalize_text(payload.get("category") or "").lower()
    first_name = _candidate_first_name(payload)
    greeting = f"Hi {first_name}, nice to meet you. " if first_name else "Hi, nice to meet you. "
    subject = language if selected_mode == "language" and language else role
    time_mode_minutes = _payload_time_mode_minutes(payload)
    time_mode_suffix = (
        f"We will keep the interview moving for about {time_mode_minutes} minutes, adapting question by question until the timer ends."
        if time_mode_minutes
        else f"I will keep the next {question_count} scored questions aligned to your selected experience level."
    )
    technical_suffix = (
        f"We will keep the interview running for about {time_mode_minutes} minutes, and I will adapt the next questions based on your answers until the timer ends."
        if time_mode_minutes
        else f"I will keep the interview technical and tailor the next {question_count} scored questions to your strengths."
    )
    if selected_mode == "language" and language:
        if category == "mock":
            return (
                f"{greeting}I will be taking your {language} mock interview today. "
                "Let us keep this conversational, and feel free to think out loud. "
                f"We will begin with {language} fundamentals, go one level deeper conceptually, "
                "and then I will use one practical language question to tailor the rest of the round. "
                "Because this is a mock round, I may include a short behavioral section near the end as well."
            )
        return (
            f"{greeting}I will be taking your {language} technical interview today. "
            "Let us keep this conversational, and feel free to think out loud. "
            f"We will begin with {language} fundamentals, go one level deeper conceptually, "
            "and then I will use one practical language question to tailor the later questions. "
            f"{time_mode_suffix}"
        )
    if category == "resume":
        return (
            f"{greeting}I will be taking your resume-based interview for {subject} today. "
            "I have reviewed the profile signals extracted from your resume, and I will use your background to keep the conversation personalized, practical, and natural. "
            "We will cover technical depth first, and I will also include a small HR or behavioral section based on your profile."
        )
    if category == "mock":
        return (
            f"{greeting}I will be taking your {subject} mock interview today. "
            "Let us keep this conversational, and feel free to think out loud. "
            "I will first understand where you are strongest, then I will adapt the interview one question at a time. "
            "Because this is a mock round, I may include a short behavioral section near the end as well."
        )
    return (
        f"{greeting}I will be taking your {subject} technical interview today. "
        "Let us keep this conversational, and feel free to think out loud. "
        "I will first confirm the technical area you want to focus on, then I will adapt the next questions based on your answers. "
        f"{technical_suffix}"
    )


def _language_opening_turn(
    payload: Dict[str, Any],
    question_count: int,
    variation: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    language = _normalize_text(payload.get("primary_language") or "the selected language")
    difficulty_guidance = _difficulty_from_experience(payload.get("experience") or "")
    question_pack = _pick_language_phase_question(
        language,
        "warmup",
        difficulty_guidance,
        _normalize_text((variation or {}).get("seed") or language),
        0,
    )
    return {
        "assistant_intro": _adaptive_intro(payload, question_count),
        "question": question_pack["question"],
        "question_type": question_pack["question_type"],
        "expected_points": question_pack["expected_points"],
        "evaluation_focus": question_pack["evaluation_focus"],
        "topic_tag": question_pack["topic_tag"],
        "interview_phase": "warmup",
        "count_towards_score": True,
    }


def _adaptive_discovery_question(payload: Dict[str, Any], variation: Optional[Dict[str, str]] = None) -> str:
    role = _normalize_text(payload.get("job_role") or "this role")
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    language = _normalize_text(payload.get("primary_language") or "")
    role_lower = role.lower()
    shuffler = random.Random(_normalize_text((variation or {}).get("seed") or role or language or "adaptive"))
    if selected_mode == "language" and language:
        options = [
            f"Tell me about one real project or problem where you used {language}, and what part of the language mattered most.",
            f"Tell me about one {language} debugging issue, implementation decision, or feature you handled in real work or practice.",
            f"Give me one concrete example of using {language} in a project, and explain what technical choice mattered there.",
        ]
        return shuffler.choice(options)
    if any(keyword in role_lower for keyword in ("backend", "full stack", "full-stack", "fullstack", "software engineer", "software developer")):
        options = [
            f"To start, which backend languages, frameworks, databases, or tools are you most comfortable with for this {role} role?",
            f"Before we go deeper, which backend stack do you actually feel strongest with for this {role} role?",
            f"To get the interview aligned properly, which backend technologies have you used most confidently in real work for this {role} role?",
        ]
    else:
        options = [
            f"To start, which languages, frameworks, tools, or technical areas are you most comfortable with for this {role} role?",
            f"Before we dive in, which technical stack or problem areas would you like me to focus on first for this {role} role?",
            f"To tailor this interview properly, which technologies or technical areas do you feel strongest with for this {role} role?",
        ]
    return shuffler.choice(options)


def _append_session_question(session: Dict[str, Any], question_payload: Dict[str, Any]) -> Dict[str, Any]:
    question_text = _normalize_text(question_payload.get("question") or "")
    if not question_text:
        raise ProviderError("Generated question text was empty.")

    question = {
        "id": len(session.get("questions", [])) + 1,
        "question": question_text,
        "question_type": _safe_question_type(question_payload.get("question_type")),
        "expected_points": _safe_list(question_payload.get("expected_points"))[:5],
        "evaluation_focus": _safe_list(question_payload.get("evaluation_focus"))[:4],
        "count_towards_score": bool(question_payload.get("count_towards_score", True)),
        "topic_tag": _normalize_text(question_payload.get("topic_tag") or ""),
        "interview_phase": _normalize_text(question_payload.get("interview_phase") or ""),
    }

    session.setdefault("questions", []).append(question)
    session.setdefault("question_outline", []).append(
        {
            "id": question["id"],
            "question": question["question"],
            "question_type": question["question_type"],
            "interview_phase": question["interview_phase"],
        }
    )
    return question


def _adaptive_total_questions(session: Dict[str, Any]) -> int:
    state = session.get("meta", {}).get("adaptive_state") or {}
    if not state.get("enabled"):
        return len(session.get("questions", []))
    if _session_uses_time_mode(session):
        answered = len(session.get("evaluations", []) or [])
        visible_total = max(len(session.get("questions", [])), answered + 1)
        if session.get("completed_at") or session.get("summary"):
            visible_total = max(len(session.get("questions", [])), answered)
        return max(visible_total, 1)
    if _normalize_text(state.get("mode") or "").lower() == "hr":
        return max(
            len(session.get("questions", [])),
            int(state.get("scored_question_target", 0)),
        )
    return max(
        len(session.get("questions", [])),
        int(state.get("scored_question_target", 0)) + max(0, int(state.get("discovery_questions_asked", 0))),
    )


def _adaptive_state_summary(state: Dict[str, Any]) -> str:
    if _normalize_text(state.get("mode") or "").lower() == "hr":
        return "\n".join(
            [
                f"Role label: {state.get('role_label') or 'Not specified'}",
                f"Round mode: {state.get('round_mode') or 'hr_behavioral'}",
                f"Focus areas: {', '.join(state.get('focus_areas') or []) or 'General HR'}",
                f"Focus plan: {', '.join(state.get('focus_plan') or []) or 'Adaptive'}",
                f"Phase plan: {', '.join(state.get('phase_plan') or []) or 'Adaptive'}",
                f"Confidence summary: {state.get('confidence_summary') or 'Not confirmed yet'}",
                f"Covered topics: {', '.join(state.get('covered_topics') or []) or 'None yet'}",
                f"Questions answered: {state.get('scored_questions_answered', 0)}",
            ]
        )
    return "\n".join(
        [
            f"Role label: {state.get('role_label') or 'Not specified'}",
            f"Selected mode: {state.get('selected_mode') or 'role'}",
            f"Preferred language: {state.get('preferred_language') or 'Not confirmed'}",
            f"Languages mentioned: {', '.join(state.get('languages') or []) or 'None yet'}",
            f"Frameworks mentioned: {', '.join(state.get('frameworks') or []) or 'None yet'}",
            f"Databases mentioned: {', '.join(state.get('databases') or []) or 'None yet'}",
            f"Tools mentioned: {', '.join(state.get('tools') or []) or 'None yet'}",
            f"Focus areas: {', '.join(state.get('focus_areas') or []) or 'None yet'}",
            f"Technical phase plan: {', '.join(state.get('technical_phase_plan') or []) or 'Adaptive'}",
            f"Next technical phase: {_next_adaptive_phase(state, 'technical')}",
            f"Difficulty guidance: {state.get('difficulty_guidance') or 'moderate'}",
            f"Confidence summary: {state.get('confidence_summary') or 'Not confirmed yet'}",
            f"Covered topics: {', '.join(state.get('covered_topics') or []) or 'None yet'}",
            f"Technical questions answered: {state.get('technical_questions_answered', 0)}",
            f"HR questions answered: {state.get('hr_questions_answered', 0)}",
        ]
    )


def _fallback_stack_analysis(answer_text: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    languages = _extract_known_terms(answer_text, KNOWN_LANGUAGES)
    frameworks = _extract_known_terms(answer_text, KNOWN_FRAMEWORKS)
    databases = _extract_known_terms(answer_text, KNOWN_DATABASES)
    tools = _extract_known_terms(answer_text, KNOWN_TOOLS)
    language_focus_areas = _extract_known_terms(answer_text, KNOWN_LANGUAGE_FOCUS_AREAS)
    preferred_language = _extract_preferred_language(answer_text, languages)

    if not preferred_language and frameworks:
        framework_to_language = {
            "FastAPI": "Python",
            "Django": "Python",
            "Flask": "Python",
            "Spring Boot": "Java",
            "Spring": "Java",
            "Express.js": "JavaScript",
            "NestJS": "TypeScript",
            "Laravel": "PHP",
            "ASP.NET": "C#",
            "Gin": "Go",
        }
        for framework in frameworks:
            implied = framework_to_language.get(framework)
            if implied:
                preferred_language = implied
                if implied not in languages:
                    languages.append(implied)
                break

    if not preferred_language and payload.get("primary_language"):
        preferred_language = _normalize_text(payload.get("primary_language"))
        if preferred_language and preferred_language not in languages:
            languages.append(preferred_language)

    needs_clarification = False
    clarification_question = ""
    if len(languages) > 1 and not _extract_preferred_language(answer_text, languages):
        needs_clarification = True
        clarification_question = (
            f"You mentioned {', '.join(languages[:3])}. Which one would you like me to focus on first for this interview?"
        )
    elif not languages and not frameworks:
        needs_clarification = True
        clarification_question = (
            "Which backend language or framework would you like me to focus on first, and what stack have you actually used?"
        )

    focus_areas = _merge_unique(frameworks, databases)
    focus_areas = _merge_unique(focus_areas, tools)
    focus_areas = _merge_unique(focus_areas, language_focus_areas)
    if preferred_language:
        focus_areas = _merge_unique([preferred_language], focus_areas)

    stack_summary = ", ".join(focus_areas[:4]) or (preferred_language or "your preferred stack")
    acknowledgement = (
        f"Thanks. I will tailor the interview around {stack_summary}."
        if stack_summary
        else "Thanks. I will tailor the interview around what you are most comfortable with."
    )

    return {
        "preferred_language": preferred_language,
        "languages": languages,
        "frameworks": frameworks,
        "databases": databases,
        "tools": tools,
        "focus_areas": focus_areas,
        "confidence_summary": f"Candidate appears most comfortable with {stack_summary}." if stack_summary else "",
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "acknowledgement": acknowledgement,
    }


async def _analyze_discovery_answer(session: Dict[str, Any], answer_text: str) -> Tuple[Dict[str, Any], str]:
    payload = session.get("context", {})
    fallback = _fallback_stack_analysis(answer_text, payload)
    prompt = f"""
You are an experienced technical interviewer tailoring a live interview after the candidate's stack-discovery answer.

Interview context:
{_context_summary(payload)}

Candidate discovery answer:
{answer_text}

Return valid JSON:
{{
  "preferred_language": "single preferred language if clearly stated, else empty string",
  "languages": ["languages explicitly mentioned or strongly implied"],
  "frameworks": ["frameworks explicitly mentioned or strongly implied"],
  "databases": ["databases explicitly mentioned or strongly implied"],
  "tools": ["tools, cloud, APIs, or infrastructure items explicitly mentioned or strongly implied"],
  "focus_areas": ["the best interview focus areas to use next"],
  "confidence_summary": "one short summary of the candidate's stack comfort",
  "needs_clarification": false,
  "clarification_question": "one short clarification question if needed, otherwise empty string",
  "acknowledgement": "one short human-like acknowledgement before the next step"
}}

Rules:
- Do not assume a language or framework unless the candidate clearly mentioned it or strongly implied it.
- If the candidate mentions multiple backend languages without a preference, set needs_clarification to true.
- If the answer is too vague, ask one short clarification question.
- Keep acknowledgement natural and concise, like a real interviewer.
- Avoid markdown.
"""
    try:
        analysis, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            LIVE_AI_TIMEOUT_SECONDS,
        )
        normalized = {
            "preferred_language": _normalize_text(analysis.get("preferred_language") or fallback["preferred_language"]),
            "languages": _safe_list(analysis.get("languages")) or fallback["languages"],
            "frameworks": _safe_list(analysis.get("frameworks")) or fallback["frameworks"],
            "databases": _safe_list(analysis.get("databases")) or fallback["databases"],
            "tools": _safe_list(analysis.get("tools")) or fallback["tools"],
            "focus_areas": _safe_list(analysis.get("focus_areas")) or fallback["focus_areas"],
            "confidence_summary": _normalize_text(analysis.get("confidence_summary") or fallback["confidence_summary"]),
            "needs_clarification": bool(analysis.get("needs_clarification")) if "needs_clarification" in analysis else fallback["needs_clarification"],
            "clarification_question": _normalize_text(analysis.get("clarification_question") or fallback["clarification_question"]),
            "acknowledgement": _normalize_text(analysis.get("acknowledgement") or fallback["acknowledgement"]),
        }
        return normalized, provider
    except ProviderError:
        return fallback, "fallback"


def _apply_discovery_analysis(state: Dict[str, Any], analysis: Dict[str, Any]) -> None:
    state["preferred_language"] = _normalize_text(
        analysis.get("preferred_language") or state.get("preferred_language") or ""
    )
    state["languages"] = _merge_unique(state.get("languages") or [], _safe_list(analysis.get("languages")))
    state["frameworks"] = _merge_unique(state.get("frameworks") or [], _safe_list(analysis.get("frameworks")))
    state["databases"] = _merge_unique(state.get("databases") or [], _safe_list(analysis.get("databases")))
    state["tools"] = _merge_unique(state.get("tools") or [], _safe_list(analysis.get("tools")))
    state["focus_areas"] = _merge_unique(state.get("focus_areas") or [], _safe_list(analysis.get("focus_areas")))
    state["confidence_summary"] = _normalize_text(
        analysis.get("confidence_summary") or state.get("confidence_summary") or ""
    )


def _adaptive_focus_candidates(session: Dict[str, Any], last_question: Optional[Dict[str, Any]] = None) -> List[str]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    role_blueprint = session.get("meta", {}).get("role_blueprint") or {}
    selected_options = _safe_list(session.get("context", {}).get("selected_options") or [])
    selected_mode = _normalize_text(state.get("selected_mode") or session.get("context", {}).get("selected_mode") or "").lower()
    preferred_language = _normalize_text(state.get("preferred_language") or "")
    candidates: List[str] = []
    if selected_mode == "language" and preferred_language:
        candidates = _merge_unique(candidates, [preferred_language])
    candidates = _merge_unique(candidates, state.get("frameworks") or [])
    candidates = _merge_unique(candidates, state.get("databases") or [])
    candidates = _merge_unique(candidates, state.get("tools") or [])
    candidates = _merge_unique(candidates, [preferred_language])
    candidates = _merge_unique(candidates, selected_options)
    candidates = _merge_unique(candidates, _safe_list(role_blueprint.get("tech_stack")))
    candidates = _merge_unique(candidates, _safe_list(role_blueprint.get("core_areas")))
    if last_question:
        candidates = _merge_unique(candidates, [_normalize_text(last_question.get("topic_tag") or "")])
    return [item for item in candidates if item]


def _next_adaptive_track(state: Dict[str, Any]) -> str:
    if not state.get("include_hr"):
        return "technical"
    if int(state.get("hr_questions_answered", 0)) >= int(state.get("hr_question_target", 0)):
        return "technical"
    technical_before_hr = max(2, int(state.get("scored_question_target", 0)) - int(state.get("hr_question_target", 0)))
    if int(state.get("technical_questions_answered", 0)) >= technical_before_hr:
        return "hr"
    return "technical"


def _next_uncovered_topic(session: Dict[str, Any], last_question: Optional[Dict[str, Any]] = None) -> str:
    state = session.get("meta", {}).get("adaptive_state") or {}
    selected_mode = _normalize_text(state.get("selected_mode") or session.get("context", {}).get("selected_mode") or "").lower()
    preferred_language = _normalize_text(state.get("preferred_language") or "")
    covered = {item.lower() for item in state.get("covered_topics") or []}
    last_topic = _normalize_text((last_question or {}).get("topic_tag") or "")
    if selected_mode == "language" and preferred_language and preferred_language.lower() not in covered:
        return preferred_language
    for candidate in _adaptive_focus_candidates(session, last_question):
        lowered = candidate.lower()
        if lowered not in covered and lowered != last_topic.lower():
            return candidate
    return last_topic or preferred_language or _normalize_text(session.get("context", {}).get("job_role") or "backend fundamentals")


def _fallback_adaptive_question_legacy(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    evaluation: Optional[Dict[str, Any]],
    desired_track: str,
) -> Dict[str, Any]:
    role = _normalize_text(session.get("context", {}).get("job_role") or "the role")
    score = int((evaluation or {}).get("score") or 0)
    topic = _next_uncovered_topic(session, last_question)

    if desired_track == "hr":
        return {
            "assistant_reply": "Thank you. I’d also like to understand how you work with people, pressure, and ownership.",
            "question": (
                f"Tell me about a time you had to explain a technical decision, handle pressure, or coordinate with others while working as a {role}. "
                "What was the situation, what did you do, and what happened?"
            ),
            "question_type": "behavioral",
            "expected_points": [
                "clear situation",
                "specific actions taken",
                "communication or prioritization choices",
                "result and learning",
            ],
            "evaluation_focus": ["structure", "ownership", "communication"],
            "topic_tag": "behavioral ownership",
        }

    if score < 55:
        return {
            "assistant_reply": "Thanks, that helps. Let’s keep it a little more concrete and stay on the same stack for a moment.",
            "question": f"Can you walk me through a real backend example where you used {topic}, including what you built and the main trade-offs?",
            "question_type": "practical",
            "expected_points": [
                "clear project context",
                "specific implementation steps",
                "relevant backend concepts",
                "trade-offs or result",
            ],
            "evaluation_focus": ["specificity", "practical detail", "clarity"],
            "topic_tag": topic,
        }

    if score >= 80:
        return {
            "assistant_reply": "Nice, that was clear. Let’s go one level deeper there.",
            "question": f"What edge cases, failure modes, or production trade-offs do you watch for when working with {topic} in a backend system?",
            "question_type": "scenario",
            "expected_points": [
                "important edge cases",
                "failure handling or resilience",
                "trade-offs",
                "practical mitigation steps",
            ],
            "evaluation_focus": ["depth", "real-world awareness", "clarity"],
            "topic_tag": topic,
        }

    next_topic = _next_uncovered_topic(session, last_question)
    return {
        "assistant_reply": "Good. Let’s move to another area you’re likely to face in a real backend interview.",
        "question": f"How would you design, implement, or troubleshoot {next_topic} for a {role} service?",
        "question_type": "practical",
        "expected_points": [
            "clear approach",
            "relevant tools or concepts",
            "real implementation detail",
            "trade-offs or debugging awareness",
        ],
        "evaluation_focus": ["technical reasoning", "practicality", "clarity"],
        "topic_tag": next_topic,
    }


def _fallback_adaptive_question(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    evaluation: Optional[Dict[str, Any]],
    desired_track: str,
) -> Dict[str, Any]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    context = session.get("context", {}) or {}
    role = _normalize_text(context.get("job_role") or state.get("role_label") or "the role")
    preferred_language = _normalize_text(state.get("preferred_language") or "")
    score = int((evaluation or {}).get("score") or 0)
    phase = _next_adaptive_phase(state, desired_track)
    topic = _next_uncovered_topic(session, last_question)
    difficulty_guidance = _normalize_text(state.get("difficulty_guidance") or "moderate")
    selected_mode = _normalize_text(state.get("selected_mode") or context.get("selected_mode") or "").lower()
    subject = preferred_language if selected_mode == "language" and preferred_language else role
    language_mode = selected_mode == "language" and bool(preferred_language)
    variation_seed = _normalize_text((session.get("meta", {}).get("interview_variation") or {}).get("seed") or preferred_language or role)
    rotation_index = int(state.get("technical_questions_answered", 0))

    if desired_track == "hr":
        return {
            "assistant_reply": "Good. Before we wrap up, I also want to understand how you handle communication, ownership, and pressure.",
            "question": (
                f"Tell me about a time you had to explain a technical decision, handle pressure, or coordinate with others while working in {subject}. "
                "What was the situation, what did you do, and what happened?"
            ),
            "question_type": "behavioral",
            "expected_points": [
                "clear situation",
                "specific actions taken",
                "communication or prioritization choices",
                "result and learning",
            ],
            "evaluation_focus": ["structure", "ownership", "communication"],
            "topic_tag": "behavioral ownership",
            "interview_phase": "behavioral_bridge",
        }

    if phase == "warmup":
        topic_label = preferred_language if language_mode else (topic or preferred_language or "your strongest technical area")
        if language_mode:
            question_pack = _pick_language_phase_question(
                preferred_language,
                "warmup",
                difficulty_guidance,
                variation_seed,
                rotation_index,
            )
            question_text = question_pack["question"]
            expected_points = question_pack["expected_points"]
            evaluation_focus = question_pack["evaluation_focus"]
            topic_label = question_pack["topic_tag"]
        else:
            question_text = (
                f"Can you explain one core concept in {topic_label} that you are comfortable with, "
                "and give a small real example of where you would use it?"
            )
            expected_points = [
                "clear definition in simple terms",
                "main purpose or behavior",
                "one concrete example",
                "confident and structured explanation",
            ]
            evaluation_focus = ["clarity", "confidence", "fundamentals"]
        return {
            "assistant_reply": "Thanks. Let us start with something simple and settle into the conversation.",
            "question": question_text,
            "question_type": "fundamental",
            "expected_points": expected_points,
            "evaluation_focus": evaluation_focus,
            "topic_tag": topic_label,
            "interview_phase": phase,
        }

    if phase == "concept_deep_dive":
        if score < 55:
            return {
                "assistant_reply": "You are on the right track. Let us keep it concrete and stay with the same topic for a moment.",
                "question": (
                    (
                        f"No problem. In {preferred_language}, can you give me one real example of using a core language feature or construct, "
                        "what problem it solved, and why that approach made sense?"
                    )
                    if language_mode
                    else (
                        f"No problem. Can you give me one real example of using {topic}, what problem it solved, "
                        "and why you chose that approach?"
                    )
                ),
                "question_type": "practical",
                "expected_points": [
                    "clear project context",
                    "specific implementation detail",
                    "why the choice made sense",
                    "result or lesson",
                ],
                "evaluation_focus": ["specificity", "practical detail", "clarity"],
                "topic_tag": topic,
                "interview_phase": phase,
            }
        if language_mode:
            question_pack = _pick_language_phase_question(
                preferred_language,
                "concept_deep_dive",
                difficulty_guidance,
                variation_seed,
                rotation_index,
            )
            question_text = question_pack["question"]
            expected_points = question_pack["expected_points"]
            topic = question_pack["topic_tag"]
        else:
            question_text = (
                f"How is {topic} different from the closest alternative you would compare it with, "
                "and when would you choose one over the other in a real system?"
            )
            expected_points = [
                "clear comparison",
                "important trade-offs",
                "real usage choice",
                "structured reasoning",
            ]
        return {
            "assistant_reply": "Good. Let us go one level deeper on that.",
            "question": question_text,
            "question_type": "conceptual",
            "expected_points": expected_points,
            "evaluation_focus": ["conceptual depth", "trade-offs", "clarity"],
            "topic_tag": topic,
            "interview_phase": phase,
        }

    if phase == "language_discovery":
        question_pack = _pick_language_phase_question(
            preferred_language,
            "language_discovery",
            difficulty_guidance,
            variation_seed,
            rotation_index,
        )
        return {
            "assistant_reply": "That helps. I want one practical language example before I branch further.",
            "question": question_pack["question"],
            "question_type": question_pack["question_type"],
            "expected_points": question_pack["expected_points"],
            "evaluation_focus": question_pack["evaluation_focus"],
            "topic_tag": question_pack["topic_tag"],
            "interview_phase": phase,
        }

    if phase == "structured_thinking":
        follow_up = (
            "Keep it step by step and simple."
            if "introductory" in difficulty_guidance
            else "Call out the data structure, time complexity, and any optimization if it matters."
        )
        return {
            "assistant_reply": "That makes sense. Let us do a more structured problem-solving question next.",
            "question": (
                "Imagine you are given a technical problem on the spot. "
                f"Walk me through how you would approach it before writing code. {follow_up}"
            ),
            "question_type": "practical",
            "expected_points": [
                "step-by-step approach",
                "data structure or system choice",
                "time or space complexity awareness",
                "possible optimization or trade-off",
            ],
            "evaluation_focus": ["problem solving", "structure", "clarity"],
            "topic_tag": topic or "problem solving",
            "interview_phase": phase,
        }

    scenario_suffix = (
        "What trade-offs would you consider while optimizing it?"
        if "advanced" in difficulty_guidance
        else "Explain it step by step in simple terms."
    )
    return {
        "assistant_reply": "Good. Let us finish with a more real-world scenario.",
        "question": (
            f"Imagine an application in {subject} is slowing down because of growing data or traffic. "
            f"How would you identify the issue, decide what to change first, and improve it? {scenario_suffix}"
        ),
        "question_type": "scenario",
        "expected_points": [
            "clear investigation steps",
            "useful debugging or observability signals",
            "prioritized fix or optimization plan",
            "trade-offs or practical impact",
        ],
        "evaluation_focus": ["debug mindset", "real-world judgment", "clarity"],
        "topic_tag": topic or "system performance",
        "interview_phase": "real_world_scenario",
    }


async def _generate_adaptive_question(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    answer_text: str,
    evaluation: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    variation = session.get("meta", {}).get("interview_variation") or {}
    desired_track = _next_adaptive_track(state)
    next_phase = _next_adaptive_phase(state, desired_track)
    last_score = int((evaluation or {}).get("score") or 0)
    context = session.get("context", {}) or {}
    role = _normalize_text(context.get("job_role") or state.get("role_label") or "the selected role")
    target_subject = _normalize_text(state.get("preferred_language") or role)
    prompt = f"""
You are running a live adaptive AI interview one question at a time.

Interview context:
{_context_summary(session.get("context", {}))}

Discovered candidate profile:
{_adaptive_state_summary(state)}

Recent turn:
- Previous question: {(last_question or {}).get("question") or "None"}
- Previous topic: {(last_question or {}).get("topic_tag") or "None"}
- Candidate answer: {answer_text or "No answer captured"}
- Last score: {last_score}
- Last feedback: {(evaluation or {}).get("feedback") or "Not available"}
- Last gaps: {json.dumps((evaluation or {}).get("gaps") or [], ensure_ascii=False)}

Remaining scored questions after the next turn: {max(0, int(state.get("scored_question_target", 0)) - int(state.get("scored_questions_answered", 0)) - 1)}
Desired next track: {desired_track}
Desired phase for the next question: {next_phase}
Target role: {role}
Primary technical subject: {target_subject}
Session variation:
{_variation_summary(variation)}

Return valid JSON with this exact shape:
{{
  "assistant_reply": "one short micro-feedback bridge before the next question",
  "question": "exactly one next interview question",
  "question_type": "fundamental | conceptual | practical | scenario | behavioral",
  "expected_points": ["3 to 5 concise expected answer points"],
  "evaluation_focus": ["3 concise evaluation criteria"],
  "topic_tag": "short topic label",
  "interview_phase": "{next_phase}"
}}

Rules:
- Ask exactly one question.
- Sound like a curious, calm, and supportive human interviewer.
- Keep assistant_reply gentle, natural, and short, like a real interviewer speaking conversationally.
- assistant_reply should act like real-time micro-feedback: briefly acknowledge what went well and, if helpful, mention one thing to improve before the next question.
- Make the wording feel fresh for this session instead of using stock repeated phrasing.
- If selected mode is language-based, do not jump into random generic technical topics first.
- If selected mode is language-based, follow this early order before broader applied questions: warmup fundamentals, then concept_deep_dive, then language_discovery.
- If selected mode is language-based, do not ask the candidate to choose which fundamentals topic they are comfortable with.
- If selected mode is language-based and the phase is warmup, ask one direct basic or core question from the selected language.
- If selected mode is language-based and the phase is concept_deep_dive, stay inside the selected language and push into conceptual depth, language behavior, trade-offs, or edge cases based on answer quality and difficulty guidance.
- If selected mode is language-based and the phase is concept_deep_dive, prefer direct core-language questions instead of asking the candidate to pick a topic.
- If selected mode is language-based and the phase is language_discovery, learn from one real project, debugging issue, or implementation decision in the selected language instead of asking the candidate which area they feel strongest in.
- If selected mode is language-based, anchor the early questions in the selected language's fundamentals, concepts, syntax behavior, core constructs, or practical usage patterns before branching out to frameworks, tools, databases, or wider system topics.
- If desired next track is technical, do not ask HR, self-introduction, motivation, or strengths and weaknesses questions.
- If desired next track is technical and the phase is warmup, ask a confidence-building fundamentals question that lets the candidate settle in.
- If desired next track is technical and the phase is concept_deep_dive, adapt strongly to answer quality:
  - below 55: simplify, stay on the same topic, and ask for a concrete example.
  - 55 to 79: ask for a clearer comparison, reasoning, or trade-off.
  - 80 or above: go deeper on the same topic with edge cases, trade-offs, or system impact.
- If desired next track is technical and the phase is structured_thinking, ask a no-code problem-solving question. Push for approach, data structure choice, complexity, and possible optimization.
- If desired next track is technical and the phase is real_world_scenario, ask a practical debugging, scaling, performance, or production scenario.
- If desired next track is hr, ask one realistic behavioral or communication question relevant to the role.
- Match the depth to the difficulty guidance in the state summary:
  - introductory to moderate: explain step by step and avoid abrupt jumps in difficulty.
  - moderate to advanced: expect clearer trade-offs and stronger structure.
  - advanced and scenario-based: push into edge cases, scaling, resilience, and decision trade-offs.
- Prefer the candidate's preferred language, frameworks, and tools when known.
- Avoid repeating covered topics unless you are intentionally following up on a weak answer.
- Encourage a human interview feel. Phrases like "walk me through", "talk me through your approach", or "feel free to think out loud" are good when natural.
- Keep it professional, specific, and natural.
- Do not use markdown.
"""

    try:
        generated, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            LIVE_AI_TIMEOUT_SECONDS,
        )
        question = {
            "assistant_reply": _normalize_text(generated.get("assistant_reply") or ""),
            "question": _normalize_text(generated.get("question") or ""),
            "question_type": _safe_question_type(generated.get("question_type") or ("behavioral" if desired_track == "hr" else "practical")),
            "expected_points": _safe_list(generated.get("expected_points"))[:5],
            "evaluation_focus": _safe_list(generated.get("evaluation_focus"))[:4],
            "topic_tag": _normalize_text(generated.get("topic_tag") or _next_uncovered_topic(session, last_question)),
            "interview_phase": _normalize_text(generated.get("interview_phase") or next_phase),
        }
        if desired_track == "hr":
            question["question_type"] = "behavioral"
        elif question["question_type"] == "behavioral":
            question["question_type"] = "practical"
        if not question["question"] or not question["expected_points"]:
            raise ProviderError("Adaptive question generation returned incomplete data.")
        return question, provider
    except ProviderError:
        return _fallback_adaptive_question(session, last_question, evaluation, desired_track), "fallback"


async def _generate_adaptive_opening_turn(
    payload: Dict[str, Any],
    role_blueprint: Dict[str, Any],
    question_count: int,
    variation: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Any], str]:
    variation = variation or _build_interview_variation(payload)
    if _normalize_text(payload.get("selected_mode") or "").lower() == "language" and _normalize_text(payload.get("primary_language") or ""):
        return _language_opening_turn(payload, question_count, variation), "rule-based"

    fallback = {
        "assistant_intro": _adaptive_intro(payload, question_count),
        "question": _adaptive_discovery_question(payload, variation),
        "question_type": "discovery",
        "expected_points": [
            "languages the candidate knows",
            "frameworks or backend tools used",
            "preferred stack to focus on",
        ],
        "evaluation_focus": ["clarity", "stack identification", "specificity"],
        "topic_tag": "stack discovery",
        "interview_phase": "discovery",
        "count_towards_score": False,
    }
    prompt = f"""
You are a highly experienced technical interviewer conducting a real-time interview.

Your behavior must be human-like, conversational, adaptive, and professional but friendly.

Interview context:
- Role: {_normalize_text(payload.get("job_role") or role_blueprint.get("role_label") or "the selected role")}
- Candidate skills: {json.dumps(_safe_list(payload.get("selected_options") or []), ensure_ascii=False)}
- Experience level: {_normalize_text(payload.get("experience") or "Not specified")}
- Interview type: {_normalize_text(payload.get("category") or "technical")}
- Inferred role blueprint: {json.dumps(role_blueprint, ensure_ascii=False)}
Session variation:
{_variation_summary(variation)}

Return valid JSON:
{{
  "assistant_intro": "short natural greeting like a real interviewer",
  "question": "exactly one opening discovery question",
  "question_type": "discovery",
  "expected_points": ["3 to 5 concise things the candidate should mention"],
  "evaluation_focus": ["3 concise discovery criteria"],
  "topic_tag": "stack discovery"
}}

Rules:
- Start naturally like a human interviewer.
- The greeting should feel like a real interviewer opening the round, and it is good to say that the conversation can stay natural and the candidate can think out loud.
- Ask only one question.
- Do not assume the candidate's backend language or framework.
- If selected mode is language-based, ask one direct basic or core question from that language instead of asking the candidate to choose a topic.
- Otherwise ask which languages, frameworks, databases, or tools they are actually comfortable with.
- Keep the intro concise and warm.
- Make the wording fresh for this session and avoid stock repeated phrasing.
- If this is a mock interview, you may lightly mention that a short behavioral section can appear later.
- Keep the first question discovery-focused, not HR-focused.
- Avoid markdown.
"""
    try:
        opening, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.35,
            STARTUP_AI_TIMEOUT_SECONDS,
        )
        normalized = {
            "assistant_intro": _normalize_text(opening.get("assistant_intro") or fallback["assistant_intro"]),
            "question": _normalize_text(opening.get("question") or fallback["question"]),
            "question_type": "discovery",
            "expected_points": _safe_list(opening.get("expected_points"))[:5] or fallback["expected_points"],
            "evaluation_focus": _safe_list(opening.get("evaluation_focus"))[:4] or fallback["evaluation_focus"],
            "topic_tag": _normalize_text(opening.get("topic_tag") or fallback["topic_tag"]),
            "interview_phase": "discovery",
            "count_towards_score": False,
        }
        if not normalized["question"]:
            raise ProviderError("Adaptive opening turn returned an empty question.")
        return normalized, provider
    except ProviderError:
        return fallback, "fallback"


def _register_scored_turn(state: Dict[str, Any], question: Dict[str, Any]) -> None:
    if not question.get("count_towards_score", True):
        return
    state["scored_questions_answered"] = int(state.get("scored_questions_answered", 0)) + 1
    state["last_phase"] = _normalize_text(question.get("interview_phase") or state.get("last_phase") or "")
    topic = _normalize_text(question.get("topic_tag") or "")
    if topic:
        state["covered_topics"] = _merge_unique(state.get("covered_topics") or [], [topic])
    if _normalize_text(state.get("mode") or "").lower() == "hr":
        state["hr_questions_answered"] = int(state.get("hr_questions_answered", 0)) + 1
        return
    if question.get("question_type") == "behavioral":
        state["hr_questions_answered"] = int(state.get("hr_questions_answered", 0)) + 1
    else:
        state["technical_questions_answered"] = int(state.get("technical_questions_answered", 0)) + 1


def _record_turn_result(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str,
    evaluation: Dict[str, Any],
    provider_used: str,
    next_question: Optional[Dict[str, Any]] = None,
    is_complete: bool = False,
) -> Dict[str, Any]:
    result = {
        "question_id": question["id"],
        "question": question["question"],
        "question_type": question.get("question_type", "practical"),
        "interview_phase": _normalize_text(question.get("interview_phase") or ""),
        "answer": answer_text,
        "score": max(0, min(100, int(evaluation.get("score", 0)))),
        "feedback": _normalize_text(evaluation.get("feedback") or ""),
        "strengths": _safe_list(evaluation.get("strengths"))[:3],
        "gaps": _safe_list(evaluation.get("gaps"))[:3],
        "matched_points": _safe_list(evaluation.get("matched_points"))[:4],
        "missed_points": _safe_list(evaluation.get("missed_points"))[:4],
        "suggested_answer": _normalize_text(evaluation.get("suggested_answer") or ""),
        "assistant_reply": _normalize_text(evaluation.get("assistant_reply") or "Thank you. Let us continue."),
        "relevance": _normalize_text(evaluation.get("relevance") or ""),
        "correctness": _normalize_text(evaluation.get("correctness") or ""),
        "clarity": _normalize_text(evaluation.get("clarity") or ""),
        "technical_depth": _normalize_text(evaluation.get("technical_depth") or ""),
        "logical_validity": _normalize_text(evaluation.get("logical_validity") or ""),
        "real_world_applicability": _normalize_text(evaluation.get("real_world_applicability") or ""),
        "suggestions": _safe_list(evaluation.get("suggestions"))[:3],
        "provider": provider_used,
        "count_towards_score": bool(question.get("count_towards_score", True)),
        "communication_score": _normalize_score_value(evaluation.get("communication_score")),
        "confidence_score": _normalize_score_value(evaluation.get("confidence_score")),
        "problem_solving_score": _normalize_score_value(evaluation.get("problem_solving_score")),
        "teamwork_score": _normalize_score_value(evaluation.get("teamwork_score")),
        "leadership_score": _normalize_score_value(evaluation.get("leadership_score")),
        "hr_readiness_score": _normalize_score_value(evaluation.get("hr_readiness_score")),
        "personality_attitude_score": _normalize_score_value(evaluation.get("personality_attitude_score")),
        "cultural_fit_score": _normalize_score_value(evaluation.get("cultural_fit_score")),
        "star_score": _normalize_score_value(evaluation.get("star_score")),
    }

    answers = session.setdefault("answers", [])
    evaluations = session.setdefault("evaluations", [])
    if len(answers) > question_index:
        answers[question_index] = answer_text
    else:
        answers.append(answer_text)

    if len(evaluations) > question_index:
        evaluations[question_index] = result
    else:
        evaluations.append(result)

    return {
        **result,
        "question_index": question_index,
        "is_complete": is_complete,
        "next_question": next_question["question"] if next_question else None,
        "next_question_type": next_question.get("question_type") if next_question else None,
        "next_interview_phase": _normalize_text(next_question.get("interview_phase") or "") if next_question else None,
        "progress": {
            "current": question_index + 1,
            "total": _adaptive_total_questions(session),
        },
        "providers": dict(session.get("providers", {})),
        "question_outline": session.get("question_outline", []),
    }


def _scored_evaluations(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        item
        for item in session.get("evaluations", [])
        if item.get("count_towards_score", True)
    ]


def _is_session_completed(session: Dict[str, Any]) -> bool:
    return bool(session.get("completed_at")) and isinstance(session.get("summary"), dict)


def _session_total_questions(session: Dict[str, Any]) -> int:
    adaptive_state = session.get("meta", {}).get("adaptive_state") or {}
    return (
        _adaptive_total_questions(session)
        if adaptive_state.get("enabled")
        else len(session.get("questions", []))
    )


def _session_uses_time_mode(session: Dict[str, Any]) -> bool:
    meta = session.get("meta", {}) or {}
    context = session.get("context", {}) or {}
    config_mode = _normalize_text(meta.get("config_mode") or context.get("config_mode") or "").lower()
    time_limit = meta.get("time_mode_interval") or context.get("time_mode_interval")
    return config_mode == "time" and bool(time_limit)


def _build_session_status_payload(session: Dict[str, Any]) -> Dict[str, Any]:
    questions = session.get("questions", []) or []
    evaluations = session.get("evaluations", []) or []
    answers = session.get("answers", []) or []
    current_index = min(len(evaluations), max(0, len(questions) - 1)) if questions else 0
    current_question = questions[current_index]["question"] if questions else ""
    current_question_type = questions[current_index].get("question_type", "practical") if questions else "practical"

    return {
        "session_id": session.get("session_id"),
        "created_at": session.get("created_at"),
        "completed_at": session.get("completed_at"),
        "ended_early": bool(session.get("ended_early", False)),
        "is_complete": _is_session_completed(session),
        "assistant_intro": session.get("assistant_intro", ""),
        "providers": dict(session.get("providers", {})),
        "meta": dict(session.get("meta", {})),
        "context": dict(session.get("context", {})),
        "question_outline": session.get("question_outline", []),
        "questions": questions,
        "answers": answers,
        "evaluations": evaluations,
        "current_index": current_index,
        "current_question": current_question,
        "current_question_type": current_question_type,
        "questions_answered": len(evaluations),
        "total_questions": _session_total_questions(session),
        "summary": session.get("summary"),
        "saved_report_user_ids": list(session.get("saved_report_user_ids", [])),
    }


async def _create_adaptive_interview_session(
    payload: Dict[str, Any],
    question_count: int,
    difficulty: str,
    role_blueprint: Dict[str, Any],
    blueprint_provider: str,
    variation: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    variation = variation or _build_interview_variation(payload)
    adaptive_state = _build_adaptive_state(payload, role_blueprint, question_count)
    opening_turn, opening_provider = await _generate_adaptive_opening_turn(payload, role_blueprint, question_count, variation)
    provider_meta = {
        "generation_provider": opening_provider,
        "evaluation_provider": "",
        "analysis_provider": blueprint_provider,
    }

    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "context": payload,
        "assistant_intro": opening_turn["assistant_intro"],
        "questions": [],
        "answers": [],
        "evaluations": [],
        "providers": provider_meta,
        "meta": {
            "difficulty": difficulty,
            "config_mode": payload.get("config_mode") or "question",
            "practice_type": payload.get("practice_type") or "practice",
            "interview_mode_time": payload.get("interview_mode_time"),
            "time_mode_interval": payload.get("time_mode_interval"),
            "selected_mode": payload.get("selected_mode"),
            "role_blueprint": role_blueprint,
            "adaptive_state": adaptive_state,
            "interview_variation": variation,
        },
        "question_outline": [],
        "saved_report_user_ids": [],
    }

    first_question = _append_session_question(
        session,
        {
            "question": opening_turn["question"],
            "question_type": opening_turn["question_type"],
            "expected_points": opening_turn["expected_points"],
            "evaluation_focus": opening_turn["evaluation_focus"],
            "count_towards_score": bool(opening_turn.get("count_towards_score", False)),
            "topic_tag": opening_turn["topic_tag"],
            "interview_phase": _normalize_text(opening_turn.get("interview_phase") or ""),
        },
    )

    INTERVIEW_SESSIONS[session_id] = session
    await _persist_session(session)
    return {
        "session_id": session_id,
        "assistant_intro": session["assistant_intro"],
        "total_questions": _adaptive_total_questions(session),
        "current_question": first_question["question"],
        "current_question_type": first_question["question_type"],
        "providers": provider_meta,
        "meta": session["meta"],
        "question_outline": session["question_outline"],
    }


def _hr_intro_message(payload: Dict[str, Any], question_count: int) -> str:
    role = _normalize_text(payload.get("job_role") or "candidate")
    first_name = _candidate_first_name(payload)
    greeting = f"Hi {first_name}! Nice to meet you. " if first_name else "Hi! Nice to meet you. "
    round_mode = _hr_round_label(_hr_round_mode(payload))
    focus = ", ".join(_selected_focus_areas(payload)[:3]) or "communication, leadership, and problem-solving"
    time_mode_minutes = _payload_time_mode_minutes(payload)
    pacing = (
        f"We will keep this interview moving for about {time_mode_minutes} minutes with extra attention on {focus}."
        if time_mode_minutes
        else f"We will cover about {question_count} tailored questions with extra attention on {focus}."
    )
    return (
        f"{greeting}I will be taking your {round_mode} interview for a {role} candidate today. "
        f"{pacing}"
    )


def _fallback_hr_opening_turn(payload: Dict[str, Any], question_count: int) -> Dict[str, Any]:
    role = _normalize_text(payload.get("job_role") or "your target role")
    return {
        "assistant_intro": _hr_intro_message(payload, question_count),
        "question": f"Let us start with a quick introduction. Tell me about yourself and how your background connects to {role}.",
        "question_type": "introduction",
        "expected_points": [
            "clear summary of background or education",
            "relevant experience or projects",
            f"connection to {role}",
            "confident and structured delivery",
        ],
        "evaluation_focus": ["clarity", "confidence", "structure"],
        "topic_tag": "self introduction",
    }


async def _generate_hr_opening_turn(
    payload: Dict[str, Any],
    question_count: int,
    variation: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Any], str]:
    variation = variation or _build_interview_variation(payload)
    fallback = _fallback_hr_opening_turn(payload, question_count)
    prompt = f"""
You are a warm, professional AI HR interviewer starting a live adaptive interview.

Interview context:
{_context_summary(payload)}
Session variation:
{_variation_summary(variation)}

Return valid JSON:
{{
  "assistant_intro": "short human-like greeting",
  "question": "exactly one opening HR question",
  "question_type": "introduction | conceptual | behavioral",
  "expected_points": ["3 to 5 concise things the candidate should cover"],
  "evaluation_focus": ["3 concise evaluation criteria"],
  "topic_tag": "short topic label"
}}

Rules:
- Start naturally like a real interviewer.
- The first question should feel like greeting plus icebreaker.
- Focus on self-introduction, background, or role connection.
- Keep it short, warm, and conversational.
- Avoid markdown.
"""
    try:
        opening, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            STARTUP_AI_TIMEOUT_SECONDS,
        )
        normalized = {
            "assistant_intro": _normalize_text(opening.get("assistant_intro") or fallback["assistant_intro"]),
            "question": _normalize_text(opening.get("question") or fallback["question"]),
            "question_type": _safe_question_type(opening.get("question_type") or fallback["question_type"]),
            "expected_points": _safe_list(opening.get("expected_points"))[:5] or fallback["expected_points"],
            "evaluation_focus": _safe_list(opening.get("evaluation_focus"))[:4] or fallback["evaluation_focus"],
            "topic_tag": _normalize_text(opening.get("topic_tag") or fallback["topic_tag"]),
        }
        if not normalized["question"]:
            raise ProviderError("HR opening turn returned an empty question.")
        return normalized, provider
    except ProviderError:
        return fallback, "fallback"


def _fallback_hr_adaptive_question(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    evaluation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    payload = session.get("context", {})
    role = _normalize_text(payload.get("job_role") or "the role")
    phase = _next_hr_phase(state)
    focus = _next_hr_focus(state, last_question)
    focus_label = _normalize_text(focus or "communication")
    score = int((evaluation or {}).get("score") or 0)

    assistant_reply = (
        "Thanks. Let us make the next answer more concrete."
        if score < 55
        else "That was clear. Let us go one level deeper."
        if score >= 80
        else "Good. Let us move to the next area."
    )

    if phase == "background":
        return {
            "assistant_reply": assistant_reply,
            "question": f"Walk me through the background, experiences, or projects that best prepared you for {role}, especially the parts that show your {focus_label.lower()}.",
            "question_type": "conceptual",
            "expected_points": [
                "clear summary of relevant background",
                "specific project or work example",
                "skills gained from the experience",
                f"fit with {role}",
            ],
            "evaluation_focus": ["clarity", "relevance", focus_label],
            "topic_tag": focus_label,
        }

    if phase == "motivation":
        return {
            "assistant_reply": assistant_reply,
            "question": f"What motivated you to pursue {role}, and how does that motivation connect with the way you want to show {focus_label.lower()} in your work?",
            "question_type": "conceptual",
            "expected_points": [
                "genuine motivation",
                "role alignment",
                "career intent",
                "specific example or reasoning",
            ],
            "evaluation_focus": ["motivation", "authenticity", focus_label],
            "topic_tag": focus_label,
        }

    if phase == "strengths":
        return {
            "assistant_reply": assistant_reply,
            "question": f"What would you say are your strongest qualities for {role}, and can you connect those strengths to a real example from your work, studies, or projects?",
            "question_type": "conceptual",
            "expected_points": [
                "specific strengths named clearly",
                "evidence through one concrete example",
                "relevance to the role",
                "self-awareness about impact",
            ],
            "evaluation_focus": ["self-awareness", "role relevance", "specificity"],
            "topic_tag": "strengths",
        }

    if phase == "role_fit":
        return {
            "assistant_reply": assistant_reply,
            "question": f"Why do you believe you are a strong fit for {role}, and what would make a team trust you with meaningful responsibility in that role?",
            "question_type": "conceptual",
            "expected_points": [
                "clear role-fit reasoning",
                "relevant skills or experiences",
                "understanding of role expectations",
                "professional confidence without exaggeration",
            ],
            "evaluation_focus": ["role fit", "clarity", "professional judgment"],
            "topic_tag": "role fit",
        }

    if phase == "workplace":
        return {
            "assistant_reply": assistant_reply,
            "question": "What kind of work environment helps you perform at your best, and how do you stay professional when priorities shift, feedback arrives, or pressure increases?",
            "question_type": "conceptual",
            "expected_points": [
                "clear workplace preferences",
                "adaptability under change",
                "professional response to feedback or pressure",
                "practical habits or examples",
            ],
            "evaluation_focus": ["professionalism", "adaptability", "self-awareness"],
            "topic_tag": "workplace style",
        }

    if phase == "conflict":
        return {
            "assistant_reply": assistant_reply,
            "question": "Tell me about a time you had a disagreement, conflict, or mismatch in expectations with someone you worked with. How did you handle it, and what happened in the end?",
            "question_type": "behavioral",
            "expected_points": [
                "clear conflict context",
                "calm and respectful response",
                "specific action to resolve the issue",
                "outcome or lesson learned",
            ],
            "evaluation_focus": ["conflict handling", "maturity", "STAR structure"],
            "topic_tag": "conflict management",
        }

    if phase == "situational":
        situational_prompts = {
            "communication": "Imagine you have to explain a delay or mistake to your manager and team. What would you say, and how would you handle the conversation?",
            "leadership": "Imagine a team member is stuck and the deadline is very close. What would you do to move the work forward without losing trust?",
            "problem-solving": "Imagine your deadline is tomorrow but a key task is still incomplete. What would you do, and why?",
            "teamwork": "Imagine one team member is not contributing and the project is falling behind. How would you handle it?",
            "confidence": "Imagine you are asked an unexpected question in an important meeting or interview. How would you respond while staying confident?",
        }
        return {
            "assistant_reply": assistant_reply,
            "question": situational_prompts.get(focus_label.lower(), "Imagine your deadline is tomorrow but a key task is still incomplete. What would you do, and why?"),
            "question_type": "scenario",
            "expected_points": [
                "honest situation assessment",
                "prioritization and communication",
                "ownership of next steps",
                "practical outcome or mitigation",
            ],
            "evaluation_focus": ["decision making", "responsibility", focus_label],
            "topic_tag": focus_label,
        }

    if phase == "communication":
        return {
            "assistant_reply": assistant_reply,
            "question": "How do you handle criticism or disagreement while still keeping the conversation professional and productive?",
            "question_type": "behavioral",
            "expected_points": [
                "calm response to feedback",
                "active listening",
                "respectful communication",
                "growth mindset or result",
            ],
            "evaluation_focus": ["communication", "maturity", focus_label],
            "topic_tag": focus_label,
        }

    if phase == "closing":
        return {
            "assistant_reply": "Thank you. Before we wrap up, I have one final question.",
            "question": "Do you have any questions for me, and what would you ask if this were a real interview?",
            "question_type": "conceptual",
            "expected_points": [
                "thoughtful question",
                "interest in role or team",
                "professional tone",
            ],
            "evaluation_focus": ["curiosity", "professionalism", "clarity"],
            "topic_tag": "closing",
        }

    focus_prompts = {
        "communication": "Tell me about a time you had to explain a difficult idea, handle feedback, or de-escalate a tense conversation. What happened and what was the outcome?",
        "leadership": "Tell me about a time you took initiative or led others through a difficult situation. What did you do, and what changed because of it?",
        "problem-solving": "Tell me about a difficult problem or setback you faced. How did you approach it, and what was the result?",
        "teamwork": "Tell me about a time you had to work closely with a team under pressure. What was your role, and how did the situation end?",
        "confidence": "Tell me about a time you had to stay calm and confident in an uncertain or high-pressure situation. What did you do?",
    }
    focus_key = focus.lower()
    question_text = focus_prompts.get(
        focus_key,
        f"Tell me about a time you demonstrated {focus} in a meaningful situation. What was the context, what did you do, and what happened?",
    )
    return {
        "assistant_reply": assistant_reply,
        "question": question_text,
        "question_type": "behavioral",
        "expected_points": [
            "clear situation",
            "specific action taken",
            "result or learning",
            "role ownership",
        ],
        "evaluation_focus": ["STAR structure", "specificity", focus_label],
        "topic_tag": focus_label,
    }


async def _generate_hr_adaptive_question(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    answer_text: str,
    evaluation: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    variation = session.get("meta", {}).get("interview_variation") or {}
    desired_phase = _next_hr_phase(state)
    desired_focus = _next_hr_focus(state, last_question)
    last_score = int((evaluation or {}).get("score") or 0)
    prompt = f"""
You are running a live adaptive HR interview one question at a time.

Interview context:
{_context_summary(session.get("context", {}))}

Current HR interview state:
{_adaptive_state_summary(state)}

Recent turn:
- Previous question: {(last_question or {}).get("question") or "None"}
- Previous topic: {(last_question or {}).get("topic_tag") or "None"}
- Candidate answer: {answer_text or "No answer captured"}
- Last score: {last_score}
- Last feedback: {(evaluation or {}).get("feedback") or "Not available"}
- Last gaps: {json.dumps((evaluation or {}).get("gaps") or [], ensure_ascii=False)}

Desired next phase: {desired_phase}
Desired focus area: {desired_focus}
Session variation:
{_variation_summary(variation)}

Return valid JSON with this exact shape:
{{
  "assistant_reply": "one short conversational bridge",
  "question": "exactly one next HR question",
  "question_type": "introduction | conceptual | behavioral | scenario",
  "expected_points": ["3 to 5 concise expected answer points"],
  "evaluation_focus": ["3 concise evaluation criteria"],
  "topic_tag": "short topic label"
}}

Rules:
- Ask exactly one question.
- Sound human, calm, supportive, and realistic.
- Use the role, experience level, round mode, focus areas, desired focus area, and previous answer.
- Keep the selected focus areas balanced across the interview instead of drifting into only one area.
- Respect the selected round mode exactly:
  - HR: prefer motivation, strengths, role-fit, professionalism, and workplace-style questions.
  - Behavioral: prefer STAR-based teamwork, leadership, conflict, ownership, and situational questions.
  - HR + Behavioral: intentionally mix both families across the interview.
- Respect the desired phase exactly:
  - introduction: self-introduction, background, or role connection.
  - background: relevant experience, education, or project foundation.
  - motivation: why this role, why this path, and what drives the candidate.
  - strengths: strongest qualities with evidence.
  - role_fit: why the candidate fits the role or team.
  - workplace: work style, professionalism, adaptability, feedback, or priorities.
  - behavioral: one STAR-style real example.
  - conflict: disagreement, feedback tension, or conflict resolution.
  - situational: what would you do in a realistic scenario.
  - communication: how the candidate communicates under pressure or criticism.
  - closing: ask if the candidate has any questions for the interviewer.
- If the last answer was vague or scored below 55, ask a simpler follow-up or request specifics before moving on too quickly.
- If the last answer was strong or scored 80+, you may go deeper or make the next question more challenging.
- For behavioral questions, encourage STAR structure.
- For situational questions, test judgment, responsibility, and communication.
- For the closing phase, ask if the candidate has any questions for the interviewer.
- Avoid markdown.
"""

    try:
        generated, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.25,
            LIVE_AI_TIMEOUT_SECONDS,
        )
        question = {
            "assistant_reply": _normalize_text(generated.get("assistant_reply") or ""),
            "question": _normalize_text(generated.get("question") or ""),
            "question_type": _safe_question_type(generated.get("question_type") or "behavioral"),
            "expected_points": _safe_list(generated.get("expected_points"))[:5],
            "evaluation_focus": _safe_list(generated.get("evaluation_focus"))[:4],
            "topic_tag": _normalize_text(generated.get("topic_tag") or _next_hr_focus(state, last_question)),
        }
        if not question["question"] or not question["expected_points"]:
            raise ProviderError("HR adaptive question generation returned incomplete data.")
        return question, provider
    except ProviderError:
        return _fallback_hr_adaptive_question(session, last_question, evaluation), "fallback"


async def _create_hr_adaptive_interview_session(
    payload: Dict[str, Any],
    question_count: int,
    difficulty: str,
    role_blueprint: Dict[str, Any],
    blueprint_provider: str,
    variation: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    variation = variation or _build_interview_variation(payload)
    adaptive_state = _build_hr_adaptive_state(payload, question_count)
    opening_turn, opening_provider = await _generate_hr_opening_turn(payload, question_count, variation)
    provider_meta = {
        "generation_provider": opening_provider,
        "evaluation_provider": "",
        "analysis_provider": blueprint_provider,
    }

    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "context": payload,
        "assistant_intro": opening_turn["assistant_intro"],
        "questions": [],
        "answers": [],
        "evaluations": [],
        "providers": provider_meta,
        "meta": {
            "difficulty": difficulty,
            "config_mode": payload.get("config_mode") or "question",
            "practice_type": payload.get("practice_type") or "practice",
            "interview_mode_time": payload.get("interview_mode_time"),
            "time_mode_interval": payload.get("time_mode_interval"),
            "selected_mode": payload.get("selected_mode"),
            "role_blueprint": role_blueprint,
            "adaptive_state": adaptive_state,
            "interview_variation": variation,
        },
        "question_outline": [],
        "saved_report_user_ids": [],
    }

    first_question = _append_session_question(
        session,
        {
            "question": opening_turn["question"],
            "question_type": opening_turn["question_type"],
            "expected_points": opening_turn["expected_points"],
            "evaluation_focus": opening_turn["evaluation_focus"],
            "count_towards_score": True,
            "topic_tag": opening_turn["topic_tag"],
        },
    )

    INTERVIEW_SESSIONS[session_id] = session
    await _persist_session(session)
    return {
        "session_id": session_id,
        "assistant_intro": session["assistant_intro"],
        "total_questions": question_count,
        "current_question": first_question["question"],
        "current_question_type": first_question["question_type"],
        "providers": provider_meta,
        "meta": session["meta"],
        "question_outline": session["question_outline"],
    }


async def _evaluate_hr_adaptive_interview_answer(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str,
) -> Dict[str, Any]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    context_summary = _context_summary(session["context"])
    expected_points = question.get("expected_points") or []
    evaluation_focus = question.get("evaluation_focus") or []
    prompt = f"""
You are evaluating a spoken HR interview answer.

Interview context:
{context_summary}

Current HR interview state:
{_adaptive_state_summary(state)}

Question:
{question["question"]}

Expected answer points:
{json.dumps(expected_points, ensure_ascii=False)}

Evaluation focus:
{json.dumps(evaluation_focus, ensure_ascii=False)}

Candidate answer:
{answer_text}

Return valid JSON:
{{
  "score": 0,
  "feedback": "2 to 4 sentence evaluation",
  "relevance": "Relevant | Partially Relevant | Not Relevant",
  "correctness": "Correct | Partially Correct | Incorrect",
  "clarity": "Clear | Needs Improvement",
  "technical_depth": "Good | Moderate | Weak",
  "logical_validity": "Logical | Partially Logical | Illogical",
  "real_world_applicability": "Applicable | Partially Applicable | Not Applicable",
  "strengths": ["up to 3 concise strengths"],
  "gaps": ["up to 3 concise gaps"],
  "matched_points": ["expected points that were covered"],
  "missed_points": ["expected points that were not covered"],
  "suggestions": ["up to 3 concise ways to improve"],
  "suggested_answer": "short improved answer guidance",
  "assistant_reply": "one short warm spoken response before the next question",
  "communication_score": 0,
  "confidence_score": 0,
  "problem_solving_score": 0,
  "teamwork_score": 0,
  "leadership_score": 0,
  "hr_readiness_score": 0,
  "personality_attitude_score": 0,
  "cultural_fit_score": 0,
  "star_score": 0
}}

Rules:
- Evaluate approximately, not by exact wording.
- Reward honest, structured, relevant answers even if phrasing is imperfect.
- Check clarity, structure, confidence, examples, and outcome.
- For behavioral answers, reward STAR-like structure.
- If the answer is vague, ask for specifics in the feedback or assistant reply.
- If the answer is strong, say what made it effective.
- Avoid markdown.
"""

    provider_used = session["providers"].get("evaluation_provider", "fallback")
    try:
        evaluation, provider_used = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            LIVE_AI_TIMEOUT_SECONDS,
        )
    except ProviderError:
        evaluation = _hr_heuristic_evaluation(question, answer_text)
        provider_used = "fallback"

    session["providers"]["evaluation_provider"] = provider_used
    if provider_used != "fallback":
        heuristic_defaults = _hr_heuristic_evaluation(question, answer_text)
        evaluation = _normalize_hr_evaluation_payload(evaluation, heuristic_defaults)
        evaluation = _reconcile_evaluation_with_heuristic(evaluation, heuristic_defaults)
    evaluation = _tone_feedback(_feedback_style(session, question), evaluation, question, answer_text)

    if _should_retry_answer(session, question, answer_text, evaluation):
        await _persist_session(session)
        return _build_retry_answer_control_response(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
        )

    _register_scored_turn(state, question)
    if (
        not _session_uses_time_mode(session)
        and int(state.get("scored_questions_answered", 0)) >= int(state.get("scored_question_target", 0))
    ):
        return _record_turn_result(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
            provider_used,
            next_question=None,
            is_complete=True,
        )

    if provider_used == "fallback":
        generated_question, provider = _fallback_hr_adaptive_question(session, question, evaluation), "fallback"
    else:
        generated_question, provider = await _generate_hr_adaptive_question(session, question, answer_text, evaluation)
    session["providers"]["generation_provider"] = provider
    if not evaluation.get("honest_uncertainty"):
        evaluation["assistant_reply"] = _normalize_text(
            generated_question.get("assistant_reply") or evaluation.get("assistant_reply") or "Thanks. Let us continue."
        )
    next_question = _append_session_question(
        session,
        {
            **generated_question,
            "count_towards_score": True,
        },
    )

    return _record_turn_result(
        session,
        question_index,
        question,
        answer_text,
        evaluation,
        provider_used,
        next_question=next_question,
        is_complete=False,
    )


async def _evaluate_adaptive_interview_answer(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str,
) -> Dict[str, Any]:
    state = session.get("meta", {}).get("adaptive_state") or {}

    if question.get("question_type") == "discovery":
        analysis, provider_used = await _analyze_discovery_answer(session, answer_text)
        _apply_discovery_analysis(state, analysis)
        session["providers"]["analysis_provider"] = provider_used

        acknowledgement = _normalize_text(
            analysis.get("acknowledgement")
            or "Thanks, that gives me a clear direction for the rest of the interview."
        )
        matched_points = _merge_unique(_safe_list(analysis.get("languages")), _safe_list(analysis.get("frameworks")))
        matched_points = _merge_unique(matched_points, _safe_list(analysis.get("databases")))
        matched_points = _merge_unique(matched_points, _safe_list(analysis.get("tools")))

        evaluation = {
            "score": 0,
            "feedback": f"{acknowledgement} This discovery step is only to tailor the interview, so it does not affect your score.",
            "strengths": [
                "You clarified your preferred stack for the interviewer.",
                "The interview can now adapt to your real background.",
            ],
            "gaps": (
                ["Your preferred stack still needs one quick clarification."]
                if analysis.get("needs_clarification")
                else []
            ),
            "matched_points": matched_points[:4],
            "missed_points": [],
            "suggested_answer": "Discovery turns are used only to tailor the interview and do not affect scoring.",
            "assistant_reply": acknowledgement,
            "relevance": "Relevant",
            "correctness": "Correct",
            "clarity": "Needs Improvement" if analysis.get("needs_clarification") else "Clear",
            "technical_depth": "Moderate" if matched_points else "Weak",
            "logical_validity": "Logical",
            "real_world_applicability": "Applicable" if matched_points else "Partially Applicable",
            "suggestions": (
                ["Mention the exact language or framework you want me to focus on first."]
                if analysis.get("needs_clarification")
                else ["Keep later answers tied to the stack you just selected."]
            ),
        }

        next_question = None
        if analysis.get("needs_clarification") and int(state.get("clarification_turns", 0)) < 1:
            state["clarification_turns"] = int(state.get("clarification_turns", 0)) + 1
            state["discovery_questions_asked"] = int(state.get("discovery_questions_asked", 1)) + 1
            next_question = _append_session_question(
                session,
                {
                    "question": _normalize_text(
                        analysis.get("clarification_question")
                        or "Which language or framework would you like me to focus on first?"
                    ),
                    "question_type": "discovery",
                    "expected_points": [
                        "clear preferred language or framework",
                        "preferred backend direction",
                        "real experience reference",
                    ],
                    "evaluation_focus": ["clarity", "specificity", "focus"],
                    "count_towards_score": False,
                    "topic_tag": "stack clarification",
                },
            )
        else:
            state["discovery_complete"] = True
            discovery_transition = {
                "score": 70 if matched_points else 55,
                "feedback": evaluation["feedback"],
                "gaps": evaluation["gaps"],
            }
            generated_question, provider = await _generate_adaptive_question(
                session,
                question,
                answer_text,
                discovery_transition,
            )
            session["providers"]["generation_provider"] = provider
            if not evaluation.get("honest_uncertainty"):
                evaluation["assistant_reply"] = _normalize_text(
                    generated_question.get("assistant_reply") or acknowledgement
                )
            next_question = _append_session_question(
                session,
                {
                    **generated_question,
                    "count_towards_score": True,
                },
            )

        return _record_turn_result(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
            provider_used,
            next_question=next_question,
            is_complete=False,
        )

    context_summary = _context_summary(session["context"])
    expected_points = question.get("expected_points") or []
    evaluation_focus = question.get("evaluation_focus") or []
    prompt = f"""
You are evaluating a spoken interview answer using approximate semantic matching.

Interview context:
{context_summary}

Discovered candidate profile:
{_adaptive_state_summary(state)}

Question:
{question["question"]}

Expected answer points:
{json.dumps(expected_points, ensure_ascii=False)}

Evaluation focus:
{json.dumps(evaluation_focus, ensure_ascii=False)}

Candidate answer:
{answer_text}

Return valid JSON:
{{
  "score": 0,
  "feedback": "2 to 4 sentence evaluation",
  "relevance": "Relevant | Partially Relevant | Not Relevant",
  "correctness": "Correct | Partially Correct | Incorrect",
  "clarity": "Clear | Needs Improvement",
  "technical_depth": "Good | Moderate | Weak",
  "logical_validity": "Logical | Partially Logical | Illogical",
  "real_world_applicability": "Applicable | Partially Applicable | Not Applicable",
  "strengths": ["up to 3 concise strengths"],
  "gaps": ["up to 3 concise gaps"],
  "matched_points": ["expected points that were covered"],
  "missed_points": ["expected points that were not covered"],
  "suggestions": ["up to 3 concise ways to improve"],
  "suggested_answer": "short improved answer guidance",
  "assistant_reply": "one short warm spoken micro-feedback response before the next question",
  "communication_score": 0,
  "confidence_score": 0,
  "problem_solving_score": 0
}}

Rules:
- Evaluate approximately, not by exact wording.
- Reward relevant meaning even if phrasing is imperfect.
- Be practical and interview-focused.
- Keep the feedback grounded in how a real interviewer would react.
- If the answer is off-topic, say so gently and redirect to the topic.
- If the answer is vague, ask for more specificity.
- If the answer is too short, ask the candidate to expand on it.
- If the answer contains incorrect assumptions, correct them briefly but politely.
- If the question was a structured thinking prompt, pay special attention to step-by-step reasoning, data structure choice, and complexity awareness.
- If the question was a real-world scenario, pay special attention to debugging mindset, prioritization, and trade-offs.
- assistant_reply should sound like micro-feedback during the interview: briefly acknowledge what went well and, if needed, mention one improvement point before moving on.
- Do not use markdown.
"""

    provider_used = session["providers"].get("evaluation_provider", "fallback")
    try:
        evaluation, provider_used = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            LIVE_AI_TIMEOUT_SECONDS,
        )
    except ProviderError:
        evaluation = _heuristic_evaluation(question, answer_text)
        provider_used = "fallback"

    session["providers"]["evaluation_provider"] = provider_used
    if provider_used != "fallback":
        heuristic_defaults = _heuristic_evaluation(question, answer_text)
        evaluation = _normalize_evaluation_payload(evaluation, heuristic_defaults)
        evaluation = _reconcile_evaluation_with_heuristic(evaluation, heuristic_defaults)
    evaluation = _tone_feedback(_feedback_style(session, question), evaluation, question, answer_text)

    if _should_retry_answer(session, question, answer_text, evaluation):
        await _persist_session(session)
        return _build_retry_answer_control_response(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
        )

    if (
        _normalize_text(state.get("selected_mode") or session.get("context", {}).get("selected_mode") or "").lower() == "language"
        and _normalize_text(question.get("interview_phase") or "") == "language_discovery"
    ):
        analysis, analysis_provider = await _analyze_discovery_answer(session, answer_text)
        _apply_discovery_analysis(state, analysis)
        session["providers"]["analysis_provider"] = analysis_provider

    _register_scored_turn(state, question)
    if (
        not _session_uses_time_mode(session)
        and int(state.get("scored_questions_answered", 0)) >= int(state.get("scored_question_target", 0))
    ):
        evaluation["assistant_reply"] = _adaptive_closing_message(session, question, evaluation)
        return _record_turn_result(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
            provider_used,
            next_question=None,
            is_complete=True,
        )

    if provider_used == "fallback":
        generated_question, provider = (
            _fallback_adaptive_question(session, question, evaluation, _next_adaptive_track(state)),
            "fallback",
        )
    else:
        generated_question, provider = await _generate_adaptive_question(session, question, answer_text, evaluation)
    session["providers"]["generation_provider"] = provider
    if not evaluation.get("honest_uncertainty"):
        evaluation["assistant_reply"] = _normalize_text(
            generated_question.get("assistant_reply") or evaluation.get("assistant_reply") or "Thanks. Let’s continue."
        )
    next_question = _append_session_question(
        session,
        {
            **generated_question,
            "count_towards_score": True,
        },
    )

    return _record_turn_result(
        session,
        question_index,
        question,
        answer_text,
        evaluation,
        provider_used,
        next_question=next_question,
        is_complete=False,
    )


def _extract_skills_from_resume(resume_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and structure skills from resume insights with importance weighting."""
    if not isinstance(resume_insights, dict):
        return []
    
    extracted = resume_insights.get("extracted", {})
    if not isinstance(extracted, dict):
        return []
    
    technical_skills = _safe_list(extracted.get("technical_skills", []))
    
    # Create skill objects with importance (lower number = higher importance)
    skills = []
    for idx, skill_name in enumerate(technical_skills):
        skill_name = _normalize_text(skill_name).strip()
        if not skill_name:
            continue
        
        # Assign importance: first few skills are more important
        if idx < 3:
            importance = 1  # Top importance
        elif idx < 6:
            importance = 2  # Medium importance
        else:
            importance = 3  # Lower importance
        
        skills.append({
            "name": skill_name,
            "importance": importance,
            "question_count": 3 if importance == 1 else (2 if importance == 2 else 1),
        })
    
    return skills


async def _evaluate_skill_based_adaptive_answer(
    session: Dict[str, Any],
    question_index: int,
    question: Dict[str, Any],
    answer_text: str
) -> Dict[str, Any]:
    """Evaluate answer and handle difficulty adjustment for skill-based adaptive interviews."""
    # Standard evaluation
    context_summary = _context_summary(session["context"])
    expected_points = question.get("expected_points", [])
    evaluation_focus = question.get("evaluation_focus", [])
    
    prompt = f"""
You are evaluating a technical interview answer about {question.get("skill", "a technical skill")}.

Expected to cover: {', '.join(expected_points)}
Evaluation focus: {', '.join(evaluation_focus)}

Answer: {answer_text}

Provide a score from 0-100 and feedback.

Return JSON:
{{
  "score": <0-100>,
  "feedback": "brief feedback",
  "strengths": ["strength1"],
  "gaps": ["gap1"],
  "matched_points": ["point1"],
  "missed_points": ["point1"],
  "suggested_answer": "brief suggestion",
  "assistant_reply": "brief reply",
  "relevance": <0-100>,
  "correctness": <0-100>,
  "clarity": <0-100>,
  "technical_depth": <0-100>
}}
"""
    
    try:
        if GEMINI_API_KEY:
            evaluation = await _call_gemini_json(prompt, timeout=LIVE_AI_TIMEOUT_SECONDS)
        else:
            evaluation = await _call_ollama_json(prompt, model=OLLAMA_MODEL, timeout=OLLAMA_TIMEOUT_SECONDS)
        provider_used = "gemini" if GEMINI_API_KEY else "ollama"
    except Exception:
        evaluation = _heuristic_evaluation(question, answer_text)
        provider_used = "fallback"
    
    score = int(evaluation.get("score", 50))
    
    # Update adaptive state
    adaptive_meta = session.get("meta", {}).get("adaptive_state", {})
    adaptive_state = adaptive_meta.get("state", {})
    
    if adaptive_state:
        # Track the score
        adaptive_state["scores"].append(score)
        adaptive_state["answers"].append(answer_text)
        
        # Adjust difficulty based on score
        current_difficulty = adaptive_state.get("current_difficulty", "medium")
        new_difficulty = _adjust_difficulty(current_difficulty, score)
        adaptive_state["current_difficulty"] = new_difficulty
        adaptive_state["difficulty_history"].append(new_difficulty)
        
        # Move to next question index
        adaptive_state["current_question_index"] = question_index + 1
    
    # Build result
    result = {
        "question_id": question["id"],
        "question": question["question"],
        "question_type": "technical",
        "answer": answer_text,
        "score": max(0, min(100, score)),
        "feedback": evaluation.get("feedback", ""),
        "strengths": evaluation.get("strengths", [])[:3],
        "gaps": evaluation.get("gaps", [])[:3],
        "matched_points": evaluation.get("matched_points", [])[:4],
        "missed_points": evaluation.get("missed_points", [])[:4],
        "suggested_answer": evaluation.get("suggested_answer", ""),
        "assistant_reply": evaluation.get("assistant_reply", ""),
        "relevance": evaluation.get("relevance", 50),
        "correctness": evaluation.get("correctness", 50),
        "clarity": evaluation.get("clarity", 50),
        "technical_depth": evaluation.get("technical_depth", 50),
        "provider": provider_used,
        "difficulty_adjusted_to": adaptive_state.get("current_difficulty", "medium") if adaptive_state else "medium",
    }
    
    # Store answer and evaluation
    answers = session.get("answers", [])
    evaluations = session.get("evaluations", [])
    
    if len(answers) > question_index:
        answers[question_index] = answer_text
    else:
        answers.append(answer_text)
    
    if len(evaluations) > question_index:
        evaluations[question_index] = result
    else:
        evaluations.append(result)
    
    # Check if interview is complete
    is_complete = question_index >= adaptive_state.get("total_questions", 10) - 1 if adaptive_state else False
    
    # Generate next question if not complete
    next_question = None
    next_question_type = None
    next_question_time = None
    
    if not is_complete:
        next_q_data = await _generate_skill_based_question(session, adaptive_state)
        next_question_time = next_q_data.get("time_limit_seconds", 60)
        
        # Add next question to session
        next_question_obj = {
            "id": str(uuid.uuid4()),
            "question": next_q_data.get("question", ""),
            "question_type": "technical",
            "difficulty": next_q_data.get("difficulty", "medium"),
            "skill": next_q_data.get("skill", ""),
            "expected_points": [next_q_data.get("skill", "")],
            "evaluation_focus": ["technical accuracy", "clarity", "depth"],
            "expected_keywords": next_q_data.get("expected_keywords", []),
            "time_limit_seconds": next_question_time,
        }
        session["questions"].append(next_question_obj)
        next_question = next_question_obj["question"]
        next_question_type = "technical"
    
    await _persist_session(session)
    
    return {
        **result,
        "question_index": question_index,
        "is_complete": is_complete,
        "next_question": next_question,
        "next_question_type": next_question_type,
        "next_question_time_seconds": next_question_time,
        "current_skill": adaptive_state.get("skills", [{}])[adaptive_state.get("current_skill_index", 0)].get("name", "") if adaptive_state else "",
        "providers": dict(session.get("providers", {})),
        "progress": {
            "current": question_index + 1,
            "total": adaptive_state.get("total_questions", 10) if adaptive_state else 10,
        },
        "difficulty_progression": adaptive_state.get("difficulty_history", []) if adaptive_state else [],
    }



def _calculate_dynamic_question_count(resume_insights: Dict[str, Any], experience_years: int = 0) -> int:
    """Calculate total question count based on skills, projects, and experience."""
    if not isinstance(resume_insights, dict):
        return 10
    
    extracted = resume_insights.get("extracted", {})
    if not isinstance(extracted, dict):
        return 10
    
    skills = _extract_skills_from_resume(resume_insights)
    
    # Base: sum of all skill question counts
    base_count = sum(s.get("question_count", 1) for s in skills)
    if base_count == 0:
        base_count = 10
    
    # Add bonus for projects
    projects = _safe_list(extracted.get("projects", []))
    project_bonus = 2 if len(projects) > 0 else 0
    
    # Add bonus for experience
    experience_bonus = 1 if experience_years > 0 else 0
    
    total = base_count + project_bonus + experience_bonus
    
    # Clamp between 6 and 20
    return max(6, min(20, total))


def _build_skill_rotation_queue(skills: List[Dict[str, Any]]) -> List[str]:
    """Build a random rotation queue of skills based on question count."""
    import random as random_module
    
    queue = []
    for skill in skills:
        skill_name = skill.get("name", "")
        count = skill.get("question_count", 1)
        queue.extend([skill_name] * count)
    
    # Shuffle randomly instead of cycling
    random_module.shuffle(queue)
    return queue


def _get_baseline_difficulty(experience: str) -> str:
    """Determine starting difficulty based on experience level."""
    value = (experience or "").strip().lower()
    if "fresh" in value or "entry" in value or "0 year" in value:
        return "easy"
    if "mid" in value or "1-2 year" in value or "2-3 year" in value:
        return "medium"
    return "medium"  # Default to medium


def _adjust_difficulty(current_difficulty: str, score: float) -> str:
    """Adjust difficulty based on answer score."""
    difficulty_levels = ["easy", "medium", "hard"]
    current_idx = difficulty_levels.index(current_difficulty) if current_difficulty in difficulty_levels else 1
    
    if score >= 80:  # Correct answer
        # Increase difficulty
        new_idx = min(current_idx + 1, 2)
    elif score < 50:  # Incorrect answer
        # Decrease difficulty
        new_idx = max(current_idx - 1, 0)
    else:  # Partial/medium answer (50-79)
        # Keep same difficulty
        new_idx = current_idx
    
    return difficulty_levels[new_idx]


def _get_time_limit_for_difficulty(difficulty: str) -> int:
    """Get time limit in seconds based on difficulty."""
    time_map = {
        "easy": 45,
        "medium": 60,
        "hard": 90,
    }
    return time_map.get(difficulty, 60)


def _build_adaptive_session_state(resume_insights: Dict[str, Any], experience: str) -> Dict[str, Any]:
    """Build initial adaptive session state."""
    skills = _extract_skills_from_resume(resume_insights)
    total_questions = _calculate_dynamic_question_count(resume_insights, 0)
    skill_queue = _build_skill_rotation_queue(skills)
    baseline_difficulty = _get_baseline_difficulty(experience)
    
    return {
        "adaptive_enabled": True,
        "skills": skills,
        "skill_queue": skill_queue,
        "total_questions": total_questions,
        "current_question_index": 0,
        "current_difficulty": baseline_difficulty,
        "baseline_difficulty": baseline_difficulty,
        "difficulty_history": [baseline_difficulty],
        "answers": [],
        "scores": [],
    }


async def _generate_skill_based_question(
    session: Dict[str, Any], 
    adaptive_state: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate next question based on current skill and difficulty."""
    current_idx = adaptive_state.get("current_question_index", 0)
    skill_queue = adaptive_state.get("skill_queue", [])
    current_difficulty = adaptive_state.get("current_difficulty", "medium")
    job_role = session.get("payload", {}).get("job_role", "")
    
    # Get next skill from queue
    current_skill = skill_queue[current_idx] if current_idx < len(skill_queue) else "General Concept"
    
    prompt = f"""
You are generating a technical interview question for skill-based assessment.

Context:
- Skill to ask about: {current_skill}
- Difficulty level: {current_difficulty}
- Job role: {job_role}
- Question number: {current_idx + 1} out of {len(skill_queue)}

Generate a single {current_difficulty} level question about {current_skill} relevant to the {job_role} role.

The question should be:
- {current_difficulty.upper()} difficulty
- Focused on {current_skill}
- Answerable in 45-120 seconds
- Practical and role-relevant

Return valid JSON:
{{
  "question": "the interview question text",
  "difficulty": "{current_difficulty}",
  "skill": "{current_skill}",
  "type": "technical",
  "expected_keywords": ["keyword1", "keyword2", "keyword3"],
  "time_limit_seconds": {_get_time_limit_for_difficulty(current_difficulty)},
  "assistant_reply": "Let's discuss {current_skill}."
}}
"""
    
    try:
        if GEMINI_API_KEY:
            result = await _call_gemini_json(prompt, timeout=LIVE_AI_TIMEOUT_SECONDS)
        else:
            result = await _call_ollama_json(prompt, model=OLLAMA_MODEL, timeout=OLLAMA_TIMEOUT_SECONDS)
        
        return result if isinstance(result, dict) else {
            "question": f"Tell me about {current_skill}.",
            "difficulty": current_difficulty,
            "skill": current_skill,
            "type": "technical",
            "expected_keywords": [current_skill],
            "time_limit_seconds": _get_time_limit_for_difficulty(current_difficulty),
            "assistant_reply": f"Let's discuss {current_skill}.",
        }
    except Exception as e:
        return {
            "question": f"Explain your experience with {current_skill} and how you've used it in projects.",
            "difficulty": current_difficulty,
            "skill": current_skill,
            "type": "technical",
            "expected_keywords": [current_skill],
            "time_limit_seconds": _get_time_limit_for_difficulty(current_difficulty),
            "assistant_reply": f"Let's explore {current_skill}.",
        }


async def create_interview_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Check for resume-based adaptive interview with skill extraction
    category = _normalize_text(payload.get("category") or "").lower()
    resume_insights = payload.get("resume_insights")
    if category == "resume" and isinstance(resume_insights, dict) and resume_insights.get("extracted"):
        # Use skill-based adaptive system for resume interviews
        adaptive_state = _build_adaptive_session_state(resume_insights, payload.get("experience") or "")
        
        # Override question_count with dynamic count based on skills
        dynamic_question_count = adaptive_state["total_questions"]
        payload = {**payload, "question_count": dynamic_question_count}
        
        # Create session ID and initial session
        session_id = str(uuid.uuid4())
        temp_session = {
            "session_id": session_id,
            "payload": payload,
            "context": {
                "job_role": payload.get("job_role", ""),
                "experience": payload.get("experience", ""),
            },
        }
        
        # Create proper session structure
        session = {
            "session_id": session_id,
            "payload": payload,
            "context": temp_session["context"],
            "meta": {
                "adaptive_state": {
                    "enabled": True,
                    "mode": "skill_based",
                    "state": adaptive_state,
                }
            },
            "questions": [],
            "answers": [],
            "evaluations": [],
            "providers": {
                "generation_provider": "gemini" if GEMINI_API_KEY else "ollama",
                "evaluation_provider": "fallback",
                "analysis_provider": "gemini" if GEMINI_API_KEY else "ollama",
            },
            "started_at": time.time(),
        }
        
        # Add INTRODUCTION question first (before technical questions)
        job_role = payload.get("job_role", "this role")
        candidate_name = payload.get("candidate_name", "")
        intro_question = {
            "id": str(uuid.uuid4()),
            "question": f"Please introduce yourself and tell me about your background, experience, and why you're interested in the {job_role} role.",
            "question_type": "introduction",
            "difficulty": "easy",
            "skill": "Self-Introduction",
            "expected_points": ["background", "experience", "motivation"],
            "evaluation_focus": ["communication", "clarity", "relevance"],
            "expected_keywords": ["experience", "background", "interested", "role"],
            "time_limit_seconds": 90,
        }
        session["questions"].append(intro_question)
        
        # Generate first technical question based on skill and difficulty
        first_question_data = await _generate_skill_based_question(temp_session, adaptive_state)
        
        # Add first technical question (after introduction)
        first_question = {
            "id": str(uuid.uuid4()),
            "question": first_question_data.get("question", ""),
            "question_type": "technical",
            "difficulty": first_question_data.get("difficulty", "medium"),
            "skill": first_question_data.get("skill", ""),
            "expected_points": [first_question_data.get("skill", "")],
            "evaluation_focus": ["technical accuracy", "clarity", "depth"],
            "expected_keywords": first_question_data.get("expected_keywords", []),
            "time_limit_seconds": first_question_data.get("time_limit_seconds", 60),
        }
        session["questions"].append(first_question)
        
        # Store session
        INTERVIEW_SESSIONS[session_id] = session
        await _persist_session(session)
        
        # Build opening greeting with candidate name
        first_name = _candidate_first_name(payload)
        greeting = f"Hi {first_name}, nice to meet you. " if first_name else "Hi, nice to meet you. "
        opening_greeting = (
            f"{greeting}I will be taking your resume-based skill adaptive interview for {job_role} today. "
            f"I have reviewed the profile signals extracted from your resume, and I will use your background to keep the conversation personalized, practical, and natural. "
            f"We will cover {dynamic_question_count} questions with adaptive difficulty based on your answers. "
            f"Let us keep this conversational, and feel free to think out loud. "
            f"Let's start with a quick introduction!"
        )
        
        return {
            "session_id": session_id,
            "status": "ready",
            "message": f"Resume-based skill adaptive interview ready. Total questions: {dynamic_question_count}",
            "adaptive_enabled": True,
            "skill_count": len(adaptive_state["skills"]),
            "skills": [s.get("name") for s in adaptive_state["skills"]],
            "total_questions": dynamic_question_count,
            "starting_difficulty": "easy",
            "assistant_intro": opening_greeting,
            "current_question": intro_question["question"],
            "current_skill": intro_question["skill"],
            "current_question_type": "introduction",
            "time_limit_seconds": intro_question["time_limit_seconds"],
            "provider_used": session["providers"]["generation_provider"],
            "time_limit_map": {
                "easy": 45,
                "medium": 60,
                "hard": 90
            }
        }
    
    # Standard logic for non-resume or resume without extraction
    question_count = _resolve_question_count(payload)
    payload = {**payload, "question_count": question_count}
    interview_variation = _build_interview_variation(payload)
    difficulty = _difficulty_from_experience(payload.get("experience") or "")
    target_subject = payload.get("primary_language") if payload.get("selected_mode") == "language" else payload.get("job_role")
    target_subject = target_subject or payload.get("job_role") or payload.get("primary_language") or "the selected interview focus"
    if _hr_adaptive_interview_enabled(payload):
        role_blueprint, blueprint_provider = await _infer_role_blueprint(payload)
        return await _create_hr_adaptive_interview_session(
            payload,
            question_count,
            difficulty,
            role_blueprint,
            blueprint_provider,
            interview_variation,
        )
    if _adaptive_role_interview_enabled(payload):
        role_blueprint, blueprint_provider = await _infer_role_blueprint(payload)
        return await _create_adaptive_interview_session(
            payload,
            question_count,
            difficulty,
            role_blueprint,
            blueprint_provider,
            interview_variation,
        )
    role_profile = _match_role_profile(payload.get("job_role") or "")
    role_blueprint, blueprint_provider = await _infer_role_blueprint(payload)
    role_profile_summary = ""
    if role_profile:
        role_profile_summary = (
            f"\nMatched role profile: {role_profile['label']}\n"
            f"Core fields to draw from: {', '.join(role_profile['core_fields'])}\n"
            f"Representative examples: {', '.join(role_profile['question_seeds'])}\n"
        )
    role_blueprint_summary = (
        f"\nInferred role blueprint label: {role_blueprint.get('role_label') or target_subject}\n"
        f"Inferred core areas: {', '.join(role_blueprint.get('core_areas') or [])}\n"
        f"Inferred tech stack: {', '.join(role_blueprint.get('tech_stack') or [])}\n"
        f"Inferred question focus: {', '.join(role_blueprint.get('question_focus') or [])}\n"
        f"Inferred language focus: {role_blueprint.get('language_focus') or 'None'}\n"
    )

    prompt = f"""
You are building a tailored AI interview plan.

Interview context:
{_context_summary(payload)}
{role_profile_summary}
{role_blueprint_summary}
Session variation:
{_variation_summary(interview_variation)}

Return valid JSON with this exact shape:
{{
  "assistant_intro": "short spoken welcome from the assistant",
  "questions": [
    {{
      "question": "interview question text",
      "question_type": "introduction | fundamental | conceptual | practical | scenario | behavioral",
      "expected_points": ["3 to 5 concise bullet-like points"],
      "evaluation_focus": ["3 concise criteria"]
    }}
  ]
}}

Rules:
- Generate exactly {question_count} questions.
- Questions must match the category, selected mode, target subject, experience level, configuration mode, and interview context.
- Treat the expected difficulty as {difficulty}.
- Target the interview around {target_subject}.
- Use the inferred role blueprint as the primary source for deciding tech stacks, concepts, frameworks, databases, tools, and question areas.
- Include a balanced progression of questions: introductory, conceptual/fundamental, practical, and scenario-based where relevant.
- For technical or language-oriented interviews, include fundamentals and conceptual understanding before harder applied questions.
- Use the selected options as direct focus areas when they are provided.
- If selected mode is role-based, ask role-oriented questions.
- If selected mode is language-based, ask language-oriented questions with practical coding or engineering emphasis where relevant.
- If a job role matches a known technical role profile, ask from that role's core tech stack and concepts only.
- If the job role is not a known profile, still generate role-specific questions using the role title, selected options, language, and inferred responsibilities.
- Do not ask HR questions, self-introduction questions, motivation questions, strengths/weaknesses questions, or behavioral questions.
- Prefer technical fundamentals, conceptual understanding, implementation questions, architecture questions, debugging questions, APIs, databases, networking, operating systems, cloud, testing, or security depending on the selected job role.
- If configuration mode is time mode, make the question set fit naturally within the selected time interval.
- If practice type is interview mode, keep questions realistic and progressively challenging.
- Keep expected_points practical enough to support approximate answer evaluation.
- Make this question set feel fresh for this session instead of repeating stock wording.
- Vary the angles across fundamentals, debugging, design, trade-offs, and practical examples when relevant.
- Avoid markdown.
"""

    provider_meta = {"generation_provider": "fallback", "evaluation_provider": "fallback", "analysis_provider": blueprint_provider}
    try:
        blueprint, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
            STARTUP_AI_TIMEOUT_SECONDS,
        )
        provider_meta["generation_provider"] = provider
    except ProviderError:
        blueprint = _default_questions(payload, interview_variation)

    assistant_intro = _normalize_text(blueprint.get("assistant_intro") or "")
    if not assistant_intro:
        assistant_intro = "Hello. I’m your AI interview assistant. Let’s begin whenever you’re ready."

    questions: List[Dict[str, Any]] = []
    for idx, raw_question in enumerate(blueprint.get("questions") or []):
        question_text = _normalize_text(raw_question.get("question") or "")
        if not question_text:
            continue
        questions.append(
            {
                "id": idx + 1,
                "question": question_text,
                "question_type": _safe_question_type(raw_question.get("question_type")),
                "expected_points": _safe_list(raw_question.get("expected_points"))[:5],
                "evaluation_focus": _safe_list(raw_question.get("evaluation_focus"))[:4],
            }
        )

    questions = questions[:question_count]

    if not questions:
        fallback = _default_questions(payload, interview_variation)
        assistant_intro = fallback["assistant_intro"]
        questions = [
            {
                "id": idx + 1,
                "question": item["question"],
                "question_type": _safe_question_type(item.get("question_type")),
                "expected_points": item["expected_points"],
                "evaluation_focus": item["evaluation_focus"],
            }
            for idx, item in enumerate(fallback["questions"])
        ]

    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "context": payload,
        "assistant_intro": assistant_intro,
        "questions": questions,
        "answers": [],
        "evaluations": [],
        "providers": provider_meta,
        "meta": {
            "difficulty": difficulty,
            "config_mode": payload.get("config_mode") or "question",
            "practice_type": payload.get("practice_type") or "practice",
            "interview_mode_time": payload.get("interview_mode_time"),
            "time_mode_interval": payload.get("time_mode_interval"),
            "selected_mode": payload.get("selected_mode"),
            "role_blueprint": role_blueprint,
            "interview_variation": interview_variation,
        },
        "question_outline": [
            {
                "id": question["id"],
                "question": question["question"],
                "question_type": question.get("question_type", "practical"),
            }
            for question in questions
        ],
        "saved_report_user_ids": [],
    }
    INTERVIEW_SESSIONS[session_id] = session
    await _persist_session(session)

    return {
        "session_id": session_id,
        "assistant_intro": assistant_intro,
        "total_questions": len(questions),
        "current_question": questions[0]["question"],
        "providers": provider_meta,
        "meta": session["meta"],
        "question_outline": session["question_outline"],
    }


async def evaluate_interview_answer(
    session_id: str,
    question_index: int,
    answer: str
) -> Dict[str, Any]:
    session = await _get_session(session_id)
    if not session:
        raise ProviderError("Interview session not found.")
    if _is_session_completed(session):
        raise ProviderError("Interview session is already complete.")

    questions = session["questions"]
    if question_index < 0 or question_index >= len(questions):
        raise ProviderError("Invalid question index.")

    question = questions[question_index]
    answer_text = _normalize_text(answer)
    session_meta = session.setdefault("meta", {})
    if session_meta.get("pending_end_confirmation"):
        confirmation_reply = _detect_confirmation_reply(answer_text)
        if confirmation_reply == "yes":
            session_meta.pop("pending_end_confirmation", None)
            await _persist_session(session)
            return _build_control_turn_response(
                session,
                question_index,
                question,
                "end_confirmed",
                assistant_reply="Understood. I will end the interview here and prepare your report.",
                next_question="",
                next_question_type=_normalize_text(question.get("question_type") or "practical"),
                answer_text=answer_text,
                should_end_interview=True,
            )
        if confirmation_reply == "no":
            session_meta.pop("pending_end_confirmation", None)
            await _persist_session(session)
            return _build_control_turn_response(
                session,
                question_index,
                question,
                "end_cancelled",
                assistant_reply="Alright, we will continue. Here is the current question again.",
                next_question=_normalize_text(question.get("question") or ""),
                next_question_type=_normalize_text(question.get("question_type") or "practical"),
                answer_text=answer_text,
            )
        return _build_control_turn_response(
            session,
            question_index,
            question,
            "end_confirm",
            assistant_reply="I just need a quick confirmation. Please say yes to end the interview or no to continue.",
            next_question="",
            next_question_type=_normalize_text(question.get("question_type") or "practical"),
            answer_text=answer_text,
        )

    if _detect_end_interview_request(answer_text):
        session_meta["pending_end_confirmation"] = {
            "question_index": question_index,
            "requested_at": time.time(),
        }
        await _persist_session(session)
        return _build_control_turn_response(
            session,
            question_index,
            question,
            "end_confirm",
            assistant_reply=(
                "I heard that you want to end the interview. "
                "Are you sure you want to end it? Please say yes to end the interview or no to continue."
            ),
            next_question="",
            next_question_type=_normalize_text(question.get("question_type") or "practical"),
            answer_text=answer_text,
        )

    control_command = _detect_interview_control_command(answer_text)
    if control_command:
        return _build_control_turn_response(session, question_index, question, control_command)
    off_topic_kind = _detect_off_topic_small_talk(answer_text)
    if off_topic_kind:
        return _build_off_topic_control_response(session, question_index, question, answer_text, off_topic_kind)
    adaptive_state = session.get("meta", {}).get("adaptive_state", {}) or {}
    if adaptive_state.get("enabled"):
        mode = _normalize_text(adaptive_state.get("mode") or "").lower()
        if mode == "skill_based":
            result = await _evaluate_skill_based_adaptive_answer(
                session,
                question_index,
                question,
                answer_text,
            )
        elif mode == "hr":
            result = await _evaluate_hr_adaptive_interview_answer(
                session,
                question_index,
                question,
                answer_text,
            )
        else:
            result = await _evaluate_adaptive_interview_answer(
                session,
                question_index,
                question,
                answer_text,
            )
        await _persist_session(session)
        return result

    context_summary = _context_summary(session["context"])
    expected_points = question.get("expected_points") or []
    evaluation_focus = question.get("evaluation_focus") or []

    prompt = f"""
You are evaluating a spoken interview answer using approximate semantic matching.

Interview context:
{context_summary}

Question:
{question["question"]}

Expected answer points:
{json.dumps(expected_points, ensure_ascii=False)}

Evaluation focus:
{json.dumps(evaluation_focus, ensure_ascii=False)}

Candidate answer:
{answer_text}

Return valid JSON:
{{
  "score": 0,
  "feedback": "2 to 4 sentence evaluation",
  "relevance": "Relevant | Partially Relevant | Not Relevant",
  "correctness": "Correct | Partially Correct | Incorrect",
  "clarity": "Clear | Needs Improvement",
  "technical_depth": "Good | Moderate | Weak",
  "logical_validity": "Logical | Partially Logical | Illogical",
  "real_world_applicability": "Applicable | Partially Applicable | Not Applicable",
  "strengths": ["up to 3 concise strengths"],
  "gaps": ["up to 3 concise gaps"],
  "matched_points": ["expected points that were covered"],
  "missed_points": ["expected points that were not covered"],
  "suggestions": ["up to 3 concise ways to improve"],
  "suggested_answer": "short improved answer guidance",
  "assistant_reply": "one short spoken response before the next question"
}}

Rules:
- Evaluate approximately, not by exact wording.
- Reward relevant meaning even if phrasing is imperfect.
- Be practical and interview-focused.
- If the answer is off-topic, say so gently and redirect to the topic.
- If the answer is vague, ask for more specificity.
- If the answer is too short, ask the candidate to expand on it.
- If the answer contains incorrect assumptions, correct them briefly but politely.
- Do not use markdown.
"""

    provider_used = session["providers"].get("evaluation_provider", "fallback")
    try:
        evaluation, provider_used = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
            LIVE_AI_TIMEOUT_SECONDS,
        )
    except ProviderError:
        evaluation = _heuristic_evaluation(question, answer_text)
        provider_used = "fallback"

    session["providers"]["evaluation_provider"] = provider_used

    if provider_used != "fallback":
        heuristic_defaults = _heuristic_evaluation(question, answer_text)
        evaluation = _normalize_evaluation_payload(evaluation, heuristic_defaults)
        evaluation = _reconcile_evaluation_with_heuristic(evaluation, heuristic_defaults)
    evaluation = _tone_feedback(_feedback_style(session, question), evaluation, question, answer_text)

    if _should_retry_answer(session, question, answer_text, evaluation):
        await _persist_session(session)
        return _build_retry_answer_control_response(
            session,
            question_index,
            question,
            answer_text,
            evaluation,
        )

    result = {
        "question_id": question["id"],
        "question": question["question"],
        "question_type": question.get("question_type", "practical"),
        "answer": answer_text,
        "score": max(0, min(100, int(evaluation["score"]))),
        "feedback": evaluation["feedback"],
        "strengths": evaluation["strengths"][:3],
        "gaps": evaluation["gaps"][:3],
        "matched_points": evaluation["matched_points"][:4],
        "missed_points": evaluation["missed_points"][:4],
        "suggested_answer": evaluation["suggested_answer"],
        "assistant_reply": evaluation["assistant_reply"],
        "relevance": evaluation["relevance"],
        "correctness": evaluation["correctness"],
        "clarity": evaluation["clarity"],
        "technical_depth": evaluation["technical_depth"],
        "logical_validity": evaluation["logical_validity"],
        "real_world_applicability": evaluation["real_world_applicability"],
        "suggestions": evaluation["suggestions"][:3],
        "provider": provider_used,
        "communication_score": _normalize_score_value(evaluation.get("communication_score")),
        "confidence_score": _normalize_score_value(evaluation.get("confidence_score")),
        "problem_solving_score": _normalize_score_value(evaluation.get("problem_solving_score")),
        "teamwork_score": _normalize_score_value(evaluation.get("teamwork_score")),
        "leadership_score": _normalize_score_value(evaluation.get("leadership_score")),
        "hr_readiness_score": _normalize_score_value(evaluation.get("hr_readiness_score")),
        "personality_attitude_score": _normalize_score_value(evaluation.get("personality_attitude_score")),
        "cultural_fit_score": _normalize_score_value(evaluation.get("cultural_fit_score")),
        "star_score": _normalize_score_value(evaluation.get("star_score")),
    }

    answers = session["answers"]
    evaluations = session["evaluations"]
    if len(answers) > question_index:
        answers[question_index] = answer_text
    else:
        answers.append(answer_text)

    if len(evaluations) > question_index:
        evaluations[question_index] = result
    else:
        evaluations.append(result)
    await _persist_session(session)

    is_complete = question_index >= len(questions) - 1
    next_question = None if is_complete else questions[question_index + 1]["question"]
    next_question_type = None if is_complete else questions[question_index + 1].get("question_type", "practical")

    return {
        **result,
        "question_index": question_index,
        "is_complete": is_complete,
        "next_question": next_question,
        "next_question_type": next_question_type,
        "providers": dict(session.get("providers", {})),
        "progress": {
            "current": question_index + 1,
            "total": len(questions),
        },
        "question_outline": session.get("question_outline", []),
    }


def _average_metric(evaluations: List[Dict[str, Any]], key: str) -> Optional[int]:
    values: List[int] = []
    for item in evaluations:
        score = _normalize_score_value(item.get(key))
        if score is not None:
            values.append(score)
    if not values:
        return None
    return int(round(sum(values) / len(values)))


def _build_hr_score_breakdown(session: Dict[str, Any]) -> Optional[Dict[str, int]]:
    evaluations = _scored_evaluations(session)
    breakdown = {
        "communication": _average_metric(evaluations, "communication_score"),
        "confidence": _average_metric(evaluations, "confidence_score"),
        "problem_solving": _average_metric(evaluations, "problem_solving_score"),
        "teamwork": _average_metric(evaluations, "teamwork_score"),
        "leadership": _average_metric(evaluations, "leadership_score"),
        "hr_readiness": _average_metric(evaluations, "hr_readiness_score"),
        "personality_attitude": _average_metric(evaluations, "personality_attitude_score"),
        "cultural_fit": _average_metric(evaluations, "cultural_fit_score"),
        "star_structure": _average_metric(evaluations, "star_score"),
    }
    return {key: value for key, value in breakdown.items() if value is not None} or None


def _determine_proficiency_level(score: int) -> str:
    """Determine proficiency level based on score: Beginner (0-50), Intermediate (51-85), Expert (86-100)"""
    if score <= 50:
        return "Beginner"
    elif score <= 85:
        return "Intermediate"
    else:
        return "Expert"


def _build_skill_wise_breakdown(session: Dict[str, Any]) -> Dict[str, Any]:
    """Build skill-wise performance breakdown for adaptive resume interviews."""
    evaluations = _scored_evaluations(session)
    adaptive_state = session.get("meta", {}).get("adaptive_state") or {}
    
    # Group evaluations by skill
    skills_data = {}
    for evaluation in evaluations:
        skill = evaluation.get("skill", "General")
        if skill not in skills_data:
            skills_data[skill] = []
        skills_data[skill].append(evaluation)
    
    # Build skill breakdown
    skills_breakdown = {}
    for skill, skill_evaluations in skills_data.items():
        if not skill_evaluations:
            continue
            
        # Calculate score
        skill_score = int(round(sum(e["score"] for e in skill_evaluations) / len(skill_evaluations)))
        
        # Get difficulty progression
        difficulty_progression = []
        for i, eval_item in enumerate(skill_evaluations):
            # Try to get difficulty from adaptive state history or estimate from order
            difficulty = "Medium"  # Default
            if adaptive_state and i < len(adaptive_state.get("difficulty_progression", [])):
                difficulty = adaptive_state["difficulty_progression"][i]
            difficulty_progression.append(difficulty)
        
        # Extract strengths and weaknesses from feedback
        strengths = []
        weaknesses = []
        for eval_item in skill_evaluations:
            if eval_item.get("strengths"):
                strengths.extend(_safe_list(eval_item.get("strengths")))
            if eval_item.get("gaps"):
                weaknesses.extend(_safe_list(eval_item.get("gaps")))
        
        # Remove duplicates while preserving order
        strengths = list(dict.fromkeys(strengths))[:3]
        weaknesses = list(dict.fromkeys(weaknesses))[:3]
        
        # Determine performance rating
        if skill_score >= 75:
            performance = "Strong"
        elif skill_score >= 60:
            performance = "Moderate"
        else:
            performance = "Needs Work"
        
        proficiency = _determine_proficiency_level(skill_score)
        
        skills_breakdown[skill] = {
            "score": skill_score,
            "proficiency": proficiency,
            "difficulty_progression": difficulty_progression,
            "questions_count": len(skill_evaluations),
            "performance": performance,
            "strengths": strengths if strengths else (
                [f"Some partial understanding of {skill} was visible."]
                if skill_score >= 50
                else [f"No reliable strength in {skill} was demonstrated yet."]
            ),
            "weaknesses": weaknesses if weaknesses else [f"Further practice with {skill} needed"],
            "recommendation": _generate_skill_recommendation(skill, skill_score, proficiency),
        }
    
    # Identify top and weakest skills
    sorted_skills = sorted(skills_breakdown.items(), key=lambda x: x[1]["score"], reverse=True)
    top_skills = [skill for skill, _ in sorted_skills[:3]]
    weakest_skills = [skill for skill, _ in sorted_skills[-3:][::-1]]
    
    # Calculate adaptive insights
    avg_score = int(round(sum(e["score"] for e in evaluations) / len(evaluations))) if evaluations else 0
    avg_difficulty = "Medium"
    if adaptive_state and adaptive_state.get("difficulty_progression"):
        difficulty_counts = {}
        for diff in adaptive_state["difficulty_progression"]:
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        avg_difficulty = max(difficulty_counts, key=difficulty_counts.get)
    
    return {
        "skills_breakdown": skills_breakdown,
        "top_skills": top_skills,
        "weakest_skills": weakest_skills,
        "overall_score": avg_score,
        "avg_difficulty_reached": avg_difficulty,
        "total_evaluations": len(evaluations),
    }


def _generate_skill_recommendation(skill: str, score: int, proficiency: str) -> str:
    """Generate skill-specific learning recommendation."""
    recommendations = {
        "Beginner": f"Start with fundamentals of {skill}. Build a strong foundation through tutorials and simple projects.",
        "Intermediate": f"Deepen your {skill} expertise. Work on advanced patterns, optimization, and real-world applications.",
        "Expert": f"You have strong {skill} skills. Focus on emerging trends and advanced architectural patterns.",
    }
    return recommendations.get(proficiency, f"Continue improving your {skill} skills.")


def _unique_report_items(values: List[str], limit: int = 3) -> List[str]:
    cleaned: List[str] = []
    seen = set()
    generic_strengths = {
        "you provided a direct spoken response to the question",
        "completed the interview flow with spoken responses",
        "you completed the full hr interview flow with spoken responses",
        "completed adaptive interview with progressive difficulty",
    }
    for value in values:
        item = _normalize_text(value)
        if not item:
            continue
        key = item.rstrip(".").lower()
        if key in seen or key in generic_strengths:
            continue
        seen.add(key)
        cleaned.append(item.rstrip(".") + ".")
        if len(cleaned) >= limit:
            break
    return cleaned


def _fallback_summary(session: Dict[str, Any], ended_early: bool = False) -> Dict[str, Any]:
    evaluations = _scored_evaluations(session)
    if evaluations:
        average_score = int(round(sum(item["score"] for item in evaluations) / len(evaluations)))
    else:
        average_score = 0

    strong_answers = [
        item["question"]
        for item in evaluations
        if item["score"] >= 75
    ][:3]
    weak_answers = [
        item["question"]
        for item in evaluations
        if item["score"] < 60
    ][:3]
    answered = len(evaluations)
    total = _session_total_questions(session)
    completion_note = (
        f"This report is based on {answered} evaluated answer{'s' if answered != 1 else ''}"
        f" out of {total} planned question{'s' if total != 1 else ''}."
        if total
        else f"This report is based on {answered} evaluated answer{'s' if answered != 1 else ''}."
    )
    if ended_early:
        completion_note += " The interview ended early, so the report reflects only the answers captured before ending."

    strengths_from_answers: List[str] = []
    for item in evaluations:
        if int(item.get("score", 0) or 0) >= 60:
            strengths_from_answers.extend(_safe_list(item.get("strengths")))
            strengths_from_answers.extend([f"Covered: {point}" for point in _safe_list(item.get("matched_points"))[:2]])

    improvements_from_answers: List[str] = []
    for item in evaluations:
        improvements_from_answers.extend(_safe_list(item.get("gaps")))
        improvements_from_answers.extend(_safe_list(item.get("suggestions")))
        improvements_from_answers.extend([f"Review: {point}" for point in _safe_list(item.get("missed_points"))[:2]])

    top_strengths = _unique_report_items(strengths_from_answers, 3)
    if not top_strengths:
        if evaluations and average_score < 40:
            top_strengths = ["No reliable interview strength was demonstrated yet from the evaluated answers."]
        elif evaluations:
            top_strengths = ["Some answers showed partial direction, but they need clearer evidence before calling them a strength."]
        else:
            top_strengths = ["No evaluated answers were captured, so strengths cannot be measured yet."]

    improvement_areas = _unique_report_items(improvements_from_answers, 3)
    if not improvement_areas:
        improvement_areas = [
            "Answer the exact question in clear sentences.",
            "Add one concrete example, step, result, or technical detail.",
            "Avoid filler, random text, or incomplete responses.",
        ]

    if not evaluations:
        summary_text = (
            f"{completion_note} No scored answers were available, so the system cannot make a reliable performance claim. "
            "Complete at least a few questions with clear answers to receive accurate strengths, gaps, and scoring."
        )
    elif average_score < 40:
        summary_text = (
            f"{completion_note} The captured answers were mostly unclear, irrelevant, incomplete, or not meaningful enough for a strong interview evaluation. "
            "The priority is to answer directly in complete sentences, then add one concrete example or technical detail."
        )
    elif average_score < 60:
        summary_text = (
            f"{completion_note} The session shows weak to partial performance. "
            "Some intent may be visible, but the answers need stronger relevance, structure, and specific evidence."
        )
    elif average_score < 75:
        summary_text = (
            f"{completion_note} The session shows a moderate base. "
            "To improve, make each answer more structured, role-specific, and supported by examples or trade-offs."
        )
    else:
        summary_text = (
            f"{completion_note} The session shows strong performance across the evaluated answers. "
            "Keep adding precise examples, measurable outcomes, and deeper reasoning to make the report even stronger."
        )

    if _normalize_text(session.get("context", {}).get("category") or "").lower() == "hr":
        score_breakdown = _build_hr_score_breakdown(session)
        return {
            "overall_score": average_score,
            "summary": summary_text,
            "top_strengths": top_strengths,
            "improvement_areas": improvement_areas,
            "strongest_questions": strong_answers,
            "needs_work_questions": weak_answers,
            "score_breakdown": score_breakdown,
        }

    return {
        "overall_score": average_score,
        "summary": summary_text,
        "top_strengths": top_strengths,
        "improvement_areas": improvement_areas,
        "strongest_questions": strong_answers,
        "needs_work_questions": weak_answers,
    }


async def complete_interview_session(session_id: str, ended_early: bool = False) -> Dict[str, Any]:
    session = await _get_session(session_id)
    if not session:
        raise ProviderError("Interview session not found.")
    is_hr_session = _normalize_text(session.get("context", {}).get("category") or "").lower() == "hr"

    if _is_session_completed(session):
        cached_summary = dict(session.get("summary") or {})
        existing_ended_early = bool(session.get("ended_early", False))
        resolved_ended_early = bool(ended_early or existing_ended_early)
        session["ended_early"] = resolved_ended_early
        await _persist_session(session)
        adaptive_state = session.get("meta", {}).get("adaptive_state") or {}
        evaluations = _scored_evaluations(session)
        return {
            **cached_summary,
            "session_id": session_id,
            "ended_early": resolved_ended_early,
            "questions_answered": len(session.get("evaluations", [])),
            "total_questions": _session_total_questions(session),
            "questions": [
                {
                    "question": item["question"],
                    "question_type": item.get("question_type", "practical"),
                    "score": item["score"],
                }
                for item in evaluations
            ],
            "providers": session.get("providers", {}),
        }

    evaluations = _scored_evaluations(session)
    context_summary = _context_summary(session.get("context", {}))
    adaptive_state = session.get("meta", {}).get("adaptive_state") or {}
    
    # Check if this is a resume interview with adaptive mode enabled
    is_resume_adaptive = (
        _normalize_text(session.get("context", {}).get("category") or "").lower() == "resume"
        and adaptive_state.get("enabled")
    )
    
    if is_resume_adaptive:
        # Use skill-wise report for adaptive resume interviews
        skill_wise_data = _build_skill_wise_breakdown(session)
        job_role = session.get('context', {}).get('job_role', 'Target Role')
        
        # Generate AI summary for skill-wise report
        prompt = f"""
You are summarizing a skill-based adaptive interview where the candidate was tested on multiple technical skills with progressive difficulty.

Interview context: {job_role}
Skills tested: {', '.join(skill_wise_data['skills_breakdown'].keys())}
Overall performance: {skill_wise_data['overall_score']}/100
Average difficulty reached: {skill_wise_data['avg_difficulty_reached']}

Skill breakdown:
{json.dumps({k: {'score': v['score'], 'proficiency': v['proficiency'], 'performance': v['performance']} for k, v in skill_wise_data['skills_breakdown'].items()}, ensure_ascii=False)}

Top 3 skills: {', '.join(skill_wise_data['top_skills'])}
Needs work: {', '.join(skill_wise_data['weakest_skills'])}

Per-question evaluations:
{json.dumps(evaluations, ensure_ascii=False)}

Return valid JSON:
{{
  "summary": "3 to 4 sentence summary focusing on technical skill proficiency and adaptive learning curve",
  "top_strengths": ["up to 3 key technical strengths"],
  "improvement_areas": ["up to 3 key technical areas needing improvement"],
  "strongest_questions": ["question texts with best performance"],
  "needs_work_questions": ["question texts with lowest performance"]
}}
"""
        
        try:
            summary_ai, provider = await _generate_json_with_fallback(
                prompt,
                ["gemini", "ollama"],
                0.2,
                LIVE_AI_TIMEOUT_SECONDS,
            )
        except ProviderError:
            summary_ai = {}
            provider = "fallback"
        
        # Build skill-wise report
        grounded_summary = _fallback_summary(session, ended_early=ended_early)
        summary = {
            "overall_score": skill_wise_data["overall_score"],
            "summary": grounded_summary["summary"],
            "top_strengths": grounded_summary["top_strengths"],
            "improvement_areas": grounded_summary["improvement_areas"],
            "strongest_questions": grounded_summary["strongest_questions"],
            "needs_work_questions": grounded_summary["needs_work_questions"],
            "interview_type": "resume_adaptive",
            "skills_breakdown": skill_wise_data["skills_breakdown"],
            "top_skills": skill_wise_data["top_skills"],
            "weakest_skills": skill_wise_data["weakest_skills"],
            "avg_difficulty_reached": skill_wise_data["avg_difficulty_reached"],
            "adaptive_insights": {
                "total_evaluations": skill_wise_data["total_evaluations"],
                "learning_curve": "Consistent progression" if skill_wise_data["avg_difficulty_reached"] in ["Hard", "Medium"] else "Building foundation",
            }
        }
    else:
        # Standard report for non-adaptive interviews
        adaptive_summary = ""
        if adaptive_state.get("enabled"):
            adaptive_summary = f"\nDiscovered candidate profile:\n{_adaptive_state_summary(adaptive_state)}\n"
        prompt = f"""
You are summarizing an AI interview session.

Interview context:
{context_summary}
{adaptive_summary}

Per-question evaluations:
{json.dumps(evaluations, ensure_ascii=False)}

Return valid JSON:
{{
  "overall_score": 0,
  "summary": "3 to 5 sentence overall interview summary",
  "top_strengths": ["up to 3 concise strengths"],
  "improvement_areas": ["up to 3 concise areas to improve"],
  "strongest_questions": ["question texts with best performance"],
  "needs_work_questions": ["question texts with lowest performance"]
}}
"""

        try:
            summary, provider = await _generate_json_with_fallback(
                prompt,
                ["gemini", "ollama"],
                0.2,
                LIVE_AI_TIMEOUT_SECONDS,
            )
        except ProviderError:
            summary = _fallback_summary(session, ended_early=ended_early)
            provider = "fallback"

        if provider != "fallback":
            fallback = _fallback_summary(session, ended_early=ended_early)
            summary = {
                "overall_score": fallback["overall_score"],
                "summary": fallback["summary"],
                "top_strengths": fallback["top_strengths"],
                "improvement_areas": fallback["improvement_areas"],
                "strongest_questions": fallback["strongest_questions"],
                "needs_work_questions": fallback["needs_work_questions"],
            }
            if is_hr_session:
                summary["score_breakdown"] = fallback.get("score_breakdown") or _build_hr_score_breakdown(session)
        elif is_hr_session and "score_breakdown" not in summary:
            summary["score_breakdown"] = _build_hr_score_breakdown(session)

    session["summary"] = summary
    session["ended_early"] = bool(ended_early)
    session["completed_at"] = time.time()
    session["providers"]["summary_provider"] = provider
    await _persist_session(session)
    return {
        **summary,
        "session_id": session_id,
        "ended_early": bool(ended_early),
        "questions_answered": len(session.get("evaluations", [])),
        "total_questions": _session_total_questions(session),
        "questions": [
            {
                "question": item["question"],
                "question_type": item.get("question_type", "practical"),
                "score": item["score"],
            }
            for item in evaluations
        ],
        "providers": session["providers"],
    }


async def get_session_payload(session_id: str) -> Optional[Dict[str, Any]]:
    return await _get_session(session_id)


async def get_session_status(session_id: str) -> Optional[Dict[str, Any]]:
    session = await _get_session(session_id)
    if not session:
        return None
    return _build_session_status_payload(session)


async def mark_session_report_saved(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    session = await _get_session(session_id)
    normalized_user_id = _normalize_text(user_id)
    if not session or not normalized_user_id:
        return session

    saved_user_ids = session.setdefault("saved_report_user_ids", [])
    if normalized_user_id not in saved_user_ids:
        saved_user_ids.append(normalized_user_id)
        await _persist_session(session)
    return session
