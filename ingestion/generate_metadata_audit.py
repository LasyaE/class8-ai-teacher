import csv
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

import pymupdf

ROOT = Path.cwd()
PDF_DIR = ROOT / "data" / "textbooks"
RAW_DIR = ROOT / "data" / "extracted" / "raw"
OCR_DIR = ROOT / "data" / "extracted" / "ocr"
REPORT_DIR = ROOT / "data" / "extracted" / "reports"

BOOKS = {
    "biological-science": ("bio.pdf", "bio"),
    "english": ("English.pdf", "English"),
    "hindi": ("hindi.pdf", "Hindi"),
    "mathematics": ("Math.pdf", "Math"),
    "physical-science": ("physics.pdf", "physics"),
    "social-studies": ("social.pdf", "social"),
    "telugu": ("telugu.pdf", "telugu"),
}

REPORT_DIR.mkdir(parents=True, exist_ok=True)

results = []

for subject, (pdf_name, folder_name) in BOOKS.items():
    folder = RAW_DIR / subject / folder_name
    metadata_path = folder / "metadata.json"
    pdf_path = PDF_DIR / pdf_name
    ocr_folder = OCR_DIR / subject

    result = {
        "subject": subject,
        "pdf": pdf_name,
        "pdf_pages": 0,
        "metadata_pages": 0,
        "metadata_records": 0,
        "text_files": 0,
        "missing_text_pages": [],
        "unexpected_text_pages": [],
        "missing_metadata_pages": [],
        "duplicate_metadata_pages": [],
        "page_index_errors": [],
        "character_count_mismatches": [],
        "word_count_mismatches": [],
        "ocr_flagged_pages": 0,
        "ocr_sidecars_found": 0,
        "ocr_sidecars_missing": [],
        "ocr_empty_files": [],
        "ocr_under_10_words": [],
        "ocr_status": {},
        "visual_references_missing": [],
        "image_dominant_pages": [],
        "metadata_subject_match": False,
        "metadata_source_pdf_match": False,
        "source_filename_case_difference": False,
        "errors": [],
    }

    if not metadata_path.is_file():
        result["errors"].append("Metadata file missing")
        results.append(result)
        continue

    if not pdf_path.is_file():
        result["errors"].append("Original PDF missing")
        results.append(result)
        continue

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding="utf-8")
        )

        with pymupdf.open(pdf_path) as pdf:
            pdf_pages = len(pdf)

        records = metadata.get("pages", [])
        result["pdf_pages"] = pdf_pages
        result["metadata_pages"] = metadata.get("pdf_page_count", 0)
        result["metadata_records"] = len(records)
        result["metadata_subject_match"] = (
            metadata.get("subject") == subject
        )

        recorded_source = metadata.get("source_pdf", "")
        result["metadata_source_pdf_match"] = (
            recorded_source == pdf_name
        )
        result["source_filename_case_difference"] = (
            recorded_source.lower() == pdf_name.lower()
            and recorded_source != pdf_name
        )

        files = list(folder.glob("page-*.txt"))
        result["text_files"] = len(files)

        file_numbers = set()
        for file in files:
            if file.stem.startswith("page-"):
                try:
                    file_numbers.add(int(file.stem[5:]))
                except ValueError:
                    pass

        expected = set(range(1, pdf_pages + 1))
        result["missing_text_pages"] = sorted(expected - file_numbers)
        result["unexpected_text_pages"] = sorted(file_numbers - expected)

        record_numbers = [
            p.get("pdf_page_number_one_based")
            for p in records if isinstance(p, dict)
        ]

        valid_numbers = [
            n for n in record_numbers
            if isinstance(n, int) and not isinstance(n, bool)
        ]

        counts = Counter(valid_numbers)

        result["missing_metadata_pages"] = sorted(
            expected - set(valid_numbers)
        )
        result["duplicate_metadata_pages"] = sorted(
            n for n, count in counts.items() if count > 1
        )

        for page in records:
            if not isinstance(page, dict):
                result["errors"].append("Invalid metadata page record")
                continue

            number = page.get("pdf_page_number_one_based")
            zero = page.get("pdf_page_index_zero_based")

            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or not isinstance(zero, int)
                or isinstance(zero, bool)
                or zero != number - 1
            ):
                result["page_index_errors"].append(number)

            text_file = page.get("text_file", "")
            text_path = ROOT / text_file if text_file else None

            if not text_path or not text_path.is_file():
                text_path = folder / f"page-{number:04d}.txt"

            if not text_path.is_file():
                continue

            text = text_path.read_text(
                encoding="utf-8", errors="replace"
            )

            if len(text) != page.get("text_characters"):
                result["character_count_mismatches"].append(number)

            if len(text.split()) != page.get("text_words"):
                result["word_count_mismatches"].append(number)

            if page.get("needs_visual_review"):
                result["ocr_flagged_pages"] += 1

                status = str(page.get("ocr_status", "missing"))
                result["ocr_status"][status] = (
                    result["ocr_status"].get(status, 0) + 1
                )

                sidecars = list(
                    ocr_folder.glob(f"page-{number:04d}-*.txt")
                )

                if not sidecars:
                    result["ocr_sidecars_missing"].append(number)

                for sidecar in sidecars:
                    result["ocr_sidecars_found"] += 1
                    ocr_text = sidecar.read_text(
                        encoding="utf-8", errors="replace"
                    ).strip()

                    words = len(ocr_text.split())

                    if not ocr_text:
                        result["ocr_empty_files"].append(
                            sidecar.name
                        )
                    elif words < 10:
                        result["ocr_under_10_words"].append(
                            sidecar.name
                        )

                reference = page.get("visual_reference")
                if not reference or not (ROOT / reference).is_file():
                    result["visual_references_missing"].append(number)

            if page.get("page_type_hint") == "image_dominant":
                result["image_dominant_pages"].append(number)

    except Exception as exc:
        result["errors"].append(str(exc))

    results.append(result)


# JSON report
audit = {
    "audit_date": datetime.now().astimezone().isoformat(),
    "project": "Class 8 Telangana State Board AI Teacher",
    "audit_type": "Read-only metadata and extraction audit",
    "subjects": results,
    "manual_visual_checks": [
        {
            "subject": "social-studies",
            "pdf_page": 274,
            "printed_page": 264,
            "finding": "World Outline Map; low OCR count is expected.",
            "status": "visually_inspected"
        },
        {
            "subject": "hindi",
            "pdf_page": 11,
            "printed_page": 1,
            "finding": "OCR question 2 has recognition errors; verified text is 'वे क्या कर रहे हैं?'",
            "status": "visually_inspected_sample"
        }
    ],
    "limitations": [
        "OCR word counts do not establish OCR accuracy.",
        "Most flagged pages have not undergone manual visual verification.",
        "Diagram, equation, map and table accuracy is not fully verified.",
        "OCR metadata status has not been changed by this audit."
    ]
}

json_path = REPORT_DIR / "metadata_audit.json"
json_path.write_text(
    json.dumps(audit, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# CSV report: one row per subject
csv_path = REPORT_DIR / "metadata_audit.csv"

with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
    fields = [
        "subject", "pdf", "pdf_pages", "metadata_pages",
        "metadata_records", "text_files",
        "missing_text_pages", "unexpected_text_pages",
        "missing_metadata_pages", "duplicate_metadata_pages",
        "page_index_errors", "character_count_mismatches",
        "word_count_mismatches", "ocr_flagged_pages",
        "ocr_sidecars_found", "ocr_sidecars_missing",
        "ocr_empty_files", "ocr_under_10_words",
        "ocr_status", "visual_references_missing",
        "image_dominant_pages", "metadata_subject_match",
        "metadata_source_pdf_match", "source_filename_case_difference",
        "errors"
    ]

    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()

    for item in results:
        row = {}
        for field in fields:
            value = item.get(field, "")
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            row[field] = value
        writer.writerow(row)

# Markdown report
md_path = REPORT_DIR / "metadata_audit.md"

lines = [
    "# Class 8 AI Teacher — Metadata Audit",
    "",
    f"Audit date: {audit['audit_date']}",
    "",
    "## Subject summary",
    "",
    "| Subject | PDF pages | Metadata records | Text files | Flagged pages | OCR sidecars | Errors |",
    "|---|---:|---:|---:|---:|---:|---|",
]

for item in results:
    lines.append(
        f"| {item['subject']} | {item['pdf_pages']} | "
        f"{item['metadata_records']} | {item['text_files']} | "
        f"{item['ocr_flagged_pages']} | {item['ocr_sidecars_found']} | "
        f"{len(item['errors'])} |"
    )

lines += [
    "",
    "## Detailed findings",
    ""
]

for item in results:
    lines += [
        f"### {item['subject']}",
        "",
        f"- PDF pages: {item['pdf_pages']}",
        f"- Metadata page count: {item['metadata_pages']}",
        f"- Metadata records: {item['metadata_records']}",
        f"- Text files: {item['text_files']}",
        f"- Missing text pages: {item['missing_text_pages']}",
        f"- Unexpected text pages: {item['unexpected_text_pages']}",
        f"- Missing metadata pages: {item['missing_metadata_pages']}",
        f"- Duplicate metadata pages: {item['duplicate_metadata_pages']}",
        f"- Page index errors: {item['page_index_errors']}",
        f"- Character mismatches: {item['character_count_mismatches']}",
        f"- Word mismatches: {item['word_count_mismatches']}",
        f"- Flagged pages: {item['ocr_flagged_pages']}",
        f"- OCR sidecars found: {item['ocr_sidecars_found']}",
        f"- OCR sidecars missing: {item['ocr_sidecars_missing']}",
        f"- Empty OCR files: {item['ocr_empty_files']}",
        f"- OCR files under 10 words: {item['ocr_under_10_words']}",
        f"- OCR status: {item['ocr_status']}",
        f"- Missing visual references: {item['visual_references_missing']}",
        f"- Image-dominant pages: {item['image_dominant_pages']}",
        f"- Subject matches: {item['metadata_subject_match']}",
        f"- Exact source filename matches: {item['metadata_source_pdf_match']}",
        f"- Filename capitalization difference: {item['source_filename_case_difference']}",
        f"- Errors: {item['errors']}",
        ""
    ]

lines += [
    "## Manually inspected pages",
    "",
    "- Social Studies PDF page 274 (printed page 264): World Outline Map. Low OCR count is expected; preserve the map visually.",
    "- Hindi PDF page 11 (printed page 1): visual sample inspected. Question 2 OCR correction identified: वे क्या कर रहे हैं?",
    "",
    "## Audit limitations",
    ""
]

for limitation in audit["limitations"]:
    lines.append(f"- {limitation}")

lines += [
    "",
    "## Important",
    "",
    "This report verifies file and metadata consistency. It does not certify complete textbook extraction accuracy or OCR accuracy.",
]

md_path.write_text("\n".join(lines), encoding="utf-8")

print("\nAUDIT REPORTS CREATED")
print(json_path)
print(csv_path)
print(md_path)
print("\nSubject records:", len(results))
print("PDF pages counted:", sum(x["pdf_pages"] for x in results))
print("Metadata records:", sum(x["metadata_records"] for x in results))
print("Extracted text files:", sum(x["text_files"] for x in results))
