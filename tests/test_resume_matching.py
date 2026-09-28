"""
Automated unit and integration tests for Resume Matching & Anti-IDOR Deletion Security.
"""

import unittest
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Resume, Base


class TestResumeMatchingAndSecurity(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # User 1
        db = SessionLocal()
        u1 = User(full_name="User One", username="user1", email="user1@example.com")
        u1.set_password("Password123!")
        db.add(u1)
        
        # User 2
        u2 = User(full_name="User Two", username="user2", email="user2@example.com")
        u2.set_password("Password123!")
        db.add(u2)
        db.commit()

        # Add resume for User 1
        r1 = Resume(
            user_id=u1.id,
            original_filename="user1_resume.pdf",
            stored_filename="user1_resume.pdf",
            extracted_text="Python Flask ML Docker SQL Git",
            extracted_data={"skills": ["python", "flask", "ml", "docker", "sql", "git"]}
        )
        db.add(r1)
        db.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.r1_id = r1.id
        db.close()

    def test_resume_matches_route_unauthenticated(self):
        res = self.client.get('/jobs/resume-matches')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.headers['Location'])

    def test_resume_matches_route_authenticated(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['username'] = 'user1'

        res = self.client.get('/jobs/resume-matches')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Jobs Matched to Your Resume', res.data)

    def test_api_resume_matches(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['username'] = 'user1'

        res = self.client.get('/api/jobs/resume-matches')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertEqual(json_data['status'], 'success')
        self.assertIn('results', json_data)

    def test_anti_idor_resume_deletion(self):
        # User 2 attempts to delete User 1's resume
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u2_id
            sess['username'] = 'user2'

        res = self.client.delete(f'/api/resume/{self.r1_id}')
        self.assertEqual(res.status_code, 404)  # Anti-IDOR: Returns 404 when not owning resource

        # Confirm resume still exists in database
        db = SessionLocal()
        resume_check = db.query(Resume).filter(Resume.id == self.r1_id).first()
        self.assertIsNotNone(resume_check)
        db.close()

    def test_authorized_resume_deletion(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.u1_id
            sess['username'] = 'user1'

        res = self.client.delete(f'/api/resume/{self.r1_id}')
        self.assertEqual(res.status_code, 200)

        # Confirm resume is removed from database
        db = SessionLocal()
        resume_check = db.query(Resume).filter(Resume.id == self.r1_id).first()
        self.assertIsNone(resume_check)
        db.close()


if __name__ == '__main__':
    unittest.main()
