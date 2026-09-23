"""
Security regression tests for the /file-content endpoint.
Verifies path traversal attacks are blocked after the Path.resolve() fix.
"""

import sys
import types
import importlib
from pathlib import Path
from unittest.mock import MagicMock, patch


def _load_app():
    """Load app module with mocked Gemini so no real API calls are made."""
    for mod in list(sys.modules.keys()):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]

    mock_embed = MagicMock()
    mock_embed.return_value.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_llm = MagicMock()

    with patch("langchain_google_genai.GoogleGenerativeAIEmbeddings", mock_embed), \
         patch("langchain_google_genai.ChatGoogleGenerativeAI", mock_llm):
        return importlib.import_module("app")


import unittest


class TestPathTraversal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app_module = _load_app()
        cls.client = app_module.app.test_client()

    def _get(self, path_value):
        return self.client.get(
            f"/file-content?repo_id=test_repo&path={path_value}"
        )

    def test_dotdot_blocked(self):
        r = self._get("../../etc/passwd")
        self.assertIn(r.status_code, (403, 404),
                      "../../etc/passwd must be blocked (403) or not found (404)")

    def test_chained_dotdot_blocked(self):
        r = self._get("....//....//etc/passwd")
        self.assertIn(r.status_code, (403, 404),
                      "Chained dotdot bypass must be blocked")

    def test_absolute_path_blocked(self):
        r = self._get("/etc/passwd")
        self.assertIn(r.status_code, (403, 404),
                      "Absolute path must be blocked")

    def test_normal_path_returns_404_not_403(self):
        # repo_id=test_repo does not exist on disk, so we expect 404, not 403
        r = self._get("README.md")
        # Should NOT be a 403 (access denied from traversal check)
        self.assertNotEqual(r.status_code, 403,
                            "Legitimate relative path must not be blocked by traversal check")


if __name__ == "__main__":
    unittest.main()
