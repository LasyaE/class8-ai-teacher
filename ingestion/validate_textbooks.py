
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "extracted" / "raw"
OCR_DIR = ROOT / "data" / "extracted" / "ocr"
OUT_DIR = ROOT / "data" / "validated"
REPORT_DIR = OUT_DIR / "reports"

OCR_LANGUAGES = {
    "mathematics": "eng",
    "physical-science": "eng",
    "biological-science": "eng",
    "social-studies": "eng",
    "english": "eng",
    "telugu": "tel",
    "hindi": "hin",
}

LEGACY_SUBJECTS = {"hindi", "telugu"}
MIN_TEXT_CHARS = 80
MIN_OCR_CHARS = 30
MIN_SCRIPT_RATIO = 0.20


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    ).strip()


def resolve_text_path(value: str, metadata_path: Path) -> Path:
    if not value:
        return Path("__missing_text_file__")

    path = Path(value)

    if path.is_absolute():
        return path

    candidates = [
        ROOT / path,
        metadata_path.parent / path,
        metadata_path.parent / path.name,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


def script_counts(text: str) -> dict:
    letters = [c for c in text if c.isalpha()]
    total = len(letters)

    if total == 0:
        return {
            "latin_ratio": 0.0,
            "telugu_ratio": 0.0,
            "devanagari_ratio": 0.0,
        }

    latin = sum(
        "A" <= c <= "Z" or "a" <= c <= "z"
        for c in letters
    )
    telugu = sum(
        "\u0c00" <= c <= "\u0c7f"
        for c in letters
    )
    devanagari = sum(
        "\u0900" <= c <= "\u097f"
        for c in letters
    )

    return {
        "latin_ratio": round(latin / total, 3),
        "telugu_ratio": round(telugu / total, 3),
        "devanagari_ratio": round(devanagari / total, 3),
    }


def expected_script(subject: str) -> str:
    if subject == "telugu":
        return "telugu"
    if subject == "hindi":
        return "devanagari"
    return "latin"


def load_metadata(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, list):
        pages = data
    elif isinstance(data, dict):
        pages = data.get("pages", [])
    else:
        raise ValueError(f"Invalid metadata structure: {path}")

    if not isinstance(pages, list):
        raise ValueError(f"Missing page list: {path}")

    return pages


def validate_page(
    subject: str,
    metadata: dict,
    metadata_path: Path,
) -> dict:

    page_number = int(
        metadata.get(
            "pdf_page_number_one_based",
            metadata.get("page_number", 0),
        )
    )

    original_path = resolve_text_path(
        metadata.get("text_file", ""),
        metadata_path,
    )
    original_text = read_text(original_path)

    language = OCR_LANGUAGES.get(subject, "eng")
    ocr_path = (
        OCR_DIR
        / subject
        / f"page-{page_number:04d}-{language}.txt"
    )
    ocr_text = read_text(ocr_path)

    original_scripts = script_counts(original_text)
    ocr_scripts = script_counts(ocr_text)

    expected = expected_script(subject)

    original_ratio = original_scripts[f"{expected}_ratio"]
    ocr_ratio = ocr_scripts[f"{expected}_ratio"]

    issues = []

    # Hindi and Telugu must use verified Unicode OCR.
    if subject in LEGACY_SUBJECTS:
        if len(ocr_text) >= MIN_OCR_CHARS and ocr_ratio >= MIN_SCRIPT_RATIO:
            selected_text = ocr_text
            selected_source = "unicode_ocr"
        else:
            selected_text = ""
            selected_source = "none"
            issues.append("valid_unicode_ocr_missing_or_weak")

    # Other subjects prefer digital extraction.
    else:
        if len(original_text) >= MIN_TEXT_CHARS:
            selected_text = original_text
            selected_source = "digital_extraction"
        elif len(ocr_text) >= MIN_OCR_CHARS:
            selected_text = ocr_text
            selected_source = "ocr_fallback"
        elif original_text:
            selected_text = original_text
            selected_source = "digital_extraction_short"
        else:
            selected_text = ""
            selected_source = "none"

    selected_scripts = script_counts(selected_text)
    selected_ratio = selected_scripts[f"{expected}_ratio"]

    if not original_text:
        issues.append("original_text_missing")
    elif len(original_text) < MIN_TEXT_CHARS:
        issues.append("original_text_short")

    if subject not in LEGACY_SUBJECTS:
        if selected_text and selected_ratio < MIN_SCRIPT_RATIO:
            issues.append("expected_script_ratio_low")

    if selected_text and "\ufffd" in selected_text:
        issues.append("replacement_character_detected")

    if not selected_text:
        issues.append("selected_text_empty")

    image_count = int(
        metadata.get("embedded_image_count", 0) or 0
    )
    image_coverage = float(
        metadata.get("image_coverage_estimate", 0) or 0
    )
    image_dominant = (
        metadata.get("page_type_hint") == "image_dominant"
    )

    if image_count > 0 or image_coverage >= 0.20 or image_dominant:
        issues.append("visual_content_present")

    blocking_issues = {
        "valid_unicode_ocr_missing_or_weak",
        "expected_script_ratio_low",
        "replacement_character_detected",
        "selected_text_empty",
    }

    status = (
        "needs_review"
        if any(issue in blocking_issues for issue in issues)
        else "machine_pass"
    )

    return {
        "subject": subject,
        "page_number": page_number,
        "source_pdf": metadata.get("source_pdf", ""),
        "original_text_file": str(original_path),
        "ocr_text_file": (
            str(ocr_path) if ocr_path.exists() else ""
        ),
        "original_characters": len(original_text),
        "original_words": len(original_text.split()),
        "ocr_characters": len(ocr_text),
        "ocr_words": len(ocr_text.split()),
        "original_expected_script_ratio": original_ratio,
        "ocr_expected_script_ratio": ocr_ratio,
        "selected_source": selected_source,
        "selected_characters": len(selected_text),
        "selected_words": len(selected_text.split()),
        "expected_script": expected,
        "expected_script_ratio": selected_ratio,
        **selected_scripts,
        "image_count": image_count,
        "image_coverage_estimate": image_coverage,
        "visual_reference": metadata.get("visual_reference", ""),
        "embedded_images": metadata.get("embedded_images", []),
        "status": status,
        "issues": issues,
        "original_text": original_text,
        "ocr_text": ocr_text,
        "selected_text": selected_text,
    }


def write_csv(path: Path, pages: list[dict], fields: list[str]):
    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for page in pages:
            row = {
                key: page.get(key, "")
                for key in fields
            }
            row["issues"] = "; ".join(page["issues"])
            writer.writerow(row)


def main():
    if not RAW_DIR.exists():
        raise SystemExit(f"Raw folder not found: {RAW_DIR}")

    metadata_files = sorted(
        RAW_DIR.rglob("metadata.json")
    )

    if not metadata_files:
        raise SystemExit("No metadata.json files found.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    all_pages = []
    subject_summaries = []

    for metadata_path in metadata_files:
        subject = metadata_path.relative_to(RAW_DIR).parts[0]
        metadata_pages = load_metadata(metadata_path)

        pages = [
            validate_page(subject, page, metadata_path)
            for page in metadata_pages
        ]

        pages.sort(key=lambda p: p["page_number"])

        subject_dir = OUT_DIR / subject
        subject_dir.mkdir(parents=True, exist_ok=True)

        # Write the selected Unicode text for each page.
        for page in pages:
            output_file = (
                subject_dir
                / f"page-{page['page_number']:04d}.txt"
            )
            output_file.write_text(
                page["selected_text"],
                encoding="utf-8",
            )

        statuses = Counter(p["status"] for p in pages)

        subject_summaries.append({
            "subject": subject,
            "pages": len(pages),
            "machine_pass": statuses["machine_pass"],
            "needs_review": statuses["needs_review"],
            "unicode_ocr_pages": sum(
                p["selected_source"] == "unicode_ocr"
                for p in pages
            ),
            "selected_words": sum(
                p["selected_words"] for p in pages
            ),
        })

        all_pages.extend(pages)

        print(
            f"{subject}: {len(pages)} pages | "
            f"{statuses['machine_pass']} machine-pass | "
            f"{statuses['needs_review']} need review"
        )

    all_pages.sort(
        key=lambda p: (p["subject"], p["page_number"])
    )

    # Detailed JSONL preserves both original and OCR versions.
    jsonl_path = REPORT_DIR / "validated_pages.jsonl"

    with jsonl_path.open("w", encoding="utf-8") as file:
        for page in all_pages:
            file.write(
                json.dumps(page, ensure_ascii=False) + "\n"
            )

    fields = [
        "subject",
        "page_number",
        "original_characters",
        "original_words",
        "ocr_characters",
        "ocr_words",
        "original_expected_script_ratio",
        "ocr_expected_script_ratio",
        "selected_source",
        "selected_characters",
        "selected_words",
        "expected_script",
        "expected_script_ratio",
        "status",
        "issues",
        "visual_reference",
    ]

    csv_path = REPORT_DIR / "page_quality_report.csv"
    unresolved_path = REPORT_DIR / "unresolved_pages.csv"

    write_csv(csv_path, all_pages, fields)

    unresolved = [
        p for p in all_pages
        if p["status"] == "needs_review"
    ]
    write_csv(unresolved_path, unresolved, fields)

    totals = Counter(p["status"] for p in all_pages)

    summary = {
        "total_pages": len(all_pages),
        "total_subjects": len(subject_summaries),
        "machine_pass": totals["machine_pass"],
        "needs_review": totals["needs_review"],
        "hindi_telugu_unicode_pages": sum(
            p["selected_source"] == "unicode_ocr"
            for p in all_pages
        ),
        "subjects": subject_summaries,
        "reports": {
            "jsonl": str(jsonl_path.relative_to(ROOT)),
            "quality_csv": str(csv_path.relative_to(ROOT)),
            "unresolved_csv": str(unresolved_path.relative_to(ROOT)),
        },
        "limitations": [
            "Machine-pass does not mean human approval.",
            "OCR can contain recognition mistakes.",
            "Visual diagrams, maps and tables need separate checks.",
            "Factual correctness has not been manually verified.",
        ],
    }

    summary_path = REPORT_DIR / "validation_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nFINAL TEXT VALIDATION COMPLETE")
    print(f"Total pages: {len(all_pages)}")
    print(f"Machine-pass: {totals['machine_pass']}")
    print(f"Needs review: {totals['needs_review']}")
    print(
        "Hindi/Telugu Unicode OCR pages:",
        summary["hindi_telugu_unicode_pages"],
    )
    print(f"Reports: {REPORT_DIR}")


if __name__ == "__main__":
    main()
