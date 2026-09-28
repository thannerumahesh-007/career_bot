"""
Unit tests for Job Matcher formula, TF-IDF semantic engine, skill gap, and ranking.
"""

import unittest
from recommender.matcher import JobMatcher
from recommender.ranking import JobRanker
from recommender.skill_gap import SkillGapAnalyzer


class TestMatchingEngine(unittest.TestCase):

    def setUp(self):
        self.matcher = JobMatcher()
        self.ranker = JobRanker()
        self.gap_analyzer = SkillGapAnalyzer()

    def test_skill_score_formula(self):
        # Job required: Python, SQL, Machine Learning, Pandas (4)
        # User skills: Python, SQL, Pandas (3)
        # Expected SkillScore = 3 / 4 = 0.75
        user_skills = ["Python", "SQL", "Pandas"]
        job_skills = ["Python", "SQL", "Machine Learning", "Pandas"]

        score, matching, missing = self.matcher.calculate_skill_score(user_skills, job_skills)
        self.assertAlmostEqual(score, 0.75, places=2)
        self.assertEqual(len(matching), 3)
        self.assertEqual(len(missing), 1)
        self.assertIn("Machine Learning", missing)

    def test_overall_match_score_weights(self):
        user_profile = {
            "skills": ["Python", "SQL", "Pandas"],
            "interests": ["Machine Learning"],
            "experience": "Fresher",
            "education": "B.Tech",
            "target_roles": ["Data Analyst"]
        }

        job = {
            "job_id": 1,
            "title": "Data Analyst",
            "company": "Data Corp",
            "location": "Hyderabad",
            "job_type": "Full-time",
            "experience": "Fresher",
            "skills": ["Python", "SQL", "Pandas", "Tableau"],
            "description": "Data Analyst with SQL and Python skills",
            "responsibilities": "Data cleaning and reporting",
            "salary": "₹5.5 LPA"
        }

        result = self.matcher.match_job(user_profile, job)

        self.assertIn("overall_score", result)
        self.assertGreaterEqual(result["overall_score"], 0.0)
        self.assertLessEqual(result["overall_score"], 1.0)
        self.assertEqual(result["match_percentage"], round(result["overall_score"] * 100, 1))

        # Check components
        comp = result["component_scores"]
        self.assertIn("skill_score", comp)
        self.assertIn("semantic_score", comp)
        self.assertIn("interest_score", comp)
        self.assertIn("experience_score", comp)

    def test_skill_gap_analysis(self):
        user_skills = ["Python", "SQL"]
        required_skills = ["Python", "SQL", "Machine Learning", "Docker", "AWS"]

        gap = self.gap_analyzer.analyze_gap(user_skills, required_skills)
        self.assertEqual(gap["match_count"], 2)
        self.assertEqual(gap["missing_count"], 3)
        self.assertIn("Docker", gap["missing_skills"])

    def test_no_strong_match_threshold(self):
        # User with irrelevant skills
        user_profile = {
            "skills": ["Cooking", "Drawing"],
            "interests": ["Music"],
            "experience": "Fresher",
            "target_roles": ["Artist"]
        }

        jobs = [{
            "job_id": 10,
            "title": "Senior Cloud Architect",
            "company": "CloudInc",
            "location": "Bangalore",
            "job_type": "Full-time",
            "experience": "5+ years",
            "skills": ["AWS", "Kubernetes", "Terraform", "Go"],
            "description": "Cloud infra deployment",
            "responsibilities": "Architect cloud solutions"
        }]

        ranked = self.ranker.rank_recommendations(user_profile, jobs)
        self.assertFalse(ranked["has_strong_match"])
        self.assertIn("No strong match found", ranked["message"])


if __name__ == "__main__":
    unittest.main()
