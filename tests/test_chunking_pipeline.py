import unittest

from data.curriculum import mathematics_catalogue


class TestMathematicsCatalogue(unittest.TestCase):
    """Validate the structure and page boundaries of catalogue entries."""

    @classmethod
    def setUpClass(cls):
        cls.entries = mathematics_catalogue.valid_entries

    def test_catalogue_contains_entries(self):
        self.assertIsInstance(self.entries, list)
        self.assertGreater(len(self.entries), 0)

    def test_required_fields_exist(self):
        required_fields = {
            "subject",
            "chapter_title",
            "start_pdf_page",
            "end_pdf_page",
            "source_pages",
            "content",
        }

        for entry in self.entries:
            with self.subTest(chapter=entry.get("chapter_title")):
                self.assertTrue(required_fields.issubset(entry.keys()))

    def test_subject_and_title_are_not_empty(self):
        for entry in self.entries:
            self.assertTrue(entry["subject"].strip())
            self.assertTrue(entry["chapter_title"].strip())

    def test_page_numbers_are_valid(self):
        for entry in self.entries:
            with self.subTest(chapter=entry["chapter_title"]):
                self.assertIsInstance(entry["start_pdf_page"], int)
                self.assertIsInstance(entry["end_pdf_page"], int)
                self.assertGreaterEqual(entry["start_pdf_page"], 1)
                self.assertGreaterEqual(
                    entry["end_pdf_page"],
                    entry["start_pdf_page"],
                )

    def test_source_pages_match_chapter_range(self):
        for entry in self.entries:
            expected_pages = list(
                range(
                    entry["start_pdf_page"],
                    entry["end_pdf_page"] + 1,
                )
            )

            with self.subTest(chapter=entry["chapter_title"]):
                self.assertEqual(entry["source_pages"], expected_pages)

    def test_chapter_content_is_not_empty(self):
        for entry in self.entries:
            self.assertIsInstance(entry["content"], str)
            self.assertTrue(entry["content"].strip())

    def test_chapter_ranges_do_not_overlap(self):
        ordered = sorted(
            self.entries,
            key=lambda entry: entry["start_pdf_page"],
        )

        for previous, current in zip(ordered, ordered[1:]):
            with self.subTest(
                previous=previous["chapter_title"],
                current=current["chapter_title"],
            ):
                self.assertLess(
                    previous["end_pdf_page"],
                    current["start_pdf_page"],
                    "Chapter page ranges overlap.",
                )


if __name__ == "__main__":
    unittest.main()
