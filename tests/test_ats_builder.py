"""
Tests for ATS Resume Builder, Target Job Description Optimization, and PDF Generation.
"""

import unittest
import json
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base, ResumeDraft
from services.ats_service import ats_service


class TestATSResumeBuilder(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Seed authenticated test user
        db = SessionLocal()
        user = User(full_name="Ada Lovelace", username="adalovelace", email="ada@lovelace.io")
        user.set_password("SecurePass123!")
        db.add(user)
        db.commit()
        self.user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["username"] = "adalovelace"
            sess["full_name"] = "Ada Lovelace"

    def test_ats_score_calculation_breakdown(self):
        """Verify deterministic 5-criteria ATS score calculation."""
        sample_resume = {
            "title": "Data Analyst Resume",
            "target_role": "Data Analyst",
            "contact_info": {
                "full_name": "Ada Lovelace",
                "email": "ada@lovelace.io",
                "phone": "+91 99999 88888",
                "location": "Bangalore, India",
                "linkedin": "linkedin.com/in/ada",
                "github": "github.com/ada"
            },
            "summary": "Results-driven Data Analyst with experience in SQL, Python, Excel, and Power BI dashboards.",
            "sections": [
                {
                    "heading": "Technical Skills",
                    "type": "skills",
                    "content": "SQL, Python, Excel, Power BI, Tableau, Pandas, NumPy, Statistics"
                },
                {
                    "heading": "Work Experience",
                    "type": "experience",
                    "items": [
                        {
                            "title": "Junior Data Analyst",
                            "organization": "Analytics Corp",
                            "period": "2023 - Present",
                            "bullets": [
                                "Analyzed business performance metrics using SQL and Power BI dashboards.",
                                "Reduced data reporting processing time by 30% through automated Python scripts."
                            ]
                        }
                    ]
                },
                {
                    "heading": "Education",
                    "type": "education",
                    "items": [
                        {
                            "title": "Bachelor of Technology",
                            "organization": "Engineering College",
                            "period": "2023",
                            "bullets": ["Coursework: Data Analytics, Statistics, DBMS"]
                        }
                    ]
                }
            ]
        }

        job_desc = (
            "Looking for a Data Analyst proficient in SQL, Python, Excel, Power BI, and data cleaning. "
            "Responsible for building KPI dashboards, interpreting metric variances, and collaborating with cross-functional teams."
        )

        res = ats_service.calculate_ats_score(sample_resume, target_job_description=job_desc)
        self.assertIn("overall_score", res)
        self.assertIn("subscores", res)
        self.assertIn("matching_keywords", res)
        self.assertTrue(0 <= res["overall_score"] <= 100)
        self.assertTrue(res["overall_score"] >= 65, f"Expected strong match >= 65, got {res['overall_score']}")

        sub = res["subscores"]
        self.assertIn("keyword_coverage", sub)
        self.assertIn("skills_coverage", sub)
        self.assertIn("section_completeness", sub)
        self.assertIn("role_relevance", sub)
        self.assertIn("action_verbs_formatting", sub)

    def test_bullet_point_enhancement(self):
        """Verify bullet point enhancement injects action verbs and quantifiable structure."""
        simple_bullet = "worked on database queries and made reports"
        enhanced = ats_service.enhance_bullet_point(simple_bullet, target_role="Data Analyst")
        self.assertTrue(len(enhanced) > len(simple_bullet))
        # Ensure it starts with capitalized action verb
        first_word = enhanced.split()[0].replace("•", "").strip()
        self.assertTrue(first_word[0].isupper())

    def test_single_column_ats_pdf_generation(self):
        """Verify PDF export outputs valid PDF byte stream with %PDF- header."""
        sample_draft = {
            "target_role": "Data Analyst",
            "contact_info": {
                "full_name": "Ada Lovelace",
                "email": "ada@lovelace.io",
                "phone": "+91 99999 88888",
                "location": "Bangalore, India",
                "linkedin": "linkedin.com/in/ada"
            },
            "summary": "Proven Data Analyst skilled in SQL and Python.",
            "sections": [
                {
                    "heading": "Technical Skills",
                    "type": "skills",
                    "content": "SQL, Python, Tableau, Excel"
                }
            ]
        }

        pdf_bytes = ats_service.generate_ats_pdf(sample_draft)
        self.assertTrue(isinstance(pdf_bytes, bytes))
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"), "Generated file must be a valid PDF document")

    def test_resume_builder_api_endpoints(self):
        """Verify resume builder get, save, and download endpoints."""
        # 1. Get initial draft
        get_res = self.client.get('/api/resume/builder/draft')
        self.assertEqual(get_res.status_code, 200)
        draft_data = get_res.get_json()["draft"]
        self.assertIn("target_role", draft_data)

        # 2. Save draft
        draft_data["summary"] = "Experienced engineer specialized in high throughput systems."
        save_res = self.client.post('/api/resume/builder/save', json=draft_data)
        self.assertEqual(save_res.status_code, 200)
        saved_json = save_res.get_json()
        self.assertEqual(saved_json["status"], "success")

        # 3. Download PDF
        pdf_res = self.client.get('/api/resume/builder/pdf')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, "application/pdf")
        self.assertTrue(pdf_res.data.startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
