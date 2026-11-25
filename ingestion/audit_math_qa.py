
import json
import re
from pathlib import Path
from collections import Counter

PROJECT = Path(r"C:\Projects\class8-ai-teacher")

INPUT = (
    PROJECT
    / "data/training/generated/mathematics/chapter_01/qa_drafts.jsonl"
)

REPORT = (
    PROJECT
    / "data/training/generated/mathematics/chapter_01/qa_audit_report.json"
)

MOJIBAKE_MARKERS = [
    "Ã",
    "Â",
    "â€",
    "âˆ",
    "ï»¿",
    "\ufffd",
]

def inspect_record(record, line_number):
    messages = record.get("messages", [])

    user = next(
        (m.get("content", "") for m in messages if m.get("role") == "user"),
        ""
    )

    assistant = next(
        (m.get("content", "") for m in messages if m.get("role") == "assistant"),
        ""
    )

    metadata = record.get("metadata", {})
    problems = []

    combined = user + "\n" + assistant

    for marker in MOJIBAKE_MARKERS:
        if marker in combined:
            problems.append(f"Possible encoding corruption: {marker}")

    if not user.strip():
        problems.append("Empty user question")

    if not assistant.strip():
        problems.append("Empty assistant answer")

    if len(assistant.strip()) < 20:
        problems.append("Answer suspiciously short")

    if re.search(r"\b(if considering extended definition|however)\b", assistant, re.I):
        problems.append("Potentially contradictory or speculative explanation")

    if re.search(r"not a whole number", assistant, re.I) and re.search(
        r"-\s*2\s+is\s+a\s+whole number", assistant, re.I
    ):
        problems.append("Contradictory whole-number claim")

    if "temperature" in user.lower() and re.search(
        r"\b10\s*[-−]\s*17\s*=\s*-?7\b", assistant
    ):
        problems.append("Temperature calculation needs textbook-context review")

    if "pen" in user.lower() and "22" in user:
        if not re.search(r"4\.40|4.4|₹\s*4", assistant):
            problems.append("Pen price answer may be incomplete")

    return {
        "line": line_number,
        "pdf_page": metadata.get("pdf_page"),
        "question": user,
        "answer": assistant,
        "source_evidence": metadata.get("source_evidence", ""),
        "problems": problems,
        "status": "needs_review" if problems else "not_flagged"
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    records = []

    with INPUT.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue

            records.append(
                inspect_record(json.loads(line), line_number)
            )

    flagged = [
        record for record in records
        if record["problems"]
    ]

    report = {
        "total_records": len(records),
        "flagged_records": len(flagged),
        "not_flagged_records": len(records) - len(flagged),
        "problem_counts": dict(
            Counter(
                problem
                for record in records
                for problem in record["problems"]
            )
        ),
        "records": records,
        "warning": (
            "Automated checks do not establish mathematical correctness. "
            "Every record requires subject-matter review before training."
        )
    }

    REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("========== QA AUDIT ==========")
    print(f"Records inspected: {len(records)}")
    print(f"Flagged records: {len(flagged)}")
    print(f"Not flagged: {len(records) - len(flagged)}")

    for record in flagged:
        print(
            f"\nLine {record['line']} | PDF page {record['pdf_page']}"
        )

        for problem in record["problems"]:
            print(f"  - {problem}")

    print(f"\nFull report: {REPORT}")


if __name__ == "__main__":
    main()
