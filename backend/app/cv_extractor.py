"""
ASCENT — CV Extractor

Extracts B.Tech branch and CGPA/CPI from student CV PDFs.
Used as an OPTIONAL BONUS on top of the core 5-factor
recommendation engine.

Student must confirm extracted information before saving.
"""

import re
import io
import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False


# ── Branch definitions ────────────────────────────────────

BRANCH_KEYWORDS = {
    "CS_IT": [
        "computer science",
        "computer engineering",
        "information technology",
        "software engineering",
        "b.tech cse",
        "b.tech cs",
        "b.e. cse",
        "b.e. cs",
        "b.tech it",
        "b.e. it",
        "computing",
        "cse",
        "data science",
        "artificial intelligence",
        "information science",
        "machine learning",
        "cyber security",
        "cybersecurity",
        "computer applications",
        # Added
        "computational mathematics",
        "mathematics and computing",
        "mathematics & computing",
        "data engineering",
        "information engineering",
        "software systems",
        "it engineering",
    ],

    "ECE_EE": [
        "electronics and communication",
        "electronics and telecommunication",
        "electronics & communication",
        "electrical and electronics",
        "electrical engineering",
        "electronics engineering",
        "electronics and instrumentation",
        "instrumentation and control",
        "telecommunication engineering",
        "vlsi",
        "embedded systems",
        "b.tech ece",
        "b.e. ece",
        "b.tech ee",
        "ece",
        # Added
        "communication engineering",
        "power engineering",
        "power systems",
        "control engineering",
        "signal processing",
    ],

    "MECHANICAL": [
        "mechanical engineering",
        "automobile engineering",
        "automotive engineering",
        "production engineering",
        "manufacturing engineering",
        "thermal engineering",
        "robotics",
        "mechatronics",
        "industrial engineering",
        "aerospace engineering",
        "aeronautical engineering",
        # Added
        "design engineering",
        "product design",
        "tool engineering",
    ],

    "CIVIL": [
        "civil engineering",
        "structural engineering",
        "geotechnical engineering",
        "environmental engineering",
        "construction engineering",
        "transportation engineering",
        "water resources engineering",
        # Added
        "urban planning",
        "town planning",
        "construction management",
    ],

    "CHEMICAL": [
        "chemical engineering",
        "petrochemical engineering",
        "petroleum engineering",
        "polymer engineering",
        "process engineering",
        # Added
        "chemical technology",
        "refinery engineering",
    ],

    "BIOTECHNOLOGY": [
        "biotechnology",
        "bio technology",
        "biochemical engineering",
        "biomedical engineering",
        "bioengineering",
        "biological engineering",
        # Added
        "bioinformatics",
        "genetic engineering",
        "pharmaceutical technology",
    ],

    "OTHER": [
        "agricultural engineering",
        "food technology",
        "food engineering",
        "mining engineering",
        "metallurgical engineering",
        "materials science",
        "materials engineering",
        "nanotechnology",
        "biomedical science",
        "biochemistry",
        "biological sciences",
        "engineering physics",
        "instrumentation engineering",
        "energy engineering",
        "renewable energy",
        "textile engineering",
        "pharmaceutical engineering",
        "environmental science",
        "architecture",
        "physics",
        "mathematics",
        "chemistry",
    ],
}


BRANCH_DISPLAY = {
    "CS_IT":         "CS / IT / Software Engineering",
    "ECE_EE":        "ECE / EE / Electronics",
    "MECHANICAL":    "Mechanical / Production",
    "CIVIL":         "Civil / Environmental",
    "CHEMICAL":      "Chemical Engineering",
    "BIOTECHNOLOGY": "Biotechnology / Biomedical",
    "OTHER":         "Other Engineering / Discipline",
}


# ── CV scoring bonus ──────────────────────────────────────

CV_BONUS = {
    "branch": {
        "CS_IT":         +3,
        "ECE_EE":         0,
        "MECHANICAL":    -2,
        "CIVIL":         -2,
        "CHEMICAL":      -2,
        "BIOTECHNOLOGY":  0,
        "OTHER":          0,
        None:             0,
    },
    "cgpa": {
        "high":    +2,
        "medium":   0,
        "low":     -2,
        None:       0,
    }
}


# ── Section markers ───────────────────────────────────────

SECTION_END_MARKERS = [
    "research experience",
    "work experience",
    "professional experience",
    "internships",
    "projects",
    "technical skills",
    "achievements",
    "publications",
    "extracurricular",
    "responsibilities",
    "certifications",
    "references",
    "referrals",
    "positions of responsibility",
    "co-curricular activities",
]

UG_MARKERS = [
    "bachelor of technology",
    "bachelor of engineering",
    "bachelor of science",
    "bachelor of computer",
    "b.tech",
    "b. tech",
    "btech",
    "b.e.",
    "b.e ",   # space variant
    "b.e,",   # comma variant
    "b.sc",
    "bsc",
    "bca",
    "undergraduate",
    "b.tech.",
    "be in",
    "b.e in",
]

PG_MARKERS = [
    "master of technology",
    "master of engineering",
    "master of science",
    "m.tech",
    "m. tech",
    "mtech",
    "m.e.",
    "m.e ",
    "m.sc",
    "msc",
    "postgraduate",
    "m.tech.",
    "me in",
    "m.e in",
    "ph.d",
    "phd",
    "doctorate",
]


def _degree_type(line):
    line_lower = line.lower()
    # Check PG first (more specific)
    if any(marker in line_lower for marker in PG_MARKERS):
        return "PG"
    if any(marker in line_lower for marker in UG_MARKERS):
        return "UG"
    return None


def _is_section_end(line):
    line = line.strip().lower()
    return any(
        line == marker or line.startswith(marker + " ")
        for marker in SECTION_END_MARKERS
    )


# ── CGPA tier ─────────────────────────────────────────────

def cgpa_tier(cgpa):
    if cgpa is None:
        return None
    if cgpa >= 8.5:
        return "high"
    if cgpa >= 7.0:
        return "medium"
    return "low"


# ── CV bonus calculation ──────────────────────────────────

def get_cv_bonus(student: dict) -> int:
    """
    Compute optional CV bonus points.
    Returns 0 if use_cv_in_recommendations is False.
    Returns 0 if student has not confirmed CV data.
    This is SEPARATE from the 5-factor score.
    Max bonus: +5 (CS_IT + CGPA>=8.5)
    Max penalty: -4 (non-CS + CGPA<7.0)
    """
    if not student.get("use_cv_in_recommendations", True):
        return 0
    if not student.get("cv_confirmed", False):
        return 0

    branch = student.get("btech_branch")
    cgpa   = student.get("btech_cgpa")

    branch_bonus = CV_BONUS["branch"].get(branch, 0)
    cgpa_bonus   = CV_BONUS["cgpa"].get(cgpa_tier(cgpa), 0)

    return branch_bonus + cgpa_bonus


# ── PDF text extraction ───────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError(
            "pdfplumber is not installed. "
            "Run: pip install pdfplumber"
        )
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    if not isinstance(pdf_bytes, bytes):
        raise TypeError("PDF input must be bytes.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("The uploaded file is not a valid PDF.")

    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            if not pdf.pages:
                raise ValueError("The PDF contains no pages.")
            for page in pdf.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception:
                    continue
    except Exception as e:
        raise ValueError(f"Could not read PDF: {str(e)}") from e

    return "\n".join(text_parts).lower()


# ── Branch matching helper ────────────────────────────────

def _find_branch_in_text(text):
    text = re.sub(r"\s+", " ", text.lower()).strip()
    matches = []

    for branch, keywords in BRANCH_KEYWORDS.items():
        if branch == "OTHER":
            continue
        for keyword in keywords:
            keyword = keyword.lower().strip()
            if not keyword:
                continue
            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(keyword)
                + r"(?![a-z0-9])"
            )
            if re.search(pattern, text):
                matches.append((len(keyword), branch))

    if matches:
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    for keyword in BRANCH_KEYWORDS["OTHER"]:
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(keyword.lower())
            + r"(?![a-z0-9])"
        )
        if re.search(pattern, text):
            return "OTHER"

    return None


# ── Branch detection ──────────────────────────────────────

def detect_branch(text: str):
    if not text:
        return "OTHER", "low"

    lines = text.lower().splitlines()
    degree_entries = []

    for i, line in enumerate(lines):
        degree = _degree_type(line)
        if degree:
            degree_entries.append((i, degree))

    ug_candidates = []
    pg_candidates = []

    for position, (start, degree) in enumerate(degree_entries):
        end = (
            degree_entries[position + 1][0]
            if position + 1 < len(degree_entries)
            else min(start + 8, len(lines))  # wider window
        )

        section_lines = []
        for line in lines[start:end]:
            if _is_section_end(line):
                break
            section_lines.append(line)

        # Try first 3 lines (not just 2) for branch name
        window = " ".join(section_lines[:3])
        branch = _find_branch_in_text(window)

        # If not found in first 3 lines, try full section
        if not branch:
            full_window = " ".join(section_lines)
            branch = _find_branch_in_text(full_window)

        if branch:
            if degree == "UG":
                ug_candidates.append(branch)
            else:
                pg_candidates.append(branch)

    if ug_candidates:
        unique = list(dict.fromkeys(ug_candidates))
        if len(unique) == 1:
            return unique[0], "high"
        return unique[0], "medium"

    if pg_candidates:
        unique = list(dict.fromkeys(pg_candidates))
        if len(unique) == 1:
            return unique[0], "medium"
        return unique[0], "low"

    # Department line fallback
    for line in lines:
        if "department" in line:
            branch = _find_branch_in_text(line)
            if branch:
                return branch, "medium"

    # General keyword scan
    scores = {
        branch: 0
        for branch in BRANCH_KEYWORDS
        if branch != "OTHER"
    }
    for line in lines:
        branch = _find_branch_in_text(line)
        if branch in scores:
            scores[branch] += 1

    if any(scores.values()):
        best = max(scores, key=scores.get)
        confidence = "medium" if scores[best] >= 2 else "low"
        return best, confidence

    for keyword in BRANCH_KEYWORDS["OTHER"]:
        if keyword in text:
            return "OTHER", "low"

    return "OTHER", "low"


# ── CGPA detection ────────────────────────────────────────

SCORE_PATTERN = re.compile(
    r"""
    \b(?:cgpa|cpi|gpa|c\.g\.p\.a\.|c\.p\.i\.)
    \s*[:=\-]?\s*
    ([0-9]{1,2}(?:\.[0-9]{1,3})?)
    (?:\s*/\s*10)?
    |
    \b([0-9](?:\.[0-9]{1,3})?)
    \s*/\s*10\b
    """,
    re.IGNORECASE | re.VERBOSE
)


def _extract_academic_scores(block):
    scores = []
    for match in SCORE_PATTERN.finditer(block):
        value_string = match.group(1) or match.group(2)
        if not value_string:
            continue
        try:
            value = float(value_string)
        except ValueError:
            continue
        if not (0 < value <= 10):
            continue
        context = block[
            max(0, match.start() - 25):
            min(len(block), match.end() + 25)
        ]
        if "%" in context:
            continue
        if "percentile" in context:
            continue
        if "gate" in context:
            continue
        scores.append(round(value, 3))
    return list(dict.fromkeys(scores))


def detect_cgpa(text: str):
    if not text:
        return None, "low", None

    lines = text.lower().splitlines()
    degree_entries = []

    for i, line in enumerate(lines):
        degree = _degree_type(line)
        if degree:
            degree_entries.append((i, degree))

    ug_scores = []
    pg_scores = []

    for position, (start, degree) in enumerate(degree_entries):
        end = (
            degree_entries[position + 1][0]
            if position + 1 < len(degree_entries)
            else min(start + 15, len(lines))
        )

        block_lines = []
        for line in lines[start:end]:
            if _is_section_end(line):
                break
            block_lines.append(line)

        block  = "\n".join(block_lines)
        scores = _extract_academic_scores(block)

        if degree == "UG":
            ug_scores.extend(scores)
        elif degree == "PG":
            pg_scores.extend(scores)

    ug_scores = list(dict.fromkeys(ug_scores))
    pg_scores = list(dict.fromkeys(pg_scores))

    if len(ug_scores) == 1:
        note = None
        if pg_scores:
            note = (
                f"Found postgraduate CGPA/CPI ({pg_scores[0]}) "
                f"and undergraduate CGPA/CPI ({ug_scores[0]}). "
                f"Showing undergraduate score."
            )
        return ug_scores[0], "high", note

    if len(ug_scores) > 1:
        return (
            None, "low",
            "Multiple undergraduate academic scores found. "
            "Please verify manually."
        )

    if pg_scores:
        return (
            None, "low",
            "Postgraduate CGPA/CPI found, but undergraduate "
            "score could not be identified. Please fill manually."
        )

    # Fallback
    all_scores = _extract_academic_scores(text)

    if len(all_scores) == 1:
        return (
            all_scores[0], "medium",
            "Academic score found but degree association "
            "could not be verified. Please confirm."
        )

    if len(all_scores) > 1:
        return (
            None, "low",
            "Multiple academic scores found without clear "
            "degree association. Please verify manually."
        )

    return None, "low", None


# ── Main extraction ───────────────────────────────────────

def extract_cv_fields(pdf_bytes: bytes) -> dict:
    result = {
        "btech_branch":       None,
        "btech_cgpa":         None,
        "branch_display":     None,
        "branch_confidence":  "low",
        "cgpa_confidence":    "low",
        "extraction_success": False,
        "raw_text_length":    0,
        "needs_confirmation": True,
        "cgpa_note":          None,
        "error":              None,
    }

    if not PDFPLUMBER_AVAILABLE:
        result["error"] = (
            "pdfplumber is not installed. Please use manual entry."
        )
        return result

    try:
        text = extract_text_from_pdf(pdf_bytes)
        result["raw_text_length"] = len(text)

        if len(text) < 100:
            result["error"] = (
                "Could not extract sufficient text from this PDF. "
                "It may be scanned or image-based. "
                "Please use manual entry."
            )
            return result

        branch, branch_conf            = detect_branch(text)
        cgpa, cgpa_conf, cgpa_note     = detect_cgpa(text)

        result["btech_branch"]         = branch
        result["btech_cgpa"]           = cgpa
        result["branch_display"]       = BRANCH_DISPLAY.get(branch, branch)
        result["branch_confidence"]    = branch_conf
        result["cgpa_confidence"]      = cgpa_conf
        result["cgpa_note"]            = cgpa_note
        result["extraction_success"]   = True
        result["needs_confirmation"]   = True

    except Exception as e:
        result["error"] = f"CV extraction failed: {str(e)}"

    return result