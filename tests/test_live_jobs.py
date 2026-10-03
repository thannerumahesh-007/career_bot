"""
Tests for Live Internet Job Search, CombinedJobProvider, Deduplication, and Source Badges.
"""

import unittest
from unittest.mock import patch, MagicMock
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base
from services.career_service import CareerService
from services.job_service import LiveJobSearchService, CombinedJobProvider


class TestLiveJobsAndCombinedProvider(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        Base.metadata.drop_all(bind=engine)
        init_db()

        db = SessionLocal()
        user = User(full_name="Job Tester", username="jobtester", email="jobtester@example.com")
        user.set_password("SecurePass123!")
        db.add(user)
        db.commit()
        db.refresh(user)

        career_service = CareerService()
        career_service.get_or_create_user_profile(db, user.id)
        self.user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['username'] = 'jobtester'

    def test_live_job_search_service_filtering(self):
        service = LiveJobSearchService()
        sample_jobs = [
            {
                "job_id": 20001,
                "title": "Machine Learning Engineer",
                "company": "Tech Corp AI",
                "location": "Remote",
                "work_mode": "Remote",
                "job_type": "Full-time",
                "experience": "2+ years",
                "skills": "Python, PyTorch, Docker",
                "description": "Looking for Machine Learning Engineer with Python experience.",
                "source": "Live (Arbeitnow)",
                "is_live": True,
                "url": "https://example.com/apply/1"
            },
            {
                "job_id": 20002,
                "title": "Frontend Developer",
                "company": "Web Agency",
                "location": "London",
                "work_mode": "On-site",
                "job_type": "Full-time",
                "experience": "Entry level",
                "skills": "JavaScript, React, CSS",
                "description": "Junior Frontend developer needed.",
                "source": "Live (Jobicy)",
                "is_live": True,
                "url": "https://example.com/apply/2"
            }
        ]

        with patch.object(service, '_query_external_apis', return_value=sample_jobs), patch.object(service, '_fetch_adzuna', return_value=[]):
            # Test filter by role keyword
            results = service.fetch_live_jobs(filters={"role": "Machine Learning"})
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["title"], "Machine Learning Engineer")
            self.assertEqual(results[0]["source"], "Live (Arbeitnow)")

            # Test filter by work mode
            remote_results = service.fetch_live_jobs(filters={"work_mode": "Remote"})
            self.assertEqual(len(remote_results), 1)
            self.assertEqual(remote_results[0]["work_mode"], "Remote")

    def test_combined_job_provider_deduplication(self):
        mock_db_job = {
            "job_id": 1001,
            "title": "Data Scientist",
            "company": "Alpha Tech",
            "location": "Bangalore",
            "skills": "Python, Pandas",
            "source": "Database",
            "is_live": False
        }
        mock_live_duplicate = {
            "job_id": "20001",
            "title": "Data Scientist",
            "company": "Alpha Tech",
            "location": "Bangalore, India",
            "skills": "Python, Pandas, Scikit-Learn",
            "source": "Live",
            "is_live": True,
            "url": "https://example.com/apply/live"
        }
        mock_live_unique = {
            "job_id": "20002",
            "title": "Cloud Architect",
            "company": "Beta Cloud",
            "location": "Remote",
            "skills": "AWS, Docker",
            "source": "Live",
            "is_live": True,
            "url": "https://example.com/apply/unique"
        }

        mock_local_provider = MagicMock()
        mock_local_provider.get_all_jobs.return_value = [mock_db_job]

        mock_live_service = MagicMock()
        mock_live_service.fetch_live_jobs.return_value = [mock_live_duplicate, mock_live_unique]

        provider = CombinedJobProvider(local_provider=mock_local_provider, live_service=mock_live_service)

        # Total combined should deduplicate the (Data Scientist, Alpha Tech) pair
        combined = provider.get_all_jobs(source="all")
        self.assertEqual(len(combined), 2)
        titles = [j["title"] for j in combined]
        self.assertIn("Data Scientist", titles)
        self.assertIn("Cloud Architect", titles)

        # Test source filtering
        live_only = provider.get_all_jobs(source="live")
        self.assertEqual(len(live_only), 2)
        for j in live_only:
            self.assertTrue(j.get("is_live", False))

        db_only = provider.get_all_jobs(source="database")
        self.assertEqual(len(db_only), 1)
        self.assertEqual(db_only[0]["source"], "Database")

    def test_jobs_route_tabs_and_rendering(self):
        # Test tab=all
        res_all = self.client.get('/jobs?tab=all')
        self.assertEqual(res_all.status_code, 200)
        self.assertIn(b"Live Internet Jobs", res_all.data)
        self.assertNotIn(b"Existing Database Jobs", res_all.data)

        # Test tab=live
        res_live = self.client.get('/jobs?tab=live')
        self.assertEqual(res_live.status_code, 200)

        # Test tab=database
        res_db = self.client.get('/jobs?tab=database')
        self.assertEqual(res_db.status_code, 200)

    def test_no_resume_guardrail(self):
        # When user has no resume, matching score must display 'Upload resume to match'
        res = self.client.get('/jobs?tab=all')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Upload resume to match", res.data)

    def test_adzuna_live_search_parsing_and_apply_url(self):
        service = LiveJobSearchService()
        sample_adzuna_payload = {
            "results": [
                {
                    "id": "5895258681",
                    "title": "<strong>Python Developer</strong>",
                    "company": {"display_name": "MANTECH"},
                    "location": {"display_name": "Herndon, Virginia"},
                    "salary_min": 120000,
                    "salary_max": 150000,
                    "redirect_url": "https://www.adzuna.com/land/ad/5895258681?apply=direct",
                    "description": "Looking for a Python Developer experienced with AWS, SQL, and Docker."
                }
            ]
        }

        with patch.object(service, '_fetch_adzuna') as mock_fetch:
            mock_fetch.return_value = [
                {
                    "job_id": "adzuna_5895258681",
                    "title": "Python Developer",
                    "company": "MANTECH",
                    "location": "Herndon, Virginia",
                    "work_mode": "On-site",
                    "job_type": "Full-time",
                    "experience": "1-3 years",
                    "education": "Bachelor's Degree in Computer Science, IT, or related discipline",
                    "skills": "Python, AWS, SQL, Docker",
                    "required_skills": ["Python", "AWS", "SQL", "Docker"],
                    "preferred_skills": "Strong analytical problem solving and collaborative engineering",
                    "responsibilities": "Develop Python microservices...",
                    "description": "Looking for a Python Developer experienced with AWS, SQL, and Docker.",
                    "keywords": "python developer herndon mantech",
                    "salary": "$120,000 - $150,000",
                    "source": "Live Job (Adzuna)",
                    "is_live": True,
                    "url": "https://www.adzuna.com/land/ad/5895258681?apply=direct",
                    "apply_url": "https://www.adzuna.com/land/ad/5895258681?apply=direct"
                }
            ]

            jobs = service.search_adzuna(query="Python", location="Herndon")
            self.assertEqual(len(jobs), 1)
            job = jobs[0]
            self.assertEqual(job["title"], "Python Developer")
            self.assertEqual(job["company"], "MANTECH")
            self.assertEqual(job["source"], "Live Job (Adzuna)")
            self.assertEqual(job["url"], "https://www.adzuna.com/land/ad/5895258681?apply=direct")
            self.assertEqual(job["apply_url"], "https://www.adzuna.com/land/ad/5895258681?apply=direct")
            self.assertIn("Python", job["skills"])

    def test_api_jobs_live_and_adzuna_routes(self):
        # Test /api/jobs/live endpoint
        res = self.client.get('/api/jobs/live?role=Python&location=Remote')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("jobs", data)
        self.assertIn("source_breakdown", data)
        self.assertIn("live_jobs", data["source_breakdown"])
        self.assertIn("careerbot_database", data["source_breakdown"])

        # Test /api/jobs/adzuna alias
        res_alias = self.client.get('/api/jobs/adzuna?combine=false')
        self.assertEqual(res_alias.status_code, 200)
        data_alias = res_alias.get_json()
        self.assertEqual(data_alias["status"], "success")

    def test_adzuna_missing_credentials_handling(self):
        service = LiveJobSearchService()
        with patch("config.Config.ADZUNA_APP_ID", ""), patch("config.Config.ADZUNA_APP_KEY", ""):
            jobs = service._fetch_adzuna(query="Python")
            self.assertEqual(jobs, [])

