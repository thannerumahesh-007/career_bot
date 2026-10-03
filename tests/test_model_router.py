"""
Tests for Centralized Gemini Model Router & Fallback System.
Verifies:
- Task-based candidate pool routing
- 429 / quota exhaustion fallback to secondary models
- Error classification (AUTHENTICATION_ERROR, RATE_LIMIT_ERROR, MODEL_NOT_FOUND, etc.)
- Halting Gemini retry chain immediately on AUTHENTICATION_ERROR (no redundant retries)
- Safe diagnostics and masking without secret exposure
"""

import unittest
from unittest.mock import patch, MagicMock
from services.model_router import ModelRouter, TASK_MODEL_POOLS, ErrorCategory


class TestGeminiModelRouter(unittest.TestCase):

    def setUp(self):
        self.router = ModelRouter()

    def test_task_model_pools_defined(self):
        """Verify that all core task candidate pools exist."""
        for task in ["chat", "resume", "interview", "news", "job_summary"]:
            self.assertIn(task, TASK_MODEL_POOLS)
            self.assertTrue(len(TASK_MODEL_POOLS[task]) >= 2)

    def test_api_key_is_never_logged_or_exposed(self):
        """Ensure secret keys are masked in router logs and debug representations."""
        secret = "AIzaSySecretApiKey123456789"
        masked = self.router._mask_key(secret)
        self.assertNotIn("SecretApiKey", masked)
        self.assertTrue(masked.startswith("AIza") and masked.endswith("6789"))

    def test_key_info_is_safe(self):
        """Ensure get_key_info exposes only boolean and length, never raw key."""
        info = self.router.get_key_info()
        self.assertIn("loaded", info)
        self.assertIn("source", info)
        self.assertIn("length", info)
        self.assertNotIn("key", info)
        self.assertNotIn("api_key", info)

    def test_error_classification(self):
        """Verify proper classification into standard categories."""
        auth_err = Exception("400 INVALID_ARGUMENT: API key not valid. Please pass a valid API key.")
        self.assertEqual(self.router.classify_error(auth_err), ErrorCategory.AUTHENTICATION_ERROR)

        auth_401 = Exception("401 Unauthorized: Invalid credentials")
        self.assertEqual(self.router.classify_error(auth_401), ErrorCategory.AUTHENTICATION_ERROR)

        quota_err = Exception("429 RESOURCE_EXHAUSTED Quota exceeded for model")
        self.assertEqual(self.router.classify_error(quota_err), ErrorCategory.RATE_LIMIT_ERROR)

        not_found_err = Exception("404 NOT_FOUND: This model is no longer available.")
        self.assertEqual(self.router.classify_error(not_found_err), ErrorCategory.MODEL_NOT_FOUND)

        temp_err = Exception("503 UNAVAILABLE: Model is overloaded.")
        self.assertEqual(self.router.classify_error(temp_err), ErrorCategory.TEMPORARY_ERROR)

        net_err = Exception("ConnectionResetError: Connection lost to host")
        self.assertEqual(self.router.classify_error(net_err), ErrorCategory.NETWORK_ERROR)

    @patch("services.model_router.genai.Client")
    def test_successful_model_call(self, mock_client_cls):
        """Verify model router succeeds when primary model responds."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a high quality response from Gemini."
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        router = ModelRouter(api_key="AIzaSyTestValidFakeKey123456789012345")
        result = router.generate_content(
            task="chat",
            prompt="Hello there",
            system_instruction="Be helpful"
        )
        self.assertEqual(result, "This is a high quality response from Gemini.")
        self.assertEqual(router.last_status["status"], "success")
        self.assertEqual(router.last_status["provider"], "gemini")

    @patch("services.model_router.genai.Client")
    def test_quota_exhaustion_fallback_sequence(self, mock_client_cls):
        """Verify router catches 429 quota exhaustion and falls back to secondary model."""
        mock_client = MagicMock()

        # Simulate 429 error on first model, success on second model
        error_429 = Exception("429 RESOURCE_EXHAUSTED Quota exceeded for model gemini-3.5-flash")
        success_response = MagicMock()
        success_response.text = "Fallback model success response."

        mock_client.models.generate_content.side_effect = [error_429, success_response]
        mock_client_cls.return_value = mock_client

        router = ModelRouter(api_key="AIzaSyTestValidFakeKey123456789012345")
        result = router.generate_content(
            task="interview",
            prompt="Generate 5 questions"
        )
        self.assertEqual(result, "Fallback model success response.")
        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        self.assertEqual(router.last_status["status"], "success")

    @patch("services.model_router.genai.Client")
    def test_authentication_error_aborts_retry_chain(self, mock_client_cls):
        """
        Verify that 400 'API key not valid' stops the retry chain immediately.
        It must NOT retry across all fallback models using the same invalid credential.
        """
        mock_client = MagicMock()
        auth_error = Exception("400 INVALID_ARGUMENT: API key not valid. Please pass a valid API key.")
        mock_client.models.generate_content.side_effect = auth_error
        mock_client_cls.return_value = mock_client

        router = ModelRouter(api_key="AIzaSyInvalidKey1234567890123456789")
        result = router.generate_content(
            task="chat",
            prompt="Hello"
        )
        # Result must be None to trigger local fallback
        self.assertIsNone(result)
        # CRITICAL: call_count must be exactly 1, NOT 4 or 5!
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertEqual(router.last_status["status"], "failed")
        self.assertEqual(router.last_status["error_type"], "authentication_error")
        self.assertEqual(router.last_status["provider"], "local_fallback")

    @patch("services.model_router.genai.Client")
    def test_diagnostic_connection_test(self, mock_client_cls):
        """Verify test_connection returns safe diagnostic information."""
        mock_client = MagicMock()
        mock_res = MagicMock()
        mock_res.text = "pong"
        mock_client.models.generate_content.return_value = mock_res
        mock_client_cls.return_value = mock_client

        router = ModelRouter(api_key="AIzaSyTestValidFakeKey123456789012345")
        diag = router.test_connection()
        self.assertTrue(diag["success"])
        self.assertTrue(diag["api_key_loaded"])
        self.assertTrue(diag["model_accessible"])
        self.assertNotIn("AIzaSy", str(diag))


if __name__ == "__main__":
    unittest.main()
