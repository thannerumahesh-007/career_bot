"""
Integration test verifying Requirement 1:
Resume upload replaces profile skills, resume deletion clears profile skills,
and uploading a second resume replaces old skills without caching stale data.
"""

import unittest
import json
import io
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, UserProfile, Resume, Base
from services.career_service import CareerService


class TestResumeReplacement(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        Base.metadata.drop_all(bind=engine)
        init_db()

        db = SessionLocal()
        user = User(full_name="Resume Tester", username="resumetester", email="resumetester@example.com")
        user.set_password("Password123!")
        db.add(user)
        db.commit()
        db.refresh(user)

        career_service = CareerService()
        career_service.get_or_create_user_profile(db, user.id)
        user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = 'resumetester'

    def test_resume_upload_delete_and_replacement_lifecycle(self):
        # Step 1: Upload Resume A
        resume_a_content = (
            "Resume A\n"
            "Technical Skills: Python, SQL, Django, PostgreSQL\n"
            "Education: Bachelor of Science in Computer Science\n"
            "Experience: 2 years Software Engineer\n"
        )
        data_a = {
            'file': (io.BytesIO(resume_a_content.encode('utf-8')), 'resume_a.txt')
        }
        res_a = self.client.post('/api/resume/upload', data=data_a, content_type='multipart/form-data')
        self.assertEqual(res_a.status_code, 200)

        data_a_json = json.loads(res_a.data)
        skills_a = data_a_json["profile"]["skills"]
        self.assertTrue(any(s.lower() == 'python' for s in skills_a))
        resume_a_id = data_a_json["resume"]["id"]

        # Step 2: Delete Resume A -> Profile skills become []
        del_res = self.client.delete(f'/api/resume/{resume_a_id}')
        self.assertEqual(del_res.status_code, 200)

        del_json = json.loads(del_res.data)
        self.assertEqual(del_json["profile"]["skills"], [])

        # Step 3: Upload Resume B -> Profile skills replaced with ONLY Resume B skills
        resume_b_content = (
            "Resume B\n"
            "Technical Skills: React, TypeScript, Node.js, GraphQL\n"
            "Education: Master of Science in Software Engineering\n"
            "Experience: 3 years Frontend Developer\n"
        )
        data_b = {
            'file': (io.BytesIO(resume_b_content.encode('utf-8')), 'resume_b.txt')
        }
        res_b = self.client.post('/api/resume/upload', data=data_b, content_type='multipart/form-data')
        self.assertEqual(res_b.status_code, 200)

        data_b_json = json.loads(res_b.data)
        skills_b = data_b_json["profile"]["skills"]

        # Verify only Skills B are present and old Skills A (Django/PostgreSQL) are NOT cached
        self.assertTrue(any(s.lower() == 'react' for s in skills_b))
        self.assertNotIn("Django", skills_b)
        self.assertNotIn("PostgreSQL", skills_b)


if __name__ == "__main__":
    unittest.main()
