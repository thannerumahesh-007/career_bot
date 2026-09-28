"""
Integration tests for CareerBot Flask application routes and API endpoints.
"""

import unittest
import json
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, UserProfile, Base
from services.career_service import CareerService


class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Create and log in test user
        db = SessionLocal()
        user = User(full_name="Route Tester", username="routetester", email="routetester@example.com")
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
            sess['username'] = 'routetester'

    def test_health_route(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["nlp"], "ready")
        self.assertIn("gemini", data)
        self.assertIn("fallback_mode", data)

    def test_pages_render(self):
        routes = ['/', '/dashboard', '/chat', '/jobs', '/resume', '/roadmap']
        for route in routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with status {res.status_code}")

    def test_profile_api(self):
        # GET profile
        res_get = self.client.get('/api/profile')
        self.assertEqual(res_get.status_code, 200)

        # POST profile update
        update_data = {
            "skills": ["Python", "SQL", "Machine Learning"],
            "education": "B.Tech CSE",
            "experience": "Fresher"
        }
        res_post = self.client.post('/api/profile', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(res_post.status_code, 200)

        data = json.loads(res_post.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("Python", data["profile"]["skills"])

    def test_chat_api(self):
        payload = {"message": "Find Python developer jobs"}
        res = self.client.post('/api/chat', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.data)
        self.assertIn("response", data)
        self.assertEqual(data["intent"], "job_search")


if __name__ == "__main__":
    unittest.main()
