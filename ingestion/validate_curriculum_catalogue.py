
"""Validate curriculum catalogue entries against curriculum page limits."""

from collections import defaultdict

# Keep curriculum metadata in production code, not in tests.conftest.
# These limits represent the total PDF page counts of the seven source books.
SUBJECT_PAGE_LIMITS = {
    "mathematics": 370,
    "physical-science": 194,
    "biological-science": 202,
    "social-studies": 282,
    "english": 162,
    "telugu": 182,
    "hindi": 82,
}


def validate_catalogue(entries):
    """Return validation issues for curriculum catalogue entries."""
    results = []
    seen = defaultdict(set)
    seen_overlaps = defaultdict(list)

    required_fields = (
        "subject",
        "chapter_title",
        "start_pdf_page",
        "end_pdf_page",
        "source_pages",
    )

    for idx, entry in enumerate(entries):
        missing = [field for field in required_fields if field not in entry]
        if missing:
            results.append({
                "index": idx,
                "error": "MISSING_REQUIRED_FIELDS",
                "message": f"Missing required fields: {missing}",
                "severity": "error",
            })
            continue

        subject = entry["subject"]
        if subject not in SUBJECT_PAGE_LIMITS:
            results.append({
                "index": idx,
                "error": "INVALID_SUBJECT",
                "message": f"Invalid subject: {subject}",
                "severity": "error",
            })
            continue

        try:
            start = int(entry["start_pdf_page"])
            end = int(entry["end_pdf_page"])
        except (ValueError, TypeError):
            results.append({
                "index": idx,
                "error": "INVALID_PAGE_NUMBER",
                "message": "Page numbers must be positive integers",
                "severity": "error",
            })
            continue

        limit = SUBJECT_PAGE_LIMITS[subject]

        if start <= 0 or end <= 0 or start > limit or end > limit:
            results.append({
                "index": idx,
                "error": "INVALID_PAGE_RANGE",
                "message": f"Page range {start}-{end} exceeds subject limit {limit}",
                "severity": "error",
            })
            continue

        if end < start or not isinstance(end, int) or end <= 0 or end > limit:
            results.append({
                "index": idx,
                "error": "INVALID_PAGE_ORDER",
                "message": "End page must be greater than or equal to start page",
                "severity": "error",
            })
            continue

        source_pages = entry["source_pages"]
        if not isinstance(source_pages, (list, tuple)) or not source_pages:
            results.append({
                "index": idx,
                "error": "MISSING_SOURCE_PAGES",
                "message": "Missing or invalid source-page evidence",
                "severity": "warning",
            })
            continue

        key = entry["chapter_title"]
        if key in seen[subject]:
            results.append({
                "index": idx,
                "error": "DUPLICATE_ENTRY",
                "message": "Duplicate chapter entry",
                "severity": "error",
            })
        else:
            seen[subject].add(key)

        for prev_start, prev_end in seen_overlaps[subject]:
            if start <= prev_end and end >= prev_start:
                results.append({
                    "index": idx,
                    "error": "OVERLAPPING_RANGE",
                    "message": (
                        f"Overlapping range with previous entry "
                        f"{prev_start}-{prev_end}"
                    ),
                    "severity": "warning",
                })

        seen_overlaps[subject].append((start, end))

    return results
