"""
Automated unit and integration tests for Resume Upload Security.
"""

import unittest
import io
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base


class TestUploadSecurity(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Create & Log in test user
        db = SessionLocal()
        user = User(full_name="Upload Tester", username="uploader", email="uploader@example.com")
        user.set_password("Password123!")
        db.add(user)
        db.commit()
        user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = 'uploader'

    def test_invalid_file_type(self):
        # Attempt to upload executable / script format
        data = {
            'file': (io.BytesIO(b'malicious code'), 'script.exe')
        }
        res = self.client.post('/api/resume/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        self.assertIn(b'Unsupported file format', res.data)

    def test_valid_txt_resume_upload(self):
        sample_resume = (
            "Alex Rivers\n"
            "Education: Bachelor of Technology in Computer Science\n"
            "Experience: Software Developer Intern 1 year\n"
            "Skills: Python, SQL, Docker, Machine Learning, PyTorch, Git"
        ).encode('utf-8')

        data = {
            'file': (io.BytesIO(sample_resume), 'Alex_Resume_2026.txt')
        }
        res = self.client.post('/api/resume/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)

        # Check profile was updated with extracted skills
        res_profile = self.client.get('/api/profile')
        self.assertIn(b'python', res_profile.data.lower())


if __name__ == '__main__':
    unittest.main()
