import os
import unittest
from unittest.mock import patch, MagicMock
from services.gemini_service import GeminiService, JARVIS_SYSTEM_INSTRUCTION
from services.elevenlabs_service import ElevenLabsService
from app import app


class TestJarvisVoiceAI(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_gemini_service_initialization(self):
        service = GeminiService()
        self.assertTrue(hasattr(service, "model_name"))
        self.assertIn("JARVIS", JARVIS_SYSTEM_INSTRUCTION)
        self.assertIn("conversational", JARVIS_SYSTEM_INSTRUCTION)

    def test_gemini_missing_key_graceful_handling(self):
        service = GeminiService()
        with patch.object(service, "is_configured", return_value=False):
            resp, success = service.generate_response("Hello")
            self.assertFalse(success)
            self.assertIn("missing", resp.lower())

    def test_gemini_conversational_history_flow(self):
        service = GeminiService()
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "I suggest going for a brisk walk or learning something new."
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(service, "is_configured", return_value=True), \
             patch.object(service, "_get_client", return_value=mock_client):

            history = [
                {"role": "user", "content": "I'm bored today."},
                {"role": "assistant", "content": "I can keep you company. We can talk about something you're interested in, or I can suggest something to do."}
            ]

            reply, success = service.generate_response("What do you suggest?", history)
            self.assertTrue(success)
            self.assertEqual(reply, "I suggest going for a brisk walk or learning something new.")

            # Verify that client was called with all turns in contents
            call_kwargs = mock_client.models.generate_content.call_args[1]
            contents = call_kwargs["contents"]
            self.assertEqual(len(contents), 3)  # 2 history turns + 1 new message
            self.assertEqual(contents[0].role, "user")
            self.assertEqual(contents[1].role, "model")
            self.assertEqual(contents[2].role, "user")

    def test_elevenlabs_missing_key_graceful_handling(self):
        service = ElevenLabsService()
        with patch.object(service, "is_configured", return_value=False):
            audio, ctype, error = service.text_to_speech("Test speech")
            self.assertIsNone(audio)
            self.assertIn("not configured", error.lower())

    def test_elevenlabs_successful_audio_synthesis(self):
        service = ElevenLabsService()
        dummy_audio = b"\xff\xfb\x90\x44"  # Mock MP3 frame

        with patch.object(service, "is_configured", return_value=True), \
             patch("requests.post") as mock_post:

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = dummy_audio
            mock_post.return_value = mock_resp

            audio, ctype, error = service.text_to_speech("All systems operational.")
            self.assertEqual(audio, dummy_audio)
            self.assertEqual(ctype, "audio/mpeg")
            self.assertIsNone(error)

    def test_api_chat_history_preservation(self):
        with patch("services.gemini_service.gemini_service.generate_response") as mock_gen:
            mock_gen.return_value = ("I can suggest several activities, sir.", True)

            initial_history = [
                {"role": "user", "content": "I'm bored today."},
                {"role": "assistant", "content": "I can keep you company."}
            ]

            res = self.app.post("/api/chat", json={
                "message": "What do you suggest?",
                "history": initial_history
            })

            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertEqual(len(data["history"]), 4)  # 2 previous + 2 new
            self.assertEqual(data["history"][-2]["content"], "What do you suggest?")
            self.assertEqual(data["history"][-1]["content"], "I can suggest several activities, sir.")

    def test_clean_text_for_tts(self):
        from services.text_cleaner import clean_text_for_tts
        sample_md = "### Introduction\n**Python** is great for *machine learning*:\n1. Simple syntax\n2. Huge community\n- Fast prototyping\nVisit [site](https://python.org)."
        cleaned = clean_text_for_tts(sample_md)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("#", cleaned)
        self.assertNotIn("https", cleaned)
        self.assertIn("First, Simple syntax", cleaned)
        self.assertIn("Second, Huge community", cleaned)

    def test_api_chat_returns_tts_text(self):
        with patch("services.gemini_service.gemini_service.generate_response") as mock_gen:
            mock_gen.return_value = ("**Machine learning** is an application of AI.", True)
            res = self.app.post("/api/chat", json={"message": "What is ML?"})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("tts_text", data)
            self.assertEqual(data["tts_text"], "Machine learning is an application of AI.")


if __name__ == "__main__":
    unittest.main()
