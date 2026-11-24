"""
ASCENT — CV Extractor

Extracts B.Tech branch and CGPA from student CV PDF.
Used as an OPTIONAL BONUS on top of the core 5-factor
recommendation engine. Does not replace any existing factor.

The student must:
1. Upload their PDF CV
2. Confirm the extracted data is correct
3. Choose whether to include it in recommendations

Validation:
- CGPA must be between 0 and 10
- Branch must be a recognised engineering discipline
- Student explicitly confirms the data before it is saved

Note: We cannot verify the document is the student's own.
We rely on student confirmation (standard practice for
all academic platforms like LinkedIn, Naukri, etc.)
"""

import re
import io
import os
import sys

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


# ── Branch definitions ────────────────────────────────────

BRANCH_KEYWORDS = {
    "CS_IT": [
        "computer science", "computer engineering",
        "information technology", "software engineering",
        "b.tech cse", "b.tech cs", "b.e. cse", "b.e. cs",
        "b.tech it", "b.e. it", "computing", "cse", " it ",
        "data science", "artificial intelligence",
        "information science",
    ],
    "ECE_EE": [
        "electronics", "communication engineering",
        "electrical engineering", "ece", " ee ",
        "electronics and communication",
        "electronics & communication",
        "electrical and electronics", "vlsi",
        "embedded systems", "b.tech ece", "b.e. ece",
        "b.tech ee", "telecommunication",
    ],
    "MECHANICAL": [
        "mechanical engineering", "mechanical",
        "b.tech me", "b.e. me", "production engineering",
        "manufacturing", "thermal engineering",
        "automobile", "robotics", "mechatronics",
        "industrial engineering",
    ],
    "CIVIL": [
        "civil engineering", "civil",
        "b.tech civil", "b.e. civil", "structural engineering",
        "geotechnical", "environmental engineering",
        "construction",
    ],
    "CHEMICAL": [
        "chemical engineering", "chemical",
        "b.tech chemical", "b.e. chemical",
        "biochemical", "petrochemical",
    ],
    "OTHER": [],
}

BRANCH_DISPLAY = {
    "CS_IT":      "CS / IT / Software Engineering",
    "ECE_EE":     "ECE / EE / Electronics",
    "MECHANICAL": "Mechanical / Production",
    "CIVIL":      "Civil / Environmental",
    "CHEMICAL":   "Chemical Engineering",
    "OTHER":      "Other Engineering",
}

# Score bonus when CV background used (optional add-on only)
# This does NOT change the 5-factor engine weights
CV_BONUS = {
    # Branch bonus for CSE/DA programme match
    "branch": {
        "CS_IT":      +3,   # Strong match
        "ECE_EE":      0,   # Neutral
        "MECHANICAL": -2,   # Weak match
        "CIVIL":      -2,   # Weak match
        "CHEMICAL":   -2,   # Weak match
        "OTHER":       0,   # Unknown
        None:          0,   # No CV uploaded
    },
    # CGPA bonus
    "cgpa": {
        "high":    +2,   # CGPA >= 8.5
        "medium":   0,   # CGPA 7.0-8.4
        "low":     -2,   # CGPA < 7.0
        None:       0,   # Not provided
    }
}


def cgpa_tier(cgpa):
    if cgpa is None:
        return None
    if cgpa >= 8.5:
        return "high"
    if cgpa >= 7.0:
        return "medium"
    return "low"


def get_cv_bonus(student: dict) -> int:
    """
    Compute CV bonus points.
    Returns 0 if use_cv_in_recommendations is False.
    Returns 0 if no CV data uploaded.
    This is SEPARATE from the 5-factor score.
    """
    if not student.get("use_cv_in_recommendations", True):
        return 0
    if not student.get("cv_confirmed", False):
        return 0

    branch  = student.get("btech_branch")
    cgpa    = student.get("btech_cgpa")

    branch_bonus = CV_BONUS["branch"].get(branch, 0)
    cgpa_bonus   = CV_BONUS["cgpa"].get(cgpa_tier(cgpa), 0)

    return branch_bonus + cgpa_bonus


# ── PDF text extraction ───────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError(
            "pdfplumber not installed. "
            "Run: pip install pdfplumber --break-system-packages"
        )
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).lower()


# ── Branch detection ──────────────────────────────────────

def detect_branch(text: str):
    scores = {b: 0 for b in BRANCH_KEYWORDS if b != "OTHER"}
    for branch, keywords in BRANCH_KEYWORDS.items():
        if branch == "OTHER":
            continue
        for kw in keywords:
            if kw.lower() in text:
                scores[branch] += 1

    best  = max(scores, key=lambda b: scores[b])
    count = scores[best]

    if count >= 2:
        return best, "high"
    elif count == 1:
        return best, "medium"
    else:
        return "OTHER", "low"


# ── CGPA detection ────────────────────────────────────────

def detect_cgpa(text: str):
    """
    Detect B.Tech CGPA from CV text.
    Uses context-aware matching — looks for CGPA values
    that appear near B.Tech/UG degree keywords.
    Falls back to highest CGPA if context matching fails,
    since B.Tech CGPA is typically higher than M.Tech CGPA
    for students who improved during undergrad.

    Returns (cgpa_float, confidence).
    """
    if not text:
        return None, "low"

    # ── Strategy 1: Context-aware search ─────────────────
    # Look for CGPA near B.Tech / undergraduate keywords
    # Split text into sections around degree mentions

    btech_context_keywords = [
        "b.tech", "b.e.", "bachelor", "undergraduate",
        "ug", "b tech", "be ", "b.e ", "btech",
        "bachelor of technology", "bachelor of engineering",
    ]

    mtech_context_keywords = [
        "m.tech", "m.e.", "master", "postgraduate",
        "pg", "m tech", "me ", "m.e ", "mtech",
        "master of technology", "master of engineering",
        "ph.d", "phd", "doctorate",
    ]

    # Split text into lines for context analysis
    lines = text.split('\n')

    # Find line indices where B.Tech and M.Tech are mentioned
    btech_lines = []
    mtech_lines = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in btech_context_keywords):
            btech_lines.append(i)
        if any(kw in line_lower for kw in mtech_context_keywords):
            mtech_lines.append(i)

    # CGPA patterns to search within context windows
    cgpa_patterns = [
        r'cgpa[\s:]*([0-9]\.[0-9]{1,2})\s*/\s*10',
        r'gpa[\s:]*([0-9]\.[0-9]{1,2})\s*/\s*10',
        r'([0-9]\.[0-9]{1,2})\s*/\s*10[\s\.,\)]',
        r'cgpa[\s:]+([0-9]\.[0-9]{1,2})',
        r'c\.g\.p\.a[\s:]+([0-9]\.[0-9]{1,2})',
        r'gpa[\s:]+([0-9]\.[0-9]{1,2})',
        r'cumulative[\s\w]*gpa[\s:]*([0-9]\.[0-9]{1,2})',
    ]

    percentage_patterns = [
        r'([0-9]{2}\.[0-9]{1,2})\s*%',
        r'percentage[\s:]+([0-9]{2}\.[0-9]{1,2})',
        r'([0-9]{2}\.[0-9]{1,2})\s*percent',
    ]

    def extract_cgpa_from_text_segment(segment: str):
        """Extract CGPA value from a text segment."""
        for pattern in cgpa_patterns:
            match = re.search(pattern, segment, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    if 0 < val <= 10:
                        return val, "high"
                except ValueError:
                    continue
        for pattern in percentage_patterns:
            match = re.search(pattern, segment, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    if val > 10:
                        val = round(val / 10.0, 2)
                    if 0 < val <= 10:
                        return val, "medium"
                except ValueError:
                    continue
        return None, "low"

    # If we found B.Tech line references, search nearby lines
    if btech_lines:
        for btech_line_idx in btech_lines:
            # Search in a window of ±5 lines around B.Tech mention
            window_start = max(0, btech_line_idx - 2)
            window_end   = min(len(lines), btech_line_idx + 6)
            window_text  = '\n'.join(lines[window_start:window_end])

            # Skip if this window also mentions M.Tech
            # (avoid picking up M.Tech CGPA from same row)
            window_has_mtech = any(
                kw in window_text.lower()
                for kw in mtech_context_keywords
            )

            cgpa, conf = extract_cgpa_from_text_segment(window_text)
            if cgpa and not window_has_mtech:
                return cgpa, conf

        # If B.Tech window also had M.Tech mention,
        # try a wider search excluding M.Tech sections
        for btech_line_idx in btech_lines:
            window_start = max(0, btech_line_idx - 2)
            window_end   = min(len(lines), btech_line_idx + 6)
            window_text  = '\n'.join(lines[window_start:window_end])
            cgpa, conf = extract_cgpa_from_text_segment(window_text)
            if cgpa:
                return cgpa, "medium"

    # ── Strategy 2: Take the highest CGPA in the document ─
    # Rationale: B.Tech students typically improve from UG
    # to PG, so B.Tech CGPA is often the higher value.
    # M.Tech CGPA tends to be lower (harder curriculum).
    # This is a heuristic — not always true.

    all_cgpas = []
    for pattern in cgpa_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = float(match.group(1))
                if 0 < val <= 10:
                    all_cgpas.append(val)
            except ValueError:
                continue

    for pattern in percentage_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                val = float(match.group(1))
                if val > 10:
                    val = round(val / 10.0, 2)
                if 0 < val <= 10:
                    all_cgpas.append(val)
            except ValueError:
                continue

    if all_cgpas:
        # Remove duplicates and sort
        unique_cgpas = sorted(set(all_cgpas), reverse=True)

        if len(unique_cgpas) == 1:
            return unique_cgpas[0], "high"

        # Multiple CGPAs found — return highest
        # and flag as medium confidence
        return unique_cgpas[0], "medium"

    return None, "low"


# ── Main extraction ───────────────────────────────────────

def extract_cv_fields(pdf_bytes: bytes) -> dict:
    """
    Extract B.Tech branch and CGPA from PDF bytes.
    Returns a dict with extracted values and metadata.
    Student must CONFIRM these values before they are saved.
    """
    result = {
        "btech_branch":       None,
        "btech_cgpa":         None,
        "branch_display":     None,
        "branch_confidence":  "low",
        "cgpa_confidence":    "low",
        "extraction_success": False,
        "raw_text_length":    0,
        "needs_confirmation": True,
        "error":              None,
        "cgpa_note":          None,
    }

    if not PDFPLUMBER_AVAILABLE:
        result["error"] = (
            "pdfplumber not installed on server. "
            "Please use manual entry."
        )
        return result

    try:
        text = extract_text_from_pdf(pdf_bytes)
        result["raw_text_length"] = len(text)

        if len(text) < 100:
            result["error"] = (
                "Could not extract text from this PDF. "
                "It may be a scanned image. "
                "Please use manual entry below."
            )
            return result

        branch, branch_conf = detect_branch(text)
        cgpa, cgpa_conf     = detect_cgpa(text)

        result["btech_branch"]       = branch
        result["btech_cgpa"]         = cgpa
        result["branch_display"]     = BRANCH_DISPLAY.get(branch, branch)
        result["branch_confidence"]  = branch_conf
        result["cgpa_confidence"]    = cgpa_conf
        result["extraction_success"] = True
        result["needs_confirmation"] = True

        if cgpa_conf == "medium":
            result["cgpa_note"] = (
                "Multiple CGPAs found in CV. "
                "Please verify this is your B.Tech CGPA."
            )

    except Exception as e:
        result["error"] = f"Extraction failed: {str(e)}"

    return result