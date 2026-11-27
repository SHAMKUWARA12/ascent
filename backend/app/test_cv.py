# Save as: backend/app/test_cv.py
# Run as: python app/test_cv.py path/to/your/cv.pdf

import sys
import io

def test_pdf(filepath):
    import pdfplumber
    
    with pdfplumber.open(filepath) as pdf:
        text_parts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        text = "\n".join(text_parts).lower()
    
    print("=" * 60)
    print("FULL EXTRACTED TEXT:")
    print("=" * 60)
    print(text)
    print("\n" + "=" * 60)
    print("LINES CONTAINING 'cgpa' or 'gpa' or '%':")
    print("=" * 60)
    for i, line in enumerate(text.split('\n')):
        if any(kw in line for kw in ['cgpa', 'gpa', '%', '/10']):
            print(f"Line {i:3d}: {line}")

if __name__ == "__main__":
    filepath = sys.argv[1]

    test_pdf(filepath)

    print("\n" + "=" * 60)
    print("CV EXTRACTOR RESULT:")
    print("=" * 60)

    from cv_extractor import extract_text_from_pdf, detect_cgpa, detect_branch

    with open(filepath, 'rb') as f:
        pdf_bytes = f.read()

    text = extract_text_from_pdf(pdf_bytes)

    branch, branch_conf = detect_branch(text)
    cgpa, cgpa_conf, note = detect_cgpa(text)

    print(f"Branch: {branch} (confidence: {branch_conf})")
    print(f"CGPA:   {cgpa} (confidence: {cgpa_conf})")

    if note:
        print(f"Note:   {note}")