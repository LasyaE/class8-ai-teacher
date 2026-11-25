
import copy
import unittest

from tests.conftest import (
    test_data,
    validate_page_numbers,
    check_duplicate_entries,
    check_overlapping_ranges,
)
from ingestion.validate_curriculum_catalogue import validate_catalogue


class TestCurriculumCatalogue(unittest.TestCase):
    """Test curriculum catalogue validation rules."""

    def setUp(self):
        self.valid_entries = copy.deepcopy(test_data["valid_entries"])
        self.invalid_entries = copy.deepcopy(test_data["invalid_entries"])

    def test_required_fields(self):
        required = {
            "subject",
            "chapter_title",
            "start_pdf_page",
            "end_pdf_page",
            "source_pages",
        }

        for entry in self.valid_entries:
            with self.subTest(entry=entry):
                self.assertTrue(required.issubset(entry.keys()))

    def test_invalid_entries_are_rejected(self):
        for entry in self.invalid_entries:
            with self.subTest(entry=entry):
                results = validate_catalogue([entry])
                self.assertTrue(
                    results,
                    f"Invalid entry was accepted: {entry}",
                )

    def test_empty_titles_are_rejected(self):
        empty_title_entries = [
            entry for entry in self.invalid_entries
            if not str(entry.get("chapter_title", "")).strip()
        ]

        for entry in empty_title_entries:
            with self.subTest(entry=entry):
                results = validate_catalogue([entry])
                self.assertTrue(results, "Empty title was not rejected")

    def test_page_number_validation(self):
        for entry in self.valid_entries:
            with self.subTest(entry=entry):
                self.assertTrue(validate_page_numbers(entry))

    def test_duplicate_entries(self):
        duplicates = check_duplicate_entries(self.valid_entries)
        self.assertEqual(duplicates, [])

    def test_overlapping_ranges(self):
        overlaps = check_overlapping_ranges(self.valid_entries)
        self.assertEqual(overlaps, [])

    def test_missing_source_pages_are_rejected(self):
        missing_evidence = [
            entry for entry in self.invalid_entries
            if not entry.get("source_pages")
        ]

        for entry in missing_evidence:
            with self.subTest(entry=entry):
                results = validate_catalogue([entry])
                self.assertTrue(
                    results,
                    "Missing source-page evidence was not rejected",
                )

    def test_unicode_preservation(self):
        for input_data, expected_output in test_data.get(
            "unicode_test_data", []
        ):
            self.assertEqual(
                input_data["chapter_title"],
                expected_output,
            )

    def test_validate_catalogue_accepts_valid_entries(self):
        results = validate_catalogue(self.valid_entries)
        self.assertEqual(results, [])

    def test_validate_catalogue_detects_duplicates(self):
        entries = copy.deepcopy(self.valid_entries)
        entries.append(copy.deepcopy(entries[0]))

        results = validate_catalogue(entries)

        self.assertTrue(
            any(result.get("error") == "DUPLICATE_ENTRY"
                for result in results),
            f"Duplicate entry not detected: {results}",
        )

    def test_validate_catalogue_detects_overlapping_ranges(self):
        self.assertTrue(
            self.valid_entries,
            "Cannot test overlap without a valid catalogue entry",
        )

        original = self.valid_entries[0]
        start = original["start_pdf_page"]
        end = original["end_pdf_page"]

        overlapping_entry = {
            "subject": original["subject"],
            "chapter_title": "Synthetic overlapping test chapter",
            "start_pdf_page": start,
            "end_pdf_page": end,
            "source_pages": list(range(start, end + 1)),
        }

        entries = copy.deepcopy(self.valid_entries)
        entries.append(overlapping_entry)

        results = validate_catalogue(entries)

        self.assertTrue(
            any(result.get("error") == "OVERLAPPING_RANGE"
                for result in results),
            f"Overlapping range not detected: {results}",
        )


if __name__ == "__main__":
    unittest.main()
