"""
Job Provider Services for CareerBot.
Combines verified local database jobs with live internet job search from legitimate job APIs.
Includes in-memory TTL caching, source tagging, multi-factor deduplication, and skill extraction.
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from config import Config
from database.models import JobModel
from nlp.skill_extractor import SkillExtractor


class JobProvider(ABC):
    """Abstract interface for fetching job postings."""

    @abstractmethod
    def get_all_jobs(self, db_session) -> list:
        pass

    @abstractmethod
    def get_job_by_id(self, db_session, job_id: Any) -> Optional[dict]:
        pass


class LocalDatasetProvider(JobProvider):
    """Loads verified job postings from local SQLite database."""

    def get_all_jobs(self, db_session=None) -> list:
        if db_session is None:
            from database.database import SessionLocal
            with SessionLocal() as session:
                return self.get_all_jobs(session)
        jobs = db_session.query(JobModel).all()
        result = []
        for j in jobs:
            d = j.to_dict()
            d["is_live"] = False
            if not d.get("source"):
                d["source"] = "CareerBot Database"
            result.append(d)
        return result

    def get_job_by_id(self, db_session=None, job_id=None) -> Optional[dict]:
        if job_id is None:
            return None
        if db_session is None:
            from database.database import SessionLocal
            with SessionLocal() as session:
                return self.get_job_by_id(session, job_id)
        job_id_str = str(job_id)
        job = db_session.query(JobModel).filter_by(job_id=job_id_str).first()
        if not job:
            try:
                job = db_session.query(JobModel).filter_by(id=int(job_id)).first()
            except Exception:
                pass
        if job:
            d = job.to_dict()
            d["is_live"] = False
            if not d.get("source"):
                d["source"] = "CareerBot Database"
            return d
        return None


class LiveJobSearchService:
    """
    Retrieves current job listings from legitimate job-search APIs.
    Does NOT scrape LinkedIn directly. Uses public APIs (Arbeitnow & Jobicy)
    and supports configurable keys (Adzuna) via environment variables.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cached_jobs_by_id: Dict[str, dict] = {}
        self.cache_ttl = getattr(Config, "LIVE_JOB_CACHE_TTL", 600)
        self.skill_extractor = SkillExtractor()

    def _clean_html(self, text: str) -> str:
        """Removes HTML markup from API descriptions."""
        if not text:
            return ""
        clean = re.sub(r'<[^>]+>', ' ', text)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    def _fetch_adzuna(self, query: str = "", location: str = "", country: str = "in", results_per_page: int = 25) -> List[dict]:
        """
        Retrieves live job listings from Adzuna Job Search API.
        Adzuna credentials remain strictly server-side (Config.ADZUNA_APP_ID & Config.ADZUNA_APP_KEY).
        Gracefully handles API errors, empty responses, rate limits, and network timeouts.
        """
        app_id = getattr(Config, "ADZUNA_APP_ID", "").strip()
        app_key = getattr(Config, "ADZUNA_APP_KEY", "").strip()

        if not app_id or not app_key:
            return []

        # Auto-detect country code from location query if relevant
        loc_lower = (location or "").lower()
        if "us" in loc_lower or "united states" in loc_lower or "america" in loc_lower:
            country_code = "us"
        elif "uk" in loc_lower or "london" in loc_lower or "britain" in loc_lower or "gb" in loc_lower:
            country_code = "gb"
        elif "canada" in loc_lower:
            country_code = "ca"
        elif "india" in loc_lower:
            country_code = "in"
        else:
            country_code = country or "in"

        clean_query = (query or "").strip()
        if not clean_query:
            clean_query = "Software Developer"

        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": clean_query,
            "results_per_page": min(max(results_per_page, 5), 50),
            "content-type": "application/json"
        }
        if location and location.lower() != "remote":
            params["where"] = location

        encoded_params = urllib.parse.urlencode(params)
        primary_url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1?{encoded_params}"

        def _request_json(target_url: str):
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "CareerBot-AdzunaClient/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))
            return None

        payload = None
        try:
            payload = _request_json(primary_url)
        except urllib.error.HTTPError as http_err:
            # If 503 or bad status on country code, attempt fallback to US endpoint
            if country_code != "us" and http_err.code in (400, 500, 502, 503):
                try:
                    fallback_url = f"https://api.adzuna.com/v1/api/jobs/us/search/1?{encoded_params}"
                    payload = _request_json(fallback_url)
                    country_code = "us"
                except Exception:
                    pass
        except Exception:
            pass

        if not payload or not isinstance(payload, dict):
            return []

        raw_results = payload.get("results", [])
        if not raw_results and country_code != "us":
            # If 0 results, retry without location constraint on US directory
            try:
                relaxed_params = dict(params)
                relaxed_params.pop("where", None)
                relaxed_url = f"https://api.adzuna.com/v1/api/jobs/us/search/1?{urllib.parse.urlencode(relaxed_params)}"
                fallback_payload = _request_json(relaxed_url)
                if fallback_payload:
                    raw_results = fallback_payload.get("results", [])
                    country_code = "us"
            except Exception:
                pass

        adzuna_jobs = []
        for item in raw_results:
            adzuna_id = item.get("id")
            title = self._clean_html(item.get("title", "Software Role"))
            company_info = item.get("company") or {}
            company = company_info.get("display_name", "Enterprise Tech").strip()
            loc_info = item.get("location") or {}
            loc_display = loc_info.get("display_name", location or "Remote").strip()
            redirect_url = item.get("redirect_url", "").strip()
            raw_desc = self._clean_html(item.get("description", ""))

            title_lower = title.lower()
            desc_lower = raw_desc.lower()
            loc_lower_str = loc_display.lower()
            if "remote" in title_lower or "remote" in loc_lower_str or "remote" in desc_lower:
                work_mode = "Remote"
            elif "hybrid" in title_lower or "hybrid" in loc_lower_str or "hybrid" in desc_lower:
                work_mode = "Hybrid"
            else:
                work_mode = "On-site"

            if "intern" in title_lower or "fresher" in title_lower or "trainee" in title_lower:
                exp = "Fresher"
            elif "junior" in title_lower or "entry" in title_lower or "graduate" in title_lower:
                exp = "Junior Developer"
            elif "lead" in title_lower or "principal" in title_lower or "architect" in title_lower:
                exp = "5+ years (Lead)"
            elif "senior" in title_lower or "sr" in title_lower:
                exp = "3-5+ years"
            else:
                exp = "1-3 years"

            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            if sal_min or sal_max:
                curr = "₹" if country_code == "in" else ("£" if country_code == "gb" else "$")
                if sal_min and sal_max and sal_min != sal_max:
                    salary_str = f"{curr}{int(sal_min):,} - {curr}{int(sal_max):,}"
                elif sal_min:
                    salary_str = f"{curr}{int(sal_min):,}+"
                else:
                    salary_str = f"Up to {curr}{int(sal_max):,}"
            else:
                salary_str = "Competitive Market Standard"

            extracted_skills = self.skill_extractor.extract_skills(f"{title} {raw_desc[:1200]}")
            if not extracted_skills:
                extracted_skills = ["Software Engineering", "Problem Solving", "Collaboration"]

            job_id_str = f"adzuna_{adzuna_id}" if adzuna_id else f"adzuna_{abs(hash(title + company)) % 10000000}"

            job_obj = {
                "job_id": job_id_str,
                "title": title,
                "company": company,
                "location": loc_display,
                "work_mode": work_mode,
                "job_type": "Full-time",
                "experience": exp,
                "education": "Bachelor's Degree in Computer Science, IT, or related engineering discipline",
                "skills": ", ".join(extracted_skills),
                "required_skills": extracted_skills,
                "preferred_skills": "Strong analytical problem solving and collaborative engineering practices",
                "responsibilities": raw_desc[:300] + ("..." if len(raw_desc) > 300 else ""),
                "description": raw_desc[:1500] if len(raw_desc) > 1500 else raw_desc,
                "keywords": f"{title} {loc_display} {company}".lower(),
                "salary": salary_str,
                "source": "Live Job (Adzuna)",
                "is_live": True,
                "url": redirect_url,
                "apply_url": redirect_url
            }
            adzuna_jobs.append(job_obj)

        return adzuna_jobs

    def search_adzuna(self, query: str = "", location: str = "", country: str = "in", results_per_page: int = 25) -> List[dict]:
        """Direct Adzuna search with result caching by job ID."""
        jobs = self._fetch_adzuna(query=query, location=location, country=country, results_per_page=results_per_page)
        for j in jobs:
            self._cached_jobs_by_id[str(j["job_id"])] = j
        return jobs

    def fetch_live_jobs(self, filters: dict = None, profile_dict: dict = None) -> List[dict]:
        """
        Fetches live jobs using:
        - resume skills / profile skills
        - preferred job role
        - user query / keyword
        - location preference
        - work mode & experience
        """
        filters = filters or {}
        profile_dict = profile_dict or {}

        role_filter = filters.get("role", "").strip()
        loc_filter = filters.get("location", "").strip()
        target_roles = profile_dict.get("target_roles", [])
        resume_skills = profile_dict.get("skills", [])

        # Priority 1: User search query
        if role_filter:
            search_query = role_filter
        # Priority 2: User profile target role
        elif target_roles and target_roles[0]:
            search_query = target_roles[0]
        # Priority 3: Resume-extracted skills
        elif resume_skills:
            search_query = " ".join(resume_skills[:2])
        # Priority 4: Default tech role
        else:
            search_query = "Software Developer"

        cache_key = f"live_feed_{search_query.lower()}_{loc_filter.lower()}"
        now = time.time()
        
        cached_entry = self._cache.get(cache_key)
        if cached_entry and (now - cached_entry.get("timestamp", 0)) < self.cache_ttl:
            raw_live_jobs = cached_entry.get("jobs", [])
        else:
            # Query Adzuna live search API
            adzuna_jobs = self._fetch_adzuna(query=search_query, location=loc_filter)
            # Query public tech job boards (Arbeitnow & Jobicy)
            public_jobs = self._query_external_apis()

            # Combine live jobs: prioritize Adzuna then public APIs
            combined_live = []
            seen_keys = set()
            for job in adzuna_jobs + public_jobs:
                key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
                if key not in seen_keys:
                    seen_keys.add(key)
                    combined_live.append(job)

            raw_live_jobs = combined_live
            self._cache[cache_key] = {
                "timestamp": now,
                "jobs": raw_live_jobs
            }
            for j in raw_live_jobs:
                self._cached_jobs_by_id[str(j["job_id"])] = j

        # Apply context-based search and filter
        return self._filter_and_rank_live_jobs(raw_live_jobs, filters, profile_dict)

    def _query_external_apis(self) -> List[dict]:
        """Queries legitimate job APIs and normalizes results into CareerBot job schemas."""
        collected_jobs = []
        id_counter = 20000

        # 1. Query Arbeitnow Job Board API (Legitimate, free public job board API)
        try:
            req = urllib.request.Request(
                "https://www.arbeitnow.com/api/job-board-api",
                headers={"User-Agent": "CareerBot-StudentRecommender/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    data_items = payload.get("data", [])
                    for item in data_items[:40]:  # Take top 40 current live tech jobs
                        id_counter += 1
                        title = item.get("title", "").strip()
                        company = item.get("company_name", "Tech Enterprise").strip()
                        url = item.get("url", "").strip()
                        location = item.get("location", "Remote").strip()
                        is_remote = item.get("remote", False) or "remote" in location.lower() or "remote" in title.lower()
                        work_mode = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")
                        raw_desc = self._clean_html(item.get("description", ""))
                        
                        tags = item.get("tags", [])
                        extracted_skills = self.skill_extractor.extract_skills(f"{title} {' '.join(tags)} {raw_desc[:800]}")
                        
                        job_types = item.get("job_types", ["Full-time"])
                        job_type = job_types[0] if job_types else "Full-time"
                        
                        exp = "Junior Developer" if "junior" in title.lower() or "graduate" in title.lower() else (
                            "Fresher" if "intern" in title.lower() or "entry" in title.lower() else "1-3 years"
                        )

                        job_obj = {
                            "job_id": str(id_counter),
                            "title": title,
                            "company": company,
                            "location": location,
                            "work_mode": work_mode,
                            "job_type": job_type,
                            "experience": exp,
                            "education": "Degree in Computer Science, IT, or related technical field",
                            "skills": ", ".join(extracted_skills) if extracted_skills else ", ".join(tags[:6]),
                            "required_skills": extracted_skills if extracted_skills else tags[:6],
                            "preferred_skills": "Experience with modern software stacks and version control",
                            "responsibilities": raw_desc[:300] + ("..." if len(raw_desc) > 300 else ""),
                            "description": raw_desc[:1200] if len(raw_desc) > 1200 else raw_desc,
                            "keywords": " ".join(tags),
                            "salary": "Competitive Market Standard",
                            "source": "Live: Arbeitnow",
                            "is_live": True,
                            "url": url
                        }
                        collected_jobs.append(job_obj)
        except Exception:
            pass

        # 2. Query Jobicy Remote Jobs API (Legitimate, clean tech remote jobs)
        try:
            req = urllib.request.Request(
                "https://jobicy.com/api/v2/remote-jobs?count=25",
                headers={"User-Agent": "CareerBot-StudentRecommender/1.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    jobs_data = payload.get("jobs", [])
                    for item in jobs_data:
                        id_counter += 1
                        title = item.get("jobTitle", "").strip()
                        company = item.get("companyName", "Tech Employer").strip()
                        url = item.get("url", "").strip()
                        loc = item.get("jobGeo", "Remote / Global").strip()
                        raw_desc = self._clean_html(item.get("jobDescription", ""))
                        
                        extracted_skills = self.skill_extractor.extract_skills(f"{title} {raw_desc[:800]}")
                        
                        exp = "Junior Developer" if "junior" in title.lower() else (
                            "Fresher" if "intern" in title.lower() else "1-2 years"
                        )

                        job_obj = {
                            "job_id": str(id_counter),
                            "title": title,
                            "company": company,
                            "location": loc or "Remote",
                            "work_mode": "Remote",
                            "job_type": item.get("jobType", ["Full-Time"])[0] if isinstance(item.get("jobType"), list) and item.get("jobType") else "Full-time",
                            "experience": exp,
                            "education": "Bachelor's Degree in Software Engineering or equivalent experience",
                            "skills": ", ".join(extracted_skills) if extracted_skills else "Python, SQL, Git",
                            "required_skills": extracted_skills if extracted_skills else ["Python", "SQL", "Git"],
                            "preferred_skills": "Strong analytical problem solving and communication skills",
                            "responsibilities": raw_desc[:300] + ("..." if len(raw_desc) > 300 else ""),
                            "description": raw_desc[:1200] if len(raw_desc) > 1200 else raw_desc,
                            "keywords": title.lower(),
                            "salary": item.get("annualSalaryMin", "Competitive Market Standard") if item.get("annualSalaryMin") else "Competitive Market Standard",
                            "source": "Live: Jobicy",
                            "is_live": True,
                            "url": url
                        }
                        collected_jobs.append(job_obj)
        except Exception:
            pass

        return collected_jobs

    def _filter_and_rank_live_jobs(self, jobs: List[dict], filters: dict, profile_dict: dict) -> List[dict]:
        """Filters live jobs using resume skills, profile skills, preferred role, and query filters."""
        if not jobs:
            return []

        role_filter = filters.get("role", "").strip().lower()
        loc_filter = filters.get("location", "").strip().lower()
        work_mode_filter = filters.get("work_mode", "").strip().lower()
        exp_filter = filters.get("experience", "").strip().lower()

        resume_skills = profile_dict.get("skills", [])
        target_roles = [r.lower() for r in profile_dict.get("target_roles", []) if r]

        filtered = []
        for job in jobs:
            t = job.get("title", "").lower()
            l = job.get("location", "").lower()
            wm = job.get("work_mode", "").lower()
            e = job.get("experience", "").lower()
            d = job.get("description", "").lower()
            skills_str = job.get("skills", "").lower()

            keep = True
            # Explicit user search query
            if role_filter:
                if role_filter not in t and role_filter not in d and role_filter not in skills_str:
                    keep = False

            # Location filter
            if loc_filter:
                if loc_filter not in l and (loc_filter == "remote" and wm != "remote"):
                    keep = False

            # Work mode filter
            if work_mode_filter:
                if work_mode_filter not in wm:
                    keep = False

            # Experience level filter
            if exp_filter:
                if exp_filter not in e:
                    keep = False

            if keep:
                filtered.append(job)

        return filtered if filtered else jobs

    def get_job_by_id(self, job_id: str) -> Optional[dict]:
        """Retrieves a cached live job by its assigned ID."""
        return self._cached_jobs_by_id.get(str(job_id))


class CombinedJobProvider(JobProvider):
    """
    Coordinates verified database jobs and live internet job postings.
    Performs source-aware deduplication and unified querying.
    """

    def __init__(self, local_provider=None, live_service=None, **kwargs):
        self.local_provider = local_provider or kwargs.get("job_service") or kwargs.get("db_service") or LocalDatasetProvider()
        self.live_service = live_service or kwargs.get("live_job_service") or LiveJobSearchService()

    def _normalize_key(self, title: str, company: str) -> str:
        """Generates a canonical deduplication key from title and company."""
        clean_title = re.sub(r'[^a-z0-9]', '', str(title).lower())
        clean_company = re.sub(r'[^a-z0-9]', '', str(company).lower())
        return f"{clean_title}::{clean_company}"

    def get_all_jobs(self, db_session=None, source: str = "all", filters: dict = None, profile_dict: dict = None) -> list:
        """
        Retrieves jobs according to the requested source ('all', 'database', 'live').
        Deduplicates jobs when appearing from multiple sources.
        """
        try:
            db_jobs = self.local_provider.get_all_jobs(db_session)
        except Exception:
            db_jobs = []
        
        if source == "database":
            return db_jobs

        live_jobs = self.live_service.fetch_live_jobs(filters=filters, profile_dict=profile_dict)
        if source == "live":
            return live_jobs

        # Combine both sources with deduplication
        seen_keys = set()
        combined = []

        # 1. Add verified database jobs first
        for job in db_jobs:
            key = self._normalize_key(job.get("title", ""), job.get("company", ""))
            seen_keys.add(key)
            combined.append(job)

        # 2. Add live jobs if not duplicate
        for job in live_jobs:
            key = self._normalize_key(job.get("title", ""), job.get("company", ""))
            if key not in seen_keys:
                seen_keys.add(key)
                combined.append(job)

        return combined

    def get_job_by_id(self, db_session=None, job_id: Any = None) -> Optional[dict]:
        """Fetches job by ID checking database first, then live jobs cache."""
        # Check database first
        try:
            job = self.local_provider.get_job_by_id(db_session, job_id)
            if job:
                return job
        except Exception:
            pass

        # Check live jobs cache
        return self.live_service.get_job_by_id(str(job_id))


# Standalone provider instance for application-wide use
job_provider = CombinedJobProvider()
