"""Tests for Corporate News feature and News API backend integration."""

import unittest
import json
from unittest.mock import patch, MagicMock
from app import app
from services.news_service import news_service, NEWS_CATEGORIES


class TestCorporateNews(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_news_page_route(self):
        """Verify GET /news renders successfully."""
        res = self.client.get('/news')
        self.assertEqual(res.status_code, 200)
        content = res.data.decode('utf-8')
        self.assertIn("Corporate & Technology News", content)
        self.assertIn("Refresh News", content)
        # Verify NEWS_API_KEY is NEVER exposed in the HTML
        if news_service.api_key:
            self.assertNotIn(news_service.api_key, content)

    def test_api_news_endpoint(self):
        """Verify GET /api/news returns valid JSON data."""
        res = self.client.get('/api/news?category=all')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("status", data)
        self.assertIn("articles", data)
        # Verify NEWS_API_KEY is NEVER exposed in the JSON response
        if news_service.api_key:
            self.assertNotIn(news_service.api_key, res.data.decode('utf-8'))

    def test_api_news_categories(self):
        """Verify all defined categories are recognized."""
        for cat_id in ["all", "tech_ai", "big_tech", "indian_it", "startups", "layoffs_hiring", "cloud_cyber"]:
            self.assertIn(cat_id, NEWS_CATEGORIES)
            self.assertIn("label", NEWS_CATEGORIES[cat_id])
            self.assertIn("query", NEWS_CATEGORIES[cat_id])

    def test_news_service_missing_key_handling(self):
        """Verify graceful error reporting when API key is missing, without fake news."""
        from unittest.mock import PropertyMock
        with patch('services.news_service.NewsService.api_key', new_callable=PropertyMock) as mock_key:
            mock_key.return_value = ""
            res = news_service.fetch_corporate_news(category="all", force_refresh=True)
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["error_type"], "invalid_api_key")
            self.assertEqual(len(res["articles"]), 0)

    def test_news_service_network_error_handling(self):
        """Verify graceful error handling on network connection failure."""
        import urllib.error
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
            res = news_service.fetch_corporate_news(category="all", force_refresh=True)
            self.assertEqual(res["status"], "error")
            self.assertEqual(res["error_type"], "network_error")
            self.assertEqual(len(res["articles"]), 0)

    def test_ai_summary_api(self):
        """Verify POST /api/news/ai-summary generates grounded executive takeaway."""
        payload = {
            "title": "NVIDIA Unveils Next-Gen AI Microarchitecture",
            "description": "NVIDIA announced a new data center platform targeting generative AI and enterprise workloads."
        }
        res = self.client.post('/api/news/ai-summary', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "ok")
        self.assertIn("summary", data)
        self.assertTrue(len(data["summary"]) > 10)


if __name__ == '__main__':
    unittest.main()
