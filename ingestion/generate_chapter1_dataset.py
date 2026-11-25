
from __future__ import annotations

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

# --------------------------------------------------
# Configuration
# --------------------------------------------------

PROJECT_DIR = Path(r"C:\Projects\class8-ai-teacher")

SOURCE_DIR = (
    PROJECT_DIR
    / "data"
    / "extracted"
    / "raw"
    / "mathematics"
    / "Math"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "data"
    / "training"
    / "generated"
    / "mathematics"
    / "chapter_01"
)

FIRST_PAGE = 13
LAST_PAGE = 45
CHAPTER_TITLE = "Rational Numbers"

SYSTEM_PROMPT = (
    "You are a Class 8 Telangana State Board Mathematics teacher. "
    "Teach Mathematics strictly in simple English. "
    "Explain concepts step by step and never invent textbook facts."
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def read_page(path: Path) -> str:
    """Read a textbook page without modifying the original."""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def normalize_text(text: str) -> str:
    """Normalize whitespace while preserving mathematical content."""
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_jsonl_atomic(path: Path, records: list[dict]) -> None:
    """Write JSONL through a temporary file, then replace atomically."""
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":")
                )
                + "\n"
            )

    temp_path.replace(path)


def validate_jsonl(path: Path) -> dict:
    """Validate JSONL syntax and basic conversation structure."""
    result = {
        "path": str(path),
        "exists": path.is_file(),
        "record_count": 0,
        "valid_json": True,
        "errors": [],
    }

    if not path.is_file():
        result["errors"].append("File does not exist.")
        return result

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                result["errors"].append(
                    f"Blank line at {line_number}"
                )
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                result["valid_json"] = False
                result["errors"].append(
                    f"Line {line_number}: {error}"
                )
                continue

            result["record_count"] += 1

            if "messages" not in record:
                result["errors"].append(
                    f"Line {line_number}: missing messages"
                )
                continue

            messages = record["messages"]

            if not isinstance(messages, list):
                result["errors"].append(
                    f"Line {line_number}: messages must be a list"
                )
                continue

            roles = [message.get("role") for message in messages]

            if roles != ["system", "user", "assistant"]:
                result["errors"].append(
                    f"Line {line_number}: unexpected message roles"
                )
                continue

            if not messages[1].get("content", "").strip():
                result["errors"].append(
                    f"Line {line_number}: empty user content"
                )

            if not messages[2].get("content", "").strip():
                result["errors"].append(
                    f"Line {line_number}: empty assistant content"
                )

    return result


# --------------------------------------------------
# Step 1: Check source directory
# --------------------------------------------------

if not SOURCE_DIR.is_dir():
    raise FileNotFoundError(
        f"Textbook source directory not found: {SOURCE_DIR}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Step 2: Read all Chapter 1 pages
# --------------------------------------------------

source_records = []
missing_pages = []

for page_number in range(FIRST_PAGE, LAST_PAGE + 1):
    filename = f"page-{page_number:04d}.txt"
    source_path = SOURCE_DIR / filename

    if not source_path.is_file():
        missing_pages.append(filename)
        continue

    raw_text = read_page(source_path)
    clean_text = normalize_text(raw_text)

    source_records.append({
        "subject": "Mathematics",
        "chapter": 1,
        "chapter_title": CHAPTER_TITLE,
        "pdf_page": page_number,
        "source_file": str(source_path.relative_to(PROJECT_DIR)),
        "text": clean_text,
        "text_sha256": content_hash(clean_text),
        "character_count": len(clean_text),
        "word_count": len(clean_text.split()),
    })

if missing_pages:
    raise FileNotFoundError(
        "Missing textbook pages: " + ", ".join(missing_pages)
    )

if len(source_records) != LAST_PAGE - FIRST_PAGE + 1:
    raise RuntimeError("Unexpected source page count.")


# --------------------------------------------------
# Step 3: Create source-grounded review records
# --------------------------------------------------
# These are NOT fine-tuning examples.
# No questions or answers are invented.
# Each page is preserved for human/agent question generation.

review_records = []

for source in source_records:
    if not source["text"]:
        continue

    review_records.append({
        "source_id": (
            f"math-ch01-pdf-{source['pdf_page']:04d}"
        ),
        "subject": source["subject"],
        "chapter": source["chapter"],
        "chapter_title": source["chapter_title"],
        "pdf_page": source["pdf_page"],
        "source_file": source["source_file"],
        "source_text": source["text"],
        "status": "needs_question_answer_generation",
    })


# --------------------------------------------------
# Step 4: Write source review dataset
# --------------------------------------------------

source_output = OUTPUT_DIR / "source_pages.jsonl"

write_jsonl_atomic(source_output, review_records)


# --------------------------------------------------
# Step 5: Create empty fine-tuning files safely
# --------------------------------------------------
# These files remain empty until grounded question-answer
# examples have been generated and checked.

train_output = OUTPUT_DIR / "train.jsonl"
validation_output = OUTPUT_DIR / "validation.jsonl"

write_jsonl_atomic(train_output, [])
write_jsonl_atomic(validation_output, [])


# --------------------------------------------------
# Step 6: Validate source and output files
# --------------------------------------------------

source_validation = validate_jsonl(source_output)
train_validation = validate_jsonl(train_output)
validation_validation = validate_jsonl(validation_output)

duplicate_hashes = [
    digest
    for digest, count in Counter(
        record["text_sha256"] for record in source_records
    ).items()
    if count > 1
]


# --------------------------------------------------
# Step 7: Generate report
# --------------------------------------------------

report = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "subject": "Mathematics",
    "chapter": 1,
    "chapter_title": CHAPTER_TITLE,
    "pdf_pages_expected": LAST_PAGE - FIRST_PAGE + 1,
    "pdf_pages_read": len(source_records),
    "source_pages_with_text": sum(
        bool(record["text"]) for record in source_records
    ),
    "review_records": len(review_records),
    "missing_pages": missing_pages,
    "duplicate_page_text_hashes": duplicate_hashes,
    "source_validation": source_validation,
    "train_validation": train_validation,
    "validation_validation": validation_validation,
    "fine_tuning_ready": False,
    "note": (
        "Source extraction completed. Fine-tuning examples "
        "must be generated from textbook content, answered, "
        "and checked before training."
    ),
}

report_output = OUTPUT_DIR / "dataset_report.json"

report_temp = report_output.with_suffix(".json.tmp")
report_temp.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)
report_temp.replace(report_output)


# --------------------------------------------------
# Step 8: Print results
# --------------------------------------------------

print("\n=== CHAPTER 1 SOURCE EXTRACTION ===")
print(f"Source pages read: {len(source_records)}")
print(f"Pages with text: {report['source_pages_with_text']}")
print(f"Review records: {len(review_records)}")

print("\n=== OUTPUT FILES ===")
print(f"Source review: {source_output}")
print(f"Training: {train_output}")
print(f"Validation: {validation_output}")
print(f"Report: {report_output}")

print("\n=== VALIDATION ===")
print(f"Source JSONL valid: {source_validation['valid_json']}")
print(f"Source records: {source_validation['record_count']}")
print(f"Training records: {train_validation['record_count']}")
print(f"Validation records: {validation_validation['record_count']}")

print("\nFine-tuning ready: NO")
print("Source extraction completed successfully.")
