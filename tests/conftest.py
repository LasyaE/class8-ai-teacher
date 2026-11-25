# tests/conftest.py
import unittest
import json

test_data = {
    "subjects": {
        "biological-science": 202,
        "english": 162,
        "hindi": 82,
        "mathematics": 370,
        "physical-science": 194,
        "social-studies": 282,
        "telugu": 182
    },
    "valid_entries": [
        {
            "subject": "mathematics",
            "chapter_title": "Algebraic Expressions",
            "start_pdf_page": 45,
            "end_pdf_page": 60,
            "source_pages": [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
        },
        {
            "subject": "telugu",
            "chapter_title": "సంఖ్యలు మరియు గుణికరణం",
            "start_pdf_page": 112,
            "end_pdf_page": 125,
            "source_pages": [112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125]
        }
    ],
    "invalid_entries": [
        {
            "subject": "english",
            "chapter_title": "",
            "start_pdf_page": 30,
            "end_pdf_page": 40
        },
        {
            "subject": "hindi",
            "chapter_title": "Invalid Chapter",
            "start_pdf_page": 10,
            "end_pdf_page": 5
        },
        {
            "subject": "mathematics",
            "chapter_title": "Invalid Page",
            "start_pdf_page": 500,
            "end_pdf_page": 510
        }
    ],
    "unicode_examples": {
        "telugu": "సంఖ్యలు మరియు గుణికరణం",
        "hindi": "संख्याएँ और गुणन"
    }
}

# Helper functions for test validation
def validate_page_numbers(entry):
    subject = entry["subject"]
    start = entry["start_pdf_page"]
    end = entry["end_pdf_page"]
    limit = test_data["subjects"][subject]
    return (isinstance(start, int) and start > 0 and start <= limit and
           isinstance(end, int) and end > 0 and end <= limit and
           end >= start)

def check_duplicate_entries(entries):
    seen = set()
    duplicates = []
    for entry in entries:
        key = (entry["subject"], entry["chapter_title"])
        if key in seen:
            duplicates.append(entry)
        else:
            seen.add(key)
    return duplicates

def check_overlapping_ranges(entries):
    sorted_entries = sorted(entries, key=lambda x: x["start_pdf_page"])
    overlaps = []
    for i in range(len(sorted_entries) - 1):
        current = sorted_entries[i]
        next_entry = sorted_entries[i+1]
        if current["end_pdf_page"] >= next_entry["start_pdf_page"]:
            overlaps.append((current, next_entry))
    return overlaps

# Test data for Unicode preservation
unicode_test_data = [
    ({"chapter_title": "సంఖ్యలు మరియు గుణికరణం"}, "సంఖ్యలు మరియు గుణికరణం"),
    ({"chapter_title": "संख्याएँ और गुणन"}, "संख्याएँ और गुणन")
]
