"""
Intent Classification Module for CareerBot.
Classifies natural-language user messages into standard intent categories.
Supports feature-aware intents for AI Interview, ATS Resume Builder, Company Following, News, and Career Skills.
"""

import re
from typing import Set

STANDARD_INTENTS: Set[str] = {
    "greeting",
    "career_skill_requirements",
    "skill_question",
    "job_search",
    "job_links",
    "resume_matched_jobs",
    "job_details",
    "resume_analysis",
    "resume_builder",
    "ats_analysis",
    "skill_gap",
    "career_roadmap",
    "company_search",
    "company_following",
    "corporate_news",
    "interview_start",
    "interview_question",
    "interview_feedback",
    "general_career_question",
    "profile_update",
    "help",
    "unknown",
    # Legacy aliases for backward compatibility
    "role_skills",
    "learning_roadmap",
    "career_advice"
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
        if any(kw in msg_lower for kw in [
            "help", "how to use", "how do i use", "what can you do", "instructions",
            "guide", "how does this work", "what are your features"
        ]):
            return "help"

        # 3. Job Links Follow-up ("I need links for those", "Give me the links", "Apply links")
        if any(kw in msg_lower for kw in [
            "links for those", "links for these", "links for them", "give me the links",
            "give me links", "need links for those", "need links", "apply links for those",
            "where can i apply for those", "send me the links", "links please", "url for those",
            "give links", "apply links"
        ]) or re.search(r'\b(need|give|send|provide|show|get)\b.*\b(link|links|url|urls|apply link)\b.*\b(those|these|them|above|jobs)\b', msg_lower) or msg_lower in ["links", "give links", "apply links", "i need links for those"]:
            return "job_links"

        # 4. Resume-Matched Jobs ("Find jobs that match my resume", "I need links for jobs that match my resume")
        if any(kw in msg_lower for kw in [
            "jobs that match my resume", "jobs matching my resume", "match my resume",
            "matching my resume", "jobs for my resume", "links for jobs that match my resume",
            "find jobs that match my resume", "which ones match my resume", "which jobs match my resume"
        ]) or re.search(r'\b(job|jobs|vacancies|openings|positions|links)\b.*\b(match|matching|for)\b.*\b(my resume|my profile|resume|cv)\b', msg_lower):
            return "resume_matched_jobs"

        # 5. AI Interview Simulator
        if any(kw in msg_lower for kw in [
            "start interview", "take interview", "mock interview", "interview me",
            "start a java interview", "start python interview", "start technical interview",
            "practice interview", "interview simulator", "conduct interview", "begin interview"
        ]) or re.search(r'\b(start|practice|begin|conduct|take)\b.*\binterview\b', msg_lower):
            return "interview_start"

        # 6. ATS Score & ATS Analysis
        if any(kw in msg_lower for kw in [
            "ats score", "check my ats", "ats check", "ats analysis", "ats rating",
            "check ats score", "test my ats", "ats compatibility", "ats review"
        ]):
            return "ats_analysis"

        # 7. Resume Builder
        if any(kw in msg_lower for kw in [
            "build my resume", "resume builder", "create resume", "make resume",
            "generate resume", "ats resume builder", "build resume", "edit resume",
            "improve my resume for", "optimize resume", "write my resume"
        ]):
            return "resume_builder"

        # 8. Resume Analysis (Private Upload Parser)
        if any(kw in msg_lower for kw in [
            "upload resume", "analyze my resume", "parse resume",
            "check my cv", "view resume", "inspect resume"
        ]) or (msg_lower in ["my resume", "view my resume"]):
            return "resume_analysis"

        # 7. Company Following & Search
        if any(kw in msg_lower for kw in [
            "follow company", "unfollow company", "following companies", "followed companies",
            "companies i follow", "follow microsoft", "follow google", "follow amazon",
            "unfollow"
        ]) or re.search(r'\b(follow|unfollow)\s+[A-Za-z0-9]+', msg_lower):
            return "company_following"

        if any(kw in msg_lower for kw in ["search company", "find company", "browse companies", "list companies"]):
            return "company_search"

        # 8. Corporate & Tech News
        if any(kw in msg_lower for kw in [
            "corporate news", "tech news", "latest news", "company news", "show news",
            "hiring news", "market news", "industry news", "news about"
        ]) or re.search(r'\bnews\b', msg_lower):
            return "corporate_news"

        # 9. Skill Gap Analysis (user asking what THEY are missing)
        if any(kw in msg_lower for kw in [
            "missing skills", "skill gap", "what am i missing", "missing skill",
            "skills am i missing", "what skills am i missing", "what do i lack",
            "where is my gap", "show my missing skills", "identify skill gap"
        ]):
            return "skill_gap"

        # 10. Role Skill Requirements (what skills does a role require)
        has_skill_keyword = any(kw in msg_lower for kw in [
            "skill", "skills", "स्किल्स", "कौशल", "స్కిల్స్", "నైపుణ్యాలు"
        ])
        has_indic_skill_query = any(kw in msg_lower for kw in [
            "क्या स्किल्स", "क्या स्किल", "स्किल्स चाहिए", "कौशल चाहिए", "बनने के लिए क्या",
            "मुझे पाइथन स्किल्स", "पाइथन स्किल्स", "जावा स्किल्स",
            "ఏ స్కిల్స్", "స్కిల్స్ కావాలి", "నైపుణ్యాలు కావాలి", "కావడానికి ఏ స్కిల్స్", "పైథాన్ స్కిల్స్"
        ])

        if (
            has_indic_skill_query
            or any(kw in msg_lower for kw in [
                "skills do i need", "skills are required", "skills needed", "required skills",
                "skills for java", "skills for python", "skills for data science",
                "skills for data analyst", "skills for machine learning",
                "what skills should i learn for", "technologies needed for", "requirements for",
                "what does a data analyst need", "what does a java developer need",
                "skill requirements", "core skills for", "python skills", "java skills",
                "developer skills"
            ])
            or (("what skills" in msg_lower or "which skills" in msg_lower) and ("need" in msg_lower or "require" in msg_lower or "for" in msg_lower))
            or (has_skill_keyword and any(kw in msg_lower for kw in ["पाइथन", "पायथन", "जावा", "python", "java", "developer", "डेवलपर", "డెవలపర్", "పైథాన్", "జావా"]))
        ):
            return "career_skill_requirements"

        # 11. Career Advice
        if any(kw in msg_lower for kw in [
            "how can i become", "how do i become", "how to become", "career advice",
            "become a", "transition to", "break into"
        ]):
            return "career_advice"

        # 12. Career Learning Roadmap
        if any(kw in msg_lower for kw in [
            "roadmap", "learning path", "what should i learn",
            "steps to become", "learning roadmap", "career path", "career roadmap",
            "milestones for"
        ]):
            return "learning_roadmap"

        # 12. Job Details (specific job inspection)
        if any(kw in msg_lower for kw in ["job details", "show job", "view job", "details of job", "tell me about job"]):
            return "job_details"

        # 13. Explicit Job Search
        if any(kw in msg_lower for kw in [
            "find job", "find jobs", "search job", "search jobs", "looking for job",
            "looking for jobs", "show jobs", "recommend job", "recommend jobs", "jobs for me",
            "vacancies", "openings", "hire", "hiring", "live jobs", "internet jobs"
        ]) or re.search(r'\b(find|search|show|recommend|look for|looking for|get)\b.*\b(job|jobs|position|positions|opening|openings|posting|postings|vacancy|vacancies)\b', msg_lower) or (re.search(r'\b(jobs|openings|vacancies)\b', msg_lower) and not re.search(r'^(what is|what are|explain)\b', msg_lower)):
            return "job_search"

        # 14. General Technical & Career Questions, Explanations & Follow-ups
        if any(kw in msg_lower for kw in [
            "what is", "what are", "explain", "tell me about", "difference between",
            "how does", "why is", "what about", "how about", "tell me more", "in detail",
            "detailed explanation", "give me a detailed", "explain that", "explain this",
            "elaborate", "can you explain", "describe", "in simple terms", "what certifications",
            "which certifications", "certifications for", "what projects", "projects for"
        ]):
            return "general_career_question"

        # 15. Profile Update
        if any(kw in msg_lower for kw in ["i know", "my skills are", "i am skilled at", "i have learned", "add skill"]):
            return "profile_update"

        if msg_lower.endswith("?"):
            return "general_career_question"

        return "unknown"
