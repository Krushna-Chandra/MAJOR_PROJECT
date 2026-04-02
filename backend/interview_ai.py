import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from typing import Any, Dict, List, Optional, Tuple

from config import load_backend_env

load_backend_env()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
OLLAMA_TIMEOUT_SECONDS = max(30, int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

INTERVIEW_SESSIONS: Dict[str, Dict[str, Any]] = {}

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
        count = 5
    return max(3, min(count, 10))


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
    selected_options = payload.get("selected_options") or []
    primary_focus = ", ".join(selected_options) if selected_options else "general interview preparation"
    config_mode = payload.get("config_mode") or "question"
    time_mode_interval = payload.get("time_mode_interval")
    interview_mode_time = payload.get("interview_mode_time")
    role_profile = _match_role_profile(payload.get("job_role") or "")
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
        derived_count = max(3, min(10, round(minutes / 2)))
        return derived_count
    return _clamp_question_count(payload.get("question_count"))


def _target_subject(payload: Dict[str, Any]) -> str:
    selected_mode = payload.get("selected_mode") or ""
    if selected_mode == "language" and payload.get("primary_language"):
        return payload["primary_language"]
    return (
        payload.get("job_role")
        or payload.get("primary_language")
        or "the selected interview focus"
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

    core_areas = selected_options[:6] if selected_options else [
        "programming fundamentals",
        "core concepts",
        "problem solving",
        "debugging",
        "system understanding",
    ]

    return {
        "role_label": job_role or primary_language or "Technical Role",
        "core_areas": core_areas,
        "tech_stack": inferred_stack,
        "question_focus": [
            f"Ask technical fundamentals for {job_role or primary_language or 'the selected role'}",
            "Ask conceptual questions based on selected topics",
            "Ask practical implementation questions",
            "Ask debugging or architecture questions where relevant",
        ],
        "language_focus": primary_language or "",
    }


async def _call_gemini_json(prompt: str, temperature: float = 0.35) -> Dict[str, Any]:
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
    data = await asyncio.to_thread(_http_post_json, url, payload, None, 80)
    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(part.get("text", "") for part in parts)
    return _extract_json_block(text)


async def _call_ollama_json(prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
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
    data = await asyncio.to_thread(_http_post_json, url, payload, None, OLLAMA_TIMEOUT_SECONDS)
    text = data.get("response", "")
    return _extract_json_block(text)


async def _generate_json_with_fallback(
    prompt: str,
    order: List[str],
    temperature: float = 0.3
) -> Tuple[Dict[str, Any], str]:
    errors = []
    for provider in order:
        try:
            if provider == "gemini":
                return await _call_gemini_json(prompt, temperature), "gemini"
            if provider == "ollama":
                return await _call_ollama_json(prompt, temperature), "ollama"
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
- If selected options are provided, use them strongly.
- If a language is provided, include it where relevant.
- Avoid markdown.
"""

    try:
        blueprint, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
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


def _default_questions(payload: Dict[str, Any]) -> Dict[str, Any]:
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

    trimmed = base_questions[:question_count]
    return {
        "assistant_intro": (
            f"Hello, I am your AI interview assistant. "
            f"I will ask you {len(trimmed)} {difficulty} questions tailored for "
            f"{language if selected_mode == 'language' and language else role}. "
            f"This interview is configured in {config_mode} mode"
            f"{f' for about {time_hint} minutes' if time_hint else ''}. "
            "I will focus only on technical, conceptual, and fundamentals questions. Answer naturally and clearly."
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

    return {
        "score": score,
        "feedback": (
            "Solid start. Keep your response structured and connect your experience "
            "more directly to the question."
        ) if score >= 65 else (
            "Your answer needs more role-relevant detail. Use a clear structure and "
            "cover the main expected points."
        ),
        "strengths": strengths[:3],
        "gaps": gaps[:3],
        "matched_points": matched_points[:4],
        "missed_points": missed_points[:4],
        "suggested_answer": suggested_answer,
        "assistant_reply": (
            "Thanks. Let’s move to the next question."
        ),
    }


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


def _adaptive_role_interview_enabled(payload: Dict[str, Any]) -> bool:
    category = _normalize_text(payload.get("category") or "").lower()
    if category not in {"technical", "mock"}:
        return False
    selected_mode = payload.get("selected_mode") or (
        "language" if payload.get("primary_language") else "role" if payload.get("job_role") else "general"
    )
    return _normalize_text(selected_mode).lower() == "role" and bool(_normalize_text(payload.get("job_role") or ""))


def _adaptive_intro(payload: Dict[str, Any], question_count: int) -> str:
    role = _normalize_text(payload.get("job_role") or "the selected role")
    category = _normalize_text(payload.get("category") or "").lower()
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


def _adaptive_discovery_question(payload: Dict[str, Any]) -> str:
    role = _normalize_text(payload.get("job_role") or "this role")
    role_lower = role.lower()
    if any(keyword in role_lower for keyword in ("backend", "full stack", "full-stack", "fullstack", "software engineer", "software developer")):
        return (
            f"To start, which backend languages, frameworks, databases, or tools are you most comfortable with for this {role} role?"
        )
    return (
        f"To start, which languages, frameworks, tools, or technical areas are you most comfortable with for this {role} role?"
    )


def _build_adaptive_state(payload: Dict[str, Any], role_blueprint: Dict[str, Any], question_count: int) -> Dict[str, Any]:
    category = _normalize_text(payload.get("category") or "").lower()
    primary_language = _normalize_text(payload.get("primary_language") or role_blueprint.get("language_focus") or "")
    include_hr = category == "mock"
    hr_target = 0 if not include_hr else (1 if question_count <= 5 else 2)
    return {
        "enabled": True,
        "include_hr": include_hr,
        "scored_question_target": question_count,
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
        "role_label": _normalize_text(role_blueprint.get("role_label") or payload.get("job_role") or "Technical Role"),
        "confidence_summary": "",
    }


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
    }

    session.setdefault("questions", []).append(question)
    session.setdefault("question_outline", []).append(
        {
            "id": question["id"],
            "question": question["question"],
            "question_type": question["question_type"],
        }
    )
    return question


def _adaptive_total_questions(session: Dict[str, Any]) -> int:
    state = session.get("meta", {}).get("adaptive_state") or {}
    if not state.get("enabled"):
        return len(session.get("questions", []))
    return max(
        len(session.get("questions", [])),
        int(state.get("scored_question_target", 0)) + max(1, int(state.get("discovery_questions_asked", 1))),
    )


def _adaptive_state_summary(state: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Role label: {state.get('role_label') or 'Not specified'}",
            f"Preferred language: {state.get('preferred_language') or 'Not confirmed'}",
            f"Languages mentioned: {', '.join(state.get('languages') or []) or 'None yet'}",
            f"Frameworks mentioned: {', '.join(state.get('frameworks') or []) or 'None yet'}",
            f"Databases mentioned: {', '.join(state.get('databases') or []) or 'None yet'}",
            f"Tools mentioned: {', '.join(state.get('tools') or []) or 'None yet'}",
            f"Focus areas: {', '.join(state.get('focus_areas') or []) or 'None yet'}",
            f"Confidence summary: {state.get('confidence_summary') or 'Not confirmed yet'}",
            f"Covered topics: {', '.join(state.get('covered_topics') or []) or 'None yet'}",
            f"Technical questions answered: {state.get('technical_questions_answered', 0)}",
            f"HR questions answered: {state.get('hr_questions_answered', 0)}",
        ]
    )


def _fallback_stack_analysis(answer_text: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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
    elif not languages and not frameworks:
        needs_clarification = True
        clarification_question = (
            "Which backend language or framework would you like me to focus on first, and what stack have you actually used?"
        )

    focus_areas = _merge_unique(frameworks, databases)
    focus_areas = _merge_unique(focus_areas, tools)
    if preferred_language:
        focus_areas = _merge_unique([preferred_language], focus_areas)

    stack_summary = ", ".join(focus_areas[:4]) or "your preferred stack"
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
    role_blueprint = session.get("meta", {}).get("role_blueprint") or {}
    prompt = f"""
You are helping an AI interviewer discover the candidate's preferred technology stack.

Interview context:
{_context_summary(payload)}

Role blueprint:
- Role label: {role_blueprint.get("role_label") or payload.get("job_role") or "Not specified"}
- Core areas: {', '.join(role_blueprint.get("core_areas") or [])}
- Tech stack hints: {', '.join(role_blueprint.get("tech_stack") or [])}

Candidate answer:
{answer_text}

Return valid JSON with this exact shape:
{{
  "preferred_language": "single best language to focus on first, or empty string",
  "languages": ["languages explicitly mentioned or directly implied"],
  "frameworks": ["frameworks explicitly mentioned"],
  "databases": ["databases explicitly mentioned"],
  "tools": ["infra or platform tools explicitly mentioned"],
  "focus_areas": ["the most useful technical areas to focus on next"],
  "confidence_summary": "one sentence on what the candidate seems strongest in",
  "needs_clarification": false,
  "clarification_question": "short follow-up question if the preference is still unclear",
  "acknowledgement": "one short human-like acknowledgement"
}}

Rules:
- Do not assume a language unless the candidate mentioned it or a framework directly implies it.
- If the candidate mentions multiple languages and no preference, ask which one to focus on first.
- Keep the acknowledgement warm and professional.
- Do not use markdown.
"""

    try:
        analysis, provider = await _generate_json_with_fallback(prompt, ["gemini", "ollama"], 0.1)
        normalized = {
            "preferred_language": _normalize_text(analysis.get("preferred_language") or ""),
            "languages": _safe_list(analysis.get("languages")),
            "frameworks": _safe_list(analysis.get("frameworks")),
            "databases": _safe_list(analysis.get("databases")),
            "tools": _safe_list(analysis.get("tools")),
            "focus_areas": _safe_list(analysis.get("focus_areas")),
            "confidence_summary": _normalize_text(analysis.get("confidence_summary") or ""),
            "needs_clarification": bool(analysis.get("needs_clarification")),
            "clarification_question": _normalize_text(analysis.get("clarification_question") or ""),
            "acknowledgement": _normalize_text(analysis.get("acknowledgement") or ""),
        }
        if not any(
            [
                normalized["preferred_language"],
                normalized["languages"],
                normalized["frameworks"],
                normalized["databases"],
                normalized["tools"],
            ]
        ):
            raise ProviderError("Discovery analysis did not return a usable stack profile.")
        return normalized, provider
    except ProviderError:
        return _fallback_stack_analysis(answer_text, payload), "fallback"


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
    candidates = _merge_unique(candidates, [state.get("preferred_language") or ""])
    candidates = _merge_unique(candidates, state.get("frameworks") or [])
    candidates = _merge_unique(candidates, state.get("databases") or [])
    candidates = _merge_unique(candidates, state.get("tools") or [])
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


def _fallback_adaptive_question(
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


async def _generate_adaptive_question(
    session: Dict[str, Any],
    last_question: Optional[Dict[str, Any]],
    answer_text: str,
    evaluation: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], str]:
    state = session.get("meta", {}).get("adaptive_state") or {}
    desired_track = _next_adaptive_track(state)
    last_score = int((evaluation or {}).get("score") or 0)
    role = _normalize_text(session.get("context", {}).get("job_role") or "the selected role")
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
Target role: {role}

Return valid JSON with this exact shape:
{{
  "assistant_reply": "one short conversational bridge",
  "question": "exactly one next interview question",
  "question_type": "fundamental | conceptual | practical | scenario | behavioral",
  "expected_points": ["3 to 5 concise expected answer points"],
  "evaluation_focus": ["3 concise evaluation criteria"],
  "topic_tag": "short topic label"
}}

Rules:
- Ask exactly one question.
- Sound like a curious, calm, and supportive human interviewer.
- Keep assistant_reply gentle, natural, and short, like a real interviewer speaking conversationally.
- If desired next track is technical, do not ask HR, self-introduction, motivation, or strengths and weaknesses questions.
- If desired next track is technical and the last score was below 55, ask a simpler follow-up or ask for a concrete example on the same stack.
- If desired next track is technical and the last score was 80 or above, go one level deeper on the same topic or a closely related backend concern.
- If desired next track is technical and the last score was between 55 and 79, move to the next relevant backend topic.
- If desired next track is hr, ask one realistic behavioral or communication question relevant to the role.
- Prefer the candidate's preferred language, frameworks, and tools when known.
- Avoid repeating covered topics unless you are intentionally following up on a weak answer.
- Keep it professional, specific, and natural.
- Do not use markdown.
"""

    try:
        generated, provider = await _generate_json_with_fallback(prompt, ["gemini", "ollama"], 0.2)
        question = {
            "assistant_reply": _normalize_text(generated.get("assistant_reply") or ""),
            "question": _normalize_text(generated.get("question") or ""),
            "question_type": _safe_question_type(generated.get("question_type") or ("behavioral" if desired_track == "hr" else "practical")),
            "expected_points": _safe_list(generated.get("expected_points"))[:5],
            "evaluation_focus": _safe_list(generated.get("evaluation_focus"))[:4],
            "topic_tag": _normalize_text(generated.get("topic_tag") or _next_uncovered_topic(session, last_question)),
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


def _register_scored_turn(state: Dict[str, Any], question: Dict[str, Any]) -> None:
    if not question.get("count_towards_score", True):
        return
    state["scored_questions_answered"] = int(state.get("scored_questions_answered", 0)) + 1
    topic = _normalize_text(question.get("topic_tag") or "")
    if topic:
        state["covered_topics"] = _merge_unique(state.get("covered_topics") or [], [topic])
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
        "answer": answer_text,
        "score": max(0, min(100, int(evaluation.get("score", 0)))),
        "feedback": _normalize_text(evaluation.get("feedback") or ""),
        "strengths": _safe_list(evaluation.get("strengths"))[:3],
        "gaps": _safe_list(evaluation.get("gaps"))[:3],
        "matched_points": _safe_list(evaluation.get("matched_points"))[:4],
        "missed_points": _safe_list(evaluation.get("missed_points"))[:4],
        "suggested_answer": _normalize_text(evaluation.get("suggested_answer") or ""),
        "assistant_reply": _normalize_text(evaluation.get("assistant_reply") or "Thank you. Let us continue."),
        "provider": provider_used,
        "count_towards_score": bool(question.get("count_towards_score", True)),
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
        "progress": {
            "current": question_index + 1,
            "total": _adaptive_total_questions(session),
        },
        "question_outline": session.get("question_outline", []),
    }


def _scored_evaluations(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        item
        for item in session.get("evaluations", [])
        if item.get("count_towards_score", True)
    ]


async def _create_adaptive_interview_session(
    payload: Dict[str, Any],
    question_count: int,
    difficulty: str,
    role_blueprint: Dict[str, Any],
    blueprint_provider: str,
) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    adaptive_state = _build_adaptive_state(payload, role_blueprint, question_count)
    provider_meta = {
        "generation_provider": "fallback",
        "evaluation_provider": "fallback",
        "analysis_provider": blueprint_provider,
    }

    session = {
        "session_id": session_id,
        "created_at": time.time(),
        "context": payload,
        "assistant_intro": _adaptive_intro(payload, question_count),
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
        },
        "question_outline": [],
    }

    first_question = _append_session_question(
        session,
        {
            "question": _adaptive_discovery_question(payload),
            "question_type": "discovery",
            "expected_points": [
                "languages the candidate knows",
                "frameworks or backend tools used",
                "preferred stack to focus on",
            ],
            "evaluation_focus": ["clarity", "stack identification", "specificity"],
            "count_towards_score": False,
            "topic_tag": "stack discovery",
        },
    )

    INTERVIEW_SESSIONS[session_id] = session
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
            generated_question, provider = await _generate_adaptive_question(session, question, answer_text, evaluation)
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
  "strengths": ["up to 3 concise strengths"],
  "gaps": ["up to 3 concise gaps"],
  "matched_points": ["expected points that were covered"],
  "missed_points": ["expected points that were not covered"],
  "suggested_answer": "short improved answer guidance",
  "assistant_reply": "one short warm spoken response before the next question"
}}

Rules:
- Evaluate approximately, not by exact wording.
- Reward relevant meaning even if phrasing is imperfect.
- Be practical and interview-focused.
- Do not use markdown.
"""

    provider_used = session["providers"].get("evaluation_provider", "fallback")
    try:
        evaluation, provider_used = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
        )
    except ProviderError:
        evaluation = _heuristic_evaluation(question, answer_text)
        provider_used = "fallback"

    session["providers"]["evaluation_provider"] = provider_used
    if provider_used != "fallback":
        heuristic_defaults = _heuristic_evaluation(question, answer_text)
        evaluation = {
            "score": int(evaluation.get("score", heuristic_defaults["score"])),
            "feedback": _normalize_text(evaluation.get("feedback") or heuristic_defaults["feedback"]),
            "strengths": _safe_list(evaluation.get("strengths")) or heuristic_defaults["strengths"],
            "gaps": _safe_list(evaluation.get("gaps")) or heuristic_defaults["gaps"],
            "matched_points": _safe_list(evaluation.get("matched_points")) or heuristic_defaults["matched_points"],
            "missed_points": _safe_list(evaluation.get("missed_points")) or heuristic_defaults["missed_points"],
            "suggested_answer": _normalize_text(evaluation.get("suggested_answer") or heuristic_defaults["suggested_answer"]),
            "assistant_reply": _normalize_text(evaluation.get("assistant_reply") or "Thanks. Let’s continue."),
        }

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
    difficulty = _difficulty_from_experience(payload.get("experience") or "")
    target_subject = payload.get("primary_language") if payload.get("selected_mode") == "language" else payload.get("job_role")
    target_subject = target_subject or payload.get("job_role") or payload.get("primary_language") or "the selected interview focus"
    role_profile = _match_role_profile(payload.get("job_role") or "")
    role_blueprint, blueprint_provider = await _infer_role_blueprint(payload)
    if _adaptive_role_interview_enabled(payload):
        return await _create_adaptive_interview_session(
            payload,
            question_count,
            difficulty,
            role_blueprint,
            blueprint_provider,
        )
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
- Do not ask HR questions, self-introduction questions, motivation questions, strengths/weaknesses questions, or behavioral questions.
- Prefer technical fundamentals, conceptual understanding, implementation questions, architecture questions, debugging questions, APIs, databases, networking, operating systems, cloud, testing, or security depending on the selected job role.
- If configuration mode is time mode, make the question set fit naturally within the selected time interval.
- If practice type is interview mode, keep questions realistic and progressively challenging.
- Keep expected_points practical enough to support approximate answer evaluation.
- Avoid markdown.
"""

    provider_meta = {"generation_provider": "fallback", "evaluation_provider": "fallback", "analysis_provider": blueprint_provider}
    try:
        blueprint, provider = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.3,
        )
        provider_meta["generation_provider"] = provider
    except ProviderError:
        blueprint = _default_questions(payload)

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
        fallback = _default_questions(payload)
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
    INTERVIEW_SESSIONS[session_id] = {
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
        },
        "question_outline": [
            {
                "id": question["id"],
                "question": question["question"],
                "question_type": question.get("question_type", "practical"),
            }
            for question in questions
        ],
    }

    return {
        "session_id": session_id,
        "assistant_intro": assistant_intro,
        "total_questions": len(questions),
        "current_question": questions[0]["question"],
        "providers": provider_meta,
        "meta": INTERVIEW_SESSIONS[session_id]["meta"],
        "question_outline": INTERVIEW_SESSIONS[session_id]["question_outline"],
    }


async def evaluate_interview_answer(
    session_id: str,
    question_index: int,
    answer: str
) -> Dict[str, Any]:
    session = INTERVIEW_SESSIONS.get(session_id)
    if not session:
        raise ProviderError("Interview session not found.")

    questions = session["questions"]
    if question_index < 0 or question_index >= len(questions):
        raise ProviderError("Invalid question index.")

    question = questions[question_index]
    answer_text = _normalize_text(answer)
    if session.get("meta", {}).get("adaptive_state", {}).get("enabled"):
        return await _evaluate_adaptive_interview_answer(
            session,
            question_index,
            question,
            answer_text,
        )

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
  "strengths": ["up to 3 concise strengths"],
  "gaps": ["up to 3 concise gaps"],
  "matched_points": ["expected points that were covered"],
  "missed_points": ["expected points that were not covered"],
  "suggested_answer": "short improved answer guidance",
  "assistant_reply": "one short spoken response before the next question"
}}

Rules:
- Evaluate approximately, not by exact wording.
- Reward relevant meaning even if phrasing is imperfect.
- Be practical and interview-focused.
- Do not use markdown.
"""

    provider_used = session["providers"].get("evaluation_provider", "fallback")
    try:
        evaluation, provider_used = await _generate_json_with_fallback(
            prompt,
            ["gemini", "ollama"],
            0.2,
        )
    except ProviderError:
        evaluation = _heuristic_evaluation(question, answer_text)
        provider_used = "fallback"

    session["providers"]["evaluation_provider"] = provider_used

    if provider_used != "fallback":
        heuristic_defaults = _heuristic_evaluation(question, answer_text)
        evaluation = {
            "score": int(evaluation.get("score", heuristic_defaults["score"])),
            "feedback": _normalize_text(evaluation.get("feedback") or heuristic_defaults["feedback"]),
            "strengths": _safe_list(evaluation.get("strengths")) or heuristic_defaults["strengths"],
            "gaps": _safe_list(evaluation.get("gaps")) or heuristic_defaults["gaps"],
            "matched_points": _safe_list(evaluation.get("matched_points")) or heuristic_defaults["matched_points"],
            "missed_points": _safe_list(evaluation.get("missed_points")) or heuristic_defaults["missed_points"],
            "suggested_answer": _normalize_text(evaluation.get("suggested_answer") or heuristic_defaults["suggested_answer"]),
            "assistant_reply": _normalize_text(evaluation.get("assistant_reply") or "Thank you. Let us continue."),
        }

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
        "provider": provider_used,
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

    is_complete = question_index >= len(questions) - 1
    next_question = None if is_complete else questions[question_index + 1]["question"]
    next_question_type = None if is_complete else questions[question_index + 1].get("question_type", "practical")

    return {
        **result,
        "question_index": question_index,
        "is_complete": is_complete,
        "next_question": next_question,
        "next_question_type": next_question_type,
        "progress": {
            "current": question_index + 1,
            "total": len(questions),
        },
        "question_outline": session.get("question_outline", []),
    }


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
    session = INTERVIEW_SESSIONS.get(session_id)
    if not session:
        raise ProviderError("Interview session not found.")

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

    session["summary"] = summary
    session["ended_early"] = bool(ended_early)
    session["completed_at"] = time.time()
    session["providers"]["summary_provider"] = provider
    return {
        **summary,
        "session_id": session_id,
        "ended_early": bool(ended_early),
        "questions_answered": len(session.get("evaluations", [])),
        "total_questions": _adaptive_total_questions(session) if adaptive_state.get("enabled") else len(session.get("questions", [])),
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


def get_session_payload(session_id: str) -> Optional[Dict[str, Any]]:
    return INTERVIEW_SESSIONS.get(session_id)
