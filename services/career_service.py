"""
Career Service Coordinator for CareerBot.
Integrates database sessions, NLP extractors, intent classification, job matchers, and LLM fallbacks.
"""

from database.models import UserProfile, ChatHistory
from nlp.skill_extractor import SkillExtractor
from nlp.intent_classifier import IntentClassifier
from recommender.ranking import JobRanker, extract_filters_from_query
from recommender.skill_gap import SkillGapAnalyzer
from services.job_service import LocalDatasetProvider
from services.gemini_service import GeminiService


class CareerService:
    """Core domain service for orchestrating user operations."""

    def __init__(self):
        self.skill_extractor = SkillExtractor()
        self.intent_classifier = IntentClassifier()
        self.ranker = JobRanker()
        self.gap_analyzer = SkillGapAnalyzer()
        self.job_provider = LocalDatasetProvider()
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

        # 3. Get job match recommendations if relevant
        query_filters = extract_filters_from_query(message)
        all_jobs = self.job_provider.get_all_jobs(db)
        match_data = self.ranker.rank_recommendations(profile_dict, all_jobs, query_filters)

        # Check if user mentioned a specific job ID (e.g. "view job 1", "job 12", "details of job 5")
        import re
        job_id_match = re.search(r'\bjob\s*(?:id\s*)?#?(\d+)\b', message.lower())
        if job_id_match:
            jid = job_id_match.group(1)
            target_job = self.job_provider.get_job_by_id(db, jid)
            if target_job:
                single_match = self.ranker.matcher.match_job(profile_dict, target_job)
                match_data["results"] = [single_match] + [r for r in match_data.get("results", []) if str(r.get("job_id")) != str(jid)]

        # Fetch recent chat history for conversation context
        recent_history_records = db.query(ChatHistory).filter_by(user_id=user_id).order_by(ChatHistory.created_at.desc()).limit(6).all()
        history_list = [{"sender": r.sender, "message": r.message} for r in reversed(recent_history_records)]

        # 4. Generate bot response text with context and language
        bot_reply = self.gemini_service.generate_chat_response(intent, message, profile_dict, match_data, history=history_list, language=language)

        # 5. Log chat interaction bound to user_id
        user_msg = ChatHistory(user_id=user_id, sender="user", message=message, intent=intent)
        bot_msg = ChatHistory(user_id=user_id, sender="bot", message=bot_reply, intent=intent)
        db.add(user_msg)
        db.add(bot_msg)
        db.commit()

        return {
            "response": bot_reply,
            "intent": intent,
            "profile": profile_dict,
            "recommendations": match_data.get("results", [])[:3]
        }

