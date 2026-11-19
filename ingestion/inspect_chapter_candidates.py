
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
BOOK_DIR = ROOT / "data" / "validated"
OUT_DIR = ROOT / "data" / "curriculum"

BOOKS = {
    "biological-science": 202,
    "english": 162,
    "hindi": 82,
    "mathematics": 370,
    "physical-science": 194,
    "social-studies": 282,
    "telugu": 182,
}

# Strong chapter markers only. Ordinary numbered questions are excluded.
MARKERS = [
    re.compile(
        r"^\s*chapter\s+(\d{1,2})\s*[:.\-–—]?\s*(.*?)\s*$",
        re.I,
    ),
    re.compile(
        r"^\s*chapter\s*$",
        re.I,
    ),
    re.compile(
        r"^\s*अध्याय\s*[-:]?\s*([०-९0-9]+)?\s*(.*?)\s*$"
    ),
    re.compile(
        r"^\s*पाठ\s*[-:]?\s*([०-९0-9]+)?\s*(.*?)\s*$"
    ),
    re.compile(
        r"^\s*इकाई\s*[-:]?\s*([०-९0-9]+)?\s*(.*?)\s*$"
    ),
    re.compile(
        r"^\s*పాఠం\s*[-:]?\s*([0-9౦-౯]+)?\s*(.*?)\s*$"
    ),
    re.compile(
        r"^\s*అధ్యాయం\s*[-:]?\s*([0-9౦-౯]+)?\s*(.*?)\s*$"
    ),
]

# Mathematics has a reliable numbered chapter pattern.
MATH_MARKER = re.compile(
    r"^\s*chapter\s+(\d{1,2})\s*$",
    re.I,
)

# Contents-page chapter entries.
CONTENTS_MARKERS = [
    re.compile(
        r"^\s*chapter\s+(\d{1,2})\s*[:.\-–—]?\s*(.{3,90})$",
        re.I,
    ),
    re.compile(
        r"^\s*(?:अध्याय|पाठ|इकाई)\s*"
        r"([०-९0-9]+)?\s*[:.\-–—]?\s*(.{3,90})$"
    ),
    re.compile(
        r"^\s*(?:పాఠం|అధ్యాయం)\s*"
        r"([0-9౦-౯]+)?\s*[:.\-–—]?\s*(.{3,90})$"
    ),
]

NOISE = [
    re.compile(r"^\s*page\s+\d+\s*$", re.I),
    re.compile(r"^\s*chapter\s*$", re.I),
    re.compile(r"^\s*unit\s+\d+\s*$", re.I),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*www\.", re.I),
]

def clean(line):
    line = line.replace("\ufeff", "").replace("\x00", "")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_noise(line):
    if not line or len(line) < 3 or len(line) > 100:
        return True

    if any(pattern.match(line) for pattern in NOISE):
        return True

    if line.count("?") > 0:
        return True

    return False


def page_files(subject):
    folder = BOOK_DIR / subject
    files = list(folder.glob("page-*.txt"))

    def page_number(path):
        match = re.search(r"(\d+)", path.stem)
        return int(match.group(1)) if match else 0

    return sorted(files, key=page_number)


def read_pages(subject):
    pages = {}

    for path in page_files(subject):
        match = re.search(r"(\d+)", path.stem)
        if not match:
            continue

        number = int(match.group(1))
        pages[number] = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    return pages


def find_title(lines, position, same_line_title=""):
    title = clean(same_line_title)

    if title and not is_noise(title):
        return title

    # Titles are often printed on the next line after "Chapter".
    for offset in range(1, 5):
        index = position + offset

        if index >= len(lines):
            break

        candidate = clean(lines[index])

        if is_noise(candidate):
            continue

        if len(candidate.split()) <= 15:
            return candidate

    return ""


def detect_page_heading(subject, page_number, text):
    lines = [clean(x) for x in text.splitlines()]
    results = []

    # Restrict chapter markers to the beginning portion of a page.
    # This reduces false detections from questions and exercises.
    for position, line in enumerate(lines[:22]):
        if not line:
            continue

        # Mathematics: only accept explicit Chapter N.
        if subject == "mathematics":
            match = MATH_MARKER.match(line)

            if match:
                number = match.group(1)
                title = find_title(lines, position)

                if title:
                    results.append({
                        "subject": subject,
                        "page": page_number,
                        "number": number,
                        "title": title,
                        "marker": line,
                        "confidence": "high",
                        "source": "explicit mathematics chapter marker",
                    })

            continue

        for pattern in MARKERS:
            match = pattern.match(line)

            if not match:
                continue

            groups = match.groups()
            number = groups[0] if groups else ""
            same_line_title = groups[-1] if groups else ""

            # Do not accept unnumbered generic markers in other subjects.
            if line.casefold() == "chapter":
                number = ""
                same_line_title = ""

            title = find_title(
                lines,
                position,
                same_line_title,
            )

            if not title:
                continue

            # Do not mistake numbered exercises for lessons.
            if re.match(
                r"^(?:what|why|how|who|where|when|name|write|"
                r"draw|explain|find|describe|identify|state|"
                r"match|fill|observe|collect)\b",
                title,
                re.I,
            ):
                continue

            results.append({
                "subject": subject,
                "page": page_number,
                "number": number or "",
                "title": title,
                "marker": line,
                "confidence": "medium",
                "source": "language-specific lesson marker",
            })

            break

    return results


def detect_numbered_contents_entries(subject, pages):
    """Look for strong chapter entries in early contents pages."""
    results = []

    for page_number, text in pages.items():
        if page_number > 15:
            continue

        lines = [clean(x) for x in text.splitlines()]

        for line in lines:
            if not line or len(line) > 110:
                continue

            for pattern in CONTENTS_MARKERS:
                match = pattern.match(line)

                if not match:
                    continue

                groups = match.groups()
                number = groups[0] or ""
                title = groups[-1] or ""

                if is_noise(title):
                    continue

                if title.casefold() in {
                    "contents",
                    "syllabus",
                    "page no.",
                    "page number",
                }:
                    continue

                results.append({
                    "subject": subject,
                    "page": page_number,
                    "number": number,
                    "title": title,
                    "marker": line,
                    "confidence": "medium",
                    "source": "contents page candidate",
                })

                break

    return results


def deduplicate(candidates):
    output = []
    seen = set()

    for item in sorted(
        candidates,
        key=lambda x: (x["page"], x["title"].casefold()),
    ):
        key = (
            item["subject"],
            item["page"],
            item["title"].casefold(),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


def build_subject(subject, expected_pages):
    pages = read_pages(subject)

    if len(pages) != expected_pages:
        raise ValueError(
            f"{subject}: expected {expected_pages} pages, "
            f"found {len(pages)}"
        )

    candidates = []

    for page_number, text in pages.items():
        candidates.extend(
            detect_page_heading(subject, page_number, text)
        )

    # Contents entries are retained separately as supporting evidence.
    contents = detect_numbered_contents_entries(subject, pages)

    candidates = deduplicate(candidates)
    contents = deduplicate(contents)

    # Keep only candidates with explicit markers for the main catalogue.
    # Contents candidates are retained for comparison and review.
    return {
        "subject": subject,
        "page_count": len(pages),
        "candidates": candidates,
        "contents_candidates": contents,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    subjects = []
    all_candidates = []
    all_contents = []

    for subject, expected in BOOKS.items():
        result = build_subject(subject, expected)

        subjects.append({
            "subject": subject,
            "pages": result["page_count"],
            "heading_candidates": len(result["candidates"]),
            "contents_candidates": len(result["contents_candidates"]),
        })

        all_candidates.extend(result["candidates"])
        all_contents.extend(result["contents_candidates"])

        print(
            f"{subject}: {result['page_count']} pages | "
            f"{len(result['candidates'])} chapter candidates | "
            f"{len(result['contents_candidates'])} contents candidates"
        )

    # Create tentative page ranges from detected chapter starts.
    chapters = []

    for subject in BOOKS:
        items = [
            item for item in all_candidates
            if item["subject"] == subject
        ]

        items.sort(key=lambda x: x["page"])

        for index, item in enumerate(items):
            start = item["page"]

            if index + 1 < len(items):
                end = items[index + 1]["page"] - 1
            else:
                end = BOOKS[subject]

            if end < start:
                end = start

            chapters.append({
                **item,
                "start_page": start,
                "end_page": end,
                "page_count": end - start + 1,
                "needs_review": True,
            })

    catalogue = {
        "project": "Class 8 Telangana State Board AI Teacher",
        "total_books": len(subjects),
        "total_pages": sum(x["pages"] for x in subjects),
        "total_chapter_candidates": len(chapters),
        "books": subjects,
        "chapters": chapters,
    }

    review = {
        "description": (
            "Automated chapter candidates and contents-page "
            "candidates. These are not manually verified chapters."
        ),
        "chapter_candidates": all_candidates,
        "contents_candidates": all_contents,
    }

    (OUT_DIR / "curriculum_catalogue.json").write_text(
        json.dumps(catalogue, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    (OUT_DIR / "chapter_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUT_DIR / "curriculum_catalogue.csv").open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        fields = [
            "subject",
            "number",
            "title",
            "page",
            "start_page",
            "end_page",
            "page_count",
            "confidence",
            "source",
            "needs_review",
        ]

        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for chapter in chapters:
            writer.writerow({
                "subject": chapter["subject"],
                "number": chapter["number"],
                "title": chapter["title"],
                "page": chapter["page"],
                "start_page": chapter["start_page"],
                "end_page": chapter["end_page"],
                "page_count": chapter["page_count"],
                "confidence": chapter["confidence"],
                "source": chapter["source"],
                "needs_review": True,
            })

    print("\nREVISED CURRICULUM CATALOGUE GENERATED")
    print(f"Books: {len(subjects)}")
    print(f"Pages scanned: {sum(x['pages'] for x in subjects)}")
    print(f"Chapter candidates: {len(chapters)}")
    print(f"Output folder: {OUT_DIR}")


if __name__ == "__main__":
    main()
