import os
import base64
import re
import zlib
import difflib
from io import BytesIO
from datetime import datetime, timezone
import numpy as np
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Header,
    Body
)
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError
from database import users_collection
from auth_utils import (
    hash_password,
    verify_password,
    create_token,
    SECRET_KEY,
    ALGORITHM
)
from coding_ai import (
    evaluate_coding_submission,
    generate_coding_challenge,
    get_coding_runtime_status,
    run_code_against_tests,
)
from interview_ai import (
    ProviderError,
    OLLAMA_MODEL,
    _call_gemini_json,
    _call_ollama_json,
    complete_interview_session,
    create_interview_session,
    evaluate_interview_answer,
    get_ai_provider_status,
    get_session_payload,
    get_session_status,
    mark_session_report_saved,
)

app = FastAPI()

RESUME_SECTION_KEYWORDS = [
    "summary",
    "objective",
    "profile",
    "experience",
    "professional experience",
    "work history",
    "work experience",
    "education",
    "academic",
    "skills",
    "technical skills",
    "projects",
    "internships",
    "certifications",
    "achievements",
    "certificates",
    "technologies",
    "internship",
]

KNOWN_RESUME_SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "angular",
    "vue",
    "node",
    "node.js",
    "express",
    "fastapi",
    "django",
    "flask",
    "spring boot",
    "sql",
    "mysql",
    "postgresql",
    "mongodb",
    "redis",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "linux",
    "rest api",
    "graphql",
    "html",
    "css",
    "pandas",
    "numpy",
    "tensorflow",
    "pytorch",
    "machine learning",
    "deep learning",
    "data analysis",
    "power bi",
    "tableau",
    "excel",
    "agile",
    "scrum",
    "communication",
    "leadership",
    "problem solving",
    "figma",
    "ui/ux",
]

JOB_MATCH_HINTS = [
    "system design",
    "microservices",
    "testing",
    "automation",
    "stakeholder management",
    "product strategy",
    "roadmap",
    "analytics",
    "customer success",
    "sales",
]

COMMON_RESUME_MISSPELLINGS = {
    "managment": "management",
    "mangement": "management",
    "developement": "development",
    "deveopment": "development",
    "enviroment": "environment",
    "experiance": "experience",
    "expereince": "experience",
    "teh": "the",
    "recieve": "receive",
    "acheived": "achieved",
    "acheivements": "achievements",
    "responsiblities": "responsibilities",
    "responsibilites": "responsibilities",
    "profficient": "proficient",
    "knowladge": "knowledge",
    "framwork": "framework",
    "algorithim": "algorithm",
    "analitics": "analytics",
    "analysis": "analysis",
    "communcation": "communication",
    "communucation": "communication",
    "collabaration": "collaboration",
    "organisation": "organization",
    "succesfully": "successfully",
    "langauge": "language",
    "databse": "database",
    "pyhton": "python",
    "javasript": "javascript",
    "reactjss": "reactjs",
    "mangodb": "mongodb",
}

RESUME_MATCH_STOPWORDS = {
    "about",
    "across",
    "after",
    "also",
    "and",
    "are",
    "build",
    "candidate",
    "collaboration",
    "company",
    "cross",
    "deliver",
    "experience",
    "good",
    "have",
    "highly",
    "including",
    "into",
    "knowledge",
    "looking",
    "must",
    "nice",
    "preferred",
    "professional",
    "role",
    "strong",
    "team",
    "teams",
    "that",
    "their",
    "this",
    "using",
    "with",
    "work",
    "years",
}


def _extract_pdf_text_from_bytes(pdf_bytes: bytes) -> str:
    readers = []
    try:
        from pypdf import PdfReader as PypdfReader  # type: ignore
        readers.append(PypdfReader)
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader as PyPdf2Reader  # type: ignore
        readers.append(PyPdf2Reader)
    except Exception:
        pass

    for reader_cls in readers:
        try:
            reader = reader_cls(BytesIO(pdf_bytes))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts).strip()
            if text:
                return text
        except Exception:
            continue
    return _extract_pdf_text_without_dependencies(pdf_bytes)


def _decode_pdf_literal_string(value: bytes) -> str:
    content = value[1:-1]
    result = bytearray()
    i = 0
    while i < len(content):
        current = content[i]
        if current != 92:  # backslash
            result.append(current)
            i += 1
            continue

        i += 1
        if i >= len(content):
            break

        escaped = content[i]
        escape_map = {
            ord("n"): b"\n",
            ord("r"): b"\r",
            ord("t"): b"\t",
            ord("b"): b"\b",
            ord("f"): b"\f",
            ord("("): b"(",
            ord(")"): b")",
            ord("\\"): b"\\",
        }
        if escaped in escape_map:
            result.extend(escape_map[escaped])
            i += 1
            continue

        if 48 <= escaped <= 55:
            octal = bytes([escaped])
            i += 1
            for _ in range(2):
                if i < len(content) and 48 <= content[i] <= 55:
                    octal += bytes([content[i]])
                    i += 1
                else:
                    break
            try:
                result.append(int(octal, 8))
            except Exception:
                pass
            continue

        if escaped in (10, 13):  # line continuation
            i += 1
            if escaped == 13 and i < len(content) and content[i] == 10:
                i += 1
            continue

        result.append(escaped)
        i += 1

    return result.decode("latin1", errors="ignore")


def _extract_pdf_text_without_dependencies(pdf_bytes: bytes) -> str:
    stream_matches = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf_bytes, re.S)
    extracted_chunks = []

    for raw_stream in stream_matches:
        candidates = [raw_stream]
        for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                decompressed = zlib.decompress(raw_stream, wbits)
                candidates.append(decompressed)
            except Exception:
                continue

        for candidate in candidates:
            literal_strings = re.findall(rb"\((?:\\.|[^\\()])*\)", candidate)
            decoded_strings = []
            for item in literal_strings:
                decoded = _decode_pdf_literal_string(item)
                cleaned = re.sub(r"\s+", " ", decoded).strip()
                if len(cleaned) >= 2 and re.search(r"[A-Za-z]", cleaned):
                    decoded_strings.append(cleaned)

            if decoded_strings:
                extracted_chunks.extend(decoded_strings)

    if not extracted_chunks:
        return ""

    deduped = []
    seen = set()
    for chunk in extracted_chunks:
        normalized = chunk.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(chunk)

    return "\n".join(deduped[:400]).strip()


def _decode_pdf_data_url(data_url: str) -> bytes:
    if not data_url or "," not in data_url:
        return b""
    try:
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except Exception:
        return b""


def _normalize_resume_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def _resume_signal_details(text: str, file_name: str = "") -> dict:
    normalized = _normalize_resume_text(text)
    lowered = normalized.lower()
    filename = (file_name or "").lower()
    skill_hits = _extract_resume_skills(text)
    section_hits = [keyword for keyword in RESUME_SECTION_KEYWORDS if keyword in lowered]
    word_count = len([word for word in normalized.split(" ") if word])

    has_email = bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I))
    has_phone = bool(re.search(r"(\+?\d[\d\s().-]{8,}\d)", text))
    has_profile_link = bool(re.search(r"(linkedin|github|portfolio)", lowered))
    has_education = bool(re.search(r"\b(bachelor|master|b\.tech|m\.tech|degree|university|college|school)\b", lowered))
    has_experience = bool(re.search(r"\b(intern|internship|experience|engineer|developer|manager|analyst|specialist|coordinator|student|worked|employment|company|consultant|associate|executive)\b", lowered))
    has_project = bool(re.search(r"\b(project|projects|developed|built|created|implemented|designed|designd|prototype|application|system)\b", lowered))
    has_resume_heading = bool(re.search(r"\b(resume|curriculum vitae|cv)\b", lowered))
    has_achievement_language = bool(re.search(r"\b(led|improved|increased|reduced|optimized|delivered|managed|launched|achieved)\b", lowered))
    has_dates = bool(re.search(r"\b(19|20)\d{2}\b", lowered))
    filename_says_resume = any(token in filename for token in ["resume", "cv", "curriculum vitae"])

    score = 0
    if filename_says_resume:
        score += 2
    if has_resume_heading:
        score += 1
    if has_email:
        score += 2
    if has_phone:
        score += 2
    if has_profile_link:
        score += 1
    if has_education:
        score += 1
    if has_experience:
        score += 2
    if has_project:
        score += 1
    if has_achievement_language:
        score += 1
    if has_dates:
        score += 1
    if skill_hits:
        score += min(3, max(1, len(skill_hits) // 2 or 1))
    if section_hits:
        score += min(4, len(section_hits))
    if word_count >= 80:
        score += 1
    if word_count >= 180:
        score += 1

    return {
        "normalized": normalized,
        "score": score,
        "text_length": len(normalized),
        "word_count": word_count,
        "filename_says_resume": filename_says_resume,
        "has_resume_heading": has_resume_heading,
        "has_email": has_email,
        "has_phone": has_phone,
        "has_profile_link": has_profile_link,
        "has_education": has_education,
        "has_experience": has_experience,
        "has_project": has_project,
        "has_achievement_language": has_achievement_language,
        "has_dates": has_dates,
        "skill_hits": skill_hits,
        "section_hits": section_hits,
    }


def _looks_like_resume(text: str, file_name: str = "") -> tuple[bool, str]:
    details = _resume_signal_details(text, file_name)

    if details["text_length"] < 25 and not details["filename_says_resume"]:
        return False, "This file does not contain enough readable content to verify it as a resume or CV."

    if details["score"] >= 4:
        return True, ""

    short_resume_like = (
        details["text_length"] >= 35 and
        (
            details["filename_says_resume"] or
            details["has_resume_heading"] or
            (details["has_email"] and details["has_experience"]) or
            (details["has_phone"] and details["has_education"]) or
            (details["has_email"] and details["has_phone"]) or
            (details["has_email"] and len(details["section_hits"]) >= 1) or
            (details["has_phone"] and len(details["section_hits"]) >= 1) or
            (details["has_experience"] and bool(details["skill_hits"])) or
            (details["has_project"] and bool(details["skill_hits"])) or
            (details["has_dates"] and (details["has_experience"] or details["has_education"])) or
            len(details["section_hits"]) >= 2
        )
    )
    if short_resume_like:
        return True, ""

    longer_resume_like = (
        details["word_count"] >= 60 and
        (
            (details["has_email"] or details["has_phone"]) and
            (
                details["has_experience"] or
                details["has_education"] or
                details["has_project"] or
                bool(details["skill_hits"]) or
                len(details["section_hits"]) >= 1
            )
        )
    )
    if longer_resume_like:
        return True, ""

    return False, "This document does not look like a resume or CV. Please upload a proper resume/CV file."


def _extract_resume_skills(text: str) -> list[str]:
    normalized = _normalize_resume_text(text).lower()
    found = []
    for skill in KNOWN_RESUME_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, normalized):
            found.append(skill.title() if skill.islower() else skill)
    return found[:24]


def _extract_resume_lines(text: str, limit: int = 8) -> list[str]:
    lines = [line.strip(" -•\t") for line in (text or "").splitlines()]
    cleaned = [line for line in lines if len(line.split()) >= 2]
    return cleaned[:limit]


def _build_resume_analysis_payload(text: str, file_name: str = "") -> dict:
    normalized = _normalize_resume_text(text)
    lines = _extract_resume_lines(text, limit=20)
    skills = _extract_resume_skills(text)
    signal_details = _resume_signal_details(text, file_name)

    education = [
        line for line in lines
        if re.search(r"\b(university|college|bachelor|master|degree|b\.tech|m\.tech|school)\b", line, re.I)
    ][:5]
    experience = [
        line for line in lines
        if re.search(r"\b(experience|intern|engineer|developer|manager|analyst|specialist|worked|company)\b", line, re.I)
    ][:6]
    projects = [
        line for line in lines
        if re.search(r"\b(project|developed|built|created|implemented|designed)\b", line, re.I)
    ][:6]

    likely_name = lines[0] if lines else ""
    if re.search(r"(resume|cv|education|skills|experience)", likely_name, re.I):
        likely_name = ""

    analysis_parts = [
        f"Candidate name: {likely_name or 'Not clearly detected'}",
        f"Skills: {', '.join(skills) if skills else 'Not clearly extracted'}",
        f"Education: {' | '.join(education) if education else 'Not clearly extracted'}",
        f"Experience: {' | '.join(experience) if experience else 'Not clearly extracted'}",
        f"Projects: {' | '.join(projects) if projects else 'Not clearly extracted'}",
        f"Resume text: {normalized[:2400]}",
    ]

    return {
        "candidate_name": likely_name,
        "skills": skills,
        "education": education,
        "experience_highlights": experience,
        "project_highlights": projects,
        "contact_found": bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)),
        "section_hits": signal_details["section_hits"],
        "resume_signal_score": signal_details["score"],
        "analysis_text": "\n".join(analysis_parts)[:4000],
        "suggested_roles": [
            role for role in [
                "Software Engineer" if any(item.lower() in normalized for item in ["python", "java", "react", "node", "api", "sql"]) else "",
                "Data Scientist" if any(item.lower() in normalized for item in ["machine learning", "pandas", "numpy", "tensorflow", "pytorch"]) else "",
                "Business Analyst" if any(item.lower() in normalized for item in ["excel", "power bi", "tableau", "analysis"]) else "",
                "Product Manager" if any(item.lower() in normalized for item in ["roadmap", "stakeholder", "product"]) else "",
            ] if role
        ][:4],
        "source_file_name": file_name,
    }


def _canonical_keyword(value: str) -> str:
    lowered = (value or "").lower().replace("/", " ").replace("-", " ")
    cleaned = re.sub(r"[^a-z0-9+#.\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_job_keywords(job_description: str) -> list[str]:
    normalized = _canonical_keyword(job_description)
    if not normalized:
        return []

    found = []
    for keyword in KNOWN_RESUME_SKILLS + JOB_MATCH_HINTS:
        canonical = _canonical_keyword(keyword)
        if canonical and canonical in normalized:
            found.append(keyword.title() if keyword.islower() else keyword)

    fallback_tokens = [
        token for token in re.findall(r"[a-z][a-z0-9+#.]{3,}", normalized)
        if token not in RESUME_MATCH_STOPWORDS
    ]
    for token in fallback_tokens[:10]:
        found.append(token.title())

    deduped = []
    seen = set()
    for item in found:
        canonical = _canonical_keyword(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(item)
    return deduped[:16]


def _is_valid_job_description(job_description: str) -> bool:
    normalized = _normalize_resume_text(job_description)
    if not normalized:
        return False
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]*", normalized)
    return len(words) >= 20


def _build_spelling_payload(text: str, match_payload: dict) -> dict:
    tokens = re.findall(r"[A-Za-z][A-Za-z+#.-]{2,}", text or "")
    unique_tokens = []
    seen = set()
    for token in tokens:
        lowered = token.lower().strip(".")
        if lowered in seen:
            continue
        seen.add(lowered)
        unique_tokens.append(lowered)

    issues = []
    issue_keys = set()

    for token in unique_tokens:
        suggestion = COMMON_RESUME_MISSPELLINGS.get(token)
        if suggestion and token != suggestion:
            key = (token, suggestion)
            if key in issue_keys:
                continue
            issue_keys.add(key)
            issues.append(
                {
                    "word": token,
                    "suggestion": suggestion,
                    "type": "common_misspelling",
                }
            )

    for keyword in match_payload.get("job_keywords") or []:
        canonical_keyword = _canonical_keyword(keyword)
        keyword_words = [part for part in canonical_keyword.split() if len(part) >= 4]
        if len(keyword_words) != 1:
            continue
        target = keyword_words[0]
        for token in unique_tokens:
            if token == target or abs(len(token) - len(target)) > 2:
                continue
            if token in COMMON_RESUME_MISSPELLINGS:
                continue
            similarity = difflib.SequenceMatcher(None, token, target).ratio()
            if similarity >= 0.84:
                key = (token, target)
                if key in issue_keys:
                    continue
                issue_keys.add(key)
                issues.append(
                    {
                        "word": token,
                        "suggestion": target,
                        "type": "job_keyword_typo",
                    }
                )

    issue_count = len(issues)
    spelling_score = max(42, 100 - issue_count * 12) if issue_count else 98
    summary = (
        "No obvious spelling problems were flagged against common resume mistakes and target-job keywords."
        if not issues
        else "Potential spelling issues were found. Clean up these words to make the resume look sharper and closer to the target role."
    )

    return {
        "score": spelling_score,
        "issue_count": issue_count,
        "issues": issues[:10],
        "summary": summary,
    }


def _build_dashboard_payload(
    scorecard: dict,
    quality: dict,
    match_payload: dict,
    spelling_payload: dict,
) -> dict:
    keyword_alignment = match_payload.get("match_score") or 0
    structure_score = scorecard.get("structure_score", 0)
    content_score = scorecard.get("content_score", 0)
    impact_score = quality.get("impact_score", 0)
    ats_score = quality.get("ats_score", 0)
    spelling_score = spelling_payload.get("score", 0)

    meters = [
        {"label": "ATS Readiness", "value": ats_score, "tone": "ink"},
        {"label": "Keyword Alignment", "value": keyword_alignment, "tone": "teal"},
        {"label": "Content Strength", "value": content_score, "tone": "gold"},
        {"label": "Structure", "value": structure_score, "tone": "slate"},
        {"label": "Impact", "value": impact_score, "tone": "teal"},
        {"label": "Spelling", "value": spelling_score, "tone": "gold"},
    ]

    weak_areas = []
    if keyword_alignment < 70:
        weak_areas.append(
            {
                "title": "Low keyword alignment",
                "detail": "The resume does not yet reflect enough of the target job description vocabulary.",
                "score": keyword_alignment,
            }
        )
    if structure_score < 70:
        weak_areas.append(
            {
                "title": "Structure needs work",
                "detail": "Section layout and recruiter scanability need improvement.",
                "score": structure_score,
            }
        )
    if impact_score < 70:
        weak_areas.append(
            {
                "title": "Achievements are not strong enough",
                "detail": "More measurable results and business impact should be added.",
                "score": impact_score,
            }
        )
    if spelling_score < 90:
        weak_areas.append(
            {
                "title": "Spelling corrections needed",
                "detail": "Potential spelling or target-keyword typos were found in the resume text.",
                "score": spelling_score,
            }
        )
    if not weak_areas:
        weak_areas.append(
            {
                "title": "No major weak area detected",
                "detail": "The resume is already fairly aligned to the supplied role. Focus on polish and stronger evidence.",
                "score": ats_score,
            }
        )

    return {
        "meters": meters,
        "weak_areas": weak_areas[:4],
    }


def _build_resume_scorecard(text: str, file_name: str = "") -> dict:
    details = _resume_signal_details(text, file_name)
    analysis = _build_resume_analysis_payload(text, file_name)

    resume_score = min(100, 34 + details["score"] * 8)
    structure_score = min(
        100,
        28
        + len(details["section_hits"]) * 8
        + (12 if details["has_email"] else 0)
        + (12 if details["has_phone"] else 0)
        + (10 if details["has_project"] else 0),
    )
    content_score = min(
        100,
        30
        + min(24, len(analysis["skills"]) * 4)
        + min(20, len(analysis["experience_highlights"]) * 5)
        + min(12, len(analysis["project_highlights"]) * 4),
    )

    return {
        "resume_score": resume_score,
        "structure_score": structure_score,
        "content_score": content_score,
    }


def _build_job_match_payload(resume_text: str, job_description: str) -> dict:
    normalized_job = _normalize_resume_text(job_description)
    if not normalized_job:
        return {
            "job_description_provided": False,
            "match_score": None,
            "matched_keywords": [],
            "missing_keywords": [],
            "job_keywords": [],
            "summary": "Add a job description to get a role-fit match score and missing keyword suggestions.",
        }

    resume_canonical = _canonical_keyword(resume_text)
    job_keywords = _extract_job_keywords(normalized_job)

    matched_keywords = []
    missing_keywords = []
    for keyword in job_keywords:
        canonical = _canonical_keyword(keyword)
        if canonical and canonical in resume_canonical:
            matched_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    coverage = len(matched_keywords) / max(1, len(job_keywords))
    match_score = min(100, max(38, int(round(coverage * 100))))

    if matched_keywords and missing_keywords:
        summary = (
            f"Your resume already reflects {len(matched_keywords)} important job keywords. "
            f"Consider adding evidence for {', '.join(missing_keywords[:4])}."
        )
    elif matched_keywords:
        summary = "Your resume aligns well with the provided role keywords."
    else:
        summary = "The job description and resume do not overlap much yet. Tailor your resume for this role."

    return {
        "job_description_provided": True,
        "match_score": match_score,
        "matched_keywords": matched_keywords[:8],
        "missing_keywords": missing_keywords[:8],
        "job_keywords": job_keywords,
        "summary": summary,
    }


def _build_resume_recommendations(
    analysis: dict,
    scorecard: dict,
    match_payload: dict,
    spelling_payload: dict,
) -> list[str]:
    recommendations = []

    if not analysis.get("contact_found"):
        recommendations.append("Add a clear email address or phone number near the top of your resume.")
    if len(analysis.get("skills") or []) < 5:
        recommendations.append("Expand the skills section with tools and technologies relevant to your target role.")
    if not analysis.get("project_highlights"):
        recommendations.append("Include one or two project bullets that show measurable impact and ownership.")
    if len(analysis.get("experience_highlights") or []) < 2:
        recommendations.append("Strengthen the experience section with role names, outcomes, and specific responsibilities.")
    if match_payload.get("missing_keywords"):
        recommendations.append(
            "Tailor the resume to the job description by addressing keywords like "
            + ", ".join(match_payload["missing_keywords"][:4])
            + "."
        )
    if scorecard.get("structure_score", 0) < 60:
        recommendations.append("Use clearer section headings so recruiters can scan education, skills, and experience quickly.")
    if spelling_payload.get("issue_count"):
        flagged_words = ", ".join(
            item["word"] for item in (spelling_payload.get("issues") or [])[:4]
        )
        recommendations.append(
            "Fix spelling issues such as " + flagged_words + " to improve professionalism and ATS trust."
        )

    if not recommendations:
        recommendations.append("Your resume looks solid. Focus next on quantifying achievements for an even stronger profile.")

    return recommendations[:5]


def _build_resume_quality_payload(
    text: str,
    analysis: dict,
    scorecard: dict,
    match_payload: dict,
    file_name: str = "",
) -> dict:
    details = _resume_signal_details(text, file_name)
    normalized = _normalize_resume_text(text)
    word_count = len(normalized.split())
    numeric_mentions = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
    detected_sections = []

    if details["has_experience"]:
        detected_sections.append("Experience")
    if details["has_education"]:
        detected_sections.append("Education")
    if details["has_project"]:
        detected_sections.append("Projects")
    if details["skill_hits"]:
        detected_sections.append("Skills")
    if any(item in details["section_hits"] for item in ["summary", "objective"]):
        detected_sections.append("Summary")

    expected_sections = ["Summary", "Experience", "Education", "Skills", "Projects"]
    missing_sections = [section for section in expected_sections if section not in detected_sections]

    section_coverage_score = min(
        100,
        22 + len(detected_sections) * 15 + (8 if details["has_email"] else 0) + (8 if details["has_phone"] else 0),
    )
    impact_score = min(
        100,
        26
        + min(30, numeric_mentions * 5)
        + min(20, len(analysis.get("experience_highlights") or []) * 4)
        + min(16, len(analysis.get("project_highlights") or []) * 4),
    )
    ats_score = min(
        100,
        int(
            round(
                scorecard.get("structure_score", 0) * 0.34
                + scorecard.get("content_score", 0) * 0.26
                + scorecard.get("resume_score", 0) * 0.2
                + section_coverage_score * 0.2
            )
        ),
    )

    strengths = []
    if details["has_email"] and details["has_phone"]:
        strengths.append("Strong contact visibility with both email and phone detected.")
    if details["has_profile_link"]:
        strengths.append("Professional profile links such as LinkedIn or GitHub are included.")
    if len(analysis.get("skills") or []) >= 6:
        strengths.append("The resume shows a healthy spread of role-relevant skills.")
    if analysis.get("project_highlights"):
        strengths.append("Project evidence is present, which helps recruiters validate hands-on experience.")
    if numeric_mentions >= 3:
        strengths.append("Quantified achievements were detected, which improves ATS and recruiter impact.")
    if match_payload.get("matched_keywords"):
        strengths.append(
            "The resume already reflects several target-role keywords such as "
            + ", ".join(match_payload["matched_keywords"][:3])
            + "."
        )

    improvement_areas = []
    if missing_sections:
        improvement_areas.append("Add missing sections like " + ", ".join(missing_sections[:3]) + ".")
    if not details["has_project"]:
        improvement_areas.append("Add a projects section with outcomes, tools, and ownership.")
    if not details["has_profile_link"]:
        improvement_areas.append("Include a LinkedIn, GitHub, or portfolio link for stronger credibility.")
    if numeric_mentions < 2:
        improvement_areas.append("Use more quantified impact such as percentages, counts, revenue, or time saved.")
    if len(analysis.get("skills") or []) < 5:
        improvement_areas.append("Expand the skills section so ATS can match your resume more accurately.")
    if match_payload.get("missing_keywords"):
        improvement_areas.append(
            "Tailor the resume for the target role by covering keywords like "
            + ", ".join(match_payload["missing_keywords"][:4])
            + "."
        )

    must_add = []
    if not details["has_email"]:
        must_add.append("A visible email address")
    if not details["has_phone"]:
        must_add.append("A visible phone number")
    if not details["has_experience"]:
        must_add.append("A clear experience section with role names and outcomes")
    if not details["has_project"]:
        must_add.append("At least one project with tools used and measurable impact")
    if len(analysis.get("skills") or []) < 5:
        must_add.append("A stronger skills section aligned with the target job")
    if numeric_mentions < 2:
        must_add.append("Quantified achievements like percentages, counts, or savings")

    return {
        "ats_score": ats_score,
        "impact_score": impact_score,
        "section_coverage_score": section_coverage_score,
        "word_count": word_count,
        "numeric_mentions": numeric_mentions,
        "quantified_achievements_found": numeric_mentions > 0,
        "detected_sections": detected_sections,
        "missing_sections": missing_sections,
        "contact_checks": {
            "email": details["has_email"],
            "phone": details["has_phone"],
            "profile_link": details["has_profile_link"],
        },
        "strengths": strengths[:6],
        "improvement_areas": improvement_areas[:6],
        "must_add": must_add[:6],
    }


def _build_role_focus_payload(match_payload: dict, quality: dict, spelling_payload: dict) -> dict:
    target_keywords = match_payload.get("job_keywords") or []
    missing_keywords = match_payload.get("missing_keywords") or []
    matched_keywords = match_payload.get("matched_keywords") or []

    where_to_improve = []
    if missing_keywords:
        where_to_improve.append(
            "Add proof for target-role keywords such as " + ", ".join(missing_keywords[:4]) + "."
        )
    if quality.get("missing_sections"):
        where_to_improve.append(
            "Strengthen missing sections like " + ", ".join(quality["missing_sections"][:3]) + "."
        )
    if quality.get("impact_score", 0) < 70:
        where_to_improve.append("Rewrite bullet points to include outcomes, metrics, or measurable impact.")
    if spelling_payload.get("issue_count"):
        where_to_improve.append("Correct spelling issues before sending the resume to recruiters.")

    return {
        "target_keywords": target_keywords[:10],
        "matched_keywords": matched_keywords[:8],
        "missing_keywords": missing_keywords[:8],
        "where_to_improve": where_to_improve[:5],
    }


def _resume_ai_text(value, fallback: str = "") -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        cleaned = _normalize_resume_text(value)
        return cleaned or fallback
    if isinstance(value, (int, float, bool)):
        cleaned = _normalize_resume_text(str(value))
        return cleaned or fallback
    if isinstance(value, dict):
        preferred = (
            value.get("text")
            or value.get("message")
            or value.get("summary")
            or value.get("detail")
            or value.get("title")
            or value.get("label")
        )
        if preferred is not None:
            cleaned = _normalize_resume_text(str(preferred))
            return cleaned or fallback
    cleaned = _normalize_resume_text(str(value))
    return cleaned or fallback


def _resume_ai_list(value, fallback=None, limit: int = 10) -> list[str]:
    if fallback is None:
        fallback = []
    if not isinstance(value, list):
        return list(fallback)[:limit]

    cleaned = []
    seen = set()
    for item in value:
        text = _resume_ai_text(item, "")
        canonical = _canonical_keyword(text)
        if not text or not canonical or canonical in seen:
            continue
        seen.add(canonical)
        cleaned.append(text)
        if len(cleaned) >= limit:
            break

    return cleaned or list(fallback)[:limit]


def _resume_ai_bool(value, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = _resume_ai_text(value, "").lower()
    if normalized in {"true", "yes", "1", "found", "present"}:
        return True
    if normalized in {"false", "no", "0", "missing", "absent"}:
        return False
    return fallback


def _resume_ai_score(value, fallback: int = 0) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        numeric = fallback
    return max(0, min(100, numeric))


def _resume_ai_issues(value, fallback=None) -> list[dict]:
    if fallback is None:
        fallback = []
    if not isinstance(value, list):
        return list(fallback)[:10]

    issues = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        word = _resume_ai_text(item.get("word"), "")
        suggestion = _resume_ai_text(item.get("suggestion"), "")
        issue_type = _resume_ai_text(item.get("type"), "ai_detected")
        key = (word.lower(), suggestion.lower(), issue_type.lower())
        if not word or not suggestion or key in seen:
            continue
        seen.add(key)
        issues.append(
            {
                "word": word.lower(),
                "suggestion": suggestion,
                "type": issue_type,
            }
        )
        if len(issues) >= 10:
            break

    return issues or list(fallback)[:10]


def _resume_ai_meters(value, fallback=None) -> list[dict]:
    if fallback is None:
        fallback = []
    if not isinstance(value, list):
        return list(fallback)

    allowed_tones = {"ink", "teal", "gold", "slate"}
    meters = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = _resume_ai_text(item.get("label"), "")
        if not label:
            continue
        meters.append(
            {
                "label": label,
                "value": _resume_ai_score(item.get("value"), 0),
                "tone": _resume_ai_text(item.get("tone"), "ink").lower()
                if _resume_ai_text(item.get("tone"), "ink").lower() in allowed_tones
                else "ink",
            }
        )
    return meters or list(fallback)


def _resume_ai_weak_areas(value, fallback=None) -> list[dict]:
    if fallback is None:
        fallback = []
    if not isinstance(value, list):
        return list(fallback)[:4]

    weak_areas = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = _resume_ai_text(item.get("title"), "")
        detail = _resume_ai_text(item.get("detail"), "")
        score = _resume_ai_score(item.get("score"), 0)
        if not title or not detail:
            continue
        weak_areas.append({"title": title, "detail": detail, "score": score})
        if len(weak_areas) >= 4:
            break
    return weak_areas or list(fallback)[:4]


def _build_resume_gemini_prompt(resume_text: str, job_description: str, file_name: str = "") -> str:
    trimmed_resume = resume_text[:12000]
    trimmed_job = job_description[:6000]

    return f"""
You are an expert ATS resume reviewer and career writing assistant.

Analyze the resume against the target job description and return STRICT JSON only.
Do not include markdown, commentary, or code fences.
Do not invent facts that are not supported by the resume or the job description.
If something is unclear, use conservative wording.
All scores must be integers from 0 to 100.
Keep lists concise and actionable.

Return this JSON shape exactly:
{{
  "analysis": {{
    "candidate_name": "string",
    "skills": ["string"],
    "education": ["string"],
    "experience_highlights": ["string"],
    "project_highlights": ["string"],
    "contact_found": true,
    "section_hits": ["string"],
    "resume_signal_score": 0,
    "analysis_text": "string",
    "suggested_roles": ["string"]
  }},
  "scorecard": {{
    "resume_score": 0,
    "structure_score": 0,
    "content_score": 0
  }},
  "match": {{
    "job_description_provided": true,
    "match_score": 0,
    "matched_keywords": ["string"],
    "missing_keywords": ["string"],
    "job_keywords": ["string"],
    "summary": "string"
  }},
  "spelling": {{
    "score": 0,
    "issue_count": 0,
    "issues": [
      {{"word": "string", "suggestion": "string", "type": "string"}}
    ],
    "summary": "string"
  }},
  "quality": {{
    "ats_score": 0,
    "impact_score": 0,
    "section_coverage_score": 0,
    "strengths": ["string"],
    "improvement_areas": ["string"],
    "must_add": ["string"]
  }},
  "dashboard": {{
    "meters": [
      {{"label": "string", "value": 0, "tone": "ink"}}
    ],
    "weak_areas": [
      {{"title": "string", "detail": "string", "score": 0}}
    ]
  }},
  "role_focus": {{
    "target_keywords": ["string"],
    "matched_keywords": ["string"],
    "missing_keywords": ["string"],
    "where_to_improve": ["string"]
  }},
  "recommendations": ["string"]
}}

Resume file name: {file_name or "Uploaded resume"}

Resume text:
{trimmed_resume}

Job description:
{trimmed_job}
""".strip()


async def _generate_resume_payload_with_ai(
    resume_text: str,
    job_description: str,
    file_name: str,
    fallback_payload: dict,
) -> tuple[dict, str, str]:
    prompt = _build_resume_gemini_prompt(resume_text, job_description, file_name)
    provider_used = "gemini"
    provider_error = ""
    try:
        ai_payload = await _call_gemini_json(prompt, temperature=0.2, timeout_seconds=90)
    except ProviderError as gemini_exc:
        provider_error = f"Gemini failed: {gemini_exc}"
        ai_payload = await _call_ollama_json(prompt, temperature=0.2, timeout_seconds=90)
        provider_used = "ollama"

    fallback_analysis = fallback_payload["analysis"]
    fallback_scorecard = fallback_payload["scorecard"]
    fallback_match = fallback_payload["match"]
    fallback_spelling = fallback_payload["spelling"]
    fallback_quality = fallback_payload["quality"]
    fallback_dashboard = fallback_payload["dashboard"]
    fallback_role_focus = fallback_payload["role_focus"]
    fallback_recommendations = fallback_payload["recommendations"]

    ai_analysis = ai_payload.get("analysis") if isinstance(ai_payload.get("analysis"), dict) else {}
    ai_scorecard = ai_payload.get("scorecard") if isinstance(ai_payload.get("scorecard"), dict) else {}
    ai_match = ai_payload.get("match") if isinstance(ai_payload.get("match"), dict) else {}
    ai_spelling = ai_payload.get("spelling") if isinstance(ai_payload.get("spelling"), dict) else {}
    ai_quality = ai_payload.get("quality") if isinstance(ai_payload.get("quality"), dict) else {}
    ai_dashboard = ai_payload.get("dashboard") if isinstance(ai_payload.get("dashboard"), dict) else {}
    ai_role_focus = ai_payload.get("role_focus") if isinstance(ai_payload.get("role_focus"), dict) else {}

    analysis = {
        "candidate_name": _resume_ai_text(ai_analysis.get("candidate_name"), fallback_analysis.get("candidate_name", "")),
        "skills": _resume_ai_list(ai_analysis.get("skills"), fallback_analysis.get("skills") or [], 24),
        "education": _resume_ai_list(ai_analysis.get("education"), fallback_analysis.get("education") or [], 5),
        "experience_highlights": _resume_ai_list(
            ai_analysis.get("experience_highlights"),
            fallback_analysis.get("experience_highlights") or [],
            6,
        ),
        "project_highlights": _resume_ai_list(
            ai_analysis.get("project_highlights"),
            fallback_analysis.get("project_highlights") or [],
            6,
        ),
        "contact_found": _resume_ai_bool(ai_analysis.get("contact_found"), fallback_analysis.get("contact_found", False)),
        "section_hits": _resume_ai_list(ai_analysis.get("section_hits"), fallback_analysis.get("section_hits") or [], 12),
        "resume_signal_score": _resume_ai_score(
            ai_analysis.get("resume_signal_score"),
            int(fallback_analysis.get("resume_signal_score") or 0),
        ),
        "analysis_text": _resume_ai_text(ai_analysis.get("analysis_text"), fallback_analysis.get("analysis_text", "")),
        "suggested_roles": _resume_ai_list(ai_analysis.get("suggested_roles"), fallback_analysis.get("suggested_roles") or [], 4),
        "source_file_name": file_name,
    }

    scorecard = {
        "resume_score": _resume_ai_score(ai_scorecard.get("resume_score"), fallback_scorecard.get("resume_score", 0)),
        "structure_score": _resume_ai_score(ai_scorecard.get("structure_score"), fallback_scorecard.get("structure_score", 0)),
        "content_score": _resume_ai_score(ai_scorecard.get("content_score"), fallback_scorecard.get("content_score", 0)),
    }

    match_payload = {
        "job_description_provided": True,
        "match_score": _resume_ai_score(ai_match.get("match_score"), fallback_match.get("match_score", 0) or 0),
        "matched_keywords": _resume_ai_list(ai_match.get("matched_keywords"), fallback_match.get("matched_keywords") or [], 8),
        "missing_keywords": _resume_ai_list(ai_match.get("missing_keywords"), fallback_match.get("missing_keywords") or [], 8),
        "job_keywords": _resume_ai_list(ai_match.get("job_keywords"), fallback_match.get("job_keywords") or [], 16),
        "summary": _resume_ai_text(ai_match.get("summary"), fallback_match.get("summary", "")),
    }

    spelling_issues = _resume_ai_issues(ai_spelling.get("issues"), fallback_spelling.get("issues") or [])
    spelling_payload = {
        "score": _resume_ai_score(ai_spelling.get("score"), fallback_spelling.get("score", 0)),
        "issue_count": max(
            len(spelling_issues),
            int(ai_spelling.get("issue_count") or 0) if str(ai_spelling.get("issue_count") or "").isdigit() else 0,
        ),
        "issues": spelling_issues[:10],
        "summary": _resume_ai_text(ai_spelling.get("summary"), fallback_spelling.get("summary", "")),
    }

    quality = {
        "ats_score": _resume_ai_score(ai_quality.get("ats_score"), fallback_quality.get("ats_score", 0)),
        "impact_score": _resume_ai_score(ai_quality.get("impact_score"), fallback_quality.get("impact_score", 0)),
        "section_coverage_score": _resume_ai_score(
            ai_quality.get("section_coverage_score"),
            fallback_quality.get("section_coverage_score", 0),
        ),
        "word_count": fallback_quality.get("word_count", 0),
        "numeric_mentions": fallback_quality.get("numeric_mentions", 0),
        "quantified_achievements_found": bool(fallback_quality.get("quantified_achievements_found")),
        "detected_sections": fallback_quality.get("detected_sections") or [],
        "missing_sections": fallback_quality.get("missing_sections") or [],
        "contact_checks": fallback_quality.get("contact_checks") or {},
        "strengths": _resume_ai_list(ai_quality.get("strengths"), fallback_quality.get("strengths") or [], 6),
        "improvement_areas": _resume_ai_list(
            ai_quality.get("improvement_areas"),
            fallback_quality.get("improvement_areas") or [],
            6,
        ),
        "must_add": _resume_ai_list(ai_quality.get("must_add"), fallback_quality.get("must_add") or [], 6),
    }

    dashboard = _build_dashboard_payload(scorecard, quality, match_payload, spelling_payload)
    if ai_dashboard:
        dashboard = {
            "meters": _resume_ai_meters(ai_dashboard.get("meters"), dashboard.get("meters") or []),
            "weak_areas": _resume_ai_weak_areas(ai_dashboard.get("weak_areas"), dashboard.get("weak_areas") or []),
        }

    role_focus = _build_role_focus_payload(match_payload, quality, spelling_payload)
    if ai_role_focus:
        role_focus = {
            "target_keywords": _resume_ai_list(
                ai_role_focus.get("target_keywords"),
                role_focus.get("target_keywords") or [],
                10,
            ),
            "matched_keywords": _resume_ai_list(
                ai_role_focus.get("matched_keywords"),
                role_focus.get("matched_keywords") or [],
                8,
            ),
            "missing_keywords": _resume_ai_list(
                ai_role_focus.get("missing_keywords"),
                role_focus.get("missing_keywords") or [],
                8,
            ),
            "where_to_improve": _resume_ai_list(
                ai_role_focus.get("where_to_improve"),
                role_focus.get("where_to_improve") or [],
                5,
            ),
        }

    recommendations = _resume_ai_list(ai_payload.get("recommendations"), fallback_recommendations, 6)

    return {
        "analysis": analysis,
        "scorecard": scorecard,
        "match": match_payload,
        "spelling": spelling_payload,
        "quality": quality,
        "dashboard": dashboard,
        "role_focus": role_focus,
        "recommendations": recommendations,
    }, provider_used, provider_error

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DIRECTORIES ----------------
UPLOAD_DIR = "uploads"
FACE_DB = "face_db"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FACE_DB, exist_ok=True)

# ---------------- FACE EMBEDDING ----------------
def get_embedding(image_path):
    try:
        from deepface import DeepFace

        emb = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet",
            enforce_detection=True
        )
        return np.array(emb[0]["embedding"])
    except Exception:
        return None

# ---------------- AUTH HELPER ----------------
def _decode_token_identity(token: str) -> tuple[dict, str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload, user_id


async def get_current_user(token: str, allow_db_fallback: bool = False):
    payload, user_id = _decode_token_identity(token)

    try:
        user = await users_collection.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise HTTPException(status_code=401, detail="Invalid token")
    except PyMongoError:
        if allow_db_fallback:
            return {
                "_id": ObjectId(user_id),
                "email": payload.get("email", ""),
                "auth_source": "token_fallback",
            }
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check your internet connection or MongoDB configuration and try again.",
        )

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# ================= REGISTER =================
@app.post("/register")
async def register(
    first_name: str = Body(...),
    last_name: str = Body(...),
    email: str = Body(...),
    password: str = Body(...)
):
    if not first_name.strip() or not last_name.strip():
        raise HTTPException(
            status_code=400,
            detail="First name and last name required"
        )

    existing = await users_collection.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    user = {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email,
        "hashed_password": hash_password(password),
        "profile_image": None
    }

    result = await users_collection.insert_one(user)

    return {
        "status": "USER REGISTERED",
        "id": str(result.inserted_id)
    }

# ================= LOGIN =================
@app.post("/login")
async def login(
    email: str = Body(...),
    password: str = Body(...)
):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found"
        )

    if not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=400,
            detail="Invalid password"
        )

    token = create_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })

    return {
        "access_token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "profile_image": user.get("profile_image")
        }
    }

# ================= REGISTER FACE =================
# functionality removed per requirements - endpoint disabled
# @app.post("/register-face")
# async def register_face(
#     file: UploadFile = File(...),
#     authorization: str = Header(...)
# ):
#     token = authorization.replace("Bearer ", "")
#     user = await get_current_user(token)
#
#     img_path = os.path.join(
#         UPLOAD_DIR,
#         f"user_{user['_id']}.jpg"
#     )
#     with open(img_path, "wb") as f:
#         f.write(await file.read())
#
#     embedding = get_embedding(img_path)
#     if embedding is None:
#         return {"status": "FACE NOT DETECTED"}
#
#     np.save(
#         os.path.join(
#             FACE_DB,
#             f"user_{user['_id']}.npy"
#         ),
#         embedding
#     )
#
#     return {"status": "FACE REGISTERED"}

# ================= FACE LOGIN =================
# functionality removed per requirements - endpoint disabled
# @app.post("/login-face")
# async def login_face(
#     file: UploadFile = File(...)
# ):
#     img_path = os.path.join(UPLOAD_DIR, "login.jpg")
#     with open(img_path, "wb") as f:
#         f.write(await file.read())
#
#     new_embedding = get_embedding(img_path)
#     if new_embedding is None:
#         return {"status": "FACE NOT DETECTED"}
#
#     best_user = None
#     best_distance = float("inf")
#
#     for fname in os.listdir(FACE_DB):
#         if fname.endswith(".npy"):
#             uid = fname.replace("user_", "").replace(".npy", "")
#             saved_embedding = np.load(
#                 os.path.join(FACE_DB, fname)
#             )


# ================= PROFILE =================
@app.get("/profile")
async def get_profile(
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token)

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "profile_image": user.get("profile_image")
    }

@app.put("/profile")
async def update_profile(
    first_name: str = Body(None),
    last_name: str = Body(None),
    profile_image: str = Body(None),
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token)

    update_data = {}

    if first_name is not None:
        first_name = first_name.strip()
        if first_name != "":
            update_data["first_name"] = first_name

    if last_name is not None:
        last_name = last_name.strip()
        if last_name != "":
            update_data["last_name"] = last_name


    if profile_image is not None:
            if profile_image == "":
                update_data["profile_image"] =None
            else:
                update_data["profile_image"] = profile_image

    if update_data:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )

    updated_user = await users_collection.find_one(
        {"_id": user["_id"]}
    )

    return {
        "status": "PROFILE UPDATED",
        "user": {
            "id": str(updated_user["_id"]),
            "email": updated_user["email"],
            "first_name": updated_user.get("first_name"),
            "last_name": updated_user.get("last_name"),
            "profile_image": updated_user.get("profile_image")
        }
    }


@app.post("/resume-analyzer")
async def analyze_resume(
    file_name: str = Body(""),
    resume_text: str = Body(""),
    resume_data_url: str = Body(""),
    job_description: str = Body(""),
    authorization: str = Header(...),
):
    token = authorization.replace("Bearer ", "")
    await get_current_user(token, allow_db_fallback=True)

    if not _is_valid_job_description(job_description):
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid job description with enough detail so the resume can be analyzed against the target role.",
        )

    extracted_text = _normalize_resume_text(resume_text)
    if not extracted_text and resume_data_url:
        pdf_bytes = _decode_pdf_data_url(resume_data_url)
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="The uploaded resume could not be decoded.")
        extracted_text = _extract_pdf_text_from_bytes(pdf_bytes)

    extracted_text = _normalize_resume_text(extracted_text)
    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="We could not read text from this PDF. Try a text-based resume PDF instead of a scanned image.",
        )

    fallback_analysis = _build_resume_analysis_payload(extracted_text, file_name)
    fallback_scorecard = _build_resume_scorecard(extracted_text, file_name)
    fallback_match_payload = _build_job_match_payload(extracted_text, job_description)
    fallback_spelling_payload = _build_spelling_payload(extracted_text, fallback_match_payload)
    fallback_quality = _build_resume_quality_payload(
        extracted_text,
        fallback_analysis,
        fallback_scorecard,
        fallback_match_payload,
        file_name,
    )
    fallback_dashboard = _build_dashboard_payload(
        fallback_scorecard,
        fallback_quality,
        fallback_match_payload,
        fallback_spelling_payload,
    )
    fallback_role_focus = _build_role_focus_payload(
        fallback_match_payload,
        fallback_quality,
        fallback_spelling_payload,
    )
    fallback_recommendations = _build_resume_recommendations(
        fallback_analysis,
        fallback_scorecard,
        fallback_match_payload,
        fallback_spelling_payload,
    )

    fallback_payload = {
        "analysis": fallback_analysis,
        "scorecard": fallback_scorecard,
        "match": fallback_match_payload,
        "spelling": fallback_spelling_payload,
        "quality": fallback_quality,
        "dashboard": fallback_dashboard,
        "role_focus": fallback_role_focus,
        "recommendations": fallback_recommendations,
    }

    provider_meta = {
        "analysis_provider": "fallback",
        "report_provider": "fallback",
        "report_model": "",
        "provider_error": "",
    }

    try:
        generated_payload, provider_used, provider_error = await _generate_resume_payload_with_ai(
            extracted_text,
            job_description,
            file_name,
            fallback_payload,
        )
        analysis = generated_payload["analysis"]
        scorecard = generated_payload["scorecard"]
        match_payload = generated_payload["match"]
        spelling_payload = generated_payload["spelling"]
        quality = generated_payload["quality"]
        dashboard = generated_payload["dashboard"]
        role_focus = generated_payload["role_focus"]
        recommendations = generated_payload["recommendations"]
        provider_meta["analysis_provider"] = provider_used
        provider_meta["report_provider"] = provider_used
        provider_meta["report_model"] = OLLAMA_MODEL if provider_used == "ollama" else ""
        provider_meta["provider_error"] = provider_error
    except ProviderError as exc:
        analysis = fallback_analysis
        scorecard = fallback_scorecard
        match_payload = fallback_match_payload
        spelling_payload = fallback_spelling_payload
        quality = fallback_quality
        dashboard = fallback_dashboard
        role_focus = fallback_role_focus
        recommendations = fallback_recommendations
        provider_meta["provider_error"] = (
            "Gemini and Ollama/Qwen were unavailable, timed out, or returned invalid JSON. "
            + str(exc)
        )

    return {
        "status": "RESUME_ANALYZED",
        "resume_text": extracted_text,
        "analysis": analysis,
        "scorecard": scorecard,
        "match": match_payload,
        "dashboard": dashboard,
        "spelling": spelling_payload,
        "role_focus": role_focus,
        "quality": quality,
        "recommendations": recommendations,
        "providers": provider_meta,
    }

# ================= INTERVIEW RESULTS =================
@app.post("/interview-result")
async def save_interview_result(
    user_id: str = Body(...),
    category: str = Body(...),
    score: int = Body(...),
    transcript: str = Body(...),
    questions_answered: int = Body(...),
    authorization: str = Header(...)
):
    """Save interview result to database"""
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)

        interview_result = {
            "user_id": user_id,
            "category": category,
            "score": score,
            "transcript": transcript,
            "questions_answered": questions_answered,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        result = await users_collection.update_one(
            {"_id": current_user["_id"]},
            {
                "$push": {
                    "interview_results": interview_result
                }
            }
        )

        return {
            "status": "INTERVIEW RESULT SAVED",
            "score": score,
            "category": category
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save interview result: {str(e)}"
        )


# ================= AI INTERVIEW =================
@app.post("/ai-interview/start")
async def start_ai_interview(
    payload: dict = Body(...),
    authorization: str = Header(None)
):
    try:
        session = await create_interview_session(payload)
        return session
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")


@app.get("/ai-interview/providers/status")
async def ai_provider_status():
    try:
        return get_ai_provider_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to inspect AI providers: {exc}")


@app.get("/coding/runtime-status")
async def coding_runtime_status():
    try:
        return get_coding_runtime_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to inspect coding runtimes: {exc}")


@app.post("/coding/challenge")
async def create_coding_challenge(payload: dict = Body(...)):
    try:
        difficulty = payload.get("difficulty") or "easy"
        excluded_questions = payload.get("excluded_questions") or []
        challenge = await generate_coding_challenge(difficulty, excluded_questions=excluded_questions)
        return {"challenge": challenge}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate coding challenge: {exc}")


@app.post("/coding/run")
async def run_coding_submission(payload: dict = Body(...)):
    try:
        language = (payload.get("language") or "").strip().lower()
        source_code = payload.get("source_code") or ""
        test_cases = payload.get("test_cases") or []
        return run_code_against_tests(language, source_code, test_cases)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run coding submission: {exc}")


@app.post("/coding/submit")
async def submit_coding_solution(payload: dict = Body(...)):
    try:
        language = (payload.get("language") or "").strip().lower()
        source_code = payload.get("source_code") or ""
        challenge = payload.get("challenge") or {}
        all_cases = list(challenge.get("public_test_cases") or []) + list(challenge.get("hidden_test_cases") or [])
        execution = run_code_against_tests(language, source_code, all_cases)
        review = await evaluate_coding_submission(challenge, language, source_code, execution)
        return {
            "execution": execution,
            "review": review,
        }
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to submit coding solution: {exc}")


@app.get("/ai-interview/session/{session_id}")
async def ai_interview_session_status(session_id: str):
    try:
        session = await get_session_status(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
        return session
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load interview session: {exc}")


@app.post("/ai-interview/evaluate")
async def evaluate_ai_interview_answer(
    session_id: str = Body(...),
    question_index: int = Body(...),
    answer: str = Body(...),
):
    try:
        return await evaluate_interview_answer(session_id, question_index, answer)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {exc}")


@app.post("/ai-interview/complete")
async def complete_ai_interview(
    session_id: str = Body(...),
    ended_early: bool = Body(False),
    authorization: str = Header(None)
):
    try:
        summary = await complete_interview_session(session_id, ended_early=ended_early)
        session = await get_session_payload(session_id)
        current_user = None
        save_warning = None

        if authorization and session:
            token = authorization.replace("Bearer ", "")
            try:
                current_user = await get_current_user(token)
                current_user_id = str(current_user["_id"])
                saved_user_ids = session.setdefault("saved_report_user_ids", [])

                if current_user_id not in saved_user_ids:
                    interview_result = {
                        "session_id": session_id,
                        "category": session.get("context", {}).get("category") or "general",
                        "selected_mode": session.get("context", {}).get("selected_mode"),
                        "job_role": session.get("context", {}).get("job_role"),
                        "primary_language": session.get("context", {}).get("primary_language"),
                        "experience": session.get("context", {}).get("experience"),
                        "context": session.get("context", {}),
                        "score": summary.get("overall_score", 0),
                        "ended_early": summary.get("ended_early", False),
                        "summary": summary.get("summary"),
                        "top_strengths": summary.get("top_strengths", []),
                        "improvement_areas": summary.get("improvement_areas", []),
                        "strongest_questions": summary.get("strongest_questions", []),
                        "needs_work_questions": summary.get("needs_work_questions", []),
                        "score_breakdown": summary.get("score_breakdown"),
                        "providers": summary.get("providers"),
                        "answers": session.get("answers", []),
                        "evaluations": session.get("evaluations", []),
                        "questions_answered": len(session.get("evaluations", [])),
                        "total_questions": len(session.get("questions", [])),
                        "question_outline": session.get("question_outline", summary.get("questions", [])),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }

                    await users_collection.update_one(
                        {"_id": current_user["_id"]},
                        {"$push": {"interview_results": interview_result}},
                    )
                    session = await mark_session_report_saved(session_id, current_user_id) or session
            except Exception as save_exc:
                save_warning = f"Interview completed, but saving the report failed: {save_exc}"

        return {
            **summary,
            "context": session.get("context", {}) if session else {},
            "answers": session.get("answers", []) if session else [],
            "evaluations": session.get("evaluations", []) if session else [],
            "questions_answered": len(session.get("evaluations", [])) if session else 0,
            "question_outline": session.get("question_outline", []) if session else [],
            "user": (
                {
                    "id": str(current_user["_id"]),
                    "email": current_user.get("email"),
                    "first_name": current_user.get("first_name"),
                    "last_name": current_user.get("last_name"),
                }
                if current_user
                else None
            ),
            "save_warning": save_warning,
        }
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to complete interview: {exc}")


@app.get("/interview-reports")
async def get_interview_reports(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        normalized_reports = list(reversed(reports))
        return {"reports": normalized_reports}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch interview reports: {exc}")


@app.get("/interview-reports/{session_id}")
async def get_interview_report(session_id: str, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        match = next((item for item in reports if item.get("session_id") == session_id), None)

        if not match:
            raise HTTPException(status_code=404, detail="Interview report not found")

        return {"report": match}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch interview report: {exc}")

