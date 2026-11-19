"""
ASCENT — CV Extractor

Extracts B.Tech branch and CGPA from a student's
CV PDF using pdfplumber for text extraction and
regex patterns for field identification.

Extracted fields:
- btech_branch: detected programme category
  ("CS_IT", "ECE_EE", "MECHANICAL", "CIVIL", "OTHER")
- btech_cgpa: float between 0.0 and 10.0
- extraction_confidence: "high" / "medium" / "low"
- raw_text_length: int (for debugging)

These are stored in the student MongoDB document
and used as Factor 6 in the recommendation engine.
"""

import re
import io
import sys
import os

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# ── Branch keyword mappings ───────────────────────────────

BRANCH_KEYWORDS = {
    "CS_IT": [
        "computer science", "computer engineering",
        "information technology", "software engineering",
        "b.tech cse", "b.tech cs", "b.e. cse",
        "b.e. cs", "b.tech it", "b.e. it",
        "computing", "cse", " cs ", " it ",
        "data science", "artificial intelligence",
    ],
    "ECE_EE": [
        "electronics", "communication engineering",
        "electrical engineering", "ece", " ee ",
        "electronics and communication",
        "electronics & communication",
        "electrical and electronics",
        "vlsi", "embedded systems",
        "b.tech ece", "b.e. ece", "b.tech ee",
    ],
    "MECHANICAL": [
        "mechanical engineering", "mechanical",
        "b.tech me", "b.e. me", "production engineering",
        "manufacturing", "thermal", "automobile",
        "robotics", "mechatronics",
    ],
    "CIVIL": [
        "civil engineering", "civil",
        "b.tech civil", "b.e. civil",
        "structural", "geotechnical",
        "environmental engineering",
    ],
    "CHEMICAL": [
        "chemical engineering", "chemical",
        "b.tech chemical", "b.e. chemical",
    ],
    "OTHER": [],  # fallback
}

# Score adjustment for each branch when applying
# to CSE/DA M.Tech programmes
BRANCH_SCORE_ADJUSTMENT = {
    "CS_IT":     +3,
    "ECE_EE":     0,
    "MECHANICAL": -3,
    "CIVIL":      -3,
    "CHEMICAL":   -3,
    "OTHER":       0,
    None:          0,  # no CV uploaded
}

# CGPA score adjustment
def cgpa_adjustment(cgpa: float) -> int:
    if cgpa is None:
        return 0
    if cgpa >= 8.5:
        return +2
    if cgpa >= 7.0:
        return 0
    return -2


# ── Text extraction ───────────────────────────────────────

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes using pdfplumber."""
    if pdfplumber is None:
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

def detect_branch(text: str) -> tuple:
    """
    Detect B.Tech branch from CV text.
    Returns (branch_code, confidence).
    """
    if not text:
        return None, "low"

    scores = {branch: 0 for branch in BRANCH_KEYWORDS}

    for branch, keywords in BRANCH_KEYWORDS.items():
        if branch == "OTHER":
            continue
        for kw in keywords:
            if kw.lower() in text:
                scores[branch] += 1

    # Find best match
    best_branch = max(
        (b for b in scores if b != "OTHER"),
        key=lambda b: scores[b],
        default=None
    )

    if best_branch and scores[best_branch] >= 2:
        confidence = "high"
    elif best_branch and scores[best_branch] == 1:
        confidence = "medium"
        best_branch = best_branch
    else:
        best_branch = "OTHER"
        confidence = "low"

    return best_branch, confidence


# ── CGPA detection ────────────────────────────────────────

def detect_cgpa(text: str) -> tuple:
    """
    Detect CGPA from CV text.
    Returns (cgpa_float, confidence).
    Handles formats: 8.5/10, 8.5, 85%, 8.52/10.0
    """
    if not text:
        return None, "low"

    patterns = [
        # Pattern: 8.5/10 or 8.52/10.0
        r'cgpa[\s:]*([0-9]\.[0-9]{1,2})\s*/\s*10',
        r'gpa[\s:]*([0-9]\.[0-9]{1,2})\s*/\s*10',
        r'([0-9]\.[0-9]{1,2})\s*/\s*10[\s\.,]',

        # Pattern: CGPA: 8.5
        r'cgpa[\s:]+([0-9]\.[0-9]{1,2})',
        r'c\.g\.p\.a[\s:]+([0-9]\.[0-9]{1,2})',
        r'gpa[\s:]+([0-9]\.[0-9]{1,2})',

        # Pattern: Cumulative GPA 8.5
        r'cumulative[\s\w]*gpa[\s:]*([0-9]\.[0-9]{1,2})',

        # Percentage: 85% → convert to CGPA ÷ 10
        r'([0-9]{2}\.[0-9]{1,2})\s*%',
        r'percentage[\s:]+([0-9]{2}\.[0-9]{1,2})',
        r'([0-9]{2}\.[0-9]{1,2})\s*percent',
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))

                # If percentage format (> 10), convert
                if val > 10:
                    val = val / 10.0

                # Sanity check: CGPA should be 0-10
                if 0 < val <= 10:
                    confidence = "high" if i < 5 else "medium"
                    return round(val, 2), confidence
            except ValueError:
                continue

    return None, "low"


# ── Main extraction function ──────────────────────────────

def extract_cv_fields(pdf_bytes: bytes) -> dict:
    """
    Main function: extract B.Tech branch and CGPA
    from PDF bytes.

    Returns dict:
    {
        "btech_branch": str or None,
        "btech_cgpa": float or None,
        "branch_confidence": str,
        "cgpa_confidence": str,
        "extraction_success": bool,
        "raw_text_length": int,
        "error": str or None
    }
    """
    result = {
        "btech_branch":       None,
        "btech_cgpa":         None,
        "branch_confidence":  "low",
        "cgpa_confidence":    "low",
        "extraction_success": False,
        "raw_text_length":    0,
        "error":              None,
    }

    try:
        text = extract_text_from_pdf(pdf_bytes)
        result["raw_text_length"] = len(text)

        if len(text) < 50:
            result["error"] = (
                "PDF text too short — may be a scanned image. "
                "Text extraction requires a text-based PDF."
            )
            return result

        branch, branch_conf = detect_branch(text)
        cgpa,   cgpa_conf   = detect_cgpa(text)

        result["btech_branch"]      = branch
        result["btech_cgpa"]        = cgpa
        result["branch_confidence"] = branch_conf
        result["cgpa_confidence"]   = cgpa_conf
        result["extraction_success"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


# ── Score adjustment helper ───────────────────────────────

def get_cv_score_adjustment(student: dict) -> int:
    """
    Compute total score adjustment from CV data.
    Returns integer to add to total_score in
    score_nit_programme().
    """
    branch = student.get("btech_branch")
    cgpa   = student.get("btech_cgpa")

    branch_adj = BRANCH_SCORE_ADJUSTMENT.get(branch, 0)
    cgpa_adj   = cgpa_adjustment(cgpa)

    return branch_adj + cgpa_adj


# ── Test locally ──────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cv_extractor.py path/to/cv.pdf")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "rb") as f:
        pdf_bytes = f.read()

    result = extract_cv_fields(pdf_bytes)
    print(f"\nCV Extraction Results:")
    print(f"  B.Tech Branch:  {result['btech_branch']} "
          f"(confidence: {result['branch_confidence']})")
    print(f"  CGPA:           {result['btech_cgpa']} "
          f"(confidence: {result['cgpa_confidence']})")
    print(f"  Text length:    {result['raw_text_length']} chars")
    if result["error"]:
        print(f"  Error: {result['error']}")

    adj = get_cv_score_adjustment({
        "btech_branch": result["btech_branch"],
        "btech_cgpa":   result["btech_cgpa"]
    })
    print(f"  Score adjustment: {adj:+d} points")