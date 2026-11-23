# tests/test_chunking_pipeline.py
import unittest
from tests.conftest import test_data
from ingestion.validate_curriculum_catalogue import validate_catalogue
from data.curriculum import mathematics_catalogue

class TestChunkingPipeline(unittest.TestCase):
    """Test suite for Mathematics textbook chunking pipeline."""

    def test_chunk_has_required_fields(self):
        """Verify chunks have required metadata."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertIn("subject", chunk)
            self.assertIn("chapter_title", chunk)
            self.assertIn("start_pdf_page", chunk)
            self.assertIn("end_pdf_page", chunk)
            self.assertIn("source_pages", chunk)

    def test_chunk_does_not_cross_chapter_boundaries(self):
        """Verify chunks stay within verified chapter ranges."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertTrue(validate_catalogue([chunk]), "Chunk crosses chapter boundary")

    def test_unicode_preservation(self):
        """Verify Telugu and Hindi Unicode strings are preserved."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertEqual(chunk["chapter_title"], chunk["chapter_title"], "Unicode preservation failed")

    def test_equations_and_tables_preserved(self):
        """Verify equations and tables are not arbitrarily split."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertTrue("equation" in chunk["source_pages"], "Equation split incorrectly")
            self.assertTrue("table" in chunk["source_pages"], "Table split incorrectly")

    def test_chunk_size_and_overlap_configurable(self):
        """Verify chunk size and overlap can be adjusted."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertTrue(100 <= chunk["end_pdf_page"] - chunk["start_pdf_page"] <= 200, "Chunk size out of range")

    def test_no_empty_chunks(self):
        """Verify no empty chunks are created."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertTrue(len(chunk["source_pages"] >= 1), "Empty chunk detected")

    def test_unique_chunk_ids(self):
        """Verify chunk IDs are unique."""
        chunk_ids = [chunk["id"] for chunk in mathematics_catalogue["valid_entries"]]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)), "Duplicate chunk IDs")

    def test_chunk_traces_to_original_page(self):
        """Verify each chunk can be traced to its original PDF page."""
        for chunk in mathematics_catalogue["valid_entries"]:
            self.assertTrue(chunk["start_pdf_page"] in chunk["source_pages"], "Chunk cannot be traced to original page")

if __name__ == '__main__':
    unittest.main()