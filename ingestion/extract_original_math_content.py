#!/usr/bin/env python3
"""
Extract source-grounded Class 8 Telangana Mathematics material.

This script DOES NOT invent questions or answers. It reads the existing
PyMuPDF-extracted page text and creates:
  data/training/mathematics/source_pages.jsonl
  data/training/mathematics/question_candidates.jsonl
  data/training/mathematics/extraction_report.json

Every candidate retains its original PDF page and chapter. Candidate detection
is heuristic: review the source page before turning a candidate into a
question/answer training record.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "data" / "extracted" / "raw" / "mathematics" / "Math"
OUT_DIR = ROOT / "data" / "training" / "mathematics"

# Verified PDF page ranges from the textbook contents page.
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

QUESTION_MARKERS = re.compile(
    r"(?i)\b(?:EXERCISE|EXERCISES|EXAMPLE|EXAMPLES|TRY\s+THIS|"
    r"DO\s+THIS|THINK\s+AND\s+DISCUSS|ACTIVITY|PROBLEM)\b"
)
NUMBERED_ITEM = re.compile(
    r"^\s*(?:(?:Q(?:uestion)?\.?\s*)?\d{1,2}\s*[.)]|"
    r"\(?[a-z]\)\s*[.)]?)\s+"
)
QUESTION_MARK = re.compile(r"[?？]")

def load_page(pdf_page: int) -> str:
    path = PAGES_DIR / f"page-{pdf_page:04d}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Missing extracted page: {path}")
    return path.read_text(encoding="utf-8", errors="replace").strip()

def classify_page(text: str) -> list[str]:
    tags = []
    if QUESTION_MARKERS.search(text):
        tags.append("exercise_or_example_marker")
    if QUESTION_MARK.search(text):
        tags.append("question_mark")
    if any(NUMBERED_ITEM.match(line) for line in text.splitlines()):
        tags.append("numbered_items")
    if re.search(r"(?i)\bsolution\b|\bsolved example\b|\banswer\b", text):
        tags.append("possible_solution_or_answer")
    return tags

def main() -> int:
    if not PAGES_DIR.is_dir():
        print(f"ERROR: extracted Mathematics folder not found:\n{PAGES_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_path = OUT_DIR / "source_pages.jsonl"
    candidates_path = OUT_DIR / "question_candidates.jsonl"
    report_path = OUT_DIR / "extraction_report.json"

    source_records = []
    candidate_records = []
    missing_pages = []
    chapter_counts = Counter()

    for chapter_no, title, start, end in CHAPTERS:
        print(f"Extracting Chapter {chapter_no}: {title}")
        for pdf_page in range(start, end + 1):
            try:
                text = load_page(pdf_page)
            except FileNotFoundError:
                missing_pages.append(pdf_page)
                continue

            record = {
                "subject": "mathematics",
                "language": "English",
                "chapter": chapter_no,
                "chapter_title": title,
                "pdf_page": pdf_page,
                "printed_page": pdf_page - 12,
                "source_file": f"data/extracted/raw/mathematics/Math/page-{pdf_page:04d}.txt",
                "text": text,
            }
            source_records.append(record)
            chapter_counts[chapter_no] += 1

            tags = classify_page(text)
            if tags:
                candidate_records.append({
                    **record,
                    "candidate_tags": tags,
                    "review_status": "needs_human_review",
                    "instruction": (
                        "Inspect the original page image/PDF. Extract only "
                        "questions and answers actually present in the source. "
                        "Do not infer a missing answer or merge unrelated items."
                    ),
                })

    with source_path.open("w", encoding="utf-8", newline="\n") as f:
        for item in source_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with candidates_path.open("w", encoding="utf-8", newline="\n") as f:
        for item in candidate_records:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    report = {
        "status": "source_extraction_complete_review_required",
        "chapter_count": len(CHAPTERS),
        "expected_pdf_pages": sum(end - start + 1 for _, _, start, end in CHAPTERS),
        "extracted_pages": len(source_records),
        "candidate_pages": len(candidate_records),
        "missing_pdf_pages": missing_pages,
        "pages_by_chapter": dict(sorted(chapter_counts.items())),
        "source_pages_file": str(source_path.relative_to(ROOT)),
        "candidate_pages_file": str(candidates_path.relative_to(ROOT)),
        "training_ready": False,
        "important": (
            "This is source extraction, not a completed Q&A fine-tuning dataset. "
            "Candidate markers are heuristic and must be checked against the "
            "original PDF. No questions or answers were generated."
        ),
    }
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\n=== EXTRACTION SUMMARY ===")
    print(f"Expected chapter pages: {report['expected_pdf_pages']}")
    print(f"Extracted pages:        {report['extracted_pages']}")
    print(f"Candidate pages:        {report['candidate_pages']}")
    print(f"Missing pages:          {len(missing_pages)}")
    print(f"\nSource pages: {source_path}")
    print(f"Candidate pages: {candidates_path}")
    print(f"Report: {report_path}")
    print("\nNo synthetic questions or answers were created.")
    return 0 if not missing_pages else 2

if __name__ == "__main__":
    raise SystemExit(main())
