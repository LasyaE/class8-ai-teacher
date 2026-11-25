
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import hashlib

from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(r"C:\Projects\class8-ai-teacher")

INPUT_FILE = (
    PROJECT_DIR
    / "data/training/generated/mathematics/chapter_01/source_pages.jsonl"
)

OUTPUT_DIR = (
    PROJECT_DIR
    / "data/training/generated/mathematics/chapter_01"
)

OUTPUT_FILE = OUTPUT_DIR / "qa_drafts.jsonl"
ERROR_LOG = OUTPUT_DIR / "qa_generation_errors.jsonl"
REPORT_FILE = OUTPUT_DIR / "qa_generation_report.json"

MODEL = "qwen3:8b"

MAX_EXAMPLES_PER_PAGE = 3
MAX_RETRIES = 3
REQUEST_TIMEOUT = 240

SYSTEM_PROMPT = """
You are an expert Class 8 Telangana State Board Mathematics teacher.

Teach Mathematics strictly in simple English.

Rules:
- Use only information supported by the supplied textbook page.
- Never invent textbook facts, exercises, or definitions.
- Explain mathematical reasoning step by step.
- Use age-appropriate English.
- If insufficient information exists, return an empty examples array.
- Every answer must include an exact supporting source quotation.
"""


# ============================================================
# OLLAMA ENDPOINT DISCOVERY
# ============================================================

SKIP_DIRS = {
    ".git", ".venv", ".venv-ai", "venv",
    "node_modules", "__pycache__", ".idea"
}

URL_PATTERN = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1)"
    r"(?::\d+)?(?:/[^\s\"'<>]*)?",
    re.IGNORECASE,
)


def discover_ollama_endpoint():
    env_host = os.environ.get("OLLAMA_HOST", "").strip()

    if env_host:
        if not env_host.startswith(("http://", "https://")):
            env_host = "http://" + env_host

        return env_host.rstrip("/")

    matches = set()

    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            path = Path(root) / filename

            if path.suffix.lower() not in {
                ".py", ".json", ".yaml", ".yml",
                ".toml", ".ini", ".cfg", ".env", ".txt"
            }:
                continue

            try:
                if path.stat().st_size > 2_000_000:
                    continue

                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            except OSError:
                continue

            for match in URL_PATTERN.finditer(content):
                context = content[
                    max(0, match.start() - 150):
                    min(len(content), match.end() + 150)
                ].lower()

                if "ollama" in context:
                    url = match.group(0).rstrip(".,);]")

                    parsed = re.match(
                        r"(https?://[^/]+)",
                        url,
                        re.IGNORECASE
                    )

                    if parsed:
                        matches.add(parsed.group(1).rstrip("/"))

    if len(matches) == 1:
        return next(iter(matches))

    raise RuntimeError(
        "Could not identify one unambiguous Ollama endpoint. "
        "Set OLLAMA_HOST=http://localhost:11434 in PowerShell."
    )


# ============================================================
# JSONL HELPERS
# ============================================================

def read_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {error}"
                ) from error

    return records


def append_jsonl(path, record):
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )
        file.flush()
        os.fsync(file.fileno())


def log_error(page, error):
    append_jsonl(ERROR_LOG, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pdf_page": page.get("pdf_page"),
        "source_id": page.get("source_id"),
        "error": str(error),
    })


# ============================================================
# TEXT AND JSON HELPERS
# ============================================================

def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def extract_json_response(content):
    content = content.strip()

    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE
    )

    content = re.sub(r"\s*```$", "", content)

    start = content.find("{")
    end = content.rfind("}")

    if start < 0 or end <= start:
        raise ValueError("Model did not return a JSON object.")

    return json.loads(content[start:end + 1])


# ============================================================
# OLLAMA GENERATION
# ============================================================

def call_ollama(endpoint, source_text):
    url = endpoint.rstrip("/") + "/api/chat"

    prompt = f"""
Generate up to {MAX_EXAMPLES_PER_PAGE} useful Class 8
Mathematics teacher-student examples from this textbook page.

Return ONLY valid JSON:

{{
  "examples": [
    {{
      "question": "Student question",
      "answer": "Step-by-step teacher explanation",
      "evidence": "Exact quotation copied from the page"
    }}
  ]
}}

Rules:
- Questions must be answerable from this page.
- Answers must be mathematically correct.
- Explain calculations step by step.
- Do not invent facts or exercises.
- Evidence must be copied exactly from the source.
- Do not create empty answers.
- Return an empty examples array if content is insufficient.

SOURCE TEXT:
{source_text}
"""

    payload = {
        "model": MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "options": {
            "temperature": 0.1
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT
    ) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "message" not in result:
        raise ValueError("Missing message in Ollama response.")

    return extract_json_response(
        result["message"].get("content", "")
    )


# ============================================================
# EXAMPLE VALIDATION
# ============================================================

def validate_example(example, source_text):
    if not isinstance(example, dict):
        return False, "Invalid example structure."

    question = example.get("question", "")
    answer = example.get("answer", "")
    evidence = example.get("evidence", "")

    if not all(
        isinstance(value, str) and value.strip()
        for value in (question, answer, evidence)
    ):
        return False, "Empty question, answer, or evidence."

    if len(question.strip()) < 8:
        return False, "Question too short."

    if len(answer.strip()) < 20:
        return False, "Answer too short."

    if len(evidence.strip()) < 12:
        return False, "Evidence too short."

    if normalize_text(evidence) not in normalize_text(source_text):
        return False, "Evidence not found in source page."

    return True, "Passed structural and evidence checks."


# ============================================================
# TRAINING RECORD FORMAT
# ============================================================

def make_record(page, example):
    return {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.strip()
            },
            {
                "role": "user",
                "content": example["question"].strip()
            },
            {
                "role": "assistant",
                "content": example["answer"].strip()
            }
        ],
        "metadata": {
            "subject": page.get("subject", "Mathematics"),
            "chapter": page.get("chapter", 1),
            "chapter_title": page.get(
                "chapter_title", "Rational Numbers"
            ),
            "pdf_page": page["pdf_page"],
            "source_file": page["source_file"],
            "source_id": page["source_id"],
            "source_evidence": example["evidence"].strip(),
            "generation_model": MODEL,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "status": "draft_needs_human_review"
        }
    }


# ============================================================
# MAIN
# ============================================================

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"Source file missing: {INPUT_FILE}"
        )

    endpoint = discover_ollama_endpoint()

    print(f"Ollama endpoint: {endpoint}")
    print(f"Model: {MODEL}")

    pages = read_jsonl(INPUT_FILE)

    if len(pages) != 33:
        raise RuntimeError(
            f"Expected 33 pages, found {len(pages)}."
        )

    # IMPORTANT: Verify the actual source field.
    first_page = pages[0]

    if "source_text" not in first_page:
        raise RuntimeError(
            "Expected 'source_text' field is missing. "
            f"Available fields: {list(first_page.keys())}"
        )

    print(
        "Source field verified: source_text "
        f"({len(first_page['source_text'])} characters on first page)"
    )

    # Check Ollama connectivity and model.
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/api/tags"
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        models = json.loads(response.read().decode("utf-8"))

    installed_models = {
        item.get("name")
        for item in models.get("models", [])
    }

    if MODEL not in installed_models:
        raise RuntimeError(
            f"{MODEL} not installed. Available: {installed_models}"
        )

    # Preserve previous drafts rather than deleting them.
    if OUTPUT_FILE.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = OUTPUT_DIR / f"qa_drafts_backup_{timestamp}.jsonl"
        OUTPUT_FILE.replace(backup)
        print(f"Previous drafts backed up to: {backup}")

    if ERROR_LOG.exists():
        ERROR_LOG.unlink()

    processed = 0
    failed = 0
    skipped = 0
    generated = 0
    seen_questions = set()

    print(f"\nStarting generation for {len(pages)} pages...\n")

    for index, page in enumerate(pages, 1):
        page_number = page.get("pdf_page")

        # CORRECT FIELD: source_text
        source_text = page.get("source_text", "")

        print(
            f"[{index}/33] Processing PDF page {page_number}..."
        )

        if not isinstance(source_text, str) or not source_text.strip():
            skipped += 1
            processed += 1
            print("  Skipped: source text is empty.")
            continue

        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = call_ollama(endpoint, source_text)

                examples = result.get("examples")

                if not isinstance(examples, list):
                    raise ValueError(
                        "Response does not contain an examples list."
                    )

                page_count = 0

                for example in examples[:MAX_EXAMPLES_PER_PAGE]:
                    valid, reason = validate_example(
                        example,
                        source_text
                    )

                    if not valid:
                        print(f"  Rejected: {reason}")
                        continue

                    question_key = normalize_text(
                        example["question"]
                    )

                    if question_key in seen_questions:
                        print("  Rejected duplicate question.")
                        continue

                    seen_questions.add(question_key)

                    record = make_record(page, example)
                    append_jsonl(OUTPUT_FILE, record)

                    generated += 1
                    page_count += 1

                print(f"  Accepted: {page_count} examples.")
                success = True
                break

            except Exception as error:
                print(
                    f"  Attempt {attempt}/{MAX_RETRIES}: {error}"
                )

                if attempt < MAX_RETRIES:
                    time.sleep(attempt * 2)

        if not success:
            failed += 1
            log_error(page, "All retries failed.")

        processed += 1

    # Verify records physically written.
    final_records = (
        read_jsonl(OUTPUT_FILE)
        if OUTPUT_FILE.exists()
        else []
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "ollama_endpoint": endpoint,
        "pages_total": len(pages),
        "pages_processed": processed,
        "pages_failed": failed,
        "pages_skipped": skipped,
        "examples_generated": generated,
        "records_verified_on_disk": len(final_records),
        "output_file": str(OUTPUT_FILE),
        "fine_tuning_ready": False,
        "status": "drafts_require_human_review"
    }

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\n========== GENERATION REPORT ==========")
    print(f"Pages processed: {processed}")
    print(f"Pages failed: {failed}")
    print(f"Pages skipped: {skipped}")
    print(f"Examples generated: {generated}")
    print(f"Records on disk: {len(final_records)}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Report: {REPORT_FILE}")
    print("Fine-tuning ready: NO")
    print("Generation finished.")


if __name__ == "__main__":
    main()
