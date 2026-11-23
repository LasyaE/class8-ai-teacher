# tests/test_curriculum_catalogue.py
import unittest
from tests.conftest import test_data, validate_page_numbers, check_duplicate_entries, check_overlapping_ranges, unicode_test_data
from ingestion.validate_curriculum_catalogue import validate_catalogue

class TestCurriculumCatalogue(unittest.TestCase):
    """Test suite for curriculum catalogue validation rules."""

    def test_required_fields(self):
        """Verify required fields are present in catalogue entries."""
        for entry in test_data["valid_entries"]:
            self.assertIn("subject", entry)
            self.assertIn("chapter_title", entry)
            self.assertIn("start_pdf_page", entry)
            self.assertIn("end_pdf_page", entry, f"Missing required field: end_pdf_page in entry {entry}")
            self.assertIn("source_pages", entry)

    def test_missing_fields(self):
        """Verify missing fields are detected."""
        for entry in test_data["invalid_entries"]:
            if "subject" not in entry:
                self.fail("Missing required field: subject")
            if "chapter_title" not in entry:
                self.fail("Missing required field: chapter_title")
            if "start_pdf_page" not in entry:
                self.fail("Missing required field: start_pdf_page")
            if "end_pdf_page" not in entry:
                self.fail("Missing required field: end_pdf_page")
            if "source_pages" not in entry:
                self.fail("Missing required field: source_pages")

    def test_empty_titles(self):
        """Verify empty chapter titles are detected."""
        for entry in test_data["invalid_entries"]:
            if entry["chapter_title"] == "":
                self.fail("Empty chapter title detected")

    def test_page_number_validation(self):
        """Verify page numbers are valid integers within subject limits."""
        for entry in test_data["valid_entries"]:
            self.assertTrue(validate_page_numbers(entry), "Page number validation failed for entry: {}".format(entry))

    def test_duplicate_entries(self):
        """Verify duplicate entries are detected."""
        duplicates = check_duplicate_entries(test_data["valid_entries"])
        self.assertEqual(len(duplicates), 0, "Duplicate entries found: {}".format(duplicates))

    def test_overlapping_ranges(self):
        """Verify overlapping chapter ranges are identified."""
        overlaps = check_overlapping_ranges(test_data["valid_entries"])
        self.assertEqual(len(overlaps), 0, "Overlapping ranges found: {}".format(overlaps))

    def test_missing_source_pages(self):
        """Verify missing source-page evidence is flagged."""
        for entry in test_data["invalid_entries"]:
            if len(entry.get("source_pages", [])) == 0:
                self.fail("Missing source-page evidence for entry: {}".format(entry))

    def test_unicode_preservation(self):
        """Verify Telugu and Hindi Unicode strings are preserved exactly."""
        for input_data, expected_output in unicode_test_data:
            self.assertEqual(input_data["chapter_title"], expected_output, "Unicode preservation failed for input: {}".format(input_data))

    def test_validate_catalogue(self):
        """Verify the production validator works with existing test data."""
        results = validate_catalogue(test_data["valid_entries"])
        self.assertEqual(len(results), 0, "Validation errors found: {}".format(results))

        # Test invalid entries
        results = validate_catalogue(test_data["invalid_entries"])
        self.assertTrue(all(r["severity"] == "error" for r in results), "Expected all errors for invalid entries")

        # Test duplicate entries
        test_data["valid_entries"].append(test_data["valid_entries"][0])
        results = validate_catalogue(test_data["valid_entries"])
        self.assertTrue(any(r["error"] == "DUPLICATE_ENTRY" for r in results), "Duplicate entry not detected")

        # Test overlapping ranges
        test_data["valid_entries"].append({"subject": "mathematics", "chapter_title": "New Chapter", "start_pdf_page": 60, "end_pdf_page": 70, "source_pages": [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70]})
        results = validate_catalogue(test_data["valid_entries"])
        self.assertTrue(any(r["error"] == "OVERLAPPING_RANGE" for r in results), "Overlapping range not detected")

if __name__ == '__main__':
    unittest.main()