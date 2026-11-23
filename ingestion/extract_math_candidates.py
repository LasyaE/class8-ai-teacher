import json
import re
from pathlib import Path

import fitz

PDF = Path("data/textbooks/Math.pdf")
OUT = Path("data/training/mathematics")
OUT.mkdir(parents=True, exist_ok=True)

CHAPTERS = [
    (1, "Rational Numbers", 13, 45),
    (2, "Linear Equations in One Variable", 46, 70),
    (3, "Construction of Quadrilaterals", 71, 92),
    (4, "Exponents and Powers", 93, 107),
    (5, "Comparing Quantities using Proportion", 108, 133),
    (6, "Square Roots and Cube Roots", 134, 159),
    (7, "Frequency Distribution Tables and Graphs", 160, 192),
    (8, "Exploring Geometrical Figures", 193, 210),
    (9, "Area of Plane Figures", 211, 242),
    (10, "Direct and Inverse Proportions", 243, 259),
    (11, "Algebraic Expressions", 260, 278),
    (12, "Factorisation", 279, 293),
    (13, "Visualizing 3-D in 2-D", 294, 308),
    (14, "Surface Area and Volume (Cube and Cuboid)", 309, 322),
    (15, "Playing with Numbers", 323, 348),
]

if not PDF.exists():
    raise FileNotFoundError(f"Textbook not found: {PDF}")

doc = fitz.open(PDF)
candidates = []

question_pattern = re.compile(
    r"(?im)^\s*(?:(?:\d{1,2})\s*[.)]|(?:[a-h])\s*[.)]|"
    r"(?:solve|find|calculate|evaluate|construct|verify|"
    r"prove|simplify|factorise|factorize|explain|write|"
    r"draw|compare|show that|how many|what is|which of))\s+"
)

for number, title, first, last in CHAPTERS:
    for page_number in range(first, last + 1):
        text = doc[page_number - 1].get_text("text")
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for index, line in enumerate(lines):
            if question_pattern.search(line):
                context = "\n".join(lines[index:index + 8])
                candidates.append({
                    "chapter": number,
                    "chapter_title": title,
                    "pdf_page": page_number,
                    "source_file": "Math.pdf",
                    "source_type": "candidate_question",
                    "candidate_text": context,
                    "requires_human_verification": True,
                })

output = OUT / "question_candidates.jsonl"
with output.open("w", encoding="utf-8") as file:
    for item in candidates:
        file.write(json.dumps(item, ensure_ascii=False) + "\n")

report = {
    "source": str(PDF),
    "pdf_pages": len(doc),
    "chapters_scanned": len(CHAPTERS),
    "pages_scanned": sum(last - first + 1 for _, _, first, last in CHAPTERS),
    "candidate_count": len(candidates),
    "output": str(output),
    "important": (
        "These are text-matching candidates, not verified questions. "
        "Review against the original PDF before using them for training."
    ),
}

(OUT / "extraction_report.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(json.dumps(report, indent=2, ensure_ascii=False))
