"""
Tests for Canonical Role Knowledge Base, Response Cleaning, and Multilingual Configurations.
"""

import unittest
from services.career_knowledge import CAREER_ROLES, get_role_details, extract_role_from_text
from services.text_cleaner import clean_chat_response, clean_text_for_tts
from services.language_config import SUPPORTED_LANGUAGES, get_language_config, get_ai_instruction
from services.gemini_service import GeminiService


class TestCareerKnowledgeAndCleaning(unittest.TestCase):

    def test_canonical_roles_exist_with_complete_schemas(self):
        """Verify core 12 roles have title, required_skills, certifications, and interview topics."""
        for role_key in [
            "data analyst", "java developer", "python developer", "machine learning engineer",
            "data scientist", "frontend developer", "backend developer", "full stack developer",
            "devops engineer", "cloud engineer", "nlp engineer", "software engineer"
        ]:
            self.assertIn(role_key, CAREER_ROLES)
            details = get_role_details(role_key)
            self.assertTrue(len(details["required_skills"]) >= 5)
            self.assertTrue(len(details["certifications"]) >= 2)
            self.assertTrue(len(details["interview_topics"]) >= 2)

    def test_data_analyst_skills_extraction_accuracy(self):
        """Ensure queries for Data Analyst return Data Analyst skills and NOT software engineering."""
        detected = extract_role_from_text("What skills do I need for data analyst?")
        self.assertEqual(detected, "data analyst")

        role_info = get_role_details(detected)
        self.assertEqual(role_info["title"], "Data Analyst")
        skills_lower = [s.lower() for s in role_info["required_skills"]]
        self.assertTrue(any("sql" in s for s in skills_lower))
        self.assertTrue(any("excel" in s for s in skills_lower))
        self.assertTrue(any("power bi" in s or "visualization" in s for s in skills_lower))

    def test_clean_chat_response_removes_markdown_artifacts(self):
        """Verify chat cleaner strips raw ###, **, \\*, and preserves clean bullet structure."""
        messy = "### Technical Requirements:\n**1. Python** and \\*SQL\\* are essential.\n• Clean bullet point."
        cleaned = clean_chat_response(messy)

        self.assertNotIn("###", cleaned)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("\\*", cleaned)
        self.assertIn("Python and SQL are essential", cleaned)
        self.assertIn("• Clean bullet point", cleaned)

    def test_clean_text_for_tts_spoken_readiness(self):
        """Verify text cleaner for TTS prepares clean spoken sentences without symbols."""
        raw = "• SQL\n• Python 3.10\nVisit [Docs](https://example.com) for details."
        tts = clean_text_for_tts(raw)
        for bad in ["[", "]", "(https:", "•"]:
            self.assertNotIn(bad, tts)

    def test_multilingual_language_config_coverage(self):
        """Verify all 6 languages have valid recognition and TTS config."""
        for code in ["en-IN", "en-US", "hi-IN", "te-IN", "ta-IN", "kn-IN", "ml-IN"]:
            self.assertIn(code, SUPPORTED_LANGUAGES)
            cfg = get_language_config(code)
            self.assertIn("name", cfg)
            self.assertIn("native_name", cfg)
            self.assertIn("tts_lang", cfg)
            instr = get_ai_instruction(code)
            self.assertTrue(len(instr) > 20)

    def test_gemini_fallback_data_analyst_response(self):
        """Verify fallback response for Data Analyst query returns actual Data Analyst skills."""
        service = GeminiService()
        profile = {"skills": [], "target_roles": ["Data Analyst"]}
        reply = service.generate_fallback_response(
            intent="career_skill_requirements",
            message="What skills do I need for data analyst?",
            profile=profile
        )
        self.assertIn("Data Analyst", reply)
        self.assertIn("SQL", reply)
        self.assertIn("Excel", reply)
        self.assertNotIn("Spring Boot", reply)


if __name__ == "__main__":
    unittest.main()
