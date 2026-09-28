"""Corporate News Service for CareerBot.
Fetches real-time corporate, business, IT, and tech industry news from News API.
Includes in-memory TTL caching, query filters, search capabilities, and Gemini AI executive summaries.
"""

import os
import json
import time
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import Config
from services.gemini_service import gemini_service

# Predefined categories focused on corporate, IT, and global business
NEWS_CATEGORIES = {
    "all": {
        "label": "All News",
        "icon": "globe",
        "query": '(technology OR AI OR "artificial intelligence" OR startup OR corporate OR business OR software OR IT OR semiconductor OR "layoffs" OR "hiring")'
    },
    "tech_ai": {
        "label": "AI & Tech",
        "icon": "cpu",
        "query": '("artificial intelligence" OR OpenAI OR NVIDIA OR "generative AI" OR LLM OR "machine learning" OR Anthropic OR ChatGPT OR DeepMind)'
    },
    "big_tech": {
        "label": "Big Tech",
        "icon": "building-2",
        "query": '(Microsoft OR Google OR Apple OR Amazon OR Meta OR NVIDIA OR Tesla OR Alphabet OR IBM)'
    },
    "indian_it": {
        "label": "Indian IT",
        "icon": "landmark",
        "query": '(TCS OR "Tata Consultancy Services" OR Infosys OR Wipro OR HCLTech OR "Tech Mahindra" OR Cognizant OR "Indian IT")'
    },
    "startups": {
        "label": "Startups & VC",
        "icon": "rocket",
        "query": '(startup OR "venture capital" OR "Series A" OR "funding round" OR unicorn OR "seed funding" OR "Y Combinator" OR acquisition)'
    },
    "layoffs_hiring": {
        "label": "Hiring & Layoffs",
        "icon": "users",
        "query": '(layoffs OR "job cuts" OR hiring OR recruitment OR workforce OR "hiring freeze" OR restructuring OR expansion)'
    },
    "cloud_cyber": {
        "label": "Cloud & Cyber",
        "icon": "shield-check",
        "query": '(AWS OR Azure OR "Google Cloud" OR cybersecurity OR "cloud computing" OR Datadog OR CrowdStrike OR semiconductor OR Intel OR TSMC OR AMD)'
    }
}


class NewsService:
    """Manages real-time corporate and business news fetching from News API."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = getattr(Config, "NEWS_CACHE_TTL", 300)

    @property
    def api_key(self) -> str:
        """Dynamically fetch the News API key from Config or environment."""
        return getattr(Config, "NEWS_API_KEY", "") or os.environ.get("NEWS_API_KEY", "").strip()

    def fetch_corporate_news(
        self,
        category: str = "all",
        search_query: str = "",
        force_refresh: bool = False,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """Fetches live corporate news from News API with error handling and caching."""
        api_key = self.api_key
        if not api_key:
            return {
                "status": "error",
                "error_type": "invalid_api_key",
                "message": "News API key is not configured. Please set NEWS_API_KEY in the .env file.",
                "articles": [],
                "total": 0
            }

        # Normalize category
        cat_key = category.strip().lower()
        if cat_key not in NEWS_CATEGORIES:
            cat_key = "all"

        clean_query = search_query.strip()
        cache_key = f"{cat_key}_{clean_query.lower()}"

        # In-memory cache check (unless explicit refresh requested)
        now = time.time()
        if not force_refresh and cache_key in self._cache:
            entry = self._cache[cache_key]
            if now - entry["timestamp"] < self.cache_ttl:
                return entry["data"]

        # Build query string
        if clean_query:
            # User search takes precedence; restrict to corporate/business domain
            query_str = f"({clean_query}) AND (company OR corporate OR business OR tech OR technology OR IT OR startup OR industry OR market)"
        else:
            query_str = NEWS_CATEGORIES[cat_key]["query"]

        params = {
            "q": query_str,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(page_size, 40)
        }
        encoded_url = f"https://newsapi.org/v2/everything?{urllib.parse.urlencode(params)}"

        headers = {
            "X-Api-Key": api_key,
            "User-Agent": "CareerBot-CorporateNews/1.0"
        }

        try:
            req = urllib.request.Request(encoded_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                raw_data = response.read().decode("utf-8")
                api_response = json.loads(raw_data)
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}"
            error_type = "api_error"
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                api_msg = err_body.get("message", e.reason)
                error_code = err_body.get("code", "")
            except Exception:
                api_msg = e.reason
                error_code = ""

            if e.code == 401 or error_code == "apiKeyInvalid":
                error_type = "invalid_api_key"
                error_msg = "News API rejected the API key (401 Unauthorized). Please check your NEWS_API_KEY."
            elif e.code == 429 or error_code == "rateLimited":
                error_type = "rate_limit"
                error_msg = "News API request limit reached. Please wait a few moments before refreshing."
            else:
                error_msg = f"News API error: {api_msg}"

            return {
                "status": "error",
                "error_type": error_type,
                "message": error_msg,
                "articles": [],
                "total": 0
            }
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error_type": "network_error",
                "message": "Unable to connect to News API. Please verify your internet connection.",
                "articles": [],
                "total": 0
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "unknown_error",
                "message": f"Unexpected error while fetching news: {str(e)}",
                "articles": [],
                "total": 0
            }

        # Inspect API status
        if api_response.get("status") != "ok":
            code = api_response.get("code", "")
            msg = api_response.get("message", "Unknown error from News API")
            err_type = "rate_limit" if code == "rateLimited" else ("invalid_api_key" if code == "apiKeyInvalid" else "api_error")
            return {
                "status": "error",
                "error_type": err_type,
                "message": msg,
                "articles": [],
                "total": 0
            }

        raw_articles = api_response.get("articles", [])
        cleaned_articles = []

        for idx, art in enumerate(raw_articles):
            title = art.get("title") or ""
            url = art.get("url") or ""

            # Filter out removed / deleted articles
            if not title or title.strip() == "[Removed]" or not url or url.startswith("https://removed.com"):
                continue

            # Determine human-readable publication time
            pub_raw = art.get("publishedAt", "")
            formatted_date = self._format_published_date(pub_raw)

            # Auto-tag appropriate category badge
            assigned_category = self._infer_category(title, art.get("description") or "", cat_key)

            # Clean company / source
            source_obj = art.get("source") or {}
            source_name = source_obj.get("name") or "Corporate Source"

            cleaned_articles.append({
                "id": idx + 1,
                "title": title.strip(),
                "description": (art.get("description") or "No description provided.").strip(),
                "url": url.strip(),
                "image_url": art.get("urlToImage") or "",
                "source": source_name,
                "author": art.get("author") or "",
                "published_at": pub_raw,
                "published_relative": formatted_date["relative"],
                "published_formatted": formatted_date["formatted"],
                "category": assigned_category
            })

        result_data = {
            "status": "ok",
            "category": cat_key,
            "category_label": NEWS_CATEGORIES[cat_key]["label"],
            "query": clean_query,
            "total": len(cleaned_articles),
            "articles": cleaned_articles,
            "last_updated": datetime.now(timezone.utc).strftime("%I:%M %p UTC")
        }

        # Cache result
        self._cache[cache_key] = {
            "timestamp": now,
            "data": result_data
        }

        return result_data

    def generate_ai_summary(self, title: str, description: str, content: str = "") -> str:
        """Uses Gemini AI to generate a concise, grounded 2-sentence executive takeaway."""
        if not title:
            return "No article details available to summarize."

        prompt = (
            "You are a professional corporate news analyst for CareerBot. "
            "Given the following real news headline and description, provide a 2-sentence executive takeaway "
            "focusing on the business impact, corporate strategy, or career/industry significance. "
            "Ground your answer STRICTLY in the provided text. Do not invent details.\n\n"
            f"Headline: {title}\n"
            f"Description: {description}\n"
            f"Context: {content[:300] if content else ''}\n\n"
            "Executive Takeaway:"
        )

        try:
            summary = gemini_service.generate_response(prompt, max_tokens=120)
            if summary and len(summary.strip()) > 10:
                return summary.strip()
        except Exception:
            pass

        # Fallback summary if Gemini API is temporarily busy
        return f"{title}. Key developments reported by industry sources regarding corporate developments and strategic market impact."

    def _infer_category(self, title: str, desc: str, selected_cat: str) -> str:
        """Infers the most relevant category badge for display."""
        if selected_cat != "all" and selected_cat in NEWS_CATEGORIES:
            return NEWS_CATEGORIES[selected_cat]["label"]

        text = f"{title} {desc}".lower()
        if any(w in text for w in ["ai", "artificial intelligence", "openai", "nvidia", "llm", "chatgpt"]):
            return "AI & Tech"
        if any(w in text for w in ["tcs", "infosys", "wipro", "hcl", "cognizant", "tech mahindra"]):
            return "Indian IT"
        if any(w in text for w in ["microsoft", "google", "apple", "amazon", "meta", "tesla", "alphabet"]):
            return "Big Tech"
        if any(w in text for w in ["layoff", "layoffs", "job cut", "hiring", "workforce", "hiring freeze"]):
            return "Hiring & Layoffs"
        if any(w in text for w in ["startup", "venture", "seed", "series a", "funding", "unicorn"]):
            return "Startups & VC"
        if any(w in text for w in ["cloud", "aws", "azure", "cybersecurity", "semiconductor", "chip", "intel", "tsmc"]):
            return "Cloud & Cyber"
        return "Corporate News"

    def _format_published_date(self, iso_str: str) -> Dict[str, str]:
        """Converts an ISO timestamp into both relative (e.g. '2 hours ago') and formatted date."""
        if not iso_str:
            return {"relative": "Recently", "formatted": "Recent"}

        try:
            # Handle ISO string with 'Z' or offset
            cleaned_iso = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned_iso)
            now = datetime.now(timezone.utc)
            delta = now - dt

            seconds = int(delta.total_seconds())
            if seconds < 60:
                relative = "Just now"
            elif seconds < 3600:
                mins = seconds // 60
                relative = f"{mins}m ago"
            elif seconds < 86400:
                hours = seconds // 3600
                relative = f"{hours}h ago"
            elif seconds < 172800:
                relative = "Yesterday"
            else:
                days = seconds // 86400
                relative = f"{days}d ago"

            formatted = dt.strftime("%b %d, %Y")
            return {"relative": relative, "formatted": formatted}
        except Exception:
            return {"relative": "Recently", "formatted": iso_str[:10] if len(iso_str) >= 10 else "Recent"}


# Global singleton instance
news_service = NewsService()
