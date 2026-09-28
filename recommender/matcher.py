"""
Job Recommendation Matching Engine for CareerBot.
Implements normalized 4-component scoring and transparent match explainability.
"""

from config import Config
from nlp.skill_dictionary import normalize_skill_key, normalize_skill
from nlp.semantic_similarity import SemanticSimilarityEngine

class JobMatcher:
    """Calculates multi-factor job match score and generates clear explanations."""

    def __init__(self):
        self.semantic_engine = SemanticSimilarityEngine()

    def calculate_skill_score(self, user_skills: list, job_skills: list) -> tuple:
        """
        Calculates SkillScore = (Number of matching required skills) / (Total required skills).
        Returns (skill_score [0.0-1.0], matching_skills, missing_skills).
        """
        if not job_skills:
            return 1.0, [], []

        # Map to canonical lowercased keys for exact matching
        user_key_map = {normalize_skill_key(s): s for s in user_skills if s}
        job_key_map = {normalize_skill_key(s): s for s in job_skills if s}

        user_keys = set(user_key_map.keys())
        job_keys = set(job_key_map.keys())

        if not job_keys:
            return 1.0, [], []

        matching_keys = user_keys.intersection(job_keys)
        missing_keys = job_keys - user_keys

        skill_score = len(matching_keys) / float(len(job_keys))

        matching_display = [normalize_skill(job_key_map[k]) for k in matching_keys]
        missing_display = [normalize_skill(job_key_map[k]) for k in missing_keys]

        return min(1.0, max(0.0, skill_score)), sorted(matching_display), sorted(missing_display)

    def calculate_interest_score(self, user_interests: list, job_title: str, job_desc: str) -> float:
        """Calculates interest alignment score [0.0 to 1.0]."""
        if not user_interests:
            return 0.5  # Neutral default

        text_lower = f"{job_title} {job_desc}".lower()
        matches = 0
        for interest in user_interests:
            if interest.lower() in text_lower:
                matches += 1

        score = matches / float(len(user_interests))
        return min(1.0, max(0.0, score if matches > 0 else 0.2))

    def calculate_experience_score(self, user_exp: str, job_exp: str) -> float:
        """Calculates experience level alignment score [0.0 to 1.0]."""
        if not user_exp or not job_exp:
            return 0.5  # Default neutral score

        u_exp = user_exp.lower()
        j_exp = job_exp.lower()

        if u_exp == j_exp:
            return 1.0
        
        # Student / Fresher / Intern compatibility
        fresher_tokens = ["fresher", "intern", "entry level", "student"]
        if any(t in u_exp for t in fresher_tokens) and any(t in j_exp for t in fresher_tokens):
            return 1.0

        if "1-2 years" in u_exp and ("entry level" in j_exp or "1-2 years" in j_exp):
            return 1.0

        if "fresher" in u_exp and "1-2 years" in j_exp:
            return 0.6

        return 0.4

    def match_job(self, user_profile: dict, job: dict) -> dict:
        """
        Executes complete match analysis for a single job posting.
        Formula: OverallScore = 0.50*SkillScore + 0.25*SemanticScore + 0.15*InterestScore + 0.10*ExpScore
        """
        user_skills = user_profile.get("skills", [])
        user_interests = user_profile.get("interests", [])
        user_exp = user_profile.get("experience", "")
        user_goals = " ".join(user_profile.get("target_roles", []))
        user_edu = user_profile.get("education", "")

        job_title = job.get("title", "")
        job_skills = job.get("required_skills", [])
        if isinstance(job_skills, str):
            job_skills = [s.strip() for s in job_skills.split(",") if s.strip()]
        job_desc = job.get("description", "")
        job_resp = job.get("responsibilities", "")
        job_exp = job.get("experience", "")

        has_resume = user_profile.get("has_resume")
        if has_resume is None:
            has_resume = bool(user_skills)

        # Requirement 1 & 5: If no resume is uploaded or skills empty, do not calculate match scores
        if not has_resume or not user_skills:
            return {
                "job_id": job.get("job_id"),
                "title": job_title,
                "company": job.get("company"),
                "location": job.get("location"),
                "work_mode": job.get("work_mode", "Not specified"),
                "job_type": job.get("job_type", "Full-time"),
                "experience": job_exp,
                "education": job.get("education"),
                "skills": job.get("skills", ""),
                "preferred_skills": job.get("preferred_skills", ""),
                "description": job_desc,
                "responsibilities": job_resp,
                "salary": job.get("salary", "Competitive Market Standard"),
                "source": job.get("source", "CareerBot Database"),
                "is_live": job.get("is_live", False),
                "url": job.get("url", ""),
                "apply_url": job.get("apply_url") or job.get("url", ""),
                "overall_score": 0.0,
                "has_match": False,
                "match_percentage": None,
                "match_band": "Upload resume to calculate match",
                "match_label": "Upload resume to calculate match",
                "skill_score": 0.0,
                "skill_pct": 0,
                "semantic_score": 0.0,
                "semantic_pct": 0,
                "interest_score": 0.0,
                "interest_pct": 0,
                "experience_score": 0.0,
                "experience_pct": 0,
                "matching_skills": [],
                "missing_skills": job_skills,
                "explanation": {
                    "summary": "Upload resume to calculate match",
                    "matching_skills": [],
                    "missing_skills": job_skills,
                    "interest_alignment": "Upload resume to calculate",
                    "experience_alignment": "Upload resume to calculate"
                },
                "raw_job": job
            }

        # 1. Skill Score
        skill_score, matching_skills, missing_skills = self.calculate_skill_score(user_skills, job_skills)

        # 2. Semantic Score
        user_text = f"{' '.join(user_skills)} {' '.join(user_interests)} {user_goals} {user_edu}".strip()
        job_text = f"{job_title} {job_desc} {job_resp} {' '.join(job_skills)}".strip()
        semantic_score = self.semantic_engine.calculate_similarity(user_text, job_text)

        # 3. Interest Score
        interest_score = self.calculate_interest_score(user_interests, job_title, job_desc)

        # 4. Experience Score
        exp_score = self.calculate_experience_score(user_exp, job_exp)

        # 5. Overall Weighted Formula
        overall_score = (
            Config.WEIGHT_SKILL * skill_score +
            Config.WEIGHT_SEMANTIC * semantic_score +
            Config.WEIGHT_INTEREST * interest_score +
            Config.WEIGHT_EXPERIENCE * exp_score
        )
        overall_score = min(1.0, max(0.0, overall_score))
        match_percentage = round(overall_score * 100, 1)

        # Assign match recommendation label
        if overall_score >= Config.STRONG_MATCH_THRESHOLD:
            match_label = "Strong Match"
        elif overall_score >= Config.MODERATE_MATCH_THRESHOLD:
            match_label = "Moderate Match"
        else:
            match_label = "Limited Match"

        # Generate structured explainability details
        explanation = {
            "summary": f"{match_percentage}% — {match_label}",
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "interest_alignment": "Strong domain match with your interests" if interest_score > 0.6 else "Moderate domain alignment",
            "experience_alignment": "Direct fit for your experience level" if exp_score > 0.7 else "May require slight role adjustment"
        }

        return {
            "job_id": job.get("job_id"),
            "title": job_title,
            "company": job.get("company"),
            "location": job.get("location"),
            "work_mode": job.get("work_mode", "Not specified"),
            "job_type": job.get("job_type", "Full-time"),
            "experience": job_exp,
            "education": job.get("education"),
            "skills": job.get("skills", ""),
            "preferred_skills": job.get("preferred_skills", ""),
            "description": job_desc,
            "responsibilities": job_resp,
            "salary": job.get("salary", "Competitive Market Standard"),
            "source": job.get("source", "CareerBot Database"),
            "is_live": job.get("is_live", False),
            "url": job.get("url", ""),
            "apply_url": job.get("apply_url") or job.get("url", ""),
            "overall_score": round(overall_score, 4),
            "has_match": True,
            "match_percentage": match_percentage,
            "match_band": match_label,
            "match_label": match_label,
            "skill_score": round(skill_score, 2),
            "skill_pct": round(skill_score * 100, 1),
            "semantic_score": round(semantic_score, 2),
            "semantic_pct": round(semantic_score * 100, 1),
            "interest_score": round(interest_score, 2),
            "interest_pct": round(interest_score * 100, 1),
            "experience_score": round(exp_score, 2),
            "experience_pct": round(exp_score * 100, 1),
            "component_scores": {
                "skill_score": round(skill_score, 2),
                "semantic_score": round(semantic_score, 2),
                "interest_score": round(interest_score, 2),
                "experience_score": round(exp_score, 2)
            },
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "explanation": explanation,
            "raw_job": job
        }

