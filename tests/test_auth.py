"""
Automated unit and integration tests for User Authentication in CareerBot.
"""

import unittest
import json
from app import app
from database.database import init_db, SessionLocal, engine
from database.models import User, Base


class TestAuthentication(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

        # Reset database tables
        Base.metadata.drop_all(bind=engine)
        init_db()

    def test_register_success(self):
        response = self.client.post('/register', data={
            'full_name': 'Test Student',
            'email': 'student@example.com',
            'username': 'teststudent',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        # Check DB entry
        db = SessionLocal()
        user = db.query(User).filter_by(username='teststudent').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('SecurePassword123!'))
        db.close()

    def test_duplicate_registration(self):
        # Register first user directly in DB
        db = SessionLocal()
        u1 = User(full_name='First User', email='first@example.com', username='firstuser')
        u1.set_password('Password123!')
        db.add(u1)
        db.commit()
        db.close()

        # Attempt duplicate registration with same email
        response = self.client.post('/register', data={
            'full_name': 'Second User',
            'email': 'first@example.com',
            'username': 'uniqueusername',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertIn(b'Registration failed', response.data)

    def test_login_success(self):
        # Register user directly in DB
        db = SessionLocal()
        u = User(full_name='Login Test', email='logintest@example.com', username='logintest')
        u.set_password('Password123!')
        db.add(u)
        db.commit()
        db.close()

        # Login with correct credentials
        response = self.client.post('/login', data={
            'login_id': 'logintest',
            'password': 'Password123!'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

    def test_login_invalid_credentials(self):
        response = self.client.post('/login', data={
            'login_id': 'nonexistentuser',
            'password': 'wrongpassword'
        })
        self.assertIn(b'Invalid username/email or password', response.data)

    def test_logout(self):
        # Register & login user directly
        db = SessionLocal()
        u = User(full_name='Logout Test', email='logout@example.com', username='logouttest')
        u.set_password('Password123!')
        db.add(u)
        db.commit()
        user_id = u.id
        db.close()

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # Logout
        response = self.client.post('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Access protected route should redirect to login
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 302)


if __name__ == '__main__':
    unittest.main()
