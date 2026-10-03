"""
Integration Tests for JARVIS Voice AI integrated into CareerBot.
Verifies:
- Conversational quality (direct answers, detailed explanations, context follow-ups)
- TTS cleaning (no markdown headers, code fences, or symbols in tts_text)
- ElevenLabs TTS endpoint (/api/tts)
- Conversation history preservation between CareerBot and JARVIS
- System health reporting
"""

import unittest
import json
from unittest.mock import patch, MagicMock
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base, ChatHistory
from services.career_service import CareerService
from services.text_cleaner import clean_text_for_tts
from services.elevenlabs_service import ElevenLabsService, DEFAULT_VOICE_ID


class TestJarvisCareerBotIntegration(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Create test user
        db = SessionLocal()
        user = User(full_name="Tony Stark", username="jarvis_user", email="tony@stark.io")
        user.set_password("SecurePassword123!")
        db.add(user)
        db.commit()
        self.user_id = user.id
        db.close()

        # Log in test user
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["username"] = "jarvis_user"
            sess["full_name"] = "Tony Stark"

    def test_text_cleaner_removes_all_markdown_and_symbols(self):
        """Verify clean_text_for_tts strips all markdown and prepares spoken text."""
        raw_input = (
            "### 1. Introduction to Machine Learning\n"
            "Machine learning is **truly** transformative.\n"
            "```python\nprint('hello')\n```\n"
            "Check `sklearn` for *algorithms*.\n"
            "* Supervised\n* Unsupervised\n"
            "[Documentation](https://scikit-learn.org)"
        )
        cleaned = clean_text_for_tts(raw_input)
        for sym in ["###", "##", "# ", "**", "*", "`", "```", "[", "]", "(https:"]:
            self.assertNotIn(sym, cleaned, f"Symbol {sym} was not cleaned from TTS text")
        self.assertIn("First,", cleaned)
        self.assertIn("Machine learning is truly transformative", cleaned)

    def test_elevenlabs_voice_configuration(self):
        """Verify ElevenLabs uses accessible voice ID and not the restricted voice."""
        service = ElevenLabsService()
        voice_id = service._get_voice_id()
        self.assertNotEqual(voice_id, "wWWn96OtTHu1sn8SRGEr", "Must not use the restricted voice library ID")
        self.assertEqual(voice_id, DEFAULT_VOICE_ID)

    def test_elevenlabs_tts_authenticated_endpoint(self):
        """Verify /api/tts converts cleaned text to audio/mpeg binary."""
        dummy_audio = b"\xff\xfb\x90\x44\x00\x00\x00\x00" * 200

        with patch("services.elevenlabs_service.elevenlabs_service.text_to_speech") as mock_tts:
            mock_tts.return_value = (dummy_audio, "audio/mpeg", None)

            res = self.client.post('/api/tts', json={"text": "All systems operational, sir."})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("Content-Type"), "audio/mpeg")
            self.assertEqual(res.data, dummy_audio)

    def test_api_chat_returns_tts_text_and_preserves_history(self):
        """Verify /api/chat returns response and clean tts_text, saving both in ChatHistory."""
        payload = {"message": "What is machine learning?"}
        res = self.client.post('/api/chat', json=payload)
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.data)
        self.assertTrue(data.get("success"))
        self.assertIn("response", data)
        self.assertIn("tts_text", data)

        # Verify no markdown headers or fences in tts_text
        for sym in ["###", "##", "# ", "```", "**"]:
            self.assertNotIn(sym, data["tts_text"])

        # Verify database history records
        db = SessionLocal()
        records = db.query(ChatHistory).filter_by(user_id=self.user_id).order_by(ChatHistory.created_at.asc()).all()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].sender, "user")
        self.assertEqual(records[0].message, "What is machine learning?")
        self.assertEqual(records[1].sender, "bot")
        db.close()

    def test_conversational_follow_up_context(self):
        """Verify follow-up 'Explain that in detail' resolves to previous subject."""
        career_service = CareerService()
        db = SessionLocal()

        # Turn 1: What is machine learning?
        res1 = career_service.process_chat_message(db, self.user_id, "What is machine learning?")
        self.assertTrue(res1.get("success"))

        # Turn 2: Explain that in detail.
        res2 = career_service.process_chat_message(db, self.user_id, "Explain that in detail.")
        self.assertTrue(res2.get("success"))

        reply_2 = res2.get("response", "").lower()
        # Must understand 'that' is machine learning
        self.assertTrue(
            "machine learning" in reply_2 or "supervised" in reply_2 or "algorithm" in reply_2 or "data" in reply_2 or "learning" in reply_2,
            f"Follow-up context lost. Got: {reply_2[:200]}"
        )

        # Verify 4 history entries in database
        records = db.query(ChatHistory).filter_by(user_id=self.user_id).order_by(ChatHistory.created_at.asc()).all()
        self.assertEqual(len(records), 4)
        db.close()

    def test_system_health_reports_jarvis_and_elevenlabs(self):
        """Verify /api/health includes ElevenLabs and JARVIS status."""
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("jarvis", data)
        self.assertEqual(data["jarvis"], "ready")
        self.assertIn("elevenlabs_configured", data)


if __name__ == "__main__":
    unittest.main()
