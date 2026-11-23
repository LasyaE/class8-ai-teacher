
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf
import requests


# ---------------------------------------------------------
# Project paths and configuration
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_PATH = PROJECT_ROOT / "data" / "textbooks" / "Math.pdf"

CANDIDATES_PATH = (
    PROJECT_ROOT
    / "data"
    / "training"
    / "mathematics"
    / "question_candidates.jsonl"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "training"
    / "mathematics"
    / "automated_review_v2"
)

RESULTS_PATH = OUTPUT_DIR / "review_results.jsonl"
ERRORS_PATH = OUTPUT_DIR / "review_errors.jsonl"
REPORT_PATH = OUTPUT_DIR / "review_report.json"
HUMAN_REVIEW_PATH = OUTPUT_DIR / "human_review_generated.jsonl"

OLLAMA_URL = "http://localhost:11434"

DEFAULT_MODEL = "qwen3:8b"

VALID_DECISIONS = {
    "KEEP",
    "MERGE",
    "REJECT",
    "CHECK",
}

MAX_ATTEMPTS = 4
REQUEST_TIMEOUT = 600
RETRY_DELAYS = (5, 15, 30)


# ---------------------------------------------------------
# JSONL utilities
# ---------------------------------------------------------

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records = []

    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}, line {line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object at line {line_number}"
                )

            records.append(record)

    return records


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(
            json.dumps(item, ensure_ascii=False) + "\n"
        )
        file.flush()
        os.fsync(file.fileno())


def atomic_write_json(
    path: Path,
    data: dict[str, Any],
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, path)


def atomic_write_jsonl(
    path: Path,
    items: list[dict[str, Any]],
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")

    with temporary.open("w", encoding="utf-8") as file:
        for item in items:
            file.write(
                json.dumps(item, ensure_ascii=False) + "\n"
            )

        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary, path)


# ---------------------------------------------------------
# Candidate loading
# ---------------------------------------------------------

def load_candidates() -> list[dict[str, Any]]:
    candidates = read_jsonl(CANDIDATES_PATH)

    validated = []

    for index, candidate in enumerate(candidates, start=1):
        candidate_text = candidate.get("candidate_text")

        if (
            not isinstance(candidate_text, str)
            or not candidate_text.strip()
        ):
            raise ValueError(
                f"Candidate {index} has no usable candidate_text."
            )

        page_number = (
            candidate.get("pdf_page")
            or candidate.get("page")
            or candidate.get("page_number")
        )

        try:
            page_number = int(page_number)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Candidate {index} has invalid PDF page."
            ) from exc

        if page_number < 1:
            raise ValueError(
                f"Candidate {index} has invalid PDF page: {page_number}"
            )

        candidate_id = (
            candidate.get("id")
            or candidate.get("candidate_id")
            or candidate.get("candidate_number")
            or str(index)
        )

        candidate = dict(candidate)
        candidate["_candidate_id"] = str(candidate_id)
        candidate["_pdf_page"] = page_number

        validated.append(candidate)

    ids = [item["_candidate_id"] for item in validated]

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate candidate IDs detected. "
            "Resolve them before reviewing."
        )

    return validated


# ---------------------------------------------------------
# Ollama connection
# ---------------------------------------------------------

def validate_model(model: str) -> None:
    try:
        response = requests.get(
            f"{OLLAMA_URL}/api/tags",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            "Cannot connect to Ollama at localhost:11434. "
            "Make sure Ollama is running."
        ) from exc

    installed_models = [
        item.get("name", "")
        for item in data.get("models", [])
    ]

    if model not in installed_models:
        raise RuntimeError(
            f"Model {model!r} is not installed. "
            f"Available models: {installed_models}"
        )


# ---------------------------------------------------------
# Classification prompt
# ---------------------------------------------------------

def build_prompt(
    candidate: dict[str, Any],
    full_page_text: str,
) -> str:

    return f"""
You are reviewing extracted content from the original
Telangana State Board Class 8 Mathematics textbook.

Your task is ONLY to classify the candidate.

Do not invent missing mathematical expressions.
Do not solve questions.
Do not rewrite textbook content.
Do not assume that a fragment is complete.

Use the full original PDF page text as context.

Choose exactly one decision:

KEEP:
The candidate is a coherent, useful, self-contained
question, worked example, activity, or concept.

MERGE:
The candidate is a fragment that should be combined
with another candidate from the same exercise,
example, or activity.

REJECT:
The candidate is clearly irrelevant, duplicate,
footer-only, or unusable textbook noise.

CHECK:
The candidate contains uncertain, incomplete,
corrupted, ambiguous, or diagram/table-dependent
content that requires further inspection.

Important rules:

1. Mathematical notation must be preserved accurately.
2. Do not assume missing fractions or operators.
3. If a diagram is required, set diagram_needed to true.
4. If a table is required, set table_needed to true.
5. If the content cannot be confidently understood,
   choose CHECK.
6. KEEP does not mean approved for model training.
7. Be conservative.

Return only valid JSON matching this structure:

{{
  "decision": "KEEP",
  "reason": "Short explanation",
  "diagram_needed": false,
  "table_needed": false,
  "requires_human_verification": true
}}

ORIGINAL PDF PAGE TEXT:

{full_page_text}

CANDIDATE:

{candidate["candidate_text"]}
""".strip()


# ---------------------------------------------------------
# Ollama classification
# ---------------------------------------------------------

def classify_candidate(
    candidate: dict[str, Any],
    full_page_text: str,
    model: str,
) -> dict[str, Any]:

    prompt = build_prompt(candidate, full_page_text)

    payload = {
        "model": model,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": [
                        "KEEP",
                        "MERGE",
                        "REJECT",
                        "CHECK",
                    ],
                },
                "reason": {
                    "type": "string",
                },
                "diagram_needed": {
                    "type": "boolean",
                },
                "table_needed": {
                    "type": "boolean",
                },
                "requires_human_verification": {
                    "type": "boolean",
                },
            },
            "required": [
                "decision",
                "reason",
                "diagram_needed",
                "table_needed",
                "requires_human_verification",
            ],
        },
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "options": {
            "temperature": 0,
        },
    }

    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()

            response_data = response.json()
            message = response_data.get("message", {})
            content = message.get("content")

            if not isinstance(content, str):
                raise ValueError(
                    "Ollama returned no text content."
                )

            classification = json.loads(content)

            if not isinstance(classification, dict):
                raise ValueError(
                    "Model response is not a JSON object."
                )

            decision = classification.get("decision")

            if decision not in VALID_DECISIONS:
                raise ValueError(
                    f"Invalid decision: {decision!r}"
                )

            if not isinstance(
                classification.get("reason"), str
            ):
                raise ValueError(
                    "Missing or invalid reason."
                )

            if not isinstance(
                classification.get("diagram_needed"), bool
            ):
                raise ValueError(
                    "Invalid diagram_needed value."
                )

            if not isinstance(
                classification.get("table_needed"), bool
            ):
                raise ValueError(
                    "Invalid table_needed value."
                )

            if not isinstance(
                classification.get(
                    "requires_human_verification"
                ),
                bool,
            ):
                raise ValueError(
                    "Invalid requires_human_verification value."
                )

            return classification

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:

            last_error = exc

            print(
                f"  Attempt {attempt}/{MAX_ATTEMPTS} failed: {exc}",
                flush=True,
            )

            if attempt < MAX_ATTEMPTS:
                delay = RETRY_DELAYS[attempt - 1]

                print(
                    f"  Retrying in {delay} seconds...",
                    flush=True,
                )

                time.sleep(delay)

    raise RuntimeError(
        f"Ollama classification failed after "
        f"{MAX_ATTEMPTS} attempts: {last_error}"
    )


# ---------------------------------------------------------
# Existing results and resume
# ---------------------------------------------------------

def load_existing_results(
    path: Path,
) -> dict[str, dict[str, Any]]:

    if not path.exists():
        return {}

    results = {}

    for item in read_jsonl(path):
        candidate_id = item.get("candidate_id")

        if candidate_id is not None:
            results[str(candidate_id)] = item

    return results


def load_existing_errors(
    path: Path,
) -> list[dict[str, Any]]:

    if not path.exists():
        return []

    return read_jsonl(path)


# ---------------------------------------------------------
# Human review file
# ---------------------------------------------------------

def write_human_review_file(
    results: dict[str, dict[str, Any]],
) -> None:

    items = []

    for item in results.values():
        if (
            item.get("decision") == "CHECK"
            or item.get("requires_human_verification")
        ):
            items.append(item)

    atomic_write_jsonl(
        HUMAN_REVIEW_PATH,
        items,
    )


# ---------------------------------------------------------
# Report generation
# ---------------------------------------------------------

def generate_report(
    candidates: list[dict[str, Any]],
    results: dict[str, dict[str, Any]],
    errors: list[dict[str, Any]],
    model: str,
) -> None:

    counts = {
        decision: 0
        for decision in VALID_DECISIONS
    }

    for item in results.values():
        decision = item.get("decision")

        if decision in counts:
            counts[decision] += 1

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "model": model,
        "total_candidates": len(candidates),
        "completed": len(results),
        "pending": max(
            0,
            len(candidates) - len(results),
        ),
        "decision_counts": counts,
        "error_count": len(errors),
        "human_verification_count": sum(
            1
            for item in results.values()
            if (
                item.get("requires_human_verification")
                or item.get("decision") == "CHECK"
            )
        ),
        "warning": (
            "Automated classifications are preliminary. "
            "KEEP is not training approval. "
            "Human source verification is required."
        ),
    }

    atomic_write_json(
        REPORT_PATH,
        report,
    )


# ---------------------------------------------------------
# Main processing
# ---------------------------------------------------------

def process_candidates(
    model: str,
    limit: int,
    resume: bool,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = load_candidates()

    if limit > 0:
        selected = candidates[:limit]
    else:
        selected = candidates

    existing_results = load_existing_results(
        RESULTS_PATH
    )

    existing_errors = load_existing_errors(
        ERRORS_PATH
    )

    if not resume and existing_results:
        raise RuntimeError(
            "Review results already exist. "
            "Use --resume to continue safely."
        )

    validate_model(model)

    print(f"Model: {model}")
    print(f"Candidates selected: {len(selected)}")
    print(f"Already completed: {len(existing_results)}")
    print("Starting candidate review...\n")

    errors_this_run = []

    with pymupdf.open(PDF_PATH) as pdf:

        for index, candidate in enumerate(
            selected,
            start=1,
        ):

            candidate_id = candidate["_candidate_id"]
            page_number = candidate["_pdf_page"]

            if candidate_id in existing_results:
                continue

            if page_number > len(pdf):
                error = {
                    "candidate_id": candidate_id,
                    "pdf_page": page_number,
                    "error": "PDF page number exceeds document length.",
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }

                append_jsonl(
                    ERRORS_PATH,
                    error,
                )

                errors_this_run.append(error)
                continue

            print(
                f"[{index}/{len(selected)}] "
                f"Candidate {candidate_id}, "
                f"PDF page {page_number}",
                flush=True,
            )

            full_page_text = pdf[
                page_number - 1
            ].get_text("text")

            try:
                classification = classify_candidate(
                    candidate,
                    full_page_text,
                    model,
                )

                result = {
                    "candidate_id": candidate_id,
                    "candidate_number": candidate.get(
                        "candidate_number"
                    ),
                    "decision": classification["decision"],
                    "reason": classification["reason"],
                    "diagram_needed": classification[
                        "diagram_needed"
                    ],
                    "table_needed": classification[
                        "table_needed"
                    ],
                    "requires_human_verification": (
                        classification[
                            "requires_human_verification"
                        ]
                        or classification["decision"] == "CHECK"
                    ),
                    "pdf_page": page_number,
                    "candidate_text": candidate[
                        "candidate_text"
                    ],
                    "source_file": candidate.get(
                        "source_file"
                    ),
                    "source_type": candidate.get(
                        "source_type"
                    ),
                    "chapter": candidate.get("chapter"),
                    "chapter_title": candidate.get(
                        "chapter_title"
                    ),
                    "model": model,
                    "reviewed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }

                append_jsonl(
                    RESULTS_PATH,
                    result,
                )

                existing_results[candidate_id] = result

                print(
                    f"  {result['decision']} — "
                    f"human review needed"
                    if result["requires_human_verification"]
                    else f"  {result['decision']}",
                    flush=True,
                )

            except Exception as exc:

                error = {
                    "candidate_id": candidate_id,
                    "pdf_page": page_number,
                    "error": str(exc),
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }

                append_jsonl(
                    ERRORS_PATH,
                    error,
                )

                errors_this_run.append(error)

                print(
                    f"  ERROR: {exc}",
                    flush=True,
                )

            write_human_review_file(
                existing_results
            )

            generate_report(
                candidates,
                existing_results,
                errors_this_run,
                model,
            )

    generate_report(
        candidates,
        existing_results,
        errors_this_run,
        model,
    )

    counts = {
        decision: sum(
            item.get("decision") == decision
            for item in existing_results.values()
        )
        for decision in VALID_DECISIONS
    }

    print("\nReview report")
    print("-------------")
    print(f"Candidates in this run: {len(selected)}")
    print(f"Completed: {len(existing_results)}")
    print(
        f"Pending: {max(0, len(candidates) - len(existing_results))}"
    )

    for decision, count in counts.items():
        print(f"{decision}: {count}")

    print(
        f"Errors this run: {len(errors_this_run)}"
    )

    print(f"\nOutput folder: {OUTPUT_DIR}")


# ---------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Automated textbook candidate classification "
            "using local Ollama."
        )
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Installed Ollama model name.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Number of candidates to process. 0 means all.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume by skipping candidates already saved.",
    )

    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative.")

    try:
        process_candidates(
            model=args.model,
            limit=args.limit,
            resume=args.resume,
        )

    except KeyboardInterrupt:
        print(
            "\nInterrupted. Completed results were saved.",
            file=sys.stderr,
        )
        raise SystemExit(130)

    except Exception as exc:
        print(
            f"\nFATAL ERROR: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
