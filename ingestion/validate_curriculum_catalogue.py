# ingestion/validate_curriculum_catalogue.py
from tests.conftest import test_data
from collections import defaultdict

def validate_catalogue(entries):
    """Validate curriculum catalogue entries against defined rules."""
    results = []
    subject_limits = test_data["subjects"]
    seen = defaultdict(set)
    seen_overlaps = defaultdict(list)
    overlaps = []

    for idx, entry in enumerate(entries):
        # Required fields check
        required_fields = ["subject", "chapter_title", "start_pdf_page", "end_pdf_page", "source_pages"]
        missing = [f for f in required_fields if f not in entry]
        if missing:
            results.append({
                "index": idx,
                "error": "MISSING_REQUIRED_FIELDS",
                "message": f"Missing required fields: {missing}",
                "severity": "error"
            })
            continue

        # Subject name and page limit check
        subject = entry["subject"]
        if subject not in subject_limits:
            results.append({
                "index": idx,
                "error": "INVALID_SUBJECT",
                "message": f"Invalid subject: {subject}",
                "severity": "error"
            })
            continue
        limit = subject_limits[subject]

        # Page number validation
        try:
            start = int(entry["start_pdf_page"])
            end = int(entry["end_pdf_page"])
        except (ValueError, TypeError):
            results.append({
                "index": idx,
                \n                "error": "INVALID_PAGE_NUMBER",
                "message": "Page numbers must be positive integers",
                "severity": "error"
            })
            continue
        if start <= 0 or end <= 0 or start > limit or end > limit:
            results.append({
                "index": idx,
                "error": "INVALID_PAGE_RANGE",
                "message": f"Page range {start}-{end} exceeds subject limit {limit}",
                "severity": "error"
            })
            continue
        if end < start:
            results.append({
                "index": idx,
                "error": "INVALID_PAGE_ORDER",
                "message": "End page must be greater than or equal to start page",
                "severity": "error"
            })
            continue

        # Source pages check
        if not entry.get("source_pages") or len(entry["source_pages"]) == 0:
            results.append({
                "index": idx,
                "error": "MISSING_SOURCE_PAGES",
                "message": "Missing source-page evidence",
                "severity": "warning"
            })
            continue

        # Duplicate check
        key = (subject, entry["chapter_title"])
        if key in seen[subject]:
            results.append({
                "index": idx,
                "error": "DUPLICATE_ENTRY",
                "message": "Duplicate chapter entry",
                "severity": "error"
            })
        else:
            seen[subject].add(key)

        # Overlapping range check
        if subject in seen_overlaps:
            for prev_start, prev_end in seen_overlaps[subject]:
                if prev_end >= start:
                    results.append({
                        "index": idx,
                        "error": "OVERLAPPING_RANGE",
                        "message": f"Overlapping range with previous entry {prev_start}-{prev_end}",
                        "severity": "warning"
                    })
        seen_overlaps[subject].append((start, end))

    return results
