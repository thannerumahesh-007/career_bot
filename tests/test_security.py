"""
Automated Security, Data Privacy, and Anti-IDOR Tests for CareerBot.
"""

import unittest
import json
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Resume, UserProfile, Base
from services.career_service import CareerService


class TestSecurityAndIsolation(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

    def test_protected_route_without_login(self):
        protected_pages = ['/dashboard', '/chat', '/jobs', '/resume', '/roadmap']
        for page in protected_pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 302, f"Unauthenticated access to {page} should redirect.")

        protected_apis = ['/api/profile', '/api/chat', '/api/resume/upload']
        for api in protected_apis:
            res = self.client.get(api) if api == '/api/profile' else self.client.post(api, json={"message": "hello"})
            self.assertEqual(res.status_code, 401, f"Unauthenticated access to {api} should return 401.")

    def test_user_data_isolation(self):
        # Create User A in DB
        db = SessionLocal()
        user_a = User(full_name="User A", username="usera", email="usera@example.com")
        user_a.set_password("Password123!")
        db.add(user_a)
        db.commit()

        career_service = CareerService()
        career_service.get_or_create_user_profile(db, user_a.id)
        career_service.update_user_profile(db, user_a.id, {'skills': ['Python', 'SQL', 'PyTorch']})
        career_service.process_chat_message(db, user_a.id, "I know Python and Machine Learning")
        user_a_id = user_a.id
        db.close()

        # Create User B in DB
        db = SessionLocal()
        user_b = User(full_name="User B", username="userb", email="userb@example.com")
        user_b.set_password("Password123!")
        db.add(user_b)
        db.commit()

        career_service.get_or_create_user_profile(db, user_b.id)
        user_b_id = user_b.id
        db.close()

        # Log in as User B
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_b_id
            sess['username'] = 'userb'

        # Fetch User B profile -> must be clean / isolated from User A
        res_profile = self.client.get('/api/profile')
        self.assertEqual(res_profile.status_code, 200)
        profile_b = json.loads(res_profile.data)
        self.assertEqual(profile_b['skills'], [], "User B must not see User A's profile skills.")

        # Fetch User B chat -> must be empty
        res_chat = self.client.get('/chat')
        self.assertNotIn(b'I know Python and Machine Learning', res_chat.data, "User B must not see User A's chat history.")

    def test_idor_protection_on_resume(self):
        db = SessionLocal()

        # Create User A in DB
        user_a = User(full_name="User A", username="user_a", email="usera@test.com")
        user_a.set_password("Pass123!")
        db.add(user_a)
        db.commit()

        # Create User A Resume
        resume_a = Resume(
            user_id=user_a.id,
            original_filename="UserA_Resume.pdf",
            stored_filename="usera_file.pdf",
            extracted_text="Secret User A Resume Text"
        )
        db.add(resume_a)
        db.commit()
        resume_a_id = resume_a.id

        # Create User B in DB
        user_b = User(full_name="User B", username="user_b", email="userb@test.com")
        user_b.set_password("Pass123!")
        db.add(user_b)
        db.commit()
        user_b_id = user_b.id
        db.close()

        # Log in as User B
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_b_id
            sess['username'] = 'user_b'

        # Attempt to access User A's resume ID via User B
        response = self.client.get(f'/api/resume/file/{resume_a_id}')
        self.assertEqual(response.status_code, 404, "Accessing another user's resume must return 404/403.")


if __name__ == '__main__':
    unittest.main()
