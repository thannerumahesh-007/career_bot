"""
Job Ranking & Pre-Filtering Engine for CareerBot.
Applies search filters prior to score calculation and handles threshold-based match alerts.
"""

from config import Config
from recommender.matcher import JobMatcher
from nlp.skill_extractor import SkillExtractor


def extract_filters_from_query(query: str) -> dict:
    """Extracts explicit filter criteria (role, location, work mode, experience) from query text."""
    if not query:
        return {}

    extractor = SkillExtractor()
    query_lower = query.lower()

    filters = {}
    
    # Location
    loc = extractor.extract_location(query)
    if loc:
        filters["location"] = loc

    # Work Mode / Remote
    if "remote" in query_lower:
        filters["work_mode"] = "Remote"

    # Target Role
    roles = extractor.extract_target_roles(query)
    if roles:
        filters["role"] = roles[0]

    # Experience Level
    exp = extractor.extract_experience(query)
    if exp:
        filters["experience"] = exp

    return filters


class JobRanker:
    """Filters, scores, and ranks job postings for a given user profile."""

    def __init__(self):
        self.matcher = JobMatcher()

    def filter_jobs(self, jobs: list, filters: dict) -> list:
        """Filters job list based on criteria prior to scoring."""
        if not filters:
            return jobs

        filtered = []
        for job in jobs:
            title = job.get("title", "").lower()
            location = job.get("location", "").lower()
            job_type = job.get("job_type", "").lower()
            exp = job.get("experience", "").lower()

            keep = True
            if "role" in filters and filters["role"].lower() not in title:
                keep = False
            if "location" in filters and filters["location"].lower() not in location:
                keep = False
            if "work_mode" in filters and filters["work_mode"].lower() == "remote" and "remote" not in location and "remote" not in job_type:
                keep = False
            if "experience" in filters and filters["experience"].lower() not in exp:
                # Allow intern/fresher cross-matching
                if not ("intern" in filters["experience"].lower() and "intern" in exp):
                    keep = False

            if keep:
                filtered.append(job)

        # If filtering is too strict and returns zero jobs, return original list to avoid empty results
        return filtered if filtered else jobs

    def rank_recommendations(self, user_profile: dict, jobs: list, query_filters: dict = None) -> dict:
        """Filters jobs, computes match scores, ranks results, and generates threshold notifications."""
        if not jobs:
            return {
                "results": [],
                "has_strong_match": False,
                "message": "No jobs currently available in dataset.",
                "total_analyzed": 0
            }

        # 1. Filter jobs first
        candidates = self.filter_jobs(jobs, query_filters or {})

        # 2. Match each candidate job
        scored_jobs = []
        for job in candidates:
            # Format raw skills if necessary
            raw_skills = job.get("skills", [])
            if isinstance(raw_skills, str):
                job["required_skills"] = [s.strip() for s in raw_skills.split(",") if s.strip()]
            else:
                job["required_skills"] = raw_skills

            match_result = self.matcher.match_job(user_profile, job)
            scored_jobs.append(match_result)

        # 3. Rank results by overall score descending
        scored_jobs.sort(key=lambda x: x["overall_score"], reverse=True)

        # 4. Threshold check
        max_score = scored_jobs[0]["overall_score"] if scored_jobs else 0.0
        has_strong_match = max_score >= Config.STRONG_MATCH_THRESHOLD

        if has_strong_match:
            msg = "Here are your top matched job opportunities!"
        else:
            msg = "No strong match found. Here are the closest available opportunities based on your current profile."

        return {
            "results": scored_jobs,
            "has_strong_match": has_strong_match,
            "message": msg,
            "total_analyzed": len(jobs),
            "filtered_count": len(candidates)
        }
