"""
Tests for Company Directory, Following/Unfollowing, and Personalized News Stream.
"""

import unittest
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base
from services.company_service import company_service


class TestCompaniesAndFollowing(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        Base.metadata.drop_all(bind=engine)
        init_db()

        # Seed authenticated user
        db = SessionLocal()
        user = User(full_name="Linus Torvalds", username="linus", email="linus@kernel.org")
        user.set_password("SecureLinux123!")
        db.add(user)
        db.commit()
        self.user_id = user.id
        db.close()

        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["username"] = "linus"
            sess["full_name"] = "Linus Torvalds"

    def test_company_directory_listing_and_search(self):
        """Verify companies list returns seeded catalog and supports keyword filtering."""
        res = self.client.get('/api/companies')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["total"] >= 5)

        # Search for Google
        search_res = self.client.get('/api/companies?q=Google')
        self.assertEqual(search_res.status_code, 200)
        search_data = search_res.get_json()
        self.assertTrue(any(c["name"] == "Google" for c in search_data["companies"]))

    def test_follow_and_unfollow_flow(self):
        """Verify following a company marks it as followed and unfollowing removes it."""
        # 1. Follow Google
        follow_res = self.client.post('/api/companies/follow/Google')
        self.assertEqual(follow_res.status_code, 200)
        f_data = follow_res.get_json()
        self.assertTrue(f_data.get("success"))

        # 2. Verify list reflects is_following=True
        list_res = self.client.get('/api/companies?q=Google')
        c_list = list_res.get_json()["companies"]
        google_entry = next(c for c in c_list if c["name"] == "Google")
        self.assertTrue(google_entry["is_following"])

        # 3. Unfollow Google
        unfollow_res = self.client.post('/api/companies/unfollow/Google')
        self.assertEqual(unfollow_res.status_code, 200)
        uf_data = unfollow_res.get_json()
        self.assertTrue(uf_data.get("success"))

        # 4. Verify list reflects is_following=False
        list_res2 = self.client.get('/api/companies?q=Google')
        c_list2 = list_res2.get_json()["companies"]
        google_entry2 = next(c for c in c_list2 if c["name"] == "Google")
        self.assertFalse(google_entry2["is_following"])

    def test_news_following_empty_state_and_personalized_query(self):
        """Verify /api/news?category=following informs when no companies are followed."""
        # User not following any companies yet
        news_res = self.client.get('/api/news?category=following')
        self.assertEqual(news_res.status_code, 200)
        news_data = news_res.get_json()
        self.assertEqual(news_data["category"], "following")
        self.assertEqual(news_data["total"], 0)
        self.assertIn("not following any companies yet", news_data.get("message", ""))


if __name__ == "__main__":
    unittest.main()
