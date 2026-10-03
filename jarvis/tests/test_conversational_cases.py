import time
import unittest
import requests
from services.text_cleaner import clean_text_for_tts

BASE_URL = "http://127.0.0.1:5000"

class TestJarvisCases(unittest.TestCase):
    def setUp(self):
        # Allow small pause between API calls to avoid rate limits
        time.sleep(1.5)

    def test_case_a_what_is_machine_learning(self):
        """Case A: Direct explanation of machine learning."""
        payload = {"message": "What is machine learning?", "history": []}
        resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=25)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), f"Chat API failed: {data}")
        text = data.get("response", "")
        tts = data.get("tts_text", "")

        # Verify direct answer
        lower = text.lower()
        self.assertTrue(
            "machine learning" in lower or "algorithms" in lower or "data" in lower or "learn" in lower,
            f"Expected direct explanation of ML, got: {text[:200]}"
        )
        # Verify no excessive markdown
        for symbol in ["###", "##", "# ", "**", "```"]:
            self.assertNotIn(symbol, tts, f"Symbol {symbol} found in TTS text")
        print("\n[Case A Passed]")
        print("Response sample:", text[:180], "...")
        print("TTS sample:", tts[:180], "...")

    def test_case_b_detailed_explanation(self):
        """Case B: Detailed explanation must be substantially detailed."""
        payload = {"message": "Give me a detailed explanation of machine learning.", "history": []}
        resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), f"Chat API failed: {data}")
        text = data.get("response", "")
        tts = data.get("tts_text", "")

        # Detailed answer should have multiple sentences and substantial length
        word_count = len(text.split())
        self.assertGreaterEqual(
            word_count, 80,
            f"Expected detailed answer with >= 80 words, got {word_count} words"
        )
        # Verify no markdown formatting symbols in TTS text
        for symbol in ["###", "##", "# ", "**", "*", "```", "~~"]:
            self.assertNotIn(symbol, tts)
        print("\n[Case B Passed]")
        print(f"Word count: {word_count}")
        print("Response sample:", text[:200], "...")

    def test_case_c_why_is_python_used(self):
        """Case C: Specifically answers Python's role in ML."""
        payload = {"message": "Why is Python used for machine learning?", "history": []}
        resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=25)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), f"Chat API failed: {data}")
        text = data.get("response", "")
        tts = data.get("tts_text", "")

        lower = text.lower()
        self.assertTrue(
            "python" in lower and ("librar" in lower or "syntax" in lower or "ecosystem" in lower or "framework" in lower or "simple" in lower),
            f"Expected explanation of Python in ML, got: {text[:200]}"
        )
        print("\n[Case C Passed]")
        print("Response sample:", text[:180], "...")

    def test_case_d_contextual_follow_up(self):
        """Case D: Explain previous answer in simple terms preserves context."""
        history = [
            {"role": "user", "content": "Why is Python used for machine learning?"},
            {
                "role": "assistant",
                "content": "Python is the primary language for machine learning due to its simple syntax, extensive ecosystem of specialized libraries like NumPy, Pandas, Scikit-learn, TensorFlow, and PyTorch, and a massive community providing support and prebuilt models."
            }
        ]
        payload = {"message": "Explain the previous answer in simple terms.", "history": history}
        resp = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=25)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("success"), f"Chat API failed: {data}")
        text = data.get("response", "")
        lower = text.lower()

        # Must recognize it is about Python and machine learning or libraries
        self.assertTrue(
            "python" in lower or "tool" in lower or "library" in lower or "easy" in lower or "lego" in lower,
            f"Context not maintained. Got: {text[:200]}"
        )
        print("\n[Case D Passed]")
        print("Response sample:", text[:180], "...")

    def test_case_e_no_excessive_markdown(self):
        """Case E: Displayed response contains no raw markdown headers or symbols."""
        test_inputs = [
            "What are three key principles of clean code?",
            "List the main steps in data science.",
        ]
        for msg in test_inputs:
            time.sleep(1.5)
            resp = requests.post(f"{BASE_URL}/api/chat", json={"message": msg, "history": []}, timeout=25)
            data = resp.json()
            disp = data.get("response", "")
            self.assertFalse(disp.startswith("#"), f"Response starts with markdown header: {disp[:50]}")
            self.assertNotIn("###", disp)
            self.assertNotIn("```", disp)
        print("\n[Case E Passed]")

    def test_case_f_tts_cleanliness_and_elevenlabs(self):
        """Case F: Verify TTS text has no symbols and ElevenLabs synthesizes clean audio."""
        dirty_input = "### 1. Python Basics\nHere is **bold** text and `code snippet` with [Link](https://python.org).\n* Item 1\n* Item 2"
        clean = clean_text_for_tts(dirty_input)
        for sym in ["###", "**", "`", "[", "]", "(https:", "*"]:
            self.assertNotIn(sym, clean, f"Found {sym} in cleaned text: {clean}")

        # Send a short clean message to /api/tts to verify ElevenLabs audio generation
        tts_payload = {"text": "Greetings, sir. JARVIS voice systems are functioning normally."}
        tts_resp = requests.post(f"{BASE_URL}/api/tts", json=tts_payload, timeout=25)
        self.assertEqual(tts_resp.status_code, 200)
        self.assertEqual(tts_resp.headers.get("Content-Type"), "audio/mpeg")
        self.assertGreater(len(tts_resp.content), 2000)
        print("\n[Case F Passed] TTS Audio generated successfully, size:", len(tts_resp.content), "bytes")

if __name__ == "__main__":
    unittest.main()
