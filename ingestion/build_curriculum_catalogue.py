
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VALIDATED_DIR = PROJECT_ROOT / "data" / "validated"
OUTPUT_DIR = PROJECT_ROOT / "data" / "curriculum"


# Expected PDF page counts for all seven Class 8 textbooks.
EXPECTED_PAGES = {
    "biological-science": 202,
    "english": 162,
    "hindi": 82,
    "mathematics": 370,
    "physical-science": 194,
    "social-studies": 282,
    "telugu": 182,
}


# ---------------------------------------------------------
# 1. Chapter, lesson and unit heading detection
# ---------------------------------------------------------

EXPLICIT_PATTERNS = [
    re.compile(
        r"^\s*(?:chapter|chap(?:ter)?\.?|lesson|unit)\s*"
        r"([0-9०-९]+|[ivxlcdm]+)?\s*[:.\-–—]?\s*(.*?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:అధ్యాయం|పాఠం|పాఠ్యాంశం)\s*"
        r"([0-9०-९]+)?\s*[:.\-–—]?\s*(.*?)\s*$"
    ),
    re.compile(
        r"^\s*(?:अध्याय|पाठ|इकाई)\s*"
        r"([0-9०-९]+)?\s*[:.\-–—]?\s*(.*?)\s*$"
    ),
]


# Numbered headings such as:
# 1. Rational Numbers
# 2. Cell Structure
# ३. जल संरक्षण

NUMBERED_PATTERN = re.compile(
    r"^\s*(\d{1,2}|[०-९]{1,2})\s*[.)\-:]\s*(.{3,100})$"
)


# ---------------------------------------------------------
# 2. Exercise and question filtering
# ---------------------------------------------------------

NUMBERED_PREFIX = (
    r"^\s*(?:\d{1,2}|[०-९]{1,2})\s*[.)\-:]\s*"
)

EXERCISE_PATTERNS = [

    # English: clear instructions and commands.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:ask|answer|explain|describe|define|list|write|"
          r"state|identify|compare|discuss|calculate|solve|"
          r"complete|choose|give|find|name|draw|match|classify)"
        + r"(?:\s|$|:)",
        re.IGNORECASE,
    ),

    # English: actual question constructions.
    # This avoids rejecting titles such as "Why Plants Need Water".
    re.compile(
        NUMBERED_PREFIX
        + r"(?:what|why|how|when|where|who|which|whose|whom)"
          r"\s+(?:is|are|was|were|do|does|did|can|could|"
          r"would|will|should|has|have|had|can't|cannot)\b",
        re.IGNORECASE,
    ),

    # English: question prompts with question punctuation.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:what|why|how|when|where|who|which|whose|whom)"
          r"\b.*[?؟]\s*$",
        re.IGNORECASE,
    ),

    # Telugu: clear instructional starters.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:అడగండి|చెప్పండి|వివరించండి|నిర్వచించండి|"
          r"రాయండి|గుర్తించండి|పోల్చండి|లెక్కించండి|"
          r"పరిష్కరించండి|సమాధానం\s+ఇవ్వండి)"
    ),

    # Telugu: question prompts.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:ఏమిటి|ఏమి|ఎందుకు|ఎలా|ఎప్పుడు|ఎక్కడ)"
          r".*[?؟]\s*$"
    ),

    # Hindi: clear instructional starters.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:पूछिए|पूछें|बताइए|बताएं|समझाइए|समझाएं|"
          r"लिखिए|लिखें|पहचानिए|तुलना\s+कीजिए|"
          r"हल\s+कीजिए|उत्तर\s+दीजिए|गणना\s+कीजिए)"
    ),

    # Hindi: question prompts.
    re.compile(
        NUMBERED_PREFIX
        + r"(?:क्या|क्यों|कैसे|कब|कहाँ|कौन|किसे)"
          r".*[?؟]\s*$"
    ),
]


NOISE_PATTERNS = [
    re.compile(r"^\s*page\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*www\.", re.IGNORECASE),
    re.compile(r"^\s*©"),
]


# ---------------------------------------------------------
# 3. Text cleaning and validation
# ---------------------------------------------------------

def read_page(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def clean_line(line: str) -> str:
    line = line.replace("\ufeff", "").replace("\x00", "")
    return re.sub(r"\s+", " ", line).strip()


def is_noise(line: str) -> bool:
    if not line or len(line) < 3:
        return True

    return any(
        pattern.match(line)
        for pattern in NOISE_PATTERNS
    )


def is_exercise_or_instruction(line: str) -> bool:
    """Reject clear numbered instructions and question prompts."""

    return any(
        pattern.match(line)
        for pattern in EXERCISE_PATTERNS
    )


def looks_like_heading(line: str) -> bool:
    if is_noise(line):
        return False

    if len(line) > 100:
        return False

    words = line.split()

    if len(words) > 14:
        return False

    if line.endswith((",", ";", "।")):
        return False

    if line.count(".") > 2:
        return False

    return True


def is_valid_chapter_candidate(
    line: str,
    title: str,
) -> tuple[bool, str]:

    """
    Validate a potential chapter heading.

    Returns:
        (True, "Valid") when accepted.
        (False, reason) when rejected.
    """

    if is_noise(title):
        return False, "Rejected: noise or too short"

    if len(title) > 100:
        return False, "Rejected: title too long"

    word_count = len(title.split())

    if word_count > 14:
        return False, "Rejected: too many words"

    if title.endswith((",", ";", "।")):
        return False, "Rejected: ends with punctuation"

    if title.count(".") > 2:
        return False, "Rejected: multiple periods"

    if is_exercise_or_instruction(line):
        return False, "Rejected: exercise or question instruction"

    return True, "Valid"


# ---------------------------------------------------------
# 4. Extract chapter candidates from individual pages
# ---------------------------------------------------------

def extract_candidates(
    text: str,
    page_number: int,
) -> list[dict]:

    lines = [
        clean_line(line)
        for line in text.splitlines()
    ]

    lines = [
        line for line in lines
        if line
    ]

    candidates = []
    seen_titles = set()

    # Chapter headings are generally near the beginning.
    for position, line in enumerate(lines[:18]):

        if is_noise(line):
            continue

        matched_explicit = False

        for pattern in EXPLICIT_PATTERNS:

            match = pattern.match(line)

            if not match:
                continue

            matched_explicit = True

            number = (match.group(1) or "").strip()
            title = (match.group(2) or "").strip()

            # Some books put the title on the next line.
            if not title and position + 1 < len(lines):
                title = lines[position + 1]

            is_valid, reason = is_valid_chapter_candidate(
                line,
                title,
            )

            if not is_valid:
                continue

            title_key = title.casefold()

            if title_key in seen_titles:
                continue

            seen_titles.add(title_key)

            candidates.append({
                "page": page_number,
                "title": title,
                "heading": line,
                "number": number,
                "confidence": "high",
                "reason": (
                    "Explicit chapter, lesson or unit heading"
                ),
            })

            break

        # Only check numbered headings when no explicit
        # chapter/lesson/unit pattern matched.
        if matched_explicit:
            continue

        numbered = NUMBERED_PATTERN.match(line)

        if not numbered:
            continue

        title = numbered.group(2).strip()
        number = numbered.group(1)

        is_valid, reason = is_valid_chapter_candidate(
            line,
            title,
        )

        if not is_valid:
            continue

        title_key = title.casefold()

        if title_key in seen_titles:
            continue

        seen_titles.add(title_key)

        candidates.append({
            "page": page_number,
            "title": title,
            "heading": line,
            "number": number,
            "confidence": "medium",
            "reason": "Numbered heading near page beginning",
            "rejection_reason": None,
        })

    return candidates


# ---------------------------------------------------------
# 5. Process each textbook
# ---------------------------------------------------------

def process_subject(
    subject: str,
    expected_pages: int,
) -> dict:

    subject_dir = VALIDATED_DIR / subject

    if not subject_dir.exists():
        raise FileNotFoundError(
            f"Missing validated folder: {subject_dir}"
        )

    page_files = sorted(
        subject_dir.glob("page-*.txt"),
        key=lambda path: path.name,
    )

    if len(page_files) != expected_pages:
        raise ValueError(
            f"{subject}: expected {expected_pages} pages, "
            f"found {len(page_files)}"
        )

    candidates = []

    for index, page_file in enumerate(
        page_files,
        start=1,
    ):

        text = read_page(page_file)

        candidates.extend(
            extract_candidates(text, index)
        )

    candidates.sort(
        key=lambda item: (
            item["page"],
            item["title"],
        )
    )

    chapters = []

    for index, candidate in enumerate(candidates):

        start_page = candidate["page"]

        if index + 1 < len(candidates):
            end_page = candidates[index + 1]["page"] - 1
        else:
            end_page = expected_pages

        if end_page < start_page:
            end_page = start_page

        chapters.append({
            "subject": subject,
            "chapter_number": candidate["number"],
            "chapter_title": candidate["title"],
            "heading_text": candidate["heading"],
            "start_page": start_page,
            "end_page": end_page,
            "page_count": end_page - start_page + 1,
            "confidence": candidate["confidence"],
            "detection_reason": candidate["reason"],
            "needs_review": True,
        })

    return {
        "subject": subject,
        "expected_pages": expected_pages,
        "actual_pages": len(page_files),
        "candidate_count": len(candidates),
        "chapters": chapters,
        "candidates": candidates,
    }


# ---------------------------------------------------------
# 6. Generate JSON, CSV and review catalogue
# ---------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_chapters = []
    all_candidates = []
    summaries = []

    for subject, expected_pages in EXPECTED_PAGES.items():

        result = process_subject(
            subject,
            expected_pages,
        )

        all_chapters.extend(
            result["chapters"]
        )

        all_candidates.extend([
            {
                "subject": subject,
                **candidate,
            }
            for candidate in result["candidates"]
        ])

        summaries.append({
            "subject": subject,
            "pages": result["actual_pages"],
            "chapter_candidates": result["candidate_count"],
        })

        print(
            f"{subject}: {result['actual_pages']} pages | "
            f"{result['candidate_count']} heading candidates"
        )

    total_pages = sum(
        item["pages"]
        for item in summaries
    )

    catalogue = {
        "project": (
            "Class 8 Telangana State Board AI Teacher"
        ),
        "description": (
            "Automatically detected chapter heading candidates. "
            "Chapter boundaries and titles require review."
        ),
        "total_books": len(summaries),
        "total_pages": total_pages,
        "total_chapter_candidates": len(all_candidates),
        "books": summaries,
        "chapters": all_chapters,
    }

    json_path = OUTPUT_DIR / "curriculum_catalogue.json"
    csv_path = OUTPUT_DIR / "curriculum_catalogue.csv"
    review_path = OUTPUT_DIR / "chapter_review.json"

    json_path.write_text(
        json.dumps(
            catalogue,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    fields = [
        "subject",
        "chapter_number",
        "chapter_title",
        "start_page",
        "end_page",
        "page_count",
        "confidence",
        "detection_reason",
        "needs_review",
    ]

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        for chapter in all_chapters:
            writer.writerow({
                key: chapter[key]
                for key in fields
            })

    review_data = {
        "message": (
            "These are automatically detected candidates, "
            "not manually verified chapters."
        ),
        "total_candidates": len(all_candidates),
        "candidates": all_candidates,
    }

    review_path.write_text(
        json.dumps(
            review_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nCURRICULUM CATALOGUE GENERATION COMPLETE")
    print(f"Books processed: {len(summaries)}")
    print(f"Pages scanned: {total_pages}")
    print(f"Heading candidates: {len(all_candidates)}")
    print(f"\nOutput folder: {OUTPUT_DIR}")
    print(f"1. {json_path.name}")
    print(f"2. {csv_path.name}")
    print(f"3. {review_path.name}")


# ---------------------------------------------------------
# 7. Focused automated tests
# ---------------------------------------------------------

def test_chapter_detection():

    # Test 1: Genuine English explicit chapter.
    result = extract_candidates(
        "Chapter 1. Cell Structure and Functions",
        1,
    )

    assert len(result) == 1
    assert result[0]["title"] == "Cell Structure and Functions"
    assert result[0]["confidence"] == "high"

    print("PASS: English explicit chapter")


    # Test 2: Genuine numbered English chapter.
    result = extract_candidates(
        "1. Rational Numbers",
        5,
    )

    assert len(result) == 1
    assert result[0]["title"] == "Rational Numbers"

    print("PASS: Numbered English chapter")


    # Test 3: English exercise instruction.
    result = extract_candidates(
        "2. Explain the following observations",
        10,
    )

    assert len(result) == 0

    print("PASS: English exercise instruction rejected")


    # Test 4: English question prompt.
    result = extract_candidates(
        "3. Why can't we see stars during day",
        13,
    )

    assert len(result) == 0

    print("PASS: English question prompt rejected")


    # Test 5: Genuine title containing asking questions.
    result = extract_candidates(
        "1. Asking Questions",
        20,
    )

    assert len(result) == 1

    print("PASS: Genuine title containing Questions preserved")


    # Test 6: Genuine Telugu chapter heading.
    result = extract_candidates(
        "అధ్యాయం 1. జీవుల నిర్మాణం",
        1,
    )

    assert len(result) == 1
    assert result[0]["confidence"] == "high"

    print("PASS: Telugu chapter heading")


    # Test 7: Telugu instruction rejected.
    result = extract_candidates(
        "2. వివరించండి",
        10,
    )

    assert len(result) == 0

    print("PASS: Telugu instruction rejected")


    # Test 8: Genuine Hindi chapter heading.
    result = extract_candidates(
        "अध्याय 1. प्राकृतिक संसाधन",
        1,
    )

    assert len(result) == 1
    assert result[0]["confidence"] == "high"

    print("PASS: Hindi chapter heading")


    print("\nALL 8 CHAPTER DETECTION TESTS PASSED")


# ---------------------------------------------------------
# 8. Single execution entry point
# ---------------------------------------------------------

if __name__ == "__main__":

    if "--test" in sys.argv:
        test_chapter_detection()
    else:
        main()
