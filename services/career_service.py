"""
Career Service Coordinator for CareerBot.
Integrates database sessions, NLP extractors, intent classification, job matchers, and LLM fallbacks.
"""

from database.models import UserProfile, ChatHistory
from nlp.skill_extractor import SkillExtractor
from nlp.intent_classifier import IntentClassifier
from recommender.ranking import JobRanker, extract_filters_from_query
from recommender.skill_gap import SkillGapAnalyzer
from services.job_service import job_provider, LiveJobSearchService
from services.career_knowledge import extract_role_from_text
from services.gemini_service import GeminiService
import re


class CareerService:
    """Core domain service for orchestrating user operations."""

    def __init__(self):
        self.skill_extractor = SkillExtractor()
        self.intent_classifier = IntentClassifier()
        self.ranker = JobRanker()
        self.gap_analyzer = SkillGapAnalyzer()
        self.job_provider = job_provider
        self.live_job_service = LiveJobSearchService()
        self.gemini_service = GeminiService()

    def get_or_create_user_profile(self, db, user_id: int) -> UserProfile:
        """Fetches or initializes the persistent user profile for the given user_id."""
        if not user_id:
            raise ValueError("user_id is required to fetch profile.")
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id, name="CareerBot Student")
            db.add(profile)
            db.commit()
            db.refresh(profile)

        # Requirement 1: Resume is the ONLY source of profile skills!
        from database.models import Resume
        active_resume = db.query(Resume).filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
        if not active_resume:
            if profile.skills:
                profile.skills = []
                db.commit()
                db.refresh(profile)
        else:
            if active_resume.extracted_data and "skills" in active_resume.extracted_data:
                r_skills = active_resume.extracted_data.get("skills", [])
                if set(profile.skills) != set(r_skills):
                    profile.skills = r_skills
                    db.commit()
                    db.refresh(profile)

        return profile

    def update_user_profile(self, db, user_id: int, new_data: dict) -> UserProfile:
        """Updates user profile for specific user_id and saves to SQLite database."""
        profile = self.get_or_create_user_profile(db, user_id)
        profile.merge_profile_data(new_data)
        db.commit()
        db.refresh(profile)
        return profile

    def replace_user_profile(self, db, user_id: int, new_data: dict) -> UserProfile:
        """Replaces user profile skills & data for specific user_id and saves to SQLite database."""
        profile = self.get_or_create_user_profile(db, user_id)
        profile.replace_profile_data(new_data)
        db.commit()
        db.refresh(profile)
        return profile

    def process_chat_message(self, db, user_id: int, message: str, language: str = "en-IN") -> dict:
        """Processes a chat message for specific user_id, classifies intent, and returns bot response WITHOUT modifying profile skills."""
        if not message or not message.strip():
            return {
                "response": "Please enter a valid message.",
                "intent": "unknown",
                "profile": self.get_or_create_user_profile(db, user_id).to_dict()
            }

        # 1. Classify intent
        intent = self.intent_classifier.classify_intent(message)

        # 2. Load profile - REQUIREMENT 2: NEVER MODIFY PROFILE SKILLS FROM CHAT MESSAGES
        from database.models import Resume
        active_resume = db.query(Resume).filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
        profile = self.get_or_create_user_profile(db, user_id)
        profile_dict = profile.to_dict()
        profile_dict["has_resume"] = active_resume is not None
        if not active_resume:
            profile_dict["skills"] = []
        else:
            profile_dict["skills"] = active_resume.extracted_data.get("skills", []) if active_resume.extracted_data else []

        # query_context is strictly temporary for this turn, NEVER saved to profile
        query_context = self.skill_extractor.extract_profile_data(message)

        # Fetch recent chat history for conversation context (10 turns for seamless follow-ups)
        recent_history_records = db.query(ChatHistory).filter_by(user_id=user_id).order_by(ChatHistory.created_at.desc()).limit(10).all()
        history_list = [{"sender": r.sender, "message": r.message} for r in reversed(recent_history_records)]

        # 3. Handle Job Search, Resume Matching & Job Links Intents with Live Search
        match_data = {"results": []}

        if intent == "job_search":
            detected_role = extract_role_from_text(message)
            explicit_skills = self.skill_extractor.extract_skills(message)
            query_filters = extract_filters_from_query(message)
            
            # Construct a targeted search query for live job APIs
            search_query = detected_role or query_filters.get("role") or ""
            if not search_query:
                # Remove common conversational terms to find the real search keyword
                cleaned_kw = re.sub(r'\b(find|search|jobs?|vacancies|openings|positions|for|me|in|please|give|show)\b', '', message, flags=re.IGNORECASE).strip()
                search_query = cleaned_kw if len(cleaned_kw) > 2 else "Software Developer"

            # Query live jobs via LiveJobSearchService (Adzuna + legitimate public boards)
            live_jobs = self.live_job_service.fetch_live_jobs(
                filters={"role": search_query, "skills": explicit_skills, "location": query_filters.get("location", "")},
                profile_dict=profile_dict
            )
            if not live_jobs and search_query:
                live_jobs = self.live_job_service.search_adzuna(query=search_query, country="in")
            if not live_jobs and search_query:
                live_jobs = self.live_job_service.search_adzuna(query=search_query, country="us")

            # Rank and score results deterministically against user profile/skills if available
            ranked = self.ranker.rank_recommendations(profile_dict, live_jobs, query_filters)
            match_data = ranked
            for j in match_data.get("results", []):
                j["is_live"] = True
                if not j.get("source") or "Database" in j.get("source"):
                    j["source"] = "Live Internet Job"

        elif intent == "resume_matched_jobs":
            if not active_resume or not profile_dict.get("skills"):
                match_data = {"results": [], "no_resume": True}
            else:
                resume_skills = profile_dict.get("skills", [])
                target_role = profile_dict.get("target_roles", ["Software Engineer"])[0] if profile_dict.get("target_roles") else "Software Engineer"
                live_jobs = self.live_job_service.fetch_live_jobs(
                    filters={"role": target_role, "skills": resume_skills},
                    profile_dict=profile_dict
                )
                if not live_jobs:
                    live_jobs = self.live_job_service.search_adzuna(query=target_role, country="in")
                ranked = self.ranker.rank_recommendations(profile_dict, live_jobs, {"role": target_role})
                match_data = ranked
                match_data["has_resume"] = True
                for j in match_data.get("results", []):
                    j["is_live"] = True
                    if not j.get("source") or "Database" in j.get("source"):
                        j["source"] = "Live Internet Job"

        elif intent == "job_links":
            extracted_prev_jobs = self._extract_jobs_from_history(history_list)
            match_data = {"results": extracted_prev_jobs, "is_link_request": True}

        else:
            # Default background job context if user mentions specific role or job
            query_filters = extract_filters_from_query(message)
            job_id_match = re.search(r'\bjob\s*(?:id\s*)?#?(\d+)\b', message.lower())
            if job_id_match:
                jid = job_id_match.group(1)
                target_job = self.job_provider.get_job_by_id(db, jid)
                if target_job:
                    single_match = self.ranker.matcher.match_job(profile_dict, target_job)
                    match_data["results"] = [single_match]

        # 4. Generate bot response text with context and language
        bot_reply = self.gemini_service.generate_chat_response(intent, message, profile_dict, match_data, history=history_list, language=language)

        # 5. Log chat interaction bound to user_id
        user_msg = ChatHistory(user_id=user_id, sender="user", message=message, intent=intent)
        bot_msg = ChatHistory(user_id=user_id, sender="bot", message=bot_reply, intent=intent)
        db.add(user_msg)
        db.add(bot_msg)
        db.commit()

        # 6. Generate clean text for TTS voice synthesis (no markdown symbols)
        from services.text_cleaner import clean_text_for_tts
        tts_text = clean_text_for_tts(bot_reply)

        return {
            "success": True,
            "response": bot_reply,
            "tts_text": tts_text,
            "intent": intent,
            "profile": profile_dict,
            "recommendations": match_data.get("results", [])[:3]
        }

    def _extract_jobs_from_history(self, history_list: list) -> list:
        """Extracts job entries and application URLs from recent conversation history."""
        if not history_list:
            return []

        jobs = []
        for turn in reversed(history_list):
            msg = turn.get("message", "")
            if turn.get("sender") == "bot":
                # Look for bullet/numbered job listings with URLs
                job_blocks = re.split(r'\n(?=(?:\*{1,2}\d+\.|\d+\.|\•)\s*)', msg)
                for block in job_blocks:
                    url_match = re.search(r'https?://[^\s\)\"\'>]+', block)
                    title_match = re.search(r'(?:\*{1,2}\d+\.|\d+\.|\•)\s*([^\n\:\*]+)', block)
                    comp_match = re.search(r'Company:\s*([^\n]+)', block) or re.search(r'at\s+([A-Za-z0-9\s]+)', block)
                    if url_match:
                        url = url_match.group(0).rstrip('.)')
                        title = title_match.group(1).strip() if title_match else "Job Opening"
                        company = comp_match.group(1).strip() if comp_match else "Company"
                        jobs.append({
                            "title": title,
                            "company": company,
                            "url": url,
                            "apply_url": url,
                            "source": "Live Internet Job"
                        })

                if jobs:
                    return jobs[:5]

                # Fallback: look for direct markdown links
                link_matches = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', msg)
                if link_matches:
                    for label, url in link_matches:
                        jobs.append({
                            "title": label,
                            "company": "Job Opening",
                            "url": url,
                            "apply_url": url,
                            "source": "Live Internet Job"
                        })
                    return jobs[:5]

        return jobs

