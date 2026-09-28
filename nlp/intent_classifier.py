"""
Intent Classification Module for CareerBot.
Classifies natural-language user messages into standard intent categories.
"""

import re

STANDARD_INTENTS = {
    "profile_update",
    "job_search",
    "job_details",
    "role_skills",
    "skill_gap",
    "career_advice",
    "learning_roadmap",
    "resume_analysis",
    "general_career_question",
    "greeting",
    "help",
    "unknown"
}

class IntentClassifier:
    """Classifies user chat messages into standard intent categories."""

    def classify_intent(self, message: str) -> str:
        """Determines intent of a user message. Always returns one of the standard intents."""
        if not message or not message.strip():
            return "unknown"

        msg_lower = message.strip().lower()

        # 1. Greetings
        if re.search(r'^(hi|hello|hey|greetings|good morning|good afternoon|good evening|howdy)\b', msg_lower):
            return "greeting"

        # 2. Help
        if any(kw in msg_lower for kw in ["help", "how to use", "how do i use", "what can you do", "instructions", "guide", "how does this work"]):
            return "help"

        # 3. Resume Analysis
        if any(kw in msg_lower for kw in ["my resume", "upload resume", "analyze my resume", "parse resume", "resume score", "check my cv"]):
            return "resume_analysis"

        # 4. Job Details (specific job inspection)
        if any(kw in msg_lower for kw in ["job details", "show job", "view job", "details of job", "tell me about job"]):
            return "job_details"

        # 5. Skill Gap Analysis (user asking what THEY are missing)
        if any(kw in msg_lower for kw in [
            "missing skills", "skill gap", "what am i missing", "missing skill",
            "skills am i missing", "what skills am i missing", "what do i lack", "where is my gap"
        ]):
            return "skill_gap"

        # 6. Role Skills Requirement (what skills does a role require)
        if any(kw in msg_lower for kw in [
            "skills do i need", "skills are required", "skills needed", "required skills",
            "skills for java", "skills for python", "skills for data science", "skills for machine learning",
            "what skills should i learn for", "technologies needed for", "requirements for"
        ]) or (("what skills" in msg_lower or "which skills" in msg_lower) and ("need" in msg_lower or "require" in msg_lower or "for" in msg_lower)):
            return "role_skills"

        # 7. Learning Roadmap
        if any(kw in msg_lower for kw in ["roadmap", "learning path", "what should i learn", "how to become", "steps to become", "learning roadmap"]):
            return "learning_roadmap"

        # 8. Career Advice
        if any(kw in msg_lower for kw in ["advice", "career option", "career guidance", "recommend role", "which role", "how can i become"]):
            return "career_advice"

        # 9. Explicit Job Search
        if any(kw in msg_lower for kw in [
            "find job", "find jobs", "search job", "search jobs", "looking for job",
            "looking for jobs", "show jobs", "recommend job", "recommend jobs", "jobs for me",
            "vacancies", "openings", "hire", "hiring"
        ]) or re.search(r'\b(find|search|show|recommend|look for|looking for|get)\b.*\b(job|jobs|position|positions|opening|openings|posting|postings|vacancy|vacancies)\b', msg_lower) or (re.search(r'\b(jobs|openings|vacancies)\b', msg_lower) and not re.search(r'^(what is|what are|explain)\b', msg_lower)):
            return "job_search"

        # 10. General Technical & Career Questions (e.g. "What is Data Science?", "Explain Machine Learning")
        if any(kw in msg_lower for kw in ["what is", "what are", "explain", "tell me about", "difference between", "how does", "why is"]):
            return "general_career_question"

        # 11. Profile Update
        if any(kw in msg_lower for kw in ["i know", "my skills are", "i am skilled at", "i have learned", "add skill"]):
            return "profile_update"

        if msg_lower.endswith("?"):
            return "general_career_question"

        return "unknown"

