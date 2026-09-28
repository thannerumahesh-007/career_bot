"""
Unit tests for NLP preprocessing, skill extraction, normalization, and intent detection.
"""

import unittest
from nlp.preprocessing import clean_text, tokenize, remove_stopwords, preprocess_text
from nlp.skill_dictionary import normalize_skill, normalize_skill_key, normalize_skill_list
from nlp.skill_extractor import SkillExtractor
from nlp.intent_classifier import IntentClassifier, STANDARD_INTENTS
from nlp.job_analyzer import JobAnalyzer


class TestNLPModules(unittest.TestCase):

    def setUp(self):
        self.extractor = SkillExtractor()
        self.intent_classifier = IntentClassifier()
        self.job_analyzer = JobAnalyzer()

    def test_text_preprocessing(self):
        text = "I am learning Python & Machine Learning!"
        clean = clean_text(text)
        self.assertIn("Python", clean)
        processed = preprocess_text(text)
        self.assertIn("python", processed)

    def test_skill_normalization(self):
        # Verify alias conversions
        self.assertEqual(normalize_skill_key("ML"), "machine learning")
        self.assertEqual(normalize_skill_key("JS"), "javascript")
        self.assertEqual(normalize_skill_key("Postgres"), "postgresql")
        self.assertEqual(normalize_skill_key("PyTorch"), "pytorch")

        # Verify display conversion
        self.assertEqual(normalize_skill("ml"), "Machine Learning")
        self.assertEqual(normalize_skill("js"), "JavaScript")

        # List normalization
        raw_list = ["ML", "machine learning", "Python", "JS", "JavaScript"]
        normalized = normalize_skill_list(raw_list)
        self.assertEqual(len(normalized), 3)
        self.assertIn("Machine Learning", normalized)
        self.assertIn("Python", normalized)
        self.assertIn("JavaScript", normalized)

    def test_skill_extraction(self):
        text = "I know Python, SQL and basic machine learning. I'm also interested in NLP and data science."
        data = self.extractor.extract_profile_data(text)

        skills = data["skills"]
        self.assertIn("Python", skills)
        self.assertIn("SQL", skills)
        self.assertIn("Machine Learning", skills)

        interests = data["interests"]
        self.assertTrue(any("NLP" in i or "Data Science" in i for i in interests))

    def test_intent_detection(self):
        test_cases = [
            ("Hello", "greeting"),
            ("Find Python developer jobs", "job_search"),
            ("What skills am I missing?", "skill_gap"),
            ("How can I become a data scientist?", "career_advice"),
            ("Give me a roadmap for machine learning", "learning_roadmap"),
            ("Analyze my resume", "resume_analysis"),
            ("Show details of job 12", "job_details"),
            ("I know Python and SQL", "profile_update"),
            ("What is NLP?", "general_career_question"),
            ("How do I use this website?", "help"),
            ("Something completely random xzy123", "unknown")
        ]

        for msg, expected_intent in test_cases:
            detected = self.intent_classifier.classify_intent(msg)
            self.assertEqual(detected, expected_intent, f"Failed for msg: '{msg}'. Expected {expected_intent}, got {detected}")
            self.assertIn(detected, STANDARD_INTENTS)

    def test_job_analysis(self):
        job_raw = {
            "job_id": 99,
            "title": "Backend Python Developer",
            "company": "Tech Corp",
            "skills": "Python, SQL, Django, PostgreSQL",
            "description": "Looking for Django developer.",
            "responsibilities": "Write REST APIs."
        }

        analyzed = self.job_analyzer.analyze_job(job_raw)
        self.assertEqual(analyzed["job_id"], 99)
        self.assertIn("Python", analyzed["required_skills"])
        self.assertIn("SQL", analyzed["required_skills"])
        self.assertIn("Django", analyzed["required_skills"])


if __name__ == "__main__":
    unittest.main()
