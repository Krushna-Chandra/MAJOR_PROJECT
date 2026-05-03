import os
import base64
import codecs
import re
import zlib
import difflib
import uuid
import smtplib
from email.message import EmailMessage
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
import numpy as np
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Header,
    Body,
    Query
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError
from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import PyMongoError
from database import users_collection, report_ratings_collection
from auth_utils import (
    hash_password,
    verify_password,
    create_token,
    create_email_verification_token,
    send_verification_email,
    verify_email_token,
    SECRET_KEY,
    ALGORITHM
)
from coding_ai import (
    build_fallback_coding_review,
    evaluate_coding_submission,
    generate_coding_challenge,
    get_coding_runtime_status,
    merge_execution_results,
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
    generate_advanced_quant_questions,
    generate_aptitude_questions,
    generate_computer_fundamentals_questions,
    generate_reasoning_questions,
    generate_verbal_questions,
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

RESUME_STRUCTURED_SECTION_KEYWORDS = {
    "objective": [
        "career objective",
        "objective",
        "professional summary",
        "summary",
        "profile",
        "professional profile",
        "about me",
        "about",
    ],
    "education": [
        "education",
        "educational qualification",
        "educational qualifications",
        "academic background",
        "academic qualification",
        "academics",
        "qualifications",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "career",
        "job experience",
    ],
    "projects_internships": [
        "internships and projects",
        "internships & projects",
        "internship and projects",
        "internship & projects",
        "projects and internships",
        "projects & internships",
        "project and internships",
        "project & internships",
    ],
    "projects": [
        "projects",
        "project",
        "project experience",
        "academic projects",
        "personal projects",
    ],
    "internships": [
        "internships",
        "internship",
        "internship experience",
        "industrial training",
        "training",
    ],
    "skills": [
        "technical skills",
        "key skills",
        "skills",
        "core competencies",
        "competencies",
        "technical competencies",
        "programming skills",
        "tools & technologies",
        "tools and technologies",
        "tools",
        "technologies",
    ],
    "achievements": [
        "achievements",
        "key achievements",
        "accomplishments",
        "awards",
        "awards & recognition",
        "recognitions",
    ],
    "languages": [
        "languages known",
        "languages",
        "language",
        "language proficiency",
        "linguistic abilities",
    ],
    "hobbies": [
        "hobbies",
        "interests",
        "extra curricular",
        "extracurricular activities",
        "personal interests",
        "activities",
        "hobbies and interests",
    ],
    "personal": [
        "personal details",
        "personal information",
    ],
    "declaration": [
        "declaration",
        "declarations",
    ],
}

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

JOB_REQUIREMENT_SECTION_PATTERNS = [
    "requirements",
    "required qualifications",
    "preferred qualifications",
    "qualifications",
    "responsibilities",
    "what you will do",
    "what we're looking for",
    "must have",
    "nice to have",
]

JOB_EDUCATION_PATTERNS = [
    r"\b(bachelor(?:'s)?(?: degree)?|master(?:'s)?(?: degree)?|phd|b\.tech|m\.tech|bca|mca|b\.e\.|bsc|msc|mba|degree in [a-z &/,-]+)\b",
]

JOB_EXPERIENCE_PATTERNS = [
    r"\b\d+\+?\s+years? of experience\b",
    r"\b\d+\+?\s+years? experience\b",
    r"\bexperience with [a-z0-9 +#./,-]+\b",
    r"\bproven experience [a-z0-9 +#./,-]+\b",
]

JOB_CERTIFICATION_PATTERNS = [
    r"\b(certification|certified|aws certified|pmp|scrum master|azure certification|google cloud certification)\b",
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

RESUME_HEADINGS_FOR_NORMALIZATION = [
    "CAREER OBJECTIVE",
    "PROFESSIONAL SUMMARY",
    "SUMMARY",
    "PROFILE",
    "EDUCATIONAL QUALIFICATION",
    "EDUCATIONAL QUALIFICATIONS",
    "EDUCATION",
    "TECHNICAL SKILLS",
    "INTERNSHIPS & PROJECTS",
    "INTERNSHIPS AND PROJECTS",
    "PROJECTS & INTERNSHIPS",
    "PROJECTS AND INTERNSHIPS",
    "INTERNSHIP & PROJECTS",
    "INTERNSHIP AND PROJECTS",
    "PROJECT & INTERNSHIPS",
    "PROJECT AND INTERNSHIPS",
    "INTERNSHIPS",
    "INTERNSHIP",
    "PROJECTS",
    "PROJECT",
    "EXPERIENCE",
    "WORK EXPERIENCE",
    "PROFESSIONAL EXPERIENCE",
    "HOBBIES",
    "INTERESTS",
    "PERSONAL DETAILS",
    "ACHIEVEMENTS",
    "ACHEIVEMENTS",
    "CERTIFICATIONS",
    "DECLARATION",
]

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
            text = _clean_extracted_pdf_text("\n".join(text_parts))
            if text:
                return text
        except Exception:
            continue
    return _extract_pdf_text_without_dependencies(pdf_bytes)


def _insert_resume_heading_breaks(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""

    heading_pattern = "|".join(
        re.sub(r"\s+", r"\\s*", re.escape(heading))
        for heading in sorted(RESUME_HEADINGS_FOR_NORMALIZATION, key=len, reverse=True)
    )
    return re.sub(
        rf"(?i)(?<![A-Z0-9])({heading_pattern})(?![A-Z0-9])",
        lambda match: f"\n{match.group(1)}\n",
        text,
    )


def _normalize_table_rows(value: str) -> str:
    lines = []
    for raw_line in str(value or "").splitlines():
        if "\t" in raw_line or re.search(r" {4,}", raw_line):
            cells = [cell.strip() for cell in re.split(r"\t| {4,}", raw_line) if cell.strip()]
            if len(cells) > 1:
                lines.append(" | ".join(cells))
                continue
        lines.append(raw_line)
    return "\n".join(lines)


def _clean_extracted_pdf_text(value: str) -> str:
    cleaned = str(value or "")
    cleaned = cleaned.replace("\x00", "")
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", cleaned)
    cleaned = re.sub(r"[•·▪◦●]", "\n- ", cleaned)
    cleaned = re.sub(r"[â€¢Â·â–ªâ—¦]", "\n- ", cleaned)
    cleaned = re.sub(r"(?<=\b[A-Z])[ \t]+(?=[A-Z]\b)", "", cleaned)
    cleaned = _normalize_table_rows(cleaned)
    cleaned = _insert_resume_heading_breaks(cleaned)
    cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _decode_pdf_text_fragment(value: bytes) -> str:
    raw = bytes(value or b"").strip()
    if not raw:
        return ""

    if raw.startswith(codecs.BOM_UTF16_BE) or raw.startswith(codecs.BOM_UTF16_LE):
        for encoding in ("utf-16", "utf-16-be", "utf-16-le"):
            try:
                return _clean_extracted_pdf_text(raw.decode(encoding, errors="ignore"))
            except Exception:
                continue

    if b"\x00" in raw:
        candidates = []
        for encoding in ("utf-16-be", "utf-16-le"):
            try:
                decoded = raw.decode(encoding, errors="ignore")
            except Exception:
                continue
            printable = sum(1 for char in decoded if char.isprintable() and char not in "\x00\x01\x02")
            if printable:
                candidates.append((printable, decoded))
        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            return _clean_extracted_pdf_text(candidates[0][1])

    for encoding in ("utf-8", "latin1"):
        try:
            return _clean_extracted_pdf_text(raw.decode(encoding, errors="ignore"))
        except Exception:
            continue
    return ""


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

    return _decode_pdf_text_fragment(bytes(result))


def _decode_pdf_hex_string(value: bytes) -> str:
    payload = re.sub(rb"\s+", b"", value[1:-1])
    if not payload:
        return ""
    if len(payload) % 2 == 1:
        payload += b"0"
    try:
        decoded = bytes.fromhex(payload.decode("ascii", errors="ignore"))
    except Exception:
        return ""
    return _decode_pdf_text_fragment(decoded)


def _extract_printable_pdf_runs(value: bytes) -> list[str]:
    if not value:
        return []
    matches = re.findall(rb"[A-Za-z0-9@._%+\-:/\\(),#& ]{4,}", value)
    chunks = []
    for match in matches:
        decoded = _decode_pdf_text_fragment(match)
        cleaned = re.sub(r"\s+", " ", decoded).strip()
        if len(cleaned) >= 4 and re.search(r"[A-Za-z]", cleaned):
            chunks.append(cleaned)
    return chunks


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
            hex_strings = re.findall(rb"<[0-9A-Fa-f\s]{4,}>", candidate)
            decoded_strings = []
            for item in literal_strings:
                decoded = _decode_pdf_literal_string(item)
                cleaned = re.sub(r"\s+", " ", decoded).strip()
                if len(cleaned) >= 2 and re.search(r"[A-Za-z]", cleaned):
                    decoded_strings.append(cleaned)
            for item in hex_strings:
                decoded = _decode_pdf_hex_string(item)
                cleaned = re.sub(r"\s+", " ", decoded).strip()
                if len(cleaned) >= 2 and re.search(r"[A-Za-z]", cleaned):
                    decoded_strings.append(cleaned)
            decoded_strings.extend(_extract_printable_pdf_runs(candidate))

            if decoded_strings:
                extracted_chunks.extend(decoded_strings)

    if not extracted_chunks:
        extracted_chunks.extend(_extract_printable_pdf_runs(pdf_bytes))

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

    return _clean_extracted_pdf_text("\n".join(deduped[:500]))


def _decode_pdf_data_url(data_url: str) -> bytes:
    if not data_url or "," not in data_url:
        return b""
    try:
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except Exception:
        return b""


def _collapse_spaced_characters(value: str) -> str:
    def _collapse_segment(segment: str) -> str:
        piece = (segment or "").strip()
        if not piece:
            return ""
        tokens = [token for token in re.split(r"\s+", piece) if token]
        if len(tokens) < 2:
            return piece

        alpha_lengths = [len(re.sub(r"[^A-Za-z0-9]", "", token)) for token in tokens]
        mostly_spelled = sum(1 for length in alpha_lengths if length <= 1) >= max(2, len(tokens) - 1)
        if not mostly_spelled:
            return piece

        collapsed_piece = "".join(tokens)
        collapsed_piece = re.sub(r"\(\s*", "(", collapsed_piece)
        collapsed_piece = re.sub(r"\s*\)", ")", collapsed_piece)
        collapsed_piece = re.sub(r"\s*([,.:;!?])", r"\1", collapsed_piece)
        return collapsed_piece

    normalized_lines = []
    for raw_line in str(value or "").splitlines():
        parts = re.split(r"(\s{2,})", raw_line)
        rebuilt = []
        for part in parts:
            if re.fullmatch(r"\s{2,}", part or ""):
                rebuilt.append(" ")
            else:
                rebuilt.append(_collapse_segment(part))
        line = "".join(rebuilt)
        line = re.sub(r"[ \t]{2,}", " ", line).strip()
        normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _canonical_resume_heading(line: str) -> str:
    compact = re.sub(r"[^A-Z]", "", (line or "").upper())
    heading_map = {
        "CAREEROBJECTIVE": "CAREER OBJECTIVE",
        "PROFESSIONALSUMMARY": "PROFESSIONAL SUMMARY",
        "SUMMARY": "SUMMARY",
        "PROFILE": "PROFILE",
        "EDUCATIONALQUALIFICATION": "EDUCATIONAL QUALIFICATION",
        "EDUCATIONALQUALIFICATIONS": "EDUCATIONAL QUALIFICATIONS",
        "EDUCATION": "EDUCATION",
        "TECHNICALSKILLS": "TECHNICAL SKILLS",
        "SKILLS": "SKILLS",
        "INTERNSHIPSPROJECTS": "INTERNSHIPS AND PROJECTS",
        "INTERNSHIPSANDPROJECTS": "INTERNSHIPS AND PROJECTS",
        "PROJECTSINTERNSHIPS": "PROJECTS AND INTERNSHIPS",
        "PROJECTSANDINTERNSHIPS": "PROJECTS AND INTERNSHIPS",
        "INTERNSHIPS": "INTERNSHIPS",
        "INTERNSHIP": "INTERNSHIP",
        "PROJECTS": "PROJECTS",
        "PROJECT": "PROJECT",
        "EXPERIENCE": "EXPERIENCE",
        "WORKEXPERIENCE": "WORK EXPERIENCE",
        "PROFESSIONALEXPERIENCE": "PROFESSIONAL EXPERIENCE",
        "HOBBIES": "HOBBIES",
        "INTERESTS": "INTERESTS",
        "PERSONALDETAILS": "PERSONAL DETAILS",
        "ACHIEVEMENTS": "ACHIEVEMENTS",
        "ACHEIVEMENTS": "ACHIEVEMENTS",
        "CERTIFICATIONS": "CERTIFICATIONS",
        "DECLARATION": "DECLARATION",
        "CURRICULUMVITAE": "CURRICULUM VITAE",
    }
    return heading_map.get(compact, "")


def _normalize_resume_line(value: str) -> str:
    line = str(value or "").replace("\x00", "").strip()
    if not line:
        return ""

    line = _collapse_spaced_characters(line)
    line = re.sub(r"(?<=\b[A-Za-z])[ \t]+(?=[A-Za-z]\b)", "", line)
    line = line.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    line = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", line)
    line = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", line)
    line = re.sub(r"\s*\|\s*", " | ", line)
    line = re.sub(r"\s*,\s*", ", ", line)
    line = re.sub(r"\s*:\s*", ": ", line)
    line = re.sub(r"[ \t]{2,}", " ", line).strip(" -\t")

    canonical_heading = _canonical_resume_heading(line)
    if canonical_heading:
        inline_match = re.match(rf"^{re.escape(canonical_heading)}\s*[:\-]\s*(.+)$", line, re.I)
        if inline_match:
            trailing_text = inline_match.group(1).strip()
            if trailing_text:
                return f"{canonical_heading}: {trailing_text}"
        return canonical_heading

    label_aliases = {
        "LANGUAGESKNOWN": "Languages Known",
        "TECHNICALSKILLS": "Technical Skills",
        "CAREEROBJECTIVE": "Career Objective",
        "EDUCATIONALQUALIFICATION": "Educational Qualification",
        "EDUCATIONALQUALIFICATIONS": "Educational Qualifications",
        "PERSONALDETAILS": "Personal Details",
    }
    compact_line = re.sub(r"[^A-Z]", "", line.upper())
    for compact_prefix, label in label_aliases.items():
        if compact_line.startswith(compact_prefix):
            parts = re.split(r"\s*:\s*", line, maxsplit=1)
            if len(parts) == 2:
                return f"{label}: {parts[1].strip()}"
            return label

    return line.strip()


def _prepare_resume_lines(value: str) -> list[str]:
    prepared = []
    previous = None
    for raw_line in str(value or "").splitlines():
        normalized_line = _normalize_resume_line(raw_line)
        if not normalized_line:
            continue
        if normalized_line == previous:
            continue
        previous = normalized_line
        prepared.append(normalized_line)

    merged_prepared = []
    index = 0
    while index < len(prepared):
        current = prepared[index]
        next_line = prepared[index + 1] if index + 1 < len(prepared) else ""
        third_line = prepared[index + 2] if index + 2 < len(prepared) else ""
        if (
            current in {"INTERNSHIPS", "INTERNSHIP", "PROJECTS", "PROJECT"}
            and next_line == "&"
            and third_line in {"INTERNSHIPS", "INTERNSHIP", "PROJECTS", "PROJECT"}
        ):
            if current.startswith("INTERNSHIP"):
                merged_prepared.append("INTERNSHIPS AND PROJECTS")
            else:
                merged_prepared.append("PROJECTS AND INTERNSHIPS")
            index += 3
            continue
        merged_prepared.append(current)
        index += 1
    return merged_prepared


def _classify_resume_section_line(line: str) -> tuple[str, str]:
    raw_line = str(line or "").strip()
    if not raw_line:
        return "", ""

    canonical_line = _canonical_keyword(raw_line)
    for section_name, keywords in RESUME_STRUCTURED_SECTION_KEYWORDS.items():
        for keyword in keywords:
            canonical_keyword = _canonical_keyword(keyword)
            if canonical_line == canonical_keyword:
                return section_name, ""
            match = re.match(rf"^{re.escape(keyword)}\s*:\s*(.+)$", raw_line, re.I)
            if match:
                return section_name, match.group(1).strip()
    return "", ""


def _score_resume_line_for_section(line: str, section_name: str) -> int:
    normalized = _normalize_resume_text(_collapse_spaced_characters(line))
    lowered = normalized.lower()
    if not normalized or normalized == "❖":
        return -1

    word_count = len(re.findall(r"[A-Za-z0-9+#]+", normalized))
    education_hit = bool(
        re.search(r"\b(college|school|university|b\.?tech|bachelor|master|degree|class|cbse|bput|matric|science)\b", lowered)
    )
    skill_hit = bool(_extract_resume_skills(normalized)) or bool(
        re.search(r"\b(c#|c\+\+|c|html|css|javascript|java script|java|python|numpy|pandas|matplotlib|machine learning|artificial intelligence)\b", lowered)
    )
    hobby_hit = bool(re.search(r"\b(playing|singing|gardening|reading|writing|traveling|travelling|music|sports)\b", lowered))
    experience_hit = bool(
        re.search(r"\b(developed|contributed|worked|learned|designed|built|implemented|improved|created|driving|adopted)\b", lowered)
    )
    project_hit = bool(
        re.search(r"\b(intern|internship|project|system|frontend|front-end|application|extension|machine learning|prediction|scheduling|drdo|range|establishment)\b", lowered)
    )

    score = 0
    if section_name == "skills":
        if skill_hit:
            score += 6
        if word_count <= 6 and not education_hit and not experience_hit:
            score += 2
        if hobby_hit or education_hit:
            score -= 4
    elif section_name == "hobbies":
        if hobby_hit:
            score += 6
        if word_count <= 4 and not skill_hit and not education_hit:
            score += 2
        if skill_hit or education_hit:
            score -= 4
    elif section_name == "education":
        if education_hit:
            score += 7
        if re.search(r"\b(2020|2021|2022|2023|2024|2025|2026|present|continuing)\b", lowered):
            score += 1
        if skill_hit or hobby_hit:
            score -= 3
    elif section_name == "experience":
        if experience_hit:
            score += 6
        if word_count >= 8:
            score += 1
        if education_hit or hobby_hit:
            score -= 3
    elif section_name in {"projects", "projects_internships", "internships"}:
        if project_hit:
            score += 6
        if re.search(r"\b(member|ambassador|attendee|facilitator)\b", lowered) and not project_hit:
            score -= 5
    elif section_name == "objective":
        if lowered.startswith("to ") or word_count >= 12:
            score += 4
    return score


def _pick_pending_resume_section(line: str, pending_sections: list[str]) -> str:
    scored = []
    for index, section_name in enumerate(pending_sections):
        score = _score_resume_line_for_section(line, section_name)
        if score > 0:
            scored.append((score, -index, section_name))
    return max(scored)[2] if scored else ""


def _build_resume_section_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current_section = ""
    inline_only_sections = {"languages", "hobbies"}
    pending_sections: list[str] = []
    previous_was_heading = False

    for line in _prepare_resume_lines(text):
        section_name, trailing = _classify_resume_section_line(line)
        if section_name:
            blocks.setdefault(section_name, [])
            if trailing:
                blocks[section_name].append(trailing)
            if previous_was_heading and not trailing:
                if section_name not in pending_sections:
                    pending_sections.append(section_name)
                current_section = ""
            else:
                pending_sections = [section_name] if not trailing else []
                current_section = "" if section_name in inline_only_sections and trailing else section_name
            previous_was_heading = True
            continue

        previous_was_heading = False

        if len(pending_sections) > 1:
            matched_section = _pick_pending_resume_section(line, pending_sections)
            if matched_section:
                blocks.setdefault(matched_section, []).append(line)
                current_section = matched_section
                continue

        if current_section:
            blocks.setdefault(current_section, []).append(line)

    return blocks


def _get_resume_section_lines(text: str, section_names: list[str], limit: int | None = None) -> list[str]:
    blocks = _build_resume_section_blocks(text)
    collected = []
    seen = set()
    for section_name in section_names:
        for item in blocks.get(section_name, []):
            cleaned = str(item or "").strip()
            canonical = _canonical_keyword(cleaned)
            if not cleaned or not canonical or canonical in seen:
                continue
            seen.add(canonical)
            collected.append(cleaned)
            if limit and len(collected) >= limit:
                return collected[:limit]
    return collected[:limit] if limit else collected


def _prepare_resume_text_for_analysis(value: str) -> str:
    prepared_lines = _prepare_resume_lines(value)
    return "\n".join(prepared_lines).strip()


def _prepare_resume_text_for_display(value: str) -> str:
    cleaned = _prepare_resume_text_for_analysis(value)
    if not cleaned:
        return ""

    normalized = cleaned.lower()
    normalized = re.sub(r"\s*&\s*", " and ", normalized)
    normalized = re.sub(r"[^\w\s@.+,#:/()-]", " ", normalized)
    normalized = _insert_resume_heading_breaks(normalized)
    normalized = re.sub(r"\s*\n\s*", "\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _normalize_resume_text(value: str) -> str:
    raw = _prepare_resume_text_for_analysis(value)
    raw = re.sub(r"(?<=\b[A-Z])[ \t]+(?=[A-Z]\b)", "", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def _dedupe_text_list(values: list[str]) -> list[str]:
    deduped = []
    seen = set()
    for item in values or []:
        cleaned = _normalize_resume_text(str(item or ""))
        canonical = cleaned.lower()
        if not cleaned or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(cleaned)
    return deduped


def _normalize_contact_text(value: str) -> str:
    raw = str(value or "")
    collapsed = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", raw)
    collapsed = re.sub(r"\s*@\s*", "@", collapsed)
    collapsed = re.sub(r"\s*\.\s*", ".", collapsed)
    collapsed = re.sub(r"([A-Za-z0-9._%+-])\s+(?=[A-Za-z0-9._%+-]*@)", r"\1", collapsed)
    collapsed = re.sub(r"(?<=@)\s+", "", collapsed)
    collapsed = re.sub(r"\s+(?=\.)", "", collapsed)
    collapsed = re.sub(r"(?<=\.)\s+", "", collapsed)
    return collapsed


def _extract_resume_emails(text: str) -> list[str]:
    normalized_text = _normalize_contact_text(text)
    emails = re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", normalized_text, re.I)
    deduped = []
    seen = set()
    for email in emails:
        cleaned = email.strip(".,;:()[]{}<> ").lower()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _extract_resume_phones(text: str) -> list[str]:
    normalized_text = _normalize_contact_text(text)
    phones = re.findall(r"(\+?\d[\d\s().-]{8,}\d)", normalized_text)
    deduped = []
    seen = set()
    for phone in phones:
        cleaned = re.sub(r"\s+", " ", phone).strip()
        canonical = re.sub(r"\D", "", cleaned)
        if len(canonical) < 10 or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(cleaned)
    return deduped


def _resume_signal_details(text: str, file_name: str = "") -> dict:
    normalized = _normalize_resume_text(text)
    lowered = normalized.lower()
    filename = (file_name or "").lower()
    skill_hits = _extract_resume_skills(text)
    section_hits = [keyword for keyword in RESUME_SECTION_KEYWORDS if keyword in lowered]
    word_count = len([word for word in normalized.split(" ") if word])
    extracted_emails = _extract_resume_emails(text)
    extracted_phones = _extract_resume_phones(text)

    has_email = bool(extracted_emails)
    has_phone = bool(extracted_phones)
    has_profile_link = bool(re.search(r"(linkedin|github|portfolio)", lowered))
    has_education = bool(re.search(r"\b(bachelor|master|b\.tech|m\.tech|degree|university|college|school)\b", lowered))
    has_experience = bool(re.search(r"\b(intern|internship|experience|engineer|developer|manager|analyst|specialist|coordinator|student|worked|employment|company|consultant|associate|executive)\b", lowered))
    has_project = bool(re.search(r"\b(project|projects|developed|built|created|implemented|designed|designd|prototype|application|system)\b", lowered))
    has_resume_heading = bool(re.search(r"\b(resume|curriculum vitae|cv)\b", lowered))
    has_achievement_language = bool(re.search(r"\b(led|improved|increased|reduced|optimized|delivered|managed|launched|achieved)\b", lowered))
    has_dates = bool(re.search(r"\b(19|20)\d{2}\b", lowered))
    filename_says_resume = any(token in filename for token in ["resume", "cv", "curriculum vitae"])
    academic_document_hits = _dedupe_text_list([
        keyword
        for keyword in [
            "marksheet",
            "mark sheet",
            "transcript",
            "statement of marks",
            "grade sheet",
            "report card",
            "hall ticket",
            "admit card",
            "subject code",
            "marks obtained",
            "maximum marks",
            "credit points",
            "sgpa",
            "cgpa",
            "gpa",
            "semester",
            "roll no",
            "roll number",
            "registration number",
            "enrollment number",
        ]
        if keyword in lowered
    ])
    has_academic_record_language = bool(academic_document_hits)

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
    if has_academic_record_language and not (has_experience or has_project or has_profile_link):
        score -= 3

    return {
        "normalized": normalized,
        "score": score,
        "text_length": len(normalized),
        "word_count": word_count,
        "filename_says_resume": filename_says_resume,
        "has_resume_heading": has_resume_heading,
        "has_email": has_email,
        "has_phone": has_phone,
        "emails": extracted_emails,
        "phones": extracted_phones,
        "has_profile_link": has_profile_link,
        "has_education": has_education,
        "has_experience": has_experience,
        "has_project": has_project,
        "has_achievement_language": has_achievement_language,
        "has_dates": has_dates,
        "has_academic_record_language": has_academic_record_language,
        "academic_document_hits": academic_document_hits,
        "skill_hits": skill_hits,
        "section_hits": section_hits,
    }


def _looks_like_resume(text: str, file_name: str = "") -> tuple[bool, str]:
    details = _resume_signal_details(text, file_name)

    contact_signals = int(details["has_email"]) + int(details["has_phone"]) + int(details["has_profile_link"])
    core_resume_signals = int(details["has_education"]) + int(details["has_experience"]) + int(details["has_project"])
    section_signal_count = len(details["section_hits"])
    strong_resume_evidence = (
        (contact_signals >= 1 and (details["has_experience"] or details["has_project"])) or
        (details["has_experience"] and bool(details["skill_hits"])) or
        (details["has_project"] and bool(details["skill_hits"])) or
        (section_signal_count >= 2 and contact_signals >= 1) or
        (details["filename_says_resume"] and contact_signals >= 1) or
        (details["has_resume_heading"] and contact_signals >= 1)
    )

    if details["text_length"] < 25 and not details["filename_says_resume"]:
        return False, "This file does not contain enough readable content to verify it as a resume or CV."

    academic_hits = len(details["academic_document_hits"] or [])
    if details["has_academic_record_language"] and academic_hits >= 3 and not strong_resume_evidence:
        return False, (
            "This PDF looks more like an academic document such as a marksheet or transcript than a resume. "
            "Please upload a text-based resume PDF."
        )

    if details["score"] >= 4:
        return True, ""

    fresher_resume_like = (
        details["word_count"] >= 35 and
        (
            (contact_signals >= 1 and core_resume_signals >= 1) or
            (contact_signals >= 1 and section_signal_count >= 1) or
            (details["has_education"] and details["skill_hits"]) or
            (details["has_project"] and details["skill_hits"]) or
            (details["has_experience"] and details["has_dates"])
        )
    )
    if fresher_resume_like:
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

    missing_hints = []
    if contact_signals == 0:
        missing_hints.append("contact details like email, phone, or LinkedIn")
    if section_signal_count == 0 and core_resume_signals == 0:
        missing_hints.append("resume sections like Skills, Education, Experience, or Projects")
    if details["word_count"] < 35:
        missing_hints.append("enough readable resume text")

    if missing_hints:
        return (
            False,
            "This PDF does not appear to be a resume yet. Please upload a text-based resume PDF with "
            + ", ".join(missing_hints)
            + ".",
        )

    return False, "This document does not look like a resume or CV. Please upload a proper resume/CV file."


def _extract_resume_skills(text: str) -> list[str]:
    normalized = _normalize_resume_text(text).lower()
    display_map = {
        "html": "HTML",
        "css": "CSS",
        "javascript": "JavaScript",
        "java script": "JavaScript",
        "java": "Java",
        "python": "Python",
        "numpy": "NumPy",
        "num py": "NumPy",
        "pandas": "Pandas",
        "matplotlib": "Matplotlib",
    }
    found = []
    for skill in KNOWN_RESUME_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, normalized):
            found.append(display_map.get(skill.lower(), skill.title() if skill.islower() else skill))

    extra_skill_aliases = {
        "javascript (basics)": "JavaScript",
        "java script": "JavaScript",
        "java (basics)": "Java",
        "data preprocessing": "Data Preprocessing",
        "datapreprocessing": "Data Preprocessing",
        "data cleaning": "Data Cleaning",
        "matplotlib": "Matplotlib",
        "numpy": "NumPy",
        "num py": "NumPy",
        "pandas": "Pandas",
    }
    for alias, label in extra_skill_aliases.items():
        if alias in normalized:
            found.append(label)
    deduped = []
    seen = set()
    for item in found:
        canonical = _canonical_keyword(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(item)
    return deduped[:24]


def _format_resume_skill_label(value: str) -> str:
    canonical = _canonical_keyword(value)
    if not canonical:
        return ""
    label_map = {
        "html": "HTML",
        "css": "CSS",
        "javascript": "JavaScript",
        "javascript basics": "JavaScript (Basics)",
        "java": "Java",
        "java basics": "Java (Basics)",
        "python": "Python",
        "numpy": "NumPy",
        "pandas": "Pandas",
        "matplotlib": "Matplotlib",
        "data preprocessing": "Data Preprocessing",
        "datapreprocessing": "Data Preprocessing",
        "datapreprocessing cleaning": "Data Cleaning",
        "data cleaning": "Data Cleaning",
    }
    if canonical in label_map:
        return label_map[canonical]
    fuzzy_prefixes = [
        ("matplot", "Matplotlib"),
        ("matpl", "Matplotlib"),
        ("pand", "Pandas"),
        ("nump", "NumPy"),
        ("pyth", "Python"),
        ("javasc", "JavaScript"),
        ("java script", "JavaScript"),
        ("javascript basic", "JavaScript (Basics)"),
        ("java basic", "Java (Basics)"),
        ("jav", "Java"),
        ("html", "HTML"),
        ("css", "CSS"),
        ("data preprocess", "Data Preprocessing"),
        ("preprocess", "Data Preprocessing"),
        ("data clean", "Data Cleaning"),
        ("cleaning", "Data Cleaning"),
    ]
    for prefix, label in fuzzy_prefixes:
        if canonical.startswith(prefix):
            return label
    return str(value).strip()


def _extract_skill_items_from_section_lines(lines: list[str], limit: int = 12) -> list[str]:
    if not lines:
        return []

    merged_lines = []
    for raw_line in lines:
        cleaned = _normalize_resume_text(raw_line).strip(" .,-|")
        if not cleaned:
            continue
        if cleaned.startswith("&") and merged_lines:
            merged_lines[-1] = f"{merged_lines[-1]} {cleaned}".strip()
        else:
            merged_lines.append(cleaned)

    found = []
    seen = set()
    for line in merged_lines:
        candidates = [part.strip() for part in re.split(r"\s*,\s*", line) if part.strip()]
        if not candidates:
            candidates = [line]

        expanded = []
        for candidate in candidates:
            if "&" in candidate:
                amp_parts = [part.strip() for part in candidate.split("&") if part.strip()]
                if len(amp_parts) == 2:
                    left_label = _format_resume_skill_label(amp_parts[0]) or amp_parts[0]
                    expanded.append(left_label)
                    right_tokens = amp_parts[1].split()
                    left_tokens = left_label.split() if left_label else []
                    if len(right_tokens) == 1 and left_tokens:
                        expanded.append(f"{left_tokens[0]} {amp_parts[1]}")
                    else:
                        expanded.append(amp_parts[1])
                    continue
            expanded.append(candidate)

        for candidate in expanded:
            label = _format_resume_skill_label(candidate)
            canonical = _canonical_keyword(label)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            found.append(label)
            if len(found) >= limit:
                return found
    if "JavaScript (Basics)" in found and "JavaScript" in found:
        found = [item for item in found if item != "JavaScript"]
    if "Java (Basics)" in found and "Java" in found:
        found = [item for item in found if item != "Java"]
    return found[:limit]


def _extract_project_section_items(lines: list[str], limit: int = 6, internships_only: bool = False) -> list[str]:
    if not lines:
        return []

    merged = []
    for raw_line in lines:
        cleaned = _normalize_resume_text(_collapse_spaced_characters(raw_line)).strip(" .,-|")
        if not cleaned:
            continue
        if (
            merged
            and (
                merged[-1].rstrip().endswith(("(", "-", "/", "|", ","))
                or re.match(r"^['\"(,./0-9-]", cleaned)
            )
        ):
            merged[-1] = f"{merged[-1]} {cleaned}".strip()
        else:
            merged.append(cleaned)

    items = []
    seen = set()
    for item in merged:
        if not re.search(r"[A-Za-z]", item):
            continue
        if (
            re.search(r"\b(member|ambassador|attendee|facilitator)\b", item, re.I)
            and not re.search(r"\b(intern|internship|project|system|application|extension|frontend|front-end|prediction|scheduling)\b", item, re.I)
        ):
            continue
        if internships_only and not re.search(r"\b(intern|internship|trainee)\b", item, re.I):
            continue
        canonical = _canonical_keyword(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        items.append(item)
        if len(items) >= limit:
            break
    return items[:limit]


def _extract_section_entries(lines: list[str], limit: int = 6) -> list[str]:
    if not lines:
        return []

    merged = []
    for raw_line in lines:
        cleaned = _normalize_resume_text(_collapse_spaced_characters(raw_line)).strip(" .,-|")
        if not cleaned:
            continue
        if (
            merged
            and (
                merged[-1].rstrip().endswith(("(", "-", "/", "|", ","))
                or re.match(r"^['\"(,./0-9-]", cleaned)
            )
        ):
            merged[-1] = f"{merged[-1]} {cleaned}".strip()
        else:
            merged.append(cleaned)

    entries = []
    seen = set()
    for item in merged:
        canonical = _canonical_keyword(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        entries.append(item)
        if len(entries) >= limit:
            break
    return entries[:limit]


def _extract_resume_lines(text: str, limit: int = 8) -> list[str]:
    lines = [line.strip(" -•\t") for line in (text or "").splitlines()]
    cleaned = [line for line in lines if len(line.split()) >= 2]
    return cleaned[:limit]


def _extract_resume_lines_smart(text: str, limit: int = 8) -> list[str]:
    lines = []
    for raw_line in (text or "").splitlines():
        cleaned_line = raw_line.strip(" -\t")
        if cleaned_line:
            lines.append(cleaned_line)
        split_segments = re.split(r"\s{3,}|\t+|[•·▪◦]\s*", cleaned_line)
        if len(split_segments) > 1:
            lines.extend(segment.strip(" -\t") for segment in split_segments if segment.strip(" -\t"))

    deduped = []
    seen = set()
    for line in lines:
        canonical = _canonical_keyword(line)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(line)

    cleaned = [line for line in deduped if len(line.split()) >= 2]
    return cleaned[:limit] if cleaned else _extract_resume_lines(text, limit=limit)


def _build_resume_analysis_payload(text: str, file_name: str = "") -> dict:
    normalized = _normalize_resume_text(text)
    lines = _extract_resume_lines_smart(text, limit=30)
    section_skills = _extract_skills_section_items(text, limit=12)
    
    # Fallback: Extract skills from experience/project descriptions
    fallback_skills = []
    experience_text = " ".join(_get_resume_section_lines(text, ["experience"], limit=20))
    if experience_text:
        fallback_skills.extend(_extract_resume_skills(experience_text))
    
    project_text = " ".join(_get_resume_section_lines(text, ["projects", "internships"], limit=20))
    if project_text:
        fallback_skills.extend(_extract_resume_skills(project_text))
    
    skills = []
    seen_skills = set()
    for item in section_skills + fallback_skills:
        label = _format_resume_skill_label(item)
        canonical = _canonical_keyword(label)
        if not canonical or canonical in seen_skills:
            continue
        seen_skills.add(canonical)
        skills.append(label)
    if "JavaScript (Basics)" in skills:
        skills = [item for item in skills if item != "JavaScript"]
    if "Java (Basics)" in skills:
        skills = [item for item in skills if item != "Java"]
    skills = skills[:24]
    signal_details = _resume_signal_details(text, file_name)

    # Improved education extraction - more keywords
    education = [
        line for line in lines
        if re.search(r"\b(university|college|bachelor|master|degree|b\.tech|m\.tech|school|high school|diploma|associate|semester|graduated|graduation|class|course|institute)\b", line, re.I)
    ][:6]
    
    # Fallback: search entire text for education
    if not education:
        all_lines = _prepare_resume_lines(text)
        education = [
            line for line in all_lines
            if re.search(r"\b(university|college|bachelor|master|degree|b\.tech|m\.tech|school|high school|diploma|associate|semester|graduated|graduation|class|course|institute)\b", line, re.I)
        ][:6]
    
    experience = _extract_section_entries(
        _get_resume_section_lines(
            text,
            ["experience"],
            limit=12,
        ),
        limit=6,
    )
    
    # Fallback: Extract experience entries with action verbs
    if not experience:
        all_prepared_lines = _prepare_resume_lines(text)
        action_verbs = r"\b(developed|contributed|worked|learned|designed|built|implemented|improved|created|drove|driving|adopted|achieved|managed|led|responsible|collaborated|coordinated|supported|assisted|maintained)\b"
        experience = [
            line for line in all_prepared_lines
            if re.search(action_verbs, line, re.I) and len(line.split()) >= 4
        ][:6]
    
    project_section_lines = _get_resume_section_lines(
        text,
        ["projects_internships", "projects", "internships"],
        limit=12,
    )
    projects = _extract_project_section_items(project_section_lines, limit=6, internships_only=False)
    
    # Fallback: Extract projects if section not found
    if not projects:
        all_prepared_lines = _prepare_resume_lines(text)
        project_keywords = r"\b(project|internship|intern|system|frontend|front-end|application|extension|application|platform|solution|tool)\b"
        projects = [
            line for line in all_prepared_lines
            if re.search(project_keywords, line, re.I) and len(line.split()) >= 4 and len(line) > 20
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
        "contact_found": signal_details["has_email"] or signal_details["has_phone"],
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


def _extract_resume_section_block(text: str, heading_patterns: list[str], limit: int = 6) -> list[str]:
    lines = [line.strip(" -\t:") for line in _prepare_resume_text_for_analysis(text).splitlines()]
    cleaned_lines = [line for line in lines if line]
    if not cleaned_lines:
        return []

    section_heading_pattern = re.compile(
        r"^(summary|objective|profile|experience|professional experience|work history|work experience|education|educational qualification|educational qualifications|academic|skills|technical skills|projects|internships and projects|internships|certifications|achievements|certificates|technologies|internship|hobbies|interests|extra curricular|extracurricular activities?|personal details|declaration|curriculum vitae)\b[:\s-]*$",
        re.I,
    )
    heading_line_matcher = re.compile(
        r"^(?P<heading>(?:"
        + "|".join(heading_patterns)
        + r"))(?:\s*[:\-|]\s*(?P<trailing>.*))?$",
        re.I,
    )

    extracted = []
    capture = False
    for line in cleaned_lines:
        normalized_line = re.sub(r"\s+", " ", line).strip()
        if not normalized_line:
            continue

        heading_hit = heading_line_matcher.match(normalized_line)
        if heading_hit:
            capture = True
            trailing = (heading_hit.group("trailing") or "").strip(" :-|")
            if trailing.upper() in {"AND PROJECTS", "& PROJECTS"}:
                trailing = ""
            if trailing:
                extracted.append(trailing)
            continue

        if capture and section_heading_pattern.search(normalized_line):
            break

        if capture and len(normalized_line.split()) >= 1:
            if (
                extracted
                and (
                    extracted[-1].rstrip().endswith(("(", "-", "/", "|", ","))
                    or re.match(r"^['\"(,./0-9-]", normalized_line)
                )
            ):
                extracted[-1] = f"{extracted[-1]} {normalized_line}".strip()
            else:
                extracted.append(normalized_line)
            if len(extracted) >= limit:
                break

    deduped = []
    seen = set()
    for item in extracted:
        canonical = _canonical_keyword(item)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(item)
    return deduped[:limit]


def _extract_inline_section_items(
    text: str,
    heading_patterns: list[str],
    stop_headings: list[str],
    limit: int = 6,
) -> list[str]:
    normalized = _normalize_resume_text(text)
    if not normalized:
        return []

    heading_pattern = "(?:" + "|".join(heading_patterns) + ")"
    stop_pattern = "(?:" + "|".join(stop_headings) + ")"
    match = re.search(
        rf"{heading_pattern}\s*[:\-]\s*(.+?)(?=\s+(?:{stop_pattern})\s*[:\-]|\Z)",
        normalized,
        re.I,
    )
    if not match:
        return []

    raw_section = match.group(1).strip()
    candidates = re.split(r"[|;,]|(?:\s{2,})", raw_section)
    extracted = []
    seen = set()
    for item in candidates:
        cleaned = _normalize_resume_text(item).strip(" .-:")
        canonical = _canonical_keyword(cleaned)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        extracted.append(cleaned)
        if len(extracted) >= limit:
            break
    return extracted[:limit]


def _extract_skills_section_items(text: str, limit: int = 12) -> list[str]:
    section_items = _get_resume_section_lines(text, ["skills"], limit=limit + 8)
    section_text = "\n".join(section_items)
    section_skills = _extract_skill_items_from_section_lines(section_items, limit=limit)
    detected_skills = _extract_resume_skills(section_text)
    merged = []
    seen = set()
    for item in section_skills + detected_skills:
        label = _format_resume_skill_label(item)
        canonical = _canonical_keyword(label)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        merged.append(label)
    return merged[:limit]


def _extract_resume_section_details(
    text: str,
    heading_patterns: list[str],
    fallback_pattern: str,
    stop_headings: list[str],
    limit: int = 6,
) -> list[str]:
    section_items = _extract_resume_section_block(text, heading_patterns, limit=limit)
    inline_items = _extract_inline_section_items(text, heading_patterns, stop_headings, limit=limit)
    line_items = [
        line for line in _extract_resume_lines_smart(text, limit=24)
        if re.search(fallback_pattern, line, re.I)
    ][:limit]

    deduped = []
    seen = set()
    for item in section_items + inline_items + line_items:
        cleaned = _normalize_resume_text(item)
        canonical = _canonical_keyword(cleaned)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(cleaned)
    return deduped[:limit]


def _extract_resume_hobbies(text: str) -> list[str]:
    hr_context_keywords = {
        "age", "gender", "marital", "status", "availability", "date of birth", "dob",
        "nationality", "visa", "salary", "ctc", "notice", "location", "city",
        "phone", "email", "linkedin", "github", "portfolio", "website",
        "willing", "relocate", "travel", "languages", "certifications"
    }
    
    objective_keywords = {
        "work", "seeking", "looking", "pursue", "career", "professional", "goal",
        "objective", "develop", "enhance", "utilize", "leverage", "contribute",
        "deliver", "results", "skills", "abilities", "expertise", "experience",
        "opportunity", "role", "position", "organization", "company", "team",
        "dynamic environment", "fast-paced", "growth", "challenging"
    }
    
    resume_section_headings = {
        "objective", "career objective", "professional summary", "summary", "profile",
        "education", "experience", "work experience", "skills", "technical skills",
        "projects", "internships", "achievements", "declaration", "personal details",
        "certifications", "languages known", "interests", "extracurricular"
    }
    
    def _is_valid_hobby(item: str) -> bool:
        """Check if item is a valid hobby (not HR context, objective, or heading)"""
        if not item:
            return False
            
        normalized = _normalize_resume_text(item).lower()
        
        # Filter HR context keywords
        for keyword in hr_context_keywords:
            if keyword in normalized:
                return False
        
        # Filter professional objective keywords (indicates objective text, not hobby)
        # Only filter if multiple professional keywords appear (to avoid false positives)
        professional_keyword_count = sum(1 for keyword in objective_keywords if keyword in normalized)
        if professional_keyword_count >= 3:  # Multiple career-related words = not a hobby
            return False
        
        # Filter section headings
        for heading in resume_section_headings:
            if heading in normalized:
                return False
        
        # Filter all-caps names (multiple characters, all uppercase, no spaces like "BHABABHANJANPANDA")
        if item.isupper() and len(item) > 6 and ' ' not in item:
            return False
        
        # Filter very long entries (likely paragraph text, not hobbies)
        if len(normalized.split()) > 20:
            return False
            
        return True
    
    structured_items = _get_resume_section_lines(text, ["hobbies"], limit=6)
    if structured_items:
        items = []
        seen = set()
        for entry in structured_items:
            for part in re.split(r",|/|\||;", entry):
                cleaned = _normalize_resume_text(part).strip(" .-")
                canonical = _canonical_keyword(cleaned)
                if not canonical or canonical in seen or not _is_valid_hobby(cleaned):
                    continue
                seen.add(canonical)
                items.append(cleaned)
        if items:
            return items[:6]

    for line in _prepare_resume_lines(text):
        match = re.match(r"^(?:Hobbies|Interests)\s*:\s*(.+)$", line, re.I)
        if not match:
            continue
        raw_items = re.split(r",|/|\||;", match.group(1))
        hobbies = []
        seen = set()
        for item in raw_items:
            cleaned = _normalize_resume_text(item).strip(" .-")
            canonical = _canonical_keyword(cleaned)
            if not canonical or canonical in seen or not _is_valid_hobby(cleaned):
                continue
            seen.add(canonical)
            hobbies.append(cleaned)
        if hobbies:
            return hobbies[:6]

    section_items = _extract_resume_section_block(
        text,
        [
            r"\bhobbies\b",
            r"\binterests\b",
            r"\bextra[\s-]*curricular\b",
            r"\bextracurricular activities?\b",
        ],
        limit=6,
    )
    if section_items:
        # Filter out invalid hobbies (names, headings, HR context, professional objectives)
        filtered = []
        for item in section_items:
            if _is_valid_hobby(item):
                filtered.append(item)
        if filtered:
            return filtered[:6]

    normalized = _normalize_resume_text(text)
    inline_match = re.search(
        r"\b(?:hobbies|interests)\b\s*[:\-]\s*([^.|\n]{4,240})",
        normalized,
        re.I,
    )
    if not inline_match:
        return []

    raw_items = re.split(r",|/|\||;|\s{2,}", inline_match.group(1))
    hobbies = []
    seen = set()
    for item in raw_items:
        cleaned = _normalize_resume_text(item).strip(" .-")
        canonical = _canonical_keyword(cleaned)
        if not canonical or canonical in seen or not _is_valid_hobby(cleaned):
            continue
        seen.add(canonical)
        hobbies.append(cleaned)
    return hobbies[:6]


def _add_spaces_to_concatenated_text(text: str) -> str:
    """
    Intelligently add spaces to text that has been concatenated (spaces removed).
    Uses greedy word matching with a comprehensive dictionary.
    """
    if not text or len(text) < 2:
        return text
    
    text = text.lower()
    
    # Comprehensive word dictionary, sorted by length (longest first for greedy matching)
    words = [
        # Long words
        "continuously", "developing", "environment", "abilities", "creativity", 
        "problem-solving", "problem", "solving", "deliver", "quality", "results",
        "experience", "professional", "organization", "opportunity", "challenge",
        # Medium words
        "work", "working", "where", "while", "utilize", "ability", "creative",
        "develop", "learning", "high", "best", "well", "good", "dynamic",
        "skills", "goal", "seek", "help", "lead", "build", "improve",
        "playing", "reading", "writing", "singing", "dancing", "cooking",
        # Common short words
        "to", "in", "a", "and", "can", "my", "i", "is", "be", "new",
        "of", "at", "by", "or", "an", "it", "on", "as", "we", "me",
        "no", "up", "do", "go", "so", "if", "the", "for", "with",
        "from", "that", "this", "your", "our", "but", "not", "all",
    ]
    
    words.sort(key=len, reverse=True)  # Longest first
    
    result = []
    i = 0
    
    while i < len(text):
        matched = False
        
        # Try to match words starting from current position
        for word in words:
            if text[i:i+len(word)] == word:
                result.append(word)
                i += len(word)
                matched = True
                break
        
        if not matched:
            # No word matched, take single character and continue
            result.append(text[i])
            i += 1
    
    # Join with spaces and clean up
    output = ' '.join(result)
    # Fix spacing around hyphens and punctuation
    output = re.sub(r'\s*-\s*', '-', output)
    output = re.sub(r'\s+', ' ', output)
    
    return output.strip()


def _extract_resume_objective(text: str) -> str:
    # Try to extract directly from raw text before aggressive processing
    raw_lines = str(text or "").splitlines()
    
    # Look for objective heading and get following lines
    for i, line in enumerate(raw_lines):
        section_name, trailing = _classify_resume_section_line(line)
        if section_name == "objective":
            if trailing:
                # Inline: "Career Objective: text here"
                obj_text = trailing[:420]
            else:
                # Heading on separate line, collect following lines
                obj_lines = []
                for j in range(i + 1, min(i + 5, len(raw_lines))):
                    next_line = raw_lines[j].strip()
                    if not next_line:
                        continue
                    # Stop if we hit another section heading
                    next_section, _ = _classify_resume_section_line(next_line)
                    if next_section:
                        break
                    obj_lines.append(next_line)
                
                if not obj_lines:
                    continue
                obj_text = " ".join(obj_lines)[:420]
            
            if not obj_text:
                continue
            
            # Clean OCR artifacts: remove scattered spaces and reconstruct
            # Step 1: Remove all spaces first to get the concatenated text
            obj_cleaned = re.sub(r'\s+', '', obj_text)
            
            # Step 2: Add spaces intelligently using word dictionary
            obj_spaced = _add_spaces_to_concatenated_text(obj_cleaned)
            
            # Step 3: Capitalize first letter
            if obj_spaced and len(obj_spaced) > 0:
                obj_spaced = obj_spaced[0].upper() + obj_spaced[1:]
            
            return obj_spaced.strip()
    
    return ""


def _extract_resume_achievements(text: str) -> list[str]:
    structured_items = _get_resume_section_lines(text, ["achievements"], limit=6)
    if structured_items:
        return structured_items[:6]

    return _extract_resume_section_details(
        text,
        [
            r"\bachievements\b",
            r"\bkey achievements\b",
            r"\baccomplishments\b",
        ],
        r"\b(member|ambassador|attendee|award|achievement|leadership|facilitator)\b",
        [
            r"\bprojects\b",
            r"\binternships?\b",
            r"\bexperience\b",
            r"\beducation\b",
            r"\bskills\b",
            r"\btechnical skills\b",
            r"\bhobbies\b",
            r"\binterests\b",
            r"\bpersonal details\b",
            r"\bdeclaration\b",
        ],
        limit=6,
    )


def _extract_resume_languages(text: str) -> list[str]:
    structured_items = _get_resume_section_lines(text, ["languages"], limit=3)
    if structured_items:
        items = []
        seen = set()
        for entry in structured_items:
            for part in re.split(r",|/|\||;", entry):
                cleaned = _normalize_resume_text(part).strip(" .-")
                canonical = _canonical_keyword(cleaned)
                if not canonical or canonical in seen:
                    continue
                seen.add(canonical)
                items.append(cleaned.title())
        if items:
            return items[:6]

    for line in _prepare_resume_lines(text):
        match = re.match(r"^Languages Known\s*:\s*(.+)$", line, re.I)
        if not match:
            continue
        items = re.split(r",|/|\||;", match.group(1))
        deduped = []
        seen = set()
        for item in items:
            cleaned = _normalize_resume_text(item).strip(" .-")
            canonical = _canonical_keyword(cleaned)
            if not canonical or canonical in seen:
                continue
            seen.add(canonical)
            deduped.append(cleaned.title())
        if deduped:
            return deduped[:6]

    normalized = _normalize_resume_text(text)
    inline_match = re.search(
        r"\blanguages?(?: known)?\b\s*[:\-]\s*([a-z ,/|]{4,160})",
        normalized,
        re.I,
    )
    if not inline_match:
        return []

    items = re.split(r",|/|\||;", inline_match.group(1))
    deduped = []
    seen = set()
    for item in items:
        cleaned = _normalize_resume_text(item).strip(" .-")
        canonical = _canonical_keyword(cleaned)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(cleaned.title())
    return deduped[:6]


def _extract_candidate_name_from_resume(text: str, file_name: str = "") -> str:
    heading_stopwords = {
        "career objective",
        "professional summary",
        "summary",
        "profile",
        "educational qualification",
        "educational qualifications",
        "education",
        "technical skills",
        "skills",
        "internships and projects",
        "internships",
        "projects",
        "experience",
        "work experience",
        "personal details",
        "achievements",
        "declaration",
        "curriculum vitae",
        "cv",
    }
    institution_words = {"school", "college", "university", "institute", "engineering", "board"}

    for line in _prepare_resume_lines(text):
        if not line:
            continue
        normalized_line = _normalize_resume_text(line).lower()
        if normalized_line in heading_stopwords:
            continue
        if any(word in normalized_line for word in institution_words):
            continue
        if re.fullmatch(r"[a-zA-Z]+(?: [a-zA-Z]+){1,3}", line):
            words = line.split()
            if all(len(word) >= 2 for word in words):
                return " ".join(word.capitalize() for word in words)

    file_stem = Path(file_name or "").stem
    cleaned_stem = re.sub(r"\(\d+\)$", "", file_stem).replace("_", " ").replace("-", " ").strip()
    cleaned_stem = re.sub(r"\bc\.?v\.?\b", "", cleaned_stem, flags=re.I).strip()
    if re.fullmatch(r"[a-zA-Z]+(?: [a-zA-Z]+){1,3}", cleaned_stem):
        return " ".join(word.capitalize() for word in cleaned_stem.split())
    return ""


def _get_resume_section_display_label(section_name: str) -> str:
    return {
        "objective": "Career Objective",
        "education": "Education",
        "experience": "Experience",
        "projects_internships": "Projects & Internships",
        "projects": "Projects",
        "internships": "Internships",
        "skills": "Technical Skills",
        "achievements": "Key Achievements",
        "languages": "Languages",
        "hobbies": "Interests",
        "personal": "Personal Details",
        "declaration": "Declaration",
    }.get(section_name, section_name.replace("_", " ").title())


def _build_ordered_resume_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = None
    current_lines: list[str] = []

    for line in _prepare_resume_lines(text):
        section_name, trailing = _classify_resume_section_line(line)
        if section_name:
            if current_heading is not None or current_lines:
                sections.append((current_heading or "Profile", current_lines))
            current_heading = _get_resume_section_display_label(section_name)
            current_lines = []
            if trailing:
                current_lines.append(trailing)
            continue

        if current_heading is None:
            current_heading = "Profile"
        current_lines.append(line)

    if current_heading is not None or current_lines:
        sections.append((current_heading or "Profile", current_lines))

    return sections


def _build_simple_resume_text(
    candidate_name: str,
    job_role: str,
    extracted: dict,
    original_text: str = "",
) -> str:
    if original_text:
        sections = _build_ordered_resume_sections(original_text)
        header_lines = [candidate_name or "Candidate"]
        if job_role:
            header_lines.append(job_role)

        rendered_sections = ["\n".join(header_lines)]
        for heading, lines in sections:
            if not lines:
                rendered_sections.append(heading)
            else:
                rendered_sections.append(f"{heading}\n" + "\n".join(lines))
        return "\n\n".join(rendered_sections).strip()

    sections = []
    header_lines = [candidate_name or "Candidate"]
    if job_role:
        header_lines.append(job_role)
    sections.append("\n".join(header_lines))

    summary_text = str(extracted.get("career_objective") or "").strip()
    if summary_text:
        sections.append("Summary\n" + summary_text)

    if extracted.get("educational_qualifications"):
        sections.append(
            "Education\n- " + "\n- ".join(extracted.get("educational_qualifications") or [])
        )

    if extracted.get("technical_skills"):
        sections.append(
            "Technical Skills\n- " + "\n- ".join(extracted.get("technical_skills") or [])
        )

    def _projectish_key(value: str) -> str:
        normalized = _canonical_keyword(value)
        normalized = re.sub(r"^(?:(?:internship|trainee)\s+)+", "", normalized)
        return normalized.strip()

    project_like = []
    if extracted.get("internships"):
        project_like.extend(extracted.get("internships") or [])
    if extracted.get("projects"):
        for item in extracted.get("projects") or []:
            if _projectish_key(item) not in {_projectish_key(existing) for existing in project_like}:
                project_like.append(item)
    deduped_project_like = []
    seen_project_keys = set()
    for item in project_like:
        key = _projectish_key(item)
        if not key or key in seen_project_keys:
            continue
        seen_project_keys.add(key)
        deduped_project_like.append(item)
    project_like = deduped_project_like
    if project_like:
        sections.append(
            "Projects & Internships\n- " + "\n- ".join(project_like)
        )

    if extracted.get("experience"):
        sections.append(
            "Experience\n- " + "\n- ".join(extracted.get("experience") or [])
        )

    if extracted.get("achievements"):
        sections.append(
            "Key Achievements\n- " + "\n- ".join(extracted.get("achievements") or [])
        )

    if extracted.get("languages"):
        sections.append(
            "Languages\n- " + "\n- ".join(extracted.get("languages") or [])
        )

    if extracted.get("hobbies"):
        sections.append(
            "Interests\n- " + "\n- ".join(extracted.get("hobbies") or [])
        )

    return "\n\n".join(section for section in sections if section).strip()


def _build_resume_interview_extract_payload(text: str, file_name: str = "", job_role: str = "") -> dict:
    try:
        normalized = _normalize_resume_text(text)
        analysis = _build_resume_analysis_payload(text, file_name)
        project_section_lines = _get_resume_section_lines(
            text,
            ["projects_internships", "projects", "internships"],
            limit=12,
        )
        internships = _extract_project_section_items(project_section_lines, limit=6, internships_only=True)
        hobbies = _extract_resume_hobbies(text) or []
        career_objective = _extract_resume_objective(text) or ""
        achievements = _extract_resume_achievements(text) or []
        languages = _extract_resume_languages(text) or []
        educational_qualifications = analysis.get("education") or []
        experience = analysis.get("experience_highlights") or []
        projects = analysis.get("project_highlights") or []
        skills = analysis.get("skills") or []
        candidate_name = _extract_candidate_name_from_resume(text, file_name) or analysis.get("candidate_name") or ""

        extracted = {
            "career_objective": career_objective if isinstance(career_objective, str) else "",
            "educational_qualifications": educational_qualifications[:6] if isinstance(educational_qualifications, list) else [],
            "technical_skills": skills[:12] if isinstance(skills, list) else [],
            "projects": projects[:6] if isinstance(projects, list) else [],
            "internships": internships[:6] if isinstance(internships, list) else [],
            "experience": experience[:6] if isinstance(experience, list) else [],
            "achievements": achievements[:6] if isinstance(achievements, list) else [],
            "languages": languages[:6] if isinstance(languages, list) else [],
            "hobbies": hobbies[:6] if isinstance(hobbies, list) else [],
        }

        strong_signal_found = bool((skills and isinstance(skills, list)) or (projects and isinstance(projects, list)) or (experience and isinstance(experience, list)))
        recommended_focus = []
        for item in (skills[:8] if isinstance(skills, list) else []) + (projects[:4] if isinstance(projects, list) else []) + (experience[:4] if isinstance(experience, list) else []):
            cleaned = _normalize_resume_text(item)
            if cleaned and cleaned not in recommended_focus:
                recommended_focus.append(cleaned)

        return {
            "resume_text": normalized,
            "raw_resume_text": text[:12000],
            "normalized_resume_text": _prepare_resume_text_for_display(text)[:12000],
            "analysis": analysis,
            "candidate_name": candidate_name,
            "extracted": extracted,
            "simple_resume_text": _build_simple_resume_text(candidate_name, job_role, extracted, text)[:12000],
            "job_role": job_role,
            "interview_ready": strong_signal_found,
            "ready_reason": (
                "The resume has enough usable interview signals to generate personalized questions."
                if strong_signal_found
                else "Add at least one clear skill, project, or experience item before starting a resume-based interview."
            ),
            "recommended_focus": recommended_focus[:10],
        }
    except Exception as exc:
        # Return minimal valid payload on error
        return {
            "resume_text": _normalize_resume_text(text),
            "raw_resume_text": text[:12000],
            "normalized_resume_text": _prepare_resume_text_for_display(text)[:12000],
            "analysis": {},
            "candidate_name": "",
            "extracted": {
                "career_objective": "",
                "educational_qualifications": [],
                "technical_skills": [],
                "projects": [],
                "internships": [],
                "experience": [],
                "achievements": [],
                "languages": [],
                "hobbies": [],
            },
            "simple_resume_text": "",
            "job_role": job_role,
            "interview_ready": False,
            "ready_reason": f"Error during resume extraction: {str(exc)}",
            "recommended_focus": [],
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


def _split_job_description_lines(job_description: str) -> list[str]:
    if not job_description:
        return []

    normalized_newlines = re.sub(r"[\r\f]+", "\n", job_description)
    seeded_lines = []
    for block in normalized_newlines.split("\n"):
        block = re.sub(r"\s+", " ", block).strip(" -\t")
        if not block:
            continue
        seeded_lines.append(block)

        bullet_splits = re.split(r"\s*[•·▪◦]\s+|\s+-\s+|\s+\*\s+", block)
        if len(bullet_splits) > 1:
            seeded_lines.extend(item.strip(" -\t") for item in bullet_splits if item.strip(" -\t"))

    deduped = []
    seen = set()
    for line in seeded_lines:
        canonical = _canonical_keyword(line)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        deduped.append(line)
    return deduped[:120]


def _extract_job_requirement_items(job_description: str, patterns: list[str], limit: int = 6) -> list[str]:
    lines = _split_job_description_lines(job_description)
    results = []
    seen = set()

    for line in lines:
        lowered = line.lower()
        if len(lowered.split()) < 2:
            continue
        if not any(re.search(pattern, lowered, re.I) for pattern in patterns):
            continue
        canonical = _canonical_keyword(line)
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(line)
        if len(results) >= limit:
            break

    return results


def _extract_job_requirement_skills(job_description: str) -> tuple[list[str], list[str], list[str]]:
    lines = _split_job_description_lines(job_description)
    all_keywords = _extract_job_keywords(job_description)
    required, preferred, tools = [], [], []
    req_seen, pref_seen, tool_seen = set(), set(), set()

    for line in lines:
        lowered = line.lower()
        line_keywords = []
        for keyword in all_keywords:
            canonical = _canonical_keyword(keyword)
            if canonical and canonical in _canonical_keyword(line):
                line_keywords.append(keyword)

        is_preferred = bool(re.search(r"\b(preferred|nice to have|plus|good to have)\b", lowered))
        is_required = bool(
            re.search(r"\b(requirements?|must have|required|qualification|looking for|responsibilities)\b", lowered)
        ) or not is_preferred

        for keyword in line_keywords:
            canonical = _canonical_keyword(keyword)
            if keyword.lower() in {"agile", "scrum", "git", "linux", "aws", "azure", "gcp", "docker", "kubernetes"}:
                if canonical not in tool_seen:
                    tool_seen.add(canonical)
                    tools.append(keyword)

            if is_preferred:
                if canonical not in pref_seen:
                    pref_seen.add(canonical)
                    preferred.append(keyword)
            elif is_required and canonical not in req_seen:
                req_seen.add(canonical)
                required.append(keyword)

    if not required:
        required = all_keywords[:8]
    if not tools:
        tools = [item for item in required if item in {"AWS", "Azure", "Gcp", "Docker", "Kubernetes", "Git", "Linux"}][:6]

    return required[:10], preferred[:8], tools[:8]


def _build_job_requirements_payload(job_description: str) -> dict:
    normalized_job = _normalize_resume_text(job_description)
    if not normalized_job:
        return {
            "job_description_provided": False,
            "required_skills": [],
            "preferred_skills": [],
            "education_requirements": [],
            "experience_requirements": [],
            "certifications": [],
            "responsibilities": [],
            "tools_and_platforms": [],
            "summary": "Add a target job description to extract required skills, education, experience, and other role requirements.",
        }

    required_skills, preferred_skills, tools_and_platforms = _extract_job_requirement_skills(normalized_job)
    education_requirements = _extract_job_requirement_items(normalized_job, JOB_EDUCATION_PATTERNS, limit=4)
    experience_requirements = _extract_job_requirement_items(normalized_job, JOB_EXPERIENCE_PATTERNS, limit=5)
    certifications = _extract_job_requirement_items(normalized_job, JOB_CERTIFICATION_PATTERNS, limit=4)
    responsibilities = _extract_job_requirement_items(
        normalized_job,
        [
            r"\b(responsible|responsibilities|build|develop|design|lead|manage|analyze|collaborate|deliver|maintain|support)\b",
        ],
        limit=6,
    )

    summary_parts = []
    if required_skills:
        summary_parts.append(f"Key skills: {', '.join(required_skills[:4])}.")
    if education_requirements:
        summary_parts.append(f"Education: {education_requirements[0]}.")
    if experience_requirements:
        summary_parts.append(f"Experience: {experience_requirements[0]}.")
    if certifications:
        summary_parts.append(f"Certifications: {certifications[0]}.")

    return {
        "job_description_provided": True,
        "required_skills": required_skills[:10],
        "preferred_skills": preferred_skills[:8],
        "education_requirements": education_requirements,
        "experience_requirements": experience_requirements,
        "certifications": certifications,
        "responsibilities": responsibilities,
        "tools_and_platforms": tools_and_platforms[:8],
        "summary": " ".join(summary_parts).strip()
        or "The job description was read successfully, but only broad role requirements could be extracted.",
    }


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


def _missing_required_skills(analysis: dict, job_requirements: dict) -> list[str]:
    required_skills = job_requirements.get("required_skills") or []
    resume_skill_index = {_canonical_keyword(skill) for skill in analysis.get("skills") or []}
    return [
        skill for skill in required_skills if _canonical_keyword(skill) not in resume_skill_index
    ][:8]


def _resume_specific_edit_actions(
    analysis: dict,
    quality: dict,
    match_payload: dict,
    job_requirements: dict,
) -> list[str]:
    actions = []
    missing_required = _missing_required_skills(analysis, job_requirements)

    if missing_required:
        actions.append(
            "Add or strengthen proof for required skills such as "
            + ", ".join(missing_required[:4])
            + " in your skills section or project bullets."
        )

    if not analysis.get("project_highlights"):
        actions.append(
            "Add at least one project entry with the tech stack, what you built, and the result or impact."
        )
    else:
        actions.append(
            "Rewrite your strongest project bullet to include the tool used, the feature delivered, and a measurable result."
        )

    if quality.get("numeric_mentions", 0) < 2:
        actions.append(
            "Add numbers to your best bullets, such as users reached, features delivered, performance gains, rankings, or completion counts."
        )

    if not quality.get("contact_checks", {}).get("profile_link"):
        actions.append(
            "Place your LinkedIn or GitHub link in the header so recruiters can verify your work quickly."
        )

    if match_payload.get("missing_keywords"):
        actions.append(
            "Mirror important job-description wording like "
            + ", ".join(match_payload["missing_keywords"][:4])
            + " where it truthfully matches your work."
        )

    return actions[:6]


def _build_resume_recommendations(
    analysis: dict,
    scorecard: dict,
    match_payload: dict,
    spelling_payload: dict,
    job_requirements: dict,
    quality: dict,
) -> list[str]:
    recommendations = []
    targeted_actions = _resume_specific_edit_actions(
        analysis,
        quality,
        match_payload,
        job_requirements,
    )

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

    recommendations.extend(
        action for action in targeted_actions if action not in recommendations
    )

    if not recommendations:
        recommendations.append("Your resume looks solid. Focus next on quantifying achievements for an even stronger profile.")

    return recommendations[:6]


def _build_resume_quality_payload(
    text: str,
    analysis: dict,
    scorecard: dict,
    match_payload: dict,
    job_requirements: dict,
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
    missing_required = _missing_required_skills(analysis, job_requirements)
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
    if not missing_required and job_requirements.get("required_skills"):
        strengths.append("The resume already covers most of the core required skills from the target job.")

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
    if missing_required:
        improvement_areas.append(
            "Show clearer evidence for required skills such as "
            + ", ".join(missing_required[:4])
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
    if missing_required:
        must_add.append("Evidence of the most important required skills through projects, internships, or experience bullets")

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


def _build_role_focus_payload(match_payload: dict, quality: dict, spelling_payload: dict, job_requirements: dict | None = None) -> dict:
    target_keywords = match_payload.get("job_keywords") or []
    missing_keywords = match_payload.get("missing_keywords") or []
    matched_keywords = match_payload.get("matched_keywords") or []
    job_requirements = job_requirements or {}
    missing_required = [
        skill for skill in (job_requirements.get("required_skills") or [])
        if _canonical_keyword(skill) not in {_canonical_keyword(item) for item in matched_keywords}
    ]

    where_to_improve = []
    if missing_required:
        where_to_improve.append(
            "Add direct evidence for required skills such as " + ", ".join(missing_required[:4]) + "."
        )
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
        cleaned = _normalize_resume_text(re.sub(r"[*_`#]+", "", value))
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
            cleaned = _normalize_resume_text(re.sub(r"[*_`#]+", "", str(preferred)))
            return cleaned or fallback
    cleaned = _normalize_resume_text(re.sub(r"[*_`#]+", "", str(value)))
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


def _resume_ai_prefer_richer_list(primary, fallback=None, limit: int = 10) -> list[str]:
    primary_list = _resume_ai_list(primary, [], limit)
    fallback_list = _resume_ai_list(fallback, [], limit)
    if len(primary_list) >= max(2, min(4, len(fallback_list) or 2)):
        return primary_list[:limit]
    if fallback_list and len(fallback_list) > len(primary_list):
        return fallback_list[:limit]
    return primary_list[:limit] or fallback_list[:limit]


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


def _resume_ai_response_is_degenerate(
    scorecard: dict,
    match_payload: dict,
    quality: dict,
    analysis: dict,
    fallback_quality: dict,
) -> bool:
    zeroish_scores = all(
        _resume_ai_score(scorecard.get(key), 0) == 0
        for key in ("resume_score", "structure_score", "content_score")
    ) and _resume_ai_score(match_payload.get("match_score"), 0) == 0 and _resume_ai_score(
        quality.get("ats_score"), 0
    ) == 0

    ai_text = " ".join(
        [
            _resume_ai_text(analysis.get("analysis_text"), ""),
            _resume_ai_text(match_payload.get("summary"), ""),
            " ".join(_resume_ai_list(quality.get("improvement_areas"), [], 6)),
            " ".join(_resume_ai_list(quality.get("must_add"), [], 6)),
        ]
    ).lower()

    claims_unreadable = any(
        phrase in ai_text
        for phrase in [
            "unreadable",
            "cannot be processed",
            "cannot verify",
            "garbled",
            "no sections detected clearly",
        ]
    )

    fallback_has_content = (
        int(fallback_quality.get("word_count") or 0) >= 150
        or bool(fallback_quality.get("detected_sections"))
        or bool((analysis.get("skills") or []))
        or bool((analysis.get("education") or []))
        or bool((analysis.get("experience_highlights") or []))
    )

    return zeroish_scores or (claims_unreadable and fallback_has_content)


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
Think like a strong recruiter plus ATS reviewer:
- Score based on evidence, not generic harshness.
- A decent student or fresher resume should not be scored unrealistically low if it has clear sections, real projects, education, and contact details.
- Do not punish the candidate for lacking senior-level experience if the resume appears to be for a fresher or student.
- Use the job description to judge alignment, but do not claim missing experience that the job description itself does not require.
- Recommendations must be concrete resume edits, not vague career advice.
- When suggesting improvements, prefer things the candidate can actually add or rewrite in the resume.

Use this scoring rubric:
- `resume_score`: overall recruiter quality of the current draft.
- `structure_score`: formatting logic, section clarity, scanability, and completeness.
- `content_score`: relevance and strength of skills, projects, education, and experience evidence.
- `ats_score`: weighted ATS/readability score based on section completeness, keyword alignment, contact visibility, and proof of impact.
- `impact_score`: strength of measurable outcomes, achievements, ownership, and action verbs.
- `match_score`: alignment to the target role, based only on the provided job description.

Recommendation quality rules:
- `strengths` must mention what is genuinely working in the current resume.
- `improvement_areas` must identify the real gaps.
- `must_add` should contain only the highest-priority missing items.
- `recommendations` must read like specific edit instructions, for example:
  "Add a 2-line skills section with Python, React, SQL, and Git near the top."
  "Rewrite the Chrome extension project bullet to mention users, results, or performance impact."
  "Move LinkedIn and GitHub into the header so recruiters can see them immediately."
- Prefer direct, useful advice about sections, bullets, keywords, metrics, projects, education, and role fit.

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
  "job_requirements": {{
    "job_description_provided": true,
    "required_skills": ["string"],
    "preferred_skills": ["string"],
    "education_requirements": ["string"],
    "experience_requirements": ["string"],
    "certifications": ["string"],
    "responsibilities": ["string"],
    "tools_and_platforms": ["string"],
    "summary": "string"
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
    fallback_job_requirements = fallback_payload["job_requirements"]
    fallback_scorecard = fallback_payload["scorecard"]
    fallback_match = fallback_payload["match"]
    fallback_spelling = fallback_payload["spelling"]
    fallback_quality = fallback_payload["quality"]
    fallback_dashboard = fallback_payload["dashboard"]
    fallback_role_focus = fallback_payload["role_focus"]
    fallback_recommendations = fallback_payload["recommendations"]

    ai_analysis = ai_payload.get("analysis") if isinstance(ai_payload.get("analysis"), dict) else {}
    ai_job_requirements = ai_payload.get("job_requirements") if isinstance(ai_payload.get("job_requirements"), dict) else {}
    ai_scorecard = ai_payload.get("scorecard") if isinstance(ai_payload.get("scorecard"), dict) else {}
    ai_match = ai_payload.get("match") if isinstance(ai_payload.get("match"), dict) else {}
    ai_spelling = ai_payload.get("spelling") if isinstance(ai_payload.get("spelling"), dict) else {}
    ai_quality = ai_payload.get("quality") if isinstance(ai_payload.get("quality"), dict) else {}
    ai_dashboard = ai_payload.get("dashboard") if isinstance(ai_payload.get("dashboard"), dict) else {}
    ai_role_focus = ai_payload.get("role_focus") if isinstance(ai_payload.get("role_focus"), dict) else {}

    analysis = {
        "candidate_name": _resume_ai_text(ai_analysis.get("candidate_name"), fallback_analysis.get("candidate_name", "")),
        "skills": _resume_ai_prefer_richer_list(ai_analysis.get("skills"), fallback_analysis.get("skills") or [], 24),
        "education": _resume_ai_prefer_richer_list(ai_analysis.get("education"), fallback_analysis.get("education") or [], 5),
        "experience_highlights": _resume_ai_prefer_richer_list(
            ai_analysis.get("experience_highlights"),
            fallback_analysis.get("experience_highlights") or [],
            6,
        ),
        "project_highlights": _resume_ai_prefer_richer_list(
            ai_analysis.get("project_highlights"),
            fallback_analysis.get("project_highlights") or [],
            6,
        ),
        "contact_found": _resume_ai_bool(ai_analysis.get("contact_found"), fallback_analysis.get("contact_found", False)),
        "section_hits": _resume_ai_prefer_richer_list(ai_analysis.get("section_hits"), fallback_analysis.get("section_hits") or [], 12),
        "resume_signal_score": _resume_ai_score(
            ai_analysis.get("resume_signal_score"),
            int(fallback_analysis.get("resume_signal_score") or 0),
        ),
        "analysis_text": _resume_ai_text(ai_analysis.get("analysis_text"), fallback_analysis.get("analysis_text", "")),
        "suggested_roles": _resume_ai_prefer_richer_list(ai_analysis.get("suggested_roles"), fallback_analysis.get("suggested_roles") or [], 4),
        "source_file_name": file_name,
    }

    job_requirements = {
        "job_description_provided": True,
        "required_skills": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("required_skills"),
            fallback_job_requirements.get("required_skills") or [],
            10,
        ),
        "preferred_skills": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("preferred_skills"),
            fallback_job_requirements.get("preferred_skills") or [],
            8,
        ),
        "education_requirements": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("education_requirements"),
            fallback_job_requirements.get("education_requirements") or [],
            5,
        ),
        "experience_requirements": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("experience_requirements"),
            fallback_job_requirements.get("experience_requirements") or [],
            6,
        ),
        "certifications": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("certifications"),
            fallback_job_requirements.get("certifications") or [],
            5,
        ),
        "responsibilities": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("responsibilities"),
            fallback_job_requirements.get("responsibilities") or [],
            6,
        ),
        "tools_and_platforms": _resume_ai_prefer_richer_list(
            ai_job_requirements.get("tools_and_platforms"),
            fallback_job_requirements.get("tools_and_platforms") or [],
            8,
        ),
        "summary": _resume_ai_text(
            ai_job_requirements.get("summary"),
            fallback_job_requirements.get("summary", ""),
        ),
    }

    scorecard = {
        "resume_score": _resume_ai_score(ai_scorecard.get("resume_score"), fallback_scorecard.get("resume_score", 0)),
        "structure_score": _resume_ai_score(ai_scorecard.get("structure_score"), fallback_scorecard.get("structure_score", 0)),
        "content_score": _resume_ai_score(ai_scorecard.get("content_score"), fallback_scorecard.get("content_score", 0)),
    }

    match_payload = {
        "job_description_provided": True,
        "match_score": _resume_ai_score(ai_match.get("match_score"), fallback_match.get("match_score", 0) or 0),
        "matched_keywords": _resume_ai_prefer_richer_list(ai_match.get("matched_keywords"), fallback_match.get("matched_keywords") or [], 8),
        "missing_keywords": _resume_ai_prefer_richer_list(ai_match.get("missing_keywords"), fallback_match.get("missing_keywords") or [], 8),
        "job_keywords": _resume_ai_prefer_richer_list(ai_match.get("job_keywords"), fallback_match.get("job_keywords") or [], 16),
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
        "strengths": _resume_ai_prefer_richer_list(ai_quality.get("strengths"), fallback_quality.get("strengths") or [], 6),
        "improvement_areas": _resume_ai_prefer_richer_list(
            ai_quality.get("improvement_areas"),
            fallback_quality.get("improvement_areas") or [],
            6,
        ),
        "must_add": _resume_ai_prefer_richer_list(ai_quality.get("must_add"), fallback_quality.get("must_add") or [], 6),
    }

    dashboard = _build_dashboard_payload(scorecard, quality, match_payload, spelling_payload)
    if ai_dashboard:
        dashboard = {
            "meters": _resume_ai_meters(ai_dashboard.get("meters"), dashboard.get("meters") or []),
            "weak_areas": _resume_ai_weak_areas(ai_dashboard.get("weak_areas"), dashboard.get("weak_areas") or []),
        }

    role_focus = _build_role_focus_payload(match_payload, quality, spelling_payload, job_requirements)
    if ai_role_focus:
        role_focus = {
            "target_keywords": _resume_ai_prefer_richer_list(
                ai_role_focus.get("target_keywords"),
                role_focus.get("target_keywords") or [],
                10,
            ),
            "matched_keywords": _resume_ai_prefer_richer_list(
                ai_role_focus.get("matched_keywords"),
                role_focus.get("matched_keywords") or [],
                8,
            ),
            "missing_keywords": _resume_ai_prefer_richer_list(
                ai_role_focus.get("missing_keywords"),
                role_focus.get("missing_keywords") or [],
                8,
            ),
            "where_to_improve": _resume_ai_prefer_richer_list(
                ai_role_focus.get("where_to_improve"),
                role_focus.get("where_to_improve") or [],
                5,
            ),
        }

    recommendations = _resume_ai_prefer_richer_list(ai_payload.get("recommendations"), fallback_recommendations, 6)

    if _resume_ai_response_is_degenerate(
        scorecard,
        match_payload,
        quality,
        analysis,
        fallback_quality,
    ):
        analysis = fallback_analysis
        job_requirements = fallback_job_requirements
        scorecard = fallback_scorecard
        match_payload = fallback_match
        spelling_payload = fallback_spelling
        quality = fallback_quality
        dashboard = fallback_dashboard
        role_focus = fallback_role_focus
        recommendations = fallback_recommendations

    return {
        "analysis": analysis,
        "job_requirements": job_requirements,
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

    # Generate verification token
    verification_token = create_email_verification_token(email)
    
    user = {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email,
        "hashed_password": hash_password(password),
        "profile_image": None,
        "is_verified": False,
        "verification_token": verification_token,
        "verification_token_expires": datetime.utcnow() + timedelta(hours=24),
        "created_at": datetime.utcnow()
    }

    result = await users_collection.insert_one(user)

    # Send verification email
    frontend_base_url = os.getenv("REACT_APP_FRONTEND_BASE", "http://localhost:3000")
    verification_link = f"{frontend_base_url}/verify-email?token={verification_token}&email={email}"
    
    email_sent = send_verification_email(email, verification_link)

    return {
        "status": "REGISTRATION SUCCESSFUL",
        "message": "Please check your email to verify your account",
        "id": str(result.inserted_id),
        "email": email,
        "email_sent": email_sent
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
    
    # Check if email is verified
    if not user.get("is_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Please check your email for verification link."
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

# ================= EMAIL VERIFICATION =================
@app.post("/verify-email")
async def verify_email(
    token: str = Body(...),
    email: str = Body(...)
):
    """Verify user email with token"""
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    if user.get("is_verified"):
        raise HTTPException(
            status_code=400,
            detail="Email already verified"
        )
    
    # Check if token matches
    if user.get("verification_token") != token:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )
    
    # Check if token expired
    expires_at = user.get("verification_token_expires")
    if expires_at and datetime.utcnow() > expires_at:
        raise HTTPException(
            status_code=400,
            detail="Verification token expired. Please request a new one."
        )
    
    # Update user to verified
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "is_verified": True,
                "verification_token": None,
                "verification_token_expires": None
            }
        }
    )
    
    # Create login token
    token = create_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })
    
    return {
        "status": "Email verified successfully",
        "access_token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "profile_image": user.get("profile_image"),
            "is_verified": True
        }
    }

@app.post("/resend-verification-email")
async def resend_verification_email(
    email: str = Body(...)
):
    """Resend verification email"""
    user = await users_collection.find_one({"email": email})
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    if user.get("is_verified"):
        raise HTTPException(
            status_code=400,
            detail="Email already verified"
        )
    
    # Generate new verification token
    verification_token = create_email_verification_token(email)
    
    # Update user with new token
    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "verification_token": verification_token,
                "verification_token_expires": datetime.utcnow() + timedelta(hours=24)
            }
        }
    )
    
    # Send verification email
    frontend_base_url = os.getenv("REACT_APP_FRONTEND_BASE", "http://localhost:3000")
    verification_link = f"{frontend_base_url}/verify-email?token={verification_token}&email={email}"
    
    email_sent = send_verification_email(email, verification_link)
    
    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification email"
        )
    
    return {
        "status": "Verification email sent",
        "message": "Check your email for verification link"
    }


class GoogleTokenRequest(BaseModel):
    """Request body for Google OAuth login"""
    token: str

@app.post("/auth/google-login")
async def google_login(request: GoogleTokenRequest):
    """
    Verify Google OAuth token and authenticate user
    """
    from config import load_backend_env
    load_backend_env()
    
    try:
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not google_client_id:
            raise HTTPException(
                status_code=500,
                detail="Google OAuth not configured"
            )
        
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            request.token, 
            google_requests.Request(), 
            google_client_id
        )
        
        # Extract user information from token
        email = idinfo.get("email")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")
        profile_image = idinfo.get("picture", None)
        
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Could not extract email from Google token"
            )
        
        # Find or create user
        user = await users_collection.find_one({"email": email})
        
        if not user:
            # Create new user from Google profile
            # Google users are automatically verified since Google validates the email
            user = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "hashed_password": None,  # No password for OAuth users
                "profile_image": profile_image,
                "auth_provider": "google",
                "is_verified": True,  # Automatically verified for Google OAuth
                "created_at": datetime.utcnow()
            }
            result = await users_collection.insert_one(user)
            user["_id"] = result.inserted_id
        else:
            # Update profile image if Google provides one
            if profile_image and not user.get("profile_image"):
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"profile_image": profile_image}}
                )
                user["profile_image"] = profile_image
            
            # Ensure Google users are marked as verified
            if not user.get("is_verified"):
                await users_collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"is_verified": True}}
                )
                user["is_verified"] = True
        
        # Create JWT token
        jwt_token = create_token({
            "user_id": str(user["_id"]),
            "email": user["email"]
        })
        
        return {
            "access_token": jwt_token,
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "profile_image": user.get("profile_image")
            }
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Google authentication failed: {str(e)}"
        )

# ================= FORGOT PASSWORD =================
@app.post("/auth/forgot-password")
async def forgot_password(payload: Dict[str, Any] = Body(...)):
    email = str(payload.get("email", "") or "")
    normalized_email = email.strip()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Email required")

    user = await users_collection.find_one(
        {"email": {"$regex": f"^{re.escape(normalized_email)}$", "$options": "i"}}
    )
    # Always return a generic response for security reasons.
    if not user:
        return {"status": "RESET_LINK_SENT"}

    now = datetime.now(timezone.utc)
    last_request = user.get("reset_requested_at")
    if isinstance(last_request, datetime):
        cooldown_until = last_request.replace(tzinfo=timezone.utc) + timedelta(minutes=1)
        if cooldown_until > now:
            remaining = int((cooldown_until - now).total_seconds())
            raise HTTPException(
                status_code=429,
                detail="Please wait 1 minute before requesting another reset link.",
                headers={"Retry-After": str(max(1, remaining))},
            )
    reset_token = uuid.uuid4().hex
    expires_at = now + timedelta(minutes=5)

    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "reset_token": reset_token,
            "reset_token_expiry": expires_at,
            "reset_requested_at": now,
        }}
    )

    try:
        _send_reset_email(user["email"], reset_token)
    except Exception:
        pass

    response = {"status": "RESET_LINK_SENT"}
    if DEV_RETURN_RESET_TOKEN:
        response["dev_reset_token"] = reset_token
        response["dev_reset_link"] = f"{RESET_EMAIL_BASE_URL}/reset-password?token={reset_token}"
    return response

@app.post("/auth/reset-password/verify")
async def verify_reset_token(payload: Dict[str, Any] = Body(...)):
    token = str(payload.get("token", "") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Reset token required")
    user = await users_collection.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires_at = user.get("reset_token_expiry")
    if not expires_at or not isinstance(expires_at, datetime):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    now = datetime.now(timezone.utc)
    if expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="Reset token expired")
    return {"status": "VALID"}

@app.get("/auth/reset-password/verify")
async def verify_reset_token_get(token: str = Query(...)):
    token = token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Reset token required")
    user = await users_collection.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires_at = user.get("reset_token_expiry")
    if not expires_at or not isinstance(expires_at, datetime):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    now = datetime.now(timezone.utc)
    if expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="Reset token expired")
    return {"status": "VALID"}

# ================= RESET PASSWORD =================
@app.post("/auth/reset-password")
async def reset_password(payload: Dict[str, Any] = Body(...)):
    token = str(payload.get("token", "") or "").strip()
    password = str(payload.get("password", "") or "")
    if not token:
        raise HTTPException(status_code=400, detail="Reset token required")
    if not password:
        raise HTTPException(status_code=400, detail="Password required")

    user = await users_collection.find_one({"reset_token": token})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires_at = user.get("reset_token_expiry")
    if not expires_at or not isinstance(expires_at, datetime):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    now = datetime.now(timezone.utc)
    if expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="Reset token expired")

    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"hashed_password": hash_password(password)},
            "$unset": {"reset_token": "", "reset_token_expiry": ""},
        }
    )

    return {"status": "PASSWORD_RESET"}

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

    structured_resume_text = resume_text or ""
    if not _normalize_resume_text(structured_resume_text) and resume_data_url:
        pdf_bytes = _decode_pdf_data_url(resume_data_url)
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="The uploaded resume could not be decoded.")
        structured_resume_text = _extract_pdf_text_from_bytes(pdf_bytes)

    normalized_resume_text = _normalize_resume_text(structured_resume_text)
    if not normalized_resume_text:
        raise HTTPException(
            status_code=400,
            detail="We could not read text from this PDF. Try a text-based resume PDF instead of a scanned image.",
        )

    looks_like_resume, resume_error = _looks_like_resume(structured_resume_text, file_name)
    if not looks_like_resume:
        raise HTTPException(
            status_code=400,
            detail=resume_error or "This document does not look like a resume or CV. Please upload a proper resume/CV file.",
        )

    fallback_analysis = _build_resume_analysis_payload(structured_resume_text, file_name)
    fallback_job_requirements = _build_job_requirements_payload(job_description)
    fallback_scorecard = _build_resume_scorecard(normalized_resume_text, file_name)
    fallback_match_payload = _build_job_match_payload(normalized_resume_text, job_description)
    fallback_spelling_payload = _build_spelling_payload(normalized_resume_text, fallback_match_payload)
    fallback_quality = _build_resume_quality_payload(
        structured_resume_text,
        fallback_analysis,
        fallback_scorecard,
        fallback_match_payload,
        fallback_job_requirements,
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
        fallback_job_requirements,
    )
    fallback_recommendations = _build_resume_recommendations(
        fallback_analysis,
        fallback_scorecard,
        fallback_match_payload,
        fallback_spelling_payload,
        fallback_job_requirements,
        fallback_quality,
    )

    fallback_payload = {
        "analysis": fallback_analysis,
        "job_requirements": fallback_job_requirements,
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
            structured_resume_text,
            job_description,
            file_name,
            fallback_payload,
        )
        analysis = generated_payload["analysis"]
        job_requirements = generated_payload["job_requirements"]
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
        job_requirements = fallback_job_requirements
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
        "resume_text": normalized_resume_text,
        "analysis": analysis,
        "job_requirements": job_requirements,
        "scorecard": scorecard,
        "match": match_payload,
        "dashboard": dashboard,
        "spelling": spelling_payload,
        "role_focus": role_focus,
        "quality": quality,
        "recommendations": recommendations,
        "providers": provider_meta,
    }


@app.post("/resume-analyzer/validate")
async def validate_resume_upload(
    file_name: str = Body(""),
    resume_text: str = Body(""),
    resume_data_url: str = Body(""),
    authorization: str = Header(...),
):
    token = authorization.replace("Bearer ", "")
    await get_current_user(token, allow_db_fallback=True)

    structured_resume_text = resume_text or ""
    if not _normalize_resume_text(structured_resume_text) and resume_data_url:
        pdf_bytes = _decode_pdf_data_url(resume_data_url)
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail="The uploaded resume could not be decoded.")
        structured_resume_text = _extract_pdf_text_from_bytes(pdf_bytes)
    structured_resume_text = _prepare_resume_text_for_analysis(structured_resume_text)

    normalized_resume_text = _normalize_resume_text(structured_resume_text)
    if not normalized_resume_text:
        raise HTTPException(
            status_code=400,
            detail="We could not read text from this PDF. Please upload a text-based resume PDF, not a scanned image PDF.",
        )

    looks_like_resume, resume_error = _looks_like_resume(structured_resume_text, file_name)
    if not looks_like_resume:
        raise HTTPException(
            status_code=400,
            detail=resume_error or "This document does not look like a resume or CV. Please upload a proper resume/CV file.",
        )

    details = _resume_signal_details(structured_resume_text, file_name)
    return {
        "status": "RESUME_VALIDATED",
        "valid": True,
        "message": "Resume PDF accepted.",
        "word_count": details["word_count"],
        "contact_checks": {
            "email": details["has_email"],
            "phone": details["has_phone"],
            "profile_link": details["has_profile_link"],
        },
        "resume_signal_score": details["score"],
    }


@app.post("/resume-interview/extract")
async def extract_resume_interview_data(
    file_name: str = Body(""),
    resume_text: str = Body(""),
    resume_data_url: str = Body(""),
    job_role: str = Body(""),
    authorization: str = Header(None),
):
    try:
        if authorization:
            token = authorization.replace("Bearer ", "")
            await get_current_user(token, allow_db_fallback=True)

        structured_resume_text = resume_text or ""
        if not _normalize_resume_text(structured_resume_text) and resume_data_url:
            pdf_bytes = _decode_pdf_data_url(resume_data_url)
            if not pdf_bytes:
                raise HTTPException(status_code=400, detail="The uploaded resume could not be decoded.")
            structured_resume_text = _extract_pdf_text_from_bytes(pdf_bytes)
        structured_resume_text = _prepare_resume_text_for_analysis(structured_resume_text)

        normalized_resume_text = _normalize_resume_text(structured_resume_text)
        if not normalized_resume_text:
            raise HTTPException(
                status_code=400,
                detail="We could not read useful text from this PDF. Please try another resume PDF.",
            )

        payload = _build_resume_interview_extract_payload(structured_resume_text, file_name, job_role)
        return {
            "status": "RESUME_INTERVIEW_READY",
            **payload,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume interview extraction failed: {exc}")

# ================= INTERVIEW RESULTS =================
@app.post("/interview-result")
async def save_interview_result(
    payload: dict = Body(...),
    authorization: str = Header(...)
):
    """Save interview result to database"""
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        now = datetime.now(timezone.utc).isoformat()
        category = str(payload.get("category") or "general")
        context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
        score = payload.get("overall_score", payload.get("score", 0))

        interview_result = {
            "session_id": payload.get("session_id") or f"manual-{uuid.uuid4()}",
            "user_id": str(current_user["_id"]),
            "category": category,
            "interview_type": payload.get("interview_type") or category,
            "type": payload.get("type") or category,
            "selected_mode": payload.get("selected_mode") or context.get("selected_mode"),
            "job_role": payload.get("job_role") or context.get("job_role"),
            "primary_language": payload.get("primary_language") or context.get("primary_language"),
            "experience": payload.get("experience") or context.get("experience"),
            "context": {
                "category": category,
                **context,
            },
            "score": score,
            "overall_score": score,
            "summary": payload.get("summary") or payload.get("transcript") or "",
            "top_strengths": payload.get("top_strengths", []),
            "improvement_areas": payload.get("improvement_areas", []),
            "strongest_questions": payload.get("strongest_questions", []),
            "needs_work_questions": payload.get("needs_work_questions", []),
            "score_breakdown": payload.get("score_breakdown"),
            "answers": payload.get("answers", []),
            "evaluations": payload.get("evaluations", []),
            "questions_answered": payload.get("questions_answered", 0),
            "total_questions": payload.get("total_questions", payload.get("question_count", 0)),
            "question_outline": payload.get("question_outline", payload.get("questions", [])),
            "transcript": payload.get("transcript", ""),
            "timestamp": payload.get("timestamp") or now,
            "completed_at": payload.get("completed_at") or now,
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
        fast_feedback = payload.get("fast_feedback", True)
        public_cases = list(challenge.get("public_test_cases") or [])
        hidden_cases = list(challenge.get("hidden_test_cases") or [])
        cached_public_execution = payload.get("cached_public_execution") if isinstance(payload.get("cached_public_execution"), dict) else None

        if cached_public_execution and hidden_cases:
            hidden_execution = run_code_against_tests(language, source_code, hidden_cases)
            execution = merge_execution_results(cached_public_execution, hidden_execution)
        elif cached_public_execution:
            execution = cached_public_execution
        else:
            execution = run_code_against_tests(language, source_code, public_cases + hidden_cases)
        review = (
            build_fallback_coding_review(execution)
            if fast_feedback
            else await evaluate_coding_submission(challenge, language, source_code, execution)
        )
        return {
            "execution": execution,
            "review": review,
        }
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to submit coding solution: {exc}")


@app.post("/mcq/computer-fundamentals")
async def create_computer_fundamentals_mcqs(payload: dict = Body(...)):
    try:
        count = payload.get("count") or 10
        questions = await generate_computer_fundamentals_questions(count)
        return {"questions": questions}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate computer fundamentals questions: {exc}")


@app.post("/mcq/aptitude")
async def create_aptitude_mcqs(payload: dict = Body(...)):
    try:
        count = payload.get("count") or 10
        questions = await generate_aptitude_questions(count)
        return {"questions": questions}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate aptitude questions: {exc}")


@app.post("/mcq/reasoning")
async def create_reasoning_mcqs(payload: dict = Body(...)):
    try:
        count = payload.get("count") or 10
        questions = await generate_reasoning_questions(count)
        return {"questions": questions}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate reasoning questions: {exc}")


@app.post("/mcq/verbal")
async def create_verbal_mcqs(payload: dict = Body(...)):
    try:
        count = payload.get("count") or 10
        questions = await generate_verbal_questions(count)
        return {"questions": questions}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate verbal questions: {exc}")


@app.post("/mcq/advanced-quant")
async def create_advanced_quant_mcqs(payload: dict = Body(...)):
    try:
        count = payload.get("count") or 10
        questions = await generate_advanced_quant_questions(count)
        return {"questions": questions}
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate advanced quantitative questions: {exc}")


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


@app.get("/platform-metrics")
async def get_platform_metrics():
    try:
        total_users = await users_collection.count_documents({})
        rating_summary = await report_ratings_collection.aggregate([
            {
                "$group": {
                    "_id": None,
                    "sum_ratings": {"$sum": "$rating"},
                    "total_ratings": {"$sum": 1},
                }
            }
        ]).to_list(length=1)

        summary = rating_summary[0] if rating_summary else {}
        total_ratings = int(summary.get("total_ratings", 0) or 0)
        sum_ratings = float(summary.get("sum_ratings", 0) or 0)
        average_rating = round(sum_ratings / total_ratings, 1) if total_ratings else 0.0

        return {
            "total_users": total_users,
            "average_rating": average_rating,
            "total_ratings": total_ratings,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch platform metrics: {exc}")


@app.get("/report-ratings/{session_id}")
async def get_report_rating(session_id: str, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        match = next((item for item in reports if item.get("session_id") == session_id), None)

        if not match:
            raise HTTPException(status_code=404, detail="Interview report not found")

        rating_doc = await report_ratings_collection.find_one({
            "session_id": session_id,
            "user_id": str(current_user["_id"]),
        })
        return {"rating": int(rating_doc.get("rating", 0)) if rating_doc else None}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report rating: {exc}")


@app.post("/report-ratings/{session_id}")
async def save_report_rating(
    session_id: str,
    rating: int = Body(..., embed=True),
    authorization: str = Header(...),
):
    try:
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        match = next((item for item in reports if item.get("session_id") == session_id), None)

        if not match:
            raise HTTPException(status_code=404, detail="Interview report not found")

        now = datetime.now(timezone.utc)
        await report_ratings_collection.update_one(
            {
                "session_id": session_id,
                "user_id": str(current_user["_id"]),
            },
            {
                "$set": {
                    "rating": int(rating),
                    "session_id": session_id,
                    "user_id": str(current_user["_id"]),
                    "user_email": current_user.get("email", ""),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                },
            },
            upsert=True,
        )

        return {"rating": int(rating), "message": "Rating saved successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save report rating: {exc}")

# ---------------- EMAIL RESET CONFIG ----------------
RESET_EMAIL_FROM = os.getenv("RESET_EMAIL_FROM", "").strip()
RESET_EMAIL_SMTP_HOST = os.getenv("RESET_EMAIL_SMTP_HOST", "").strip()
RESET_EMAIL_SMTP_PORT = int(os.getenv("RESET_EMAIL_SMTP_PORT", "587"))
RESET_EMAIL_SMTP_USER = os.getenv("RESET_EMAIL_SMTP_USER", "").strip()
RESET_EMAIL_SMTP_PASS = os.getenv("RESET_EMAIL_SMTP_PASS", "").strip()
RESET_EMAIL_BASE_URL = os.getenv("RESET_EMAIL_BASE_URL", "http://localhost:3000").rstrip("/")
DEV_RETURN_RESET_TOKEN = os.getenv("DEV_RETURN_RESET_TOKEN", "false").strip().lower() in {"1", "true", "yes"}

def _send_reset_email(to_email: str, token: str) -> None:
    if not RESET_EMAIL_FROM or not RESET_EMAIL_SMTP_HOST:
        return
    reset_link = f"{RESET_EMAIL_BASE_URL}/reset-password?token={token}"
    msg = EmailMessage()
    msg["Subject"] = "Reset your INTERVIEWR password"
    msg["From"] = RESET_EMAIL_FROM
    msg["To"] = to_email
    msg.set_content(
        "You requested a password reset for INTERVIEWR.\n\n"
        f"Reset link: {reset_link}\n\n"
        "This link is valid for 5 minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(RESET_EMAIL_SMTP_HOST, RESET_EMAIL_SMTP_PORT) as server:
        server.starttls()
        if RESET_EMAIL_SMTP_USER and RESET_EMAIL_SMTP_PASS:
            server.login(RESET_EMAIL_SMTP_USER, RESET_EMAIL_SMTP_PASS)
        server.send_message(msg)
