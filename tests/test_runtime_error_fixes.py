"""
Tests verifying fixes for runtime errors:
1. Jinja2 request.endpoint is None null-safety across all templates and error pages
2. Invalid route / 404 renders error.html cleanly without TypeError
3. Error handler 500 renders cleanly when request.endpoint is None
4. Model router authentication failure halts retries immediately
5. Multilingual and short query role/skill extraction:
   - "मुझे पाइथन स्किल्स।" -> Python Developer (NOT Java)
   - "पाइथन डेवलपर बनने के लिए क्या स्किल्स चाहिए?" -> Python Developer in Hindi
   - "పైథాన్ డెవలపర్ కావడానికి ఏ స్కిల్స్ కావాలి?" -> Python Developer in Telugu
   - English Python and Java queries
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import render_template
from app import app
from database.database import init_db, SessionLocal
from database.models import User
from nlp.intent_classifier import IntentClassifier
from services.career_knowledge import extract_role_from_text, get_role_details
from services.gemini_service import gemini_service
from services.model_router import model_router, ModelRouter, ErrorCategory


class TestRuntimeErrorFixes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        init_db()

        # Create test user for authenticated page testing
        db = SessionLocal()
        user = db.query(User).filter_by(username="errortester").first()
        if not user:
            user = User(full_name="Error Tester", username="errortester", email="errortester@example.com")
            user.set_password("SecurePass123!")
            db.add(user)
            db.commit()
            db.refresh(user)
        cls.test_user_id = user.id
        db.close()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user_id
            sess['username'] = 'errortester'

    # --- ERROR 1 TESTS: JINJA2 request.endpoint IS NONE ---

    def test_404_page_renders_cleanly_when_endpoint_is_none(self):
        """Verify that an invalid route triggers 404 error handler and error.html without Jinja2 TypeError."""
        res = self.client.get('/invalid-page-does-not-exist-404')
        self.assertEqual(res.status_code, 404)
        html = res.data.decode('utf-8')
        self.assertIn("Page Not Found", html)
        self.assertIn("404", html)

    def test_direct_error_template_render_with_none_endpoint(self):
        """Verify error.html renders directly in request context where request.endpoint is None."""
        with self.app.test_request_context('/unmapped-url-with-no-rule-for-testing'):
            from flask import request
            # When route has no URL rule, request.endpoint is None
            self.assertIsNone(request.endpoint)
            rendered = render_template("error.html", code=500, title="Server Error", message="Test error message")
            self.assertIn("Server Error", rendered)
            self.assertIn("500", rendered)

    def test_authenticated_pages_render_without_jinja_error(self):
        """Verify /chat, /resume, /jobs, /companies, /interview render 200 without template error."""
        self._login()
        pages = ['/chat', '/resume', '/jobs', '/companies', '/interview', '/dashboard', '/roadmap']
        for page in pages:
            res = self.client.get(page)
            self.assertEqual(res.status_code, 200, f"Page {page} failed to render with {res.status_code}")

    # --- ERROR 2 & MODEL ROUTER TESTS ---

    def test_model_router_auth_error_halts_immediately(self):
        """Verify 400 'API key not valid' aborts retry chain on first model (call_count == 1)."""
        mock_client = MagicMock()
        auth_error = Exception("400 INVALID_ARGUMENT: API key not valid. Please pass a valid API key.")
        mock_client.models.generate_content.side_effect = auth_error

        with patch("services.model_router.genai.Client", return_value=mock_client):
            router = ModelRouter(api_key="AIzaSyInvalidKeyTest12345678901234567")
            res = router.generate_content("chat", prompt="Hello")
            self.assertIsNone(res)
            # CRITICAL: exactly 1 call, stopped before trying other models
            self.assertEqual(mock_client.models.generate_content.call_count, 1)
            self.assertEqual(router.last_status["provider"], "local_fallback")
            self.assertEqual(router.last_status["error_type"], "authentication_error")

    def test_model_router_diagnostic_connection_test(self):
        """Verify diagnostic connection test safely checks status without exposing key."""
        diag = model_router.test_connection()
        self.assertIn("api_key_loaded", diag)
        self.assertIn("key_source", diag)
        self.assertIn("key_length", diag)
        self.assertNotIn(str(model_router.api_key or ""), str(diag))

    # --- LOCAL FALLBACK & MULTILINGUAL ROLE/INTENT TESTS ---

    def test_short_query_hindi_python_skills_not_java(self):
        """
        User input: 'मुझे पाइथन स्किल्स।'
        Expected: intent=career_skill_requirements, role=python developer (NOT Java)
        """
        query = "मुझे पाइथन स्किल्स।"
        classifier = IntentClassifier()
        intent = classifier.classify_intent(query)
        role = extract_role_from_text(query)

        self.assertEqual(intent, "career_skill_requirements")
        self.assertEqual(role, "python developer")

        # Even with Java previously in history, short query must detect Python
        history = [
            {"sender": "user", "message": "Tell me about Java Developer"},
            {"sender": "bot", "message": "Java Developer skills..."}
        ]
        resp = gemini_service.generate_fallback_response(intent, query, {}, history=history, language="hi")
        self.assertIn("Python Developer", resp)
        self.assertNotIn("Java Developer", resp)

    def test_hindi_python_developer_question(self):
        """
        User input: 'पाइथन डेवलपर बनने के लिए क्या स्किल्स चाहिए?'
        Expected: intent=career_skill_requirements, role=python developer, Hindi response
        """
        query = "पाइथन डेवलपर बनने के लिए क्या स्किल्स चाहिए?"
        classifier = IntentClassifier()
        intent = classifier.classify_intent(query)
        role = extract_role_from_text(query)

        self.assertEqual(intent, "career_skill_requirements")
        self.assertEqual(role, "python developer")

        resp = gemini_service.generate_fallback_response(intent, query, {}, language="hi")
        self.assertIn("Python Developer", resp)
        self.assertIn("आवश्यक प्रमुख तकनीकी स्किल्स", resp)

    def test_telugu_python_developer_question(self):
        """
        User input: 'పైథాన్ డెవలపర్ కావడానికి ఏ స్కిల్స్ కావాలి?'
        Expected: intent=career_skill_requirements, role=python developer, Telugu response
        """
        query = "పైథాన్ డెవలపర్ కావడానికి ఏ స్కిల్స్ కావాలి?"
        classifier = IntentClassifier()
        intent = classifier.classify_intent(query)
        role = extract_role_from_text(query)

        self.assertEqual(intent, "career_skill_requirements")
        self.assertEqual(role, "python developer")

        resp = gemini_service.generate_fallback_response(intent, query, {}, language="te")
        self.assertIn("Python Developer", resp)
        self.assertIn("సాంకేతిక నైపుణ్యాలు", resp)

    def test_english_python_developer_question(self):
        """
        User input: 'What skills do I need for Python Developer?'
        Expected: intent=career_skill_requirements, role=python developer, English response
        """
        query = "What skills do I need for Python Developer?"
        classifier = IntentClassifier()
        intent = classifier.classify_intent(query)
        role = extract_role_from_text(query)

        self.assertEqual(intent, "career_skill_requirements")
        self.assertEqual(role, "python developer")

        resp = gemini_service.generate_fallback_response(intent, query, {}, language="en-IN")
        self.assertIn("Python Developer", resp)
        self.assertIn("Key Technical Skills Required for Python Developer", resp)

    def test_english_java_developer_question(self):
        """
        User input: 'What skills do I need for Java Developer?'
        Expected: intent=career_skill_requirements, role=java developer, English response
        """
        query = "What skills do I need for Java Developer?"
        classifier = IntentClassifier()
        intent = classifier.classify_intent(query)
        role = extract_role_from_text(query)

        self.assertEqual(intent, "career_skill_requirements")
        self.assertEqual(role, "java developer")

        resp = gemini_service.generate_fallback_response(intent, query, {}, language="en-IN")
        self.assertIn("Java Developer", resp)
        self.assertIn("Core Java", resp)
        self.assertIn("Spring Boot", resp)


if __name__ == "__main__":
    unittest.main()
