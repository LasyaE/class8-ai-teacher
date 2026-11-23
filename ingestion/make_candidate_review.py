import json
from pathlib import Path

source = Path("data/training/mathematics/question_candidates.jsonl")
output = Path("data/training/mathematics/candidate_review.txt")

rows = [
    json.loads(line)
    for line in source.read_text(encoding="utf-8-sig").splitlines()
    if line.strip()
]

with output.open("w", encoding="utf-8") as f:
    for i, row in enumerate(rows, 1):
        f.write(f"\n{'=' * 70}\n")
        f.write(f"CANDIDATE {i}\n")
        f.write(f"Chapter: {row['chapter']} - {row['chapter_title']}\n")
        f.write(f"PDF page: {row['pdf_page']}\n")
        f.write(f"Text:\n{row['candidate_text']}\n")

print(f"Created review file: {output}")
print(f"Candidates included: {len(rows)}")
