"""
End-to-End Integration Test for complete CareerBot Adzuna Flow:
Resume/Profile -> Job Preferences -> Live Job Search -> Matching -> Job Details -> Apply URL
"""

import unittest
import json
import io
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Resume, Base
from services.career_service import CareerService
from config import Config


class TestAdzunaEndToEndFlow(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Create user
        db = SessionLocal()
        user = User(full_name="Alex Mercer", username="alexmercer", email="alex@example.com")
        user.set_password("StrongPassword123!")
        db.add(user)
        db.commit()
        db.refresh(user)

        career_service = CareerService()
        career_service.get_or_create_user_profile(db, user.id)
        self.user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'alexmercer'

    def test_complete_adzuna_career_flow(self):
        # Step 1: Update Job Preferences & Profile
        profile_res = self.client.post('/profile', data={
            "full_name": "Alex Mercer",
            "education": "B.Tech in Artificial Intelligence",
            "experience": "1 year software intern",
            "skills": "Python, Machine Learning, SQL, Pandas",
            "interests": "AI, Data Science",
            "target_roles": "Data Scientist, Machine Learning Engineer"
        }, follow_redirects=True)
        self.assertEqual(profile_res.status_code, 200)

        # Step 2: Upload Resume
        sample_resume_content = (
            "Alex Mercer - AI & Data Science Candidate\n"
            "Email: alex@example.com\n\n"
            "Technical Skills: Python, SQL, Machine Learning, Deep Learning, PyTorch, Pandas, Scikit-Learn\n"
            "Education: Bachelor of Technology in Computer Science\n"
            "Experience: Built NLP and machine learning pipelines for automated recommendation."
        )
        data = {
            'resume_file': (io.BytesIO(sample_resume_content.encode('utf-8')), 'alex_resume.txt')
        }
        upload_res = self.client.post('/resume', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(upload_res.status_code, 200)

        # Verify resume recorded
        db = SessionLocal()
        resume_record = db.query(Resume).filter_by(user_id=self.user_id).first()
        self.assertIsNotNone(resume_record)
        db.close()

        # Step 3: Query Live Adzuna Jobs via Backend API Route
        live_api_res = self.client.get('/api/jobs/live?role=Data+Scientist&location=India&combine=true')
        self.assertEqual(live_api_res.status_code, 200)
        api_data = live_api_res.get_json()
        self.assertEqual(api_data["status"], "success")
        self.assertTrue(api_data["total_jobs"] > 0)
        self.assertTrue(api_data["has_resume"])

        # Check source breakdown exists and contains both live and database
        sources = api_data.get("source_breakdown", {})
        self.assertIn("live_jobs", sources)
        self.assertIn("careerbot_database", sources)

        # Verify matched jobs have score calculated
        jobs = api_data.get("jobs", [])
        self.assertTrue(len(jobs) > 0)
        first_job = jobs[0]
        self.assertIn("match_percentage", first_job)
        self.assertIn("matching_skills", first_job)
        self.assertIn("source", first_job)

        # Step 4: Visit Job Recommendations Catalog UI (/jobs?tab=live)
        jobs_ui_res = self.client.get('/jobs?tab=live')
        self.assertEqual(jobs_ui_res.status_code, 200)
        # Verify page renders live tab and job cards
        self.assertIn(b"Job Catalog & Live Matching", jobs_ui_res.data)
        self.assertIn(b"Live Internet Jobs", jobs_ui_res.data)

        # Step 5: Check Job Details Page & Apply URL
        job_id = first_job["job_id"]
        detail_res = self.client.get(f'/jobs/{job_id}')
        self.assertEqual(detail_res.status_code, 200)
        self.assertIn(b"Match Formula Breakdown", detail_res.data)

        # If job has external application URL, verify Apply Now button exists with target="_blank"
        if first_job.get("url") and first_job["url"].startswith("http"):
            self.assertIn(b"Apply Now", detail_res.data)
            self.assertIn(b'target="_blank"', detail_res.data)
            self.assertIn(b'rel="noopener noreferrer"', detail_res.data)
            base_url = first_job["url"].split('?')[0].encode('utf-8')
            self.assertIn(base_url, detail_res.data)
