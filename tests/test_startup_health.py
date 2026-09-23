"""
Acceptance tests for the startup API-key validation probe and /health endpoint.

All tests are fully mocked — no real Gemini API calls are made.

Run with:
    python -m pytest tests/test_startup_health.py -v
"""

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helper: reload app module with a patched embed_query so we can control
# what the startup probe sees without touching the real network.
# ---------------------------------------------------------------------------

def _reload_app_with_embed_side_effect(side_effect):
    """
    Reload the `app` module from scratch so that `validate_api_key_on_startup()`
    runs again with `GoogleGenerativeAIEmbeddings.embed_query` replaced by a
    mock that raises `side_effect` (or returns normally if side_effect is None).

    Returns:
        The freshly imported `app` module.
    """
    # Remove cached module so importlib reloads from source
    for mod_name in list(sys.modules.keys()):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]

    mock_embeddings_instance = MagicMock()
    if side_effect is None:
        mock_embeddings_instance.embed_query.return_value = [0.1, 0.2, 0.3]
    else:
        mock_embeddings_instance.embed_query.side_effect = side_effect

    with patch(
        "langchain_google_genai.GoogleGenerativeAIEmbeddings",
        return_value=mock_embeddings_instance,
    ), patch(
        "config.Config.GOOGLE_API_KEY",
        new="test-api-key-for-unit-tests",
    ), patch(
        "langchain_google_genai.ChatGoogleGenerativeAI",
        return_value=MagicMock(),
    ):
        app_module = importlib.import_module("app")

    return app_module


class TestStartupHealthCheck(unittest.TestCase):

    # -----------------------------------------------------------------------
    # Scenario 1: embed_query raises an exception whose str() contains
    # "API_KEY_INVALID" → api_key_valid must be False, /health → "degraded"
    # -----------------------------------------------------------------------
    def test_invalid_key_string_in_exception(self):
        bad_key_error = Exception(
            "400 INVALID_ARGUMENT. API_KEY_INVALID — API key not valid."
        )
        app_module = _reload_app_with_embed_side_effect(bad_key_error)

        self.assertFalse(
            app_module.api_key_valid,
            "api_key_valid should be False when embed_query raises API_KEY_INVALID",
        )

        client = app_module.app.test_client()
        response = client.get("/health")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["api_key_valid"])

    # -----------------------------------------------------------------------
    # Scenario 2: embed_query raises PermissionDenied → same outcome
    # -----------------------------------------------------------------------
    def test_permission_denied_exception(self):
        from google.api_core.exceptions import PermissionDenied

        app_module = _reload_app_with_embed_side_effect(
            PermissionDenied("403 Permission denied")
        )

        self.assertFalse(app_module.api_key_valid)

        client = app_module.app.test_client()
        response = client.get("/health")
        data = response.get_json()

        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["api_key_valid"])

    # -----------------------------------------------------------------------
    # Scenario 3: embed_query raises InvalidArgument → same outcome
    # -----------------------------------------------------------------------
    def test_invalid_argument_exception(self):
        from google.api_core.exceptions import InvalidArgument

        app_module = _reload_app_with_embed_side_effect(
            InvalidArgument("400 Invalid argument")
        )

        self.assertFalse(app_module.api_key_valid)

        client = app_module.app.test_client()
        response = client.get("/health")
        data = response.get_json()

        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["api_key_valid"])

    # -----------------------------------------------------------------------
    # Scenario 4: embed_query succeeds → api_key_valid must be True,
    # /health → "ok"
    # -----------------------------------------------------------------------
    def test_valid_key_success(self):
        app_module = _reload_app_with_embed_side_effect(None)  # no exception

        self.assertTrue(
            app_module.api_key_valid,
            "api_key_valid should be True when embed_query succeeds",
        )

        client = app_module.app.test_client()
        response = client.get("/health")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["api_key_valid"])

    # -----------------------------------------------------------------------
    # Scenario 5: transient network error (NOT API_KEY_INVALID) → warning,
    # server stays up, api_key_valid stays False (conservative default) but
    # /health still responds 200 (server is up, just uncertain about key)
    # -----------------------------------------------------------------------
    def test_transient_network_error_does_not_crash(self):
        transient_error = ConnectionError("Temporary network failure")
        app_module = _reload_app_with_embed_side_effect(transient_error)

        # Conservative: flag stays False on uncertain check
        self.assertFalse(app_module.api_key_valid)

        # But the server is still serving requests — /health responds 200
        client = app_module.app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)

    # -----------------------------------------------------------------------
    # Scenario 6: GOOGLE_API_KEY is empty → no network call, flag is False
    # -----------------------------------------------------------------------
    def test_empty_api_key_skips_network_call(self):
        for mod_name in list(sys.modules.keys()):
            if mod_name == "app" or mod_name.startswith("app."):
                del sys.modules[mod_name]

        mock_embeddings_cls = MagicMock()
        mock_llm_cls = MagicMock()

        with patch("config.Config.GOOGLE_API_KEY", ""), \
             patch("langchain_google_genai.GoogleGenerativeAIEmbeddings", mock_embeddings_cls), \
             patch("langchain_google_genai.ChatGoogleGenerativeAI", mock_llm_cls):
            app_module = importlib.import_module("app")

        # GoogleGenerativeAIEmbeddings must NOT have been instantiated
        # (the probe should have short-circuited before making the object)
        mock_embeddings_cls.assert_not_called()

        self.assertFalse(app_module.api_key_valid)

        client = app_module.app.test_client()
        response = client.get("/health")
        data = response.get_json()
        self.assertEqual(data["status"], "degraded")
        self.assertFalse(data["api_key_valid"])


if __name__ == "__main__":
    unittest.main()
