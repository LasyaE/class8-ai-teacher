import unittest
from unittest.mock import MagicMock, patch

from run_pipeline import (
    check_dataset_structure,
    check_ollama_connection,
    check_ollama_model,
    check_python_environment,
)


class TestPreflightChecks(unittest.TestCase):
    """Tests for pipeline preflight checks."""

    @patch("run_pipeline.urlopen")
    def test_check_ollama_connection(self, mock_urlopen):
        """An empty Ollama response should fail the connection check."""
        response = MagicMock()
        response.read.return_value = b"[]"
        mock_urlopen.return_value = response
        mock_urlopen.return_value.__enter__.return_value = response

        result = check_ollama_connection()

        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["message"], "No response from Ollama")
        self.assertTrue(result["critical"])

    @patch("run_pipeline.urlopen")
    def test_check_ollama_model(self, mock_urlopen):
        """The configured Ollama model should be detected."""
        payload = b'{"models":[{"name":"qwen3:8b"}]}'

        response = MagicMock()
        response.read.return_value = payload
        mock_urlopen.return_value = response
        mock_urlopen.return_value.__enter__.return_value = response

        result = check_ollama_model()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["message"],
            "Ollama model qwen3:8b available",
        )
        self.assertFalse(result["critical"])

    def test_check_dataset_structure(self):
        """Dataset readiness should return a structured result."""
        result = check_dataset_structure("mathematics", 1)

        self.assertIn(result["status"], {"PASS", "WARN"})
        self.assertIsInstance(result["message"], str)
        self.assertTrue(result["message"])
        self.assertIn("critical", result)
        self.assertIsInstance(result["critical"], bool)

    @patch("run_pipeline.subprocess.run")
    def test_check_python_environment(self, mock_run):
        """Required packages should pass when pip reports them installed."""

        def mock_package_check(command, *args, **kwargs):
            package = str(command[-1])
            response = MagicMock()
            response.returncode = 0
            response.stdout = (
                f"Name: {package}\n"
                "Version: 99.0.0\n"
            )
            response.stderr = ""
            return response

        mock_run.side_effect = mock_package_check

        result = check_python_environment()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["message"],
            "AI interpreter and required packages verified",
        )
        self.assertFalse(result["critical"])


if __name__ == "__main__":
    unittest.main()

