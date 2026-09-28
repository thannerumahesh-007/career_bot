"""
Job Description Analyzer for CareerBot.
Parses job titles, descriptions, and responsibilities into structured attributes.
"""

from nlp.skill_extractor import SkillExtractor


class JobAnalyzer:
    """Extracts required skills and attributes from job postings."""

    def __init__(self):
        self.extractor = SkillExtractor()

    def analyze_job(self, job_dict: dict) -> dict:
        """Analyzes a job record dictionary and extracts canonical skills and attributes."""
        title = job_dict.get("title", "")
        description = job_dict.get("description", "")
        responsibilities = job_dict.get("responsibilities", "")
        raw_skills = job_dict.get("skills", "")

        # Combine text fields for full skill coverage
        combined_text = f"{title} {description} {responsibilities} {raw_skills}"
        extracted_skills = self.extractor.extract_skills(combined_text)

        return {
            "job_id": job_dict.get("job_id"),
            "title": title,
            "company": job_dict.get("company", "Tech Company"),
            "location": job_dict.get("location", "Remote"),
            "job_type": job_dict.get("job_type", "Full-time"),
            "experience": job_dict.get("experience", "Entry Level"),
            "required_skills": extracted_skills,
            "description": description,
            "responsibilities": responsibilities,
            "salary": job_dict.get("salary", "Competitive"),
            "url": job_dict.get("url", "demo://jobs")
        }
