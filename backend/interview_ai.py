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


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _clamp_question_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 10
    return max(10, min(count, 30))


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
        f"Question count: {_clamp_question_count(payload.get('question_count'))}",
    ]
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
    return value if value in {"technical", "hr_behavioral", "both"} else "hr_behavioral"


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
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "response_mime_type": "application/json",
        },
    }
    data = await asyncio.to_thread(_http_post_json, url, payload, None, timeout_seconds or 80)
    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(part.get("text", "") for part in parts)
    return _extract_json_block(text)


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


def _heuristic_evaluation(question: Dict[str, Any], answer: str) -> Dict[str, Any]:
    answer_text = _normalize_text(answer)
    expected_points = _safe_list(question.get("expected_points"))
    keywords = _keyword_set(expected_points)
    answer_lower = answer_text.lower()

    matched_keywords = [kw for kw in keywords if kw in answer_lower]
    coverage = len(matched_keywords) / max(len(keywords), 1)
    length_bonus = min(len(answer_text.split()) / 80, 1.0)
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
        gaps.append("Your answer was quite short and could use more specifics.")

    suggested_answer = (
        "A stronger answer would briefly give context, explain your actions clearly, "
        "and end with the result or lesson learned."
    )

    word_count = len(answer_text.split())
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

    relevance = "Not Relevant" if off_topic else ("Partially Relevant" if coverage < 0.45 else "Relevant")
    correctness = "Incorrect" if coverage < 0.18 else ("Partially Correct" if coverage < 0.65 else "Correct")
    clarity = "Needs Improvement" if word_count < 16 else "Clear"
    technical_depth = "Weak" if word_count < 18 or coverage < 0.25 else ("Moderate" if coverage < 0.7 else "Good")
    logical_validity = "Illogical" if off_topic else ("Partially Logical" if coverage < 0.55 else "Logical")
    real_world_applicability = (
        "Applicable" if has_real_world_marker and coverage >= 0.45
        else "Partially Applicable" if has_real_world_marker or coverage >= 0.28
        else "Not Applicable"
    )

    topic_label = _normalize_text(question.get("topic_tag") or question.get("question_type") or "the topic")
    suggestions = []
    if off_topic:
        suggestions.append(f"Focus directly on {topic_label} before adding extra context.")
    if word_count < 16:
        suggestions.append("Expand your answer with one concrete example or implementation detail.")
    if missed_points:
        suggestions.append("Cover the main expected points in a clearer order.")
    if not has_real_world_marker:
        suggestions.append("Tie your answer to a real project, trade-off, or production scenario.")
    suggestions = suggestions[:3]

    if off_topic:
        assistant_reply = f"That is slightly off-topic. Let us focus on {topic_label}."
    elif word_count < 10:
        assistant_reply = "Can you expand on that?"
    elif word_count < 18 or coverage < 0.28:
        assistant_reply = "Can you be more specific?"
    elif score >= 80:
        assistant_reply = "Interesting. Let us explore that a little further."
    else:
        assistant_reply = "Alright, let us continue."

    if not answer_text:
        feedback = "I could not capture a clear answer. Please answer directly, stay on the topic, and add one real example."
    elif off_topic:
        feedback = (
            f"Your response drifted away from {topic_label}. Start by answering the exact question, "
            "then support it with one relevant technical example."
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
    word_count = len(answer_text.split())

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

    if word_count < 14:
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


def _build_hr_phase_plan(question_count: int) -> List[str]:
    if question_count <= 3:
        return ["introduction", "behavioral", "closing"]
    if question_count == 4:
        return ["introduction", "motivation", "situational", "closing"]
    if question_count == 5:
        return ["introduction", "background", "behavioral", "situational", "closing"]
    if question_count == 6:
        return ["introduction", "background", "motivation", "behavioral", "situational", "closing"]
    if question_count == 7:
        return ["introduction", "background", "motivation", "behavioral", "behavioral", "situational", "closing"]

    plan = ["introduction", "background", "motivation", "behavioral", "behavioral", "communication", "situational", "closing"]
    while len(plan) < question_count:
        plan.insert(-2, "behavioral")
    return plan[: question_count - 1] + ["closing"]


def _build_focus_plan(focus_areas: List[str], question_count: int) -> List[str]:
    cleaned = [item for item in _safe_list(focus_areas) if item]
    if not cleaned:
        cleaned = ["Communication", "Leadership", "Problem-solving", "Teamwork", "Confidence"]
    return [cleaned[index % len(cleaned)] for index in range(question_count)]


def _build_hr_adaptive_state(payload: Dict[str, Any], question_count: int) -> Dict[str, Any]:
    focus_areas = _selected_focus_areas(payload)
    resolved_focus_areas = focus_areas or ["Communication", "Leadership", "Problem-solving", "Teamwork", "Confidence"]
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
        "round_mode": _hr_round_mode(payload),
        "phase_plan": _build_hr_phase_plan(question_count),
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
    if category not in {"technical", "mock"}:
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


def _build_technical_phase_plan(question_count: int) -> List[str]:
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
    if word_count > 10:
        return None

    repeat_patterns = [
        r"^repeat$",
        r"^repeat again$",
        r"^repeat question$",
        r"^repeat the question$",
        r"^say again$",
        r"^say that again$",
        r"^say the question again$",
        r"^can you repeat$",
        r"^can you repeat that$",
        r"^can you repeat the question$",
        r"^could you repeat that$",
        r"^please repeat$",
        r"^please repeat that$",
        r"^please repeat the question$",
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
        r"^(i )?can't understand$",
        r"^(i )?can't understand the question$",
        r"^can you explain$",
        r"^can you explain that$",
        r"^can you explain the question$",
        r"^could you explain$",
        r"^could you explain that$",
        r"^could you explain the question$",
        r"^please explain$",
        r"^please explain the question$",
        r"^clarify$",
        r"^clarify the question$",
        r"^simplify$",
        r"^simplify the question$",
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
        f"{opener} In a real interview, going off-topic weakens your answer and shows poor focus. "
        f"Please answer the current question about {topic_label} directly."
    )
    feedback = (
        f"Your response was not relevant to the question. In a real interview, this would be treated as poor focus and a weak answer. "
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
    include_hr = category == "mock"
    hr_target = 0 if not include_hr else (1 if question_count <= 5 else 2)
    technical_target = max(1, question_count - hr_target)
    return {
        "enabled": True,
        "include_hr": include_hr,
        "selected_mode": selected_mode or ("language" if primary_language else "role"),
        "scored_question_target": question_count,
        "technical_question_target": technical_target,
        "discovery_questions_asked": 1,
        "clarification_turns": 0,
        "discovery_complete": False,
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
        "technical_phase_plan": _build_technical_phase_plan(technical_target),
        "last_phase": "",
    }


def _adaptive_intro(payload: Dict[str, Any], question_count: int) -> str:
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    role = _normalize_text(payload.get("job_role") or "the selected role")
    language = _normalize_text(payload.get("primary_language") or "the selected language")
    category = _normalize_text(payload.get("category") or "").lower()
    subject = language if selected_mode == "language" and language else role
    if category == "mock":
        return (
            f"Hi, nice to meet you. I will be taking your {subject} mock interview today. "
            "Let us keep this conversational, and feel free to think out loud. "
            "I will first understand where you are strongest, then I will adapt the interview one question at a time. "
            "Because this is a mock round, I may include a short behavioral section near the end as well."
        )
    return (
        f"Hi, nice to meet you. I will be taking your {subject} technical interview today. "
        "Let us keep this conversational, and feel free to think out loud. "
        "I will first confirm the technical area you want to focus on, then I will adapt the next questions based on your answers. "
        f"I will keep the interview technical and tailor the next {question_count} scored questions to your strengths."
    )


def _adaptive_discovery_question(payload: Dict[str, Any], variation: Optional[Dict[str, str]] = None) -> str:
    role = _normalize_text(payload.get("job_role") or "this role")
    selected_mode = _normalize_text(payload.get("selected_mode") or "").lower()
    language = _normalize_text(payload.get("primary_language") or "")
    role_lower = role.lower()
    shuffler = random.Random(_normalize_text((variation or {}).get("seed") or role or language or "adaptive"))
    if selected_mode == "language" and language:
        options = [
            f"Before we begin properly, what kinds of {language} problems, projects, or fundamentals are you most comfortable discussing today?",
            f"To tailor this {language} round well, which parts of {language} do you feel strongest in from real work or practice?",
            f"To get the interview aligned properly, what have you used {language} for most confidently so far?",
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
    if _normalize_text(state.get("mode") or "").lower() == "hr":
        return max(
            len(session.get("questions", [])),
            int(state.get("scored_question_target", 0)),
        )
    return max(
        len(session.get("questions", [])),
        int(state.get("scored_question_target", 0)) + max(1, int(state.get("discovery_questions_asked", 1))),
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
    elif selected_mode == "language" and preferred_language and not frameworks and not databases and not tools:
        needs_clarification = True
        clarification_question = (
            f"Within {preferred_language}, which areas should I focus on first: fundamentals, debugging, problem solving, APIs, or project experience?"
        )
    elif not languages and not frameworks:
        needs_clarification = True
        clarification_question = (
            "Which backend language or framework would you like me to focus on first, and what stack have you actually used?"
        )

    focus_areas = _merge_unique(frameworks, databases)
    focus_areas = _merge_unique(focus_areas, tools)
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
    candidates: List[str] = []
    candidates = _merge_unique(candidates, state.get("frameworks") or [])
    candidates = _merge_unique(candidates, state.get("databases") or [])
    candidates = _merge_unique(candidates, state.get("tools") or [])
    candidates = _merge_unique(candidates, [state.get("preferred_language") or ""])
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
    covered = {item.lower() for item in state.get("covered_topics") or []}
    last_topic = _normalize_text((last_question or {}).get("topic_tag") or "")
    for candidate in _adaptive_focus_candidates(session, last_question):
        lowered = candidate.lower()
        if lowered not in covered and lowered != last_topic.lower():
            return candidate
    return last_topic or _normalize_text(state.get("preferred_language") or "") or _normalize_text(session.get("context", {}).get("job_role") or "backend fundamentals")


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
        topic_label = topic or preferred_language or "your strongest technical area"
        return {
            "assistant_reply": "Thanks. Let us start with something simple and settle into the conversation.",
            "question": (
                f"Can you explain one core concept in {topic_label} that you are comfortable with, "
                "and give a small real example of where you would use it?"
            ),
            "question_type": "fundamental",
            "expected_points": [
                "clear definition in simple terms",
                "main purpose or behavior",
                "one concrete example",
                "confident and structured explanation",
            ],
            "evaluation_focus": ["clarity", "confidence", "fundamentals"],
            "topic_tag": topic_label,
            "interview_phase": phase,
        }

    if phase == "concept_deep_dive":
        if score < 55:
            return {
                "assistant_reply": "You are on the right track. Let us keep it concrete and stay with the same topic for a moment.",
                "question": (
                    f"No problem. Can you give me one real example of using {topic}, what problem it solved, "
                    "and why you chose that approach?"
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
        return {
            "assistant_reply": "Good. Let us go one level deeper on that.",
            "question": (
                f"How is {topic} different from the closest alternative you would compare it with, "
                "and when would you choose one over the other in a real system?"
            ),
            "question_type": "conceptual",
            "expected_points": [
                "clear comparison",
                "important trade-offs",
                "real usage choice",
                "structured reasoning",
            ],
            "evaluation_focus": ["conceptual depth", "trade-offs", "clarity"],
            "topic_tag": topic,
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
- If selected mode is language-based, ask which projects, problem types, or areas of that language they are most comfortable with.
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
            "count_towards_score": False,
            "topic_tag": opening_turn["topic_tag"],
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
    round_mode = _hr_round_mode(payload).replace("_", " / ")
    focus = ", ".join(_selected_focus_areas(payload)[:3]) or "communication, leadership, and problem-solving"
    return (
        f"Hi! Nice to meet you. I will be taking your {round_mode} interview for a {role} candidate today. "
        f"We will cover about {question_count} tailored questions with extra attention on {focus}."
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

    _register_scored_turn(state, question)
    if int(state.get("scored_questions_answered", 0)) >= int(state.get("scored_question_target", 0)):
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

    _register_scored_turn(state, question)
    if int(state.get("scored_questions_answered", 0)) >= int(state.get("scored_question_target", 0)):
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


async def create_interview_session(payload: Dict[str, Any]) -> Dict[str, Any]:
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
        if _normalize_text(adaptive_state.get("mode") or "").lower() == "hr":
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


def _fallback_summary(session: Dict[str, Any]) -> Dict[str, Any]:
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

    if _normalize_text(session.get("context", {}).get("category") or "").lower() == "hr":
        score_breakdown = _build_hr_score_breakdown(session)
        return {
            "overall_score": average_score,
            "summary": (
                "You completed the HR interview. Keep strengthening structure, specific examples, and measurable outcomes "
                "so your communication sounds more interview-ready."
            ),
            "top_strengths": [
                "You completed the full HR interview flow with spoken responses.",
                "You gave relevant examples tied to your experience and role direction.",
                "You showed willingness to explain decisions, teamwork, and outcomes.",
            ],
            "improvement_areas": [
                "Use clearer STAR structure in behavioral answers.",
                "Add stronger outcomes, numbers, or lessons learned.",
                "Keep answers specific instead of generic or overly broad.",
            ],
            "strongest_questions": strong_answers,
            "needs_work_questions": weak_answers,
            "score_breakdown": score_breakdown,
        }

    return {
        "overall_score": average_score,
        "summary": (
            "You completed the interview. Focus on clearer structure, stronger examples, "
            "and tighter role alignment to improve further."
        ),
        "top_strengths": [
            "Completed the interview flow with spoken responses.",
            "Covered several expected points across the session.",
            "Showed willingness to explain experience verbally.",
        ],
        "improvement_areas": [
            "Make answers more specific and evidence-based.",
            "Use a clearer situation-action-result structure.",
            "Tie each answer back to the target role or language.",
        ],
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
        summary = _fallback_summary(session)
        provider = "fallback"

    if provider != "fallback":
        fallback = _fallback_summary(session)
        summary = {
            "overall_score": int(summary.get("overall_score", fallback["overall_score"])),
            "summary": _normalize_text(summary.get("summary") or fallback["summary"]),
            "top_strengths": _safe_list(summary.get("top_strengths")) or fallback["top_strengths"],
            "improvement_areas": _safe_list(summary.get("improvement_areas")) or fallback["improvement_areas"],
            "strongest_questions": _safe_list(summary.get("strongest_questions")) or fallback["strongest_questions"],
            "needs_work_questions": _safe_list(summary.get("needs_work_questions")) or fallback["needs_work_questions"],
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
