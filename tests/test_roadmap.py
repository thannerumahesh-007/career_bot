"""
Automated unit and integration tests for Career Learning Roadmap functionality.
"""

import unittest
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, UserProfile, Base
from recommender.skill_gap import normalize_role_title, get_role_requirements, calculate_roadmap


class TestRoadmap(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Create & Log in test user
        db = SessionLocal()
        user = User(full_name="Roadmap Tester", username="roadmapper", email="roadmap@example.com")
        user.set_password("Password123!")
        db.add(user)
        db.commit()

        profile = UserProfile(user_id=user.id, skills=['python', 'sql', 'git'])
        db.add(profile)
        db.commit()
        user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = 'roadmapper'

    def test_role_normalization(self):
        self.assertEqual(normalize_role_title("py developer"), "Python Developer")
        self.assertEqual(normalize_role_title("ml engineer"), "Machine Learning Engineer")
        self.assertEqual(normalize_role_title("data analytics"), "Data Analyst")
        self.assertEqual(normalize_role_title("ai developer"), "AI Engineer")

    def test_role_requirements_fallback(self):
        reqs = get_role_requirements("Python Developer")
        self.assertTrue(any('python' in s.lower() for s in reqs))
        
        # Test unknown role fallback
        fallback_reqs = get_role_requirements("Astronaut Developer")
        self.assertTrue(any('python' in s.lower() for s in fallback_reqs))

    def test_calculate_roadmap(self):
        roadmap = calculate_roadmap(['python', 'sql'], 'Python Developer')
        self.assertEqual(roadmap['target_role'], 'Python Developer')
        self.assertGreater(roadmap['completion_percentage'], 0)
        self.assertIn('steps', roadmap)

    def test_roadmap_route(self):
        res = self.client.get('/roadmap?role=Data+Scientist')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Data Scientist', res.data)

    def test_api_roadmap_route(self):
        res = self.client.post('/api/roadmap', json={'target_role': 'Machine Learning Engineer'})
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['target_role'], 'Machine Learning Engineer')


if __name__ == '__main__':
    unittest.main()
