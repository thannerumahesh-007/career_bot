"""
Gemini API Service for CareerBot.
Provides natural conversational LLM responses using the centralized ModelRouter,
grounded strictly in local database matching results, career role knowledge,
with robust candidate model fallbacks and rich deterministic local AI fallback.
"""

import os
import re
from typing import Optional, Dict, List, Any
from config import Config
from services.model_router import model_router
from services.career_knowledge import CAREER_ROLES, extract_role_from_text, get_role_details
from services.language_config import get_language_config, get_ai_instruction
from services.text_cleaner import clean_chat_response

# Exported for compatibility with all test suites
JARVIS_SYSTEM_INSTRUCTION = (
    "You are CareerBot and JARVIS, an advanced conversational AI Assistant and career mentor. "
    "Understand the user's exact request before answering. "
    "Answer the question directly, thoroughly, and contextually. "
    "Follow the requested level of detail. "
    "Maintain conversational context across turns. "
    "Do not give generic or unrelated answers."
)

CANDIDATE_MODELS = model_router.get_candidate_models("chat")


import logging
logger = logging.getLogger("CareerBot.GeminiService")


class GeminiService:
    """Handles conversational responses with Gemini ModelRouter or rich local career AI fallback."""

    def __init__(self):
        self.router = model_router

    def is_available(self) -> bool:
        """Returns True if Gemini API is configured and accessible."""
        return self.router.is_available()

    def get_last_status(self) -> Dict[str, Any]:
        """Returns the internal status of the last model router generation."""
        return getattr(self.router, "last_status", {
            "provider": "gemini",
            "status": "unknown",
            "error_type": None,
            "fallback": None
        })

    def generate_chat_response(
        self,
        intent: str,
        message: str,
        profile: dict,
        match_data: dict = None,
        history: list = None,
        language: str = "en-IN"
    ) -> str:
        """Generates natural language response. Uses Gemini ModelRouter if available, else rich local fallback."""
        if self.is_available():
            prompt = self._build_grounded_prompt(intent, message, profile, match_data, history, language=language)
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                )
            except Exception:
                config = None

            raw_reply = self.router.generate_content("chat", contents=prompt, config=config)
            if raw_reply and raw_reply.strip():
                return clean_chat_response(raw_reply.strip())

        # Fallback to rich deterministic local response
        last_stat = self.get_last_status()
        err_type = last_stat.get("error_type") or "unavailable"
        logger.info(f"Feature: chat | Provider: local_fallback | Reason: Gemini API {err_type}")
        fallback_reply = self.generate_fallback_response(intent, message, profile, match_data, history=history, language=language)
        return clean_chat_response(fallback_reply)

    def generate_text(self, prompt: str, feature: str = "chat", max_tokens: int = 500) -> Optional[str]:
        """Generates raw text using the centralized ModelRouter."""
        if self.is_available():
            try:
                from google.genai import types
                config = types.GenerateContentConfig(max_output_tokens=max_tokens)
            except Exception:
                config = None
            res = self.router.generate_content(feature, contents=prompt, config=config)
            if res:
                return clean_chat_response(res)
        return None

    def _build_grounded_prompt(
        self,
        intent: str,
        message: str,
        profile: dict,
        match_data: dict,
        history: list = None,
        language: str = "en-IN"
    ) -> str:
        skills = ", ".join(profile.get("skills", [])) or "None (No resume uploaded yet)"
        has_resume = profile.get("has_resume", False) or bool(profile.get("skills"))
        target_roles = ", ".join(profile.get("target_roles", [])) or "Software Engineering"
        lang_config = get_language_config(language)
        lang_instruction = get_ai_instruction(language)

        jobs_detail_lines = []
        if match_data and "results" in match_data:
            for j in match_data["results"][:5]:
                source_label = "Live Internet Job" if j.get("is_live", True) else "Verified Job"
                apply_url = j.get("apply_url") or j.get("url") or ""
                jobs_detail_lines.append(
                    f"Title: {j.get('title')}\n"
                    f"Company: {j.get('company')}\n"
                    f"Source: {source_label}\n"
                    f"Location: {j.get('location')}\n"
                    f"Work Mode: {j.get('work_mode', 'Not specified')}\n"
                    f"Match Score: {j.get('match_percentage') if j.get('has_match') else 'Not calculated'}\n"
                    f"Matching Skills: {', '.join(j.get('matching_skills', []))}\n"
                    f"Missing Skills: {', '.join(j.get('missing_skills', []))}\n"
                    f"Apply URL: {apply_url}\n"
                )
        jobs_summary = "\n---\n".join(jobs_detail_lines) if jobs_detail_lines else "No jobs retrieved."

        history_str = ""
        if history:
            recent_history = history[-8:]
            history_str = "Recent Conversation History (Resolve pronouns and follow-up context):\n" + "\n".join(
                [f"{h.get('sender', 'user').capitalize()}: {h.get('message', '')}" for h in recent_history]
            )

        return f"""You are CareerBot and JARVIS, an advanced conversational AI Assistant and career mentor.

LANGUAGE DIRECTIVE:
{lang_instruction}

USER QUESTION: "{message}"
INTENT DETECTED: {intent}

USER CONTEXT:
- Has Uploaded Resume: {has_resume}
- Verified Resume Skills: {skills}
- Target Roles: {target_roles}

RELEVANT ACTIVE JOBS:
{jobs_summary}

{history_str}

STRICT CONVERSATIONAL GUIDELINES:
1. ANSWER DIRECTLY: Answer the actual question directly and contextually. Do NOT prepend canned introductions like 'I'm here to assist your career journey!' on every turn. Only show the help menu if the user explicitly asks for help or features.
2. RESOLVE CONTEXT: If the user asks a follow-up (e.g. 'I need links for those', 'Which ones match my resume?', 'What skills am I missing?', 'Explain that in detail'), resolve what jobs, links, or role they were discussing in the Recent Conversation History.
3. ACCURATE ROLE KNOWLEDGE: If the user asks about Data Analyst, answer with Data Analyst skills (SQL, Excel, Python, Pandas, Power BI, Statistics). If they ask about Java Developer, answer with Java, OOP, Spring Boot, REST APIs, SQL, Git, Maven, Testing. Never answer with generic software engineering skills for specific roles.
4. HONEST SOURCE ATTRIBUTION: All job opportunities are from 'Live Internet Job'. Never claim old database jobs or generate fabricated URLs. Provide the actual Apply URLs in markdown format [View Job / Apply](url).
5. NO RAW MARKDOWN ARTIFACTS: Do not output raw escaped characters (\\, \\###, \\*). Use clean structure.
6. SPOKEN READINESS: The response will also be spoken by JARVIS voice synthesis, so structure sentences clearly and naturally."""

    def generate_fallback_response(
        self,
        intent: str,
        message: str,
        profile: dict,
        match_data: dict = None,
        history: list = None,
        language: str = "en-IN"
    ) -> str:
        """Deterministic local AI response generator based on structured career knowledge."""
        msg_lower = message.lower()
        skills = profile.get("skills", [])
        has_resume = profile.get("has_resume", False) or bool(skills)
        results = match_data.get("results", []) if match_data else []
        is_telugu = language.startswith("te") or any('\u0c00' <= c <= '\u0c7f' for c in message)
        is_hindi = language.startswith("hi") or any('\u0900' <= c <= '\u097f' for c in message)

        # Resolve context and target role from message or recent history
        detected_role_key = extract_role_from_text(message)

        prev_role_key = None
        if history:
            for h in reversed(history):
                content = (h.get("message") or "").lower()
                r = extract_role_from_text(content)
                if r:
                    prev_role_key = r
                    break

        # Resolve conversation context for follow-up questions
        prev_user_query = ""
        if history:
            for h in reversed(history):
                content = (h.get("message") or "").strip().lower()
                if h.get("sender") == "user":
                    prev_user_query = content
                    break

        combined_text = msg_lower
        if any(kw in msg_lower for kw in ["explain that", "in detail", "tell me more", "elaborate", "tell me about that", "more about that", "explain this"]):
            if prev_user_query:
                combined_text = f"{prev_user_query} {msg_lower}"

        active_role_key = (
            detected_role_key
            or prev_role_key
            or ("data analyst" if "analyst" in combined_text else None)
            or ("python developer" if any(k in combined_text for k in ["python", "पाइथन", "पायथन", "పైథాన్"]) else None)
            or ("java developer" if any(k in combined_text for k in ["java", "जावा", "జావా"]) and "javascript" not in combined_text else None)
        )
        role_info = get_role_details(active_role_key)
        role_title = role_info["title"]

        # 1. Career Skill Requirements
        if intent in ["career_skill_requirements", "role_skills", "skill_question"] or any(kw in msg_lower for kw in [
            "skills do i need", "skills are required", "skills needed", "required skills",
            "skills for", "what skills should i learn", "स्किल्स", "कौशल", "స్కిల్స్", "నైపుణ్యాలు",
            "क्या स्किल्स चाहिए", "मुझे पाइथन स्किल्स", "पाइथन स्किल्स", "जावा स्किल्स", "పైథాన్ స్కిల్స్"
        ]):
            req_skills = role_info["required_skills"]
            formatted_skills = "\n".join([f"• {s}" for s in req_skills])

            if is_telugu:
                return (
                    f"{role_title} పాత్రకు అవసరమైన ముఖ్యమైన సాంకేతిక నైపుణ్యాలు:\n\n"
                    f"{formatted_skills}\n\n"
                    f"సూచన: మీ రెజ్యూమ్‌ను Resume విభాగంలో అప్‌లోడ్ చేసి స్కిల్ గ్యాప్‌ను తనిఖీ చేయండి."
                )
            elif is_hindi:
                return (
                    f"{role_title} रोल के लिए आवश्यक प्रमुख तकनीकी स्किल्स:\n\n"
                    f"{formatted_skills}\n\n"
                    f"सलाह: अपने स्किल गैप का विश्लेषण करने के लिए Resume टैब पर अपना रेज़्यूमे अपलोड करें।"
                )
            else:
                return (
                    f"Key Technical Skills Required for {role_title}:\n\n"
                    f"{formatted_skills}\n\n"
                    f"Next Steps: Upload your resume in the Resume section to automatically detect your matching skills and personalized skill gaps."
                )

        # 2. Skill Gap Analysis
        elif intent == "skill_gap" or any(kw in msg_lower for kw in ["missing skills", "skill gap", "what am i missing"]):
            req_skills = role_info["required_skills"]
            if not has_resume or not skills:
                req_formatted = "\n".join([f"• {s}" for s in req_skills])
                if is_telugu:
                    return (
                        f"మీరు ఇంకా మీ రెజ్యూమ్‌ను అప్‌లోడ్ చేయలేదు.\n\n"
                        f"{role_title} కోసం సాధారణంగా అవసరమైన నైపుణ్యాలు:\n{req_formatted}\n\n"
                        f"మీ ఖచ్చితమైన స్కిల్ గ్యాప్‌ను చూడటానికి Resume ట్యాబ్‌లో రెజ్యూమ్‌ను అప్‌లోడ్ చేయండి."
                    )
                elif is_hindi:
                    return (
                        f"आपने अभी तक अपना रेज़्यूमे अपलोड नहीं किया है।\n\n"
                        f"{role_title} के लिए आवश्यक मुख्य स्किल्स:\n{req_formatted}\n\n"
                        f"अपना सटीक स्किल गैप देखने के लिए Resume टैब पर रेज़्यूमे अपलोड करें।"
                    )
                else:
                    return (
                        f"You haven't uploaded a resume yet, so I cannot calculate your personalized gap.\n\n"
                        f"Key skills required for {role_title}:\n{req_formatted}\n\n"
                        f"Upload your resume in the Resume tab to see your exact matching skills and missing gaps."
                    )
            else:
                user_skills_lower = [s.lower() for s in skills]
                missing = [s for s in req_skills if not any(k in s.lower() for k in user_skills_lower)]
                matching = [s for s in req_skills if any(k in s.lower() for k in user_skills_lower)]

                missing_str = "\n".join([f"• {s}" for s in missing]) if missing else "• None! You meet all core requirements."
                matching_str = ", ".join(matching) if matching else "None detected yet from this specific role list."

                if is_telugu:
                    return (
                        f"{role_title} కోసం మీ స్కిల్ గ్యాప్ విశ్లేషణ:\n\n"
                        f"సరిపోలే నైపుణ్యాలు: {matching_str}\n\n"
                        f"మిస్సింగ్ నైపుణ్యాలు:\n{missing_str}\n\n"
                        f"మరిన్ని వివరాలకు Roadmap ట్యాబ్‌ను చూడండి."
                    )
                elif is_hindi:
                    return (
                        f"{role_title} के लिए आपका स्किल गैप विश्लेषण:\n\n"
                        f"मैचिंग स्किल्स: {matching_str}\n\n"
                        f"सीखने के लिए मिसिंग स्किल्स:\n{missing_str}\n\n"
                        f"कदम-दर-कदम सीखने के लिए Roadmap टैब देखें।"
                    )
                else:
                    return (
                        f"Skill Gap Analysis for {role_title} (Based on Your Resume):\n\n"
                        f"Matching Skills: {matching_str}\n\n"
                        f"Missing Skills to Acquire:\n{missing_str}\n\n"
                        f"Check out the Roadmap tab to follow step-by-step milestones to master these missing skills."
                    )

        # 3. Follow-up: Certifications / Projects for Role
        elif any(kw in msg_lower for kw in ["certifications", "certificate", "cert"]) and (active_role_key or prev_role_key):
            certs = role_info.get("certifications", [])
            certs_formatted = "\n".join([f"• {c}" for c in certs]) if certs else "• Industry-standard certifications in this field."
            return (
                f"Recommended Industry Certifications for {role_title}:\n\n"
                f"{certs_formatted}\n\n"
                f"These credentials validate your practical skills to hiring managers."
            )

        # 4. ATS Score / Resume Builder queries
        elif intent in ["ats_analysis", "resume_builder"] or "ats" in msg_lower or "build resume" in msg_lower:
            return (
                f"CareerBot ATS Resume Builder is ready to assist you!\n\n"
                f"• Analyze your existing resume for ATS keyword and section completeness\n"
                f"• Optimize your resume directly against {role_title} or paste any job description\n"
                f"• Export an ATS-friendly single-column PDF\n\n"
                f"Visit the Resume Builder in the Resume section to get started!"
            )

        # 5. AI Interview query
        elif intent == "interview_start" or "interview" in msg_lower:
            return (
                f"Ready to practice your interview for {role_title}?\n\n"
                f"Visit the AI Interview Simulator page to start an interactive technical or behavioral session customized to your resume and experience level."
            )

        # 6. Company Following query
        elif intent == "company_following" or "follow" in msg_lower:
            return (
                "You can follow and track major tech companies in the Companies section. "
                "Following companies personalizes your Corporate News feed so you see updates on hiring and earnings first!"
            )

        # 7. Job Search
        elif intent == "job_search":
            if results:
                if is_telugu:
                    lines = [f"{role_title} కోసం ప్రస్తుత లైవ్ ఇంటర్నెట్ ఉద్యోగాలు:\n"]
                elif is_hindi:
                    lines = [f"{role_title} के लिए उपलब्ध लाइव इंटरनेट जॉब्स:\n"]
                else:
                    lines = [f"Here are current live job opportunities matching your request:\n"]

                for i, j in enumerate(results[:4], 1):
                    title = j.get("title", "Software Role")
                    company = j.get("company", "Tech Enterprise")
                    loc = j.get("location", "Remote")
                    mode = j.get("work_mode", "Not specified")
                    match_pct = f" | {j['match_percentage']}% Match" if j.get("has_match") and j.get("match_percentage") is not None else ""
                    apply_url = j.get("apply_url") or j.get("url") or ""

                    lines.append(
                        f"**{i}. {title}**\n"
                        f"Company: {company}\n"
                        f"Location: {loc} ({mode})\n"
                        f"Source: Live Internet Job{match_pct}\n"
                        f"Apply: [View Job / Apply]({apply_url})\n"
                    )
                return "\n".join(lines)
            else:
                if is_telugu:
                    return f"ప్రస్తుతం '{message}' కి సరిపోలే లైవ్ ఉద్యోగాలు కనుగొనబడలేదు. దయచేసి ఇతర కీలక పదాలతో ప్రయత్నించండి."
                elif is_hindi:
                    return f"वर्तमान में '{message}' के लिए कोई लाइव जॉब्स नहीं मिले। कृपया अन्य कीवर्ड्स के साथ प्रयास करें।"
                else:
                    return f"No current live jobs were found matching '{message}'. Try searching for specific roles like 'Python developer' or 'Data Analyst'."

        # 8. Follow-up: Job Links
        elif intent == "job_links":
            if results:
                if is_telugu:
                    lines = ["మునుపటి ఉద్యోగాల కోసం దరఖాస్తు లింకులు ఇక్కడ ఉన్నాయి:\n"]
                elif is_hindi:
                    lines = ["पिछली नौकरियों के लिए आवेदन लिंक्स:\n"]
                else:
                    lines = ["Here are the application links for the jobs mentioned above:\n"]

                for i, j in enumerate(results[:5], 1):
                    title = j.get("title", "Role")
                    company = j.get("company", "Company")
                    apply_url = j.get("apply_url") or j.get("url") or ""
                    if apply_url:
                        lines.append(f"**{i}. {title}** at {company}:\n   Link: [View Job / Apply]({apply_url})\n")
                    else:
                        lines.append(f"**{i}. {title}** at {company}: Visit company careers portal\n")
                return "\n".join(lines)
            else:
                if is_telugu:
                    return "మా సంభాషణలో మునుపటి ఉద్యోగాలు ఏవీ కనుగొనబడలేదు. దయచేసి ముందుగా ఉద్యోగాల కోసం అడగండి (ఉదాహరణకు 'Find Python jobs')."
                elif is_hindi:
                    return "मुझे हमारी बातचीत में कोई पिछली नौकरियां नहीं मिलीं। कृपया पहले जॉब्स सर्च करें (जैसे 'Find Python jobs')।"
                else:
                    return "I couldn't find any previously searched jobs in our conversation. Please ask for jobs first (e.g., 'Find Python and SQL developer jobs for me'), and I will provide the live opportunities and application links!"

        # 9. Resume Matched Jobs
        elif intent == "resume_matched_jobs":
            if match_data and match_data.get("no_resume"):
                if is_telugu:
                    return "దయచేసి ముందుగా మీ రెజ్యూమ్‌ను Resume విభాగంలో అప్‌లోడ్ చేసి పార్స్ చేయండి. ఆ తర్వాత మీ రెజ్యూమ్‌కు సరిపోలే లైవ్ ఉద్యోగాలను కనుగొనగలను."
                elif is_hindi:
                    return "कृपया पहले Resume टैब पर अपना रेज़्यूमे अपलोड और पार्स करें। इसके बाद मैं आपके रेज़्यूमे से मैच करने वाली लाइव नौकरियां खोज सकता हूँ।"
                else:
                    return "Please upload and parse your resume first in the Resume tab. I can then find live jobs that match your resume."

            if results:
                if is_telugu:
                    lines = ["మీ రెజ్యూమ్‌తో సరిపోలే ప్రస్తుత లైవ్ ఉద్యోగాలు ఇక్కడ ఉన్నాయి:\n"]
                elif is_hindi:
                    lines = ["आपके रेज़्यूमे से मैच करने वाली वर्तमान लाइव नौकरियां:\n"]
                else:
                    lines = ["Here are current jobs that match your resume:\n"]

                for i, j in enumerate(results[:4], 1):
                    title = j.get("title", "Role")
                    company = j.get("company", "Company")
                    loc = j.get("location", "Remote")
                    match_pct = f"{j.get('match_percentage', 75)}% Match"
                    matching_skills = ", ".join(j.get("matching_skills", [])[:4]) or "Core skills match"
                    missing_skills = ", ".join(j.get("missing_skills", [])[:3]) or "None"
                    apply_url = j.get("apply_url") or j.get("url") or ""

                    lines.append(
                        f"**{i}. {title}**\n"
                        f"Company: {company}\n"
                        f"Location: {loc}\n"
                        f"Match: {match_pct}\n"
                        f"Matching Skills: {matching_skills}\n"
                        f"Missing Skills: {missing_skills}\n"
                        f"Source: Live Internet Job\n"
                        f"Apply: [View Job / Apply]({apply_url})\n"
                    )
                return "\n".join(lines)
            else:
                return "No live jobs currently matched your resume profile. Visit the Jobs tab to browse all live internet job postings."

        # 10. Learning Roadmap & Career Advice
        elif intent in ["career_roadmap", "learning_roadmap", "career_advice"] or any(kw in msg_lower for kw in ["roadmap", "how can i become", "how do i become", "how to become"]):
            return (
                f"Step-by-step Learning Roadmap for {role_title}:\n\n"
                f"1. Foundations: Core programming, problem solving, and database fundamentals\n"
                f"2. Specialization: Frameworks, tools, and hands-on portfolio projects\n"
                f"3. Production Readiness: Cloud deployment, testing, and interview preparation\n\n"
                f"View interactive milestones in the Roadmap tab!"
            )

        # 11. Greeting
        elif intent == "greeting":
            if is_telugu:
                return "నమస్కారం! 👋 నేను CareerBot, మీ AI కెరీర్ అసిస్టెంట్. ఉద్యోగ శోధన, నైపుణ్యాల విశ్లేషణ, రెజ్యూమ్ బిల్డర్ మరియు ఇంటర్వ్యూలలో మీకు సహాయం చేయగలను."
            elif is_hindi:
                return "नमस्ते! 👋 मैं CareerBot हूँ, आपका AI करियर सहायक। जॉब सर्च, रेज़्यूमे एनालिसिस और इंटरव्यू प्रैक्टिस में मैं आपकी मदद कर सकता हूँ।"
            else:
                return (
                    "Hello! 👋 I'm CareerBot, your intelligent career assistant.\n\n"
                    "How can I assist your career growth today? You can ask about role skills, search live jobs, analyze your resume, or practice mock interviews."
                )

        # 12. Explicit Help Request
        elif intent == "help":
            return (
                f"CareerBot Feature Guide:\n\n"
                f"• Role Skills: 'What skills do I need for Data Analyst?'\n"
                f"• Live Job Search: 'Find Python and SQL developer jobs for me'\n"
                f"• Follow-Up Links: 'I need links for those'\n"
                f"• Resume Match: 'Find jobs that match my resume'\n"
                f"• Skill Gap: 'What skills am I missing for Machine Learning?'\n"
                f"• ATS Builder: 'Build my resume'\n"
                f"• AI Interview: 'Start a technical interview'"
            )

        # 13. General Technical & Conceptual Explanations
        elif intent in ["general_career_question", "career_question"]:
            is_detail_followup = any(kw in msg_lower for kw in ["in detail", "explain that", "elaborate", "tell me more"])

            if "machine learning" in combined_text or "ml" in combined_text:
                if is_detail_followup:
                    return (
                        "Machine Learning in detail:\n\n"
                        "Machine learning focuses on creating mathematical algorithms that learn representations directly from data to perform predictive tasks.\n\n"
                        "Detailed technical breakdown:\n"
                        "• Supervised Learning: Models like Linear/Logistic Regression, Random Forests, XGBoost, and Deep Neural Networks trained with labeled ground truth data.\n"
                        "• Unsupervised Learning: Discovering inherent structure using K-Means Clustering, DBSCAN, and Dimensionality Reduction (PCA, t-SNE).\n"
                        "• Model Evaluation & Optimization: Cross-validation, Bias-Variance trade-off, Hyperparameter tuning (GridSearchCV, Optuna), and metric analysis (ROC-AUC, F1-Score, RMSE).\n\n"
                        "Production tool stack: Python, Scikit-Learn, Pandas, NumPy, PyTorch, MLflow, and Docker for deployment."
                    )
                else:
                    return (
                        "Machine Learning is a discipline of Artificial Intelligence where algorithms discover patterns in data to make predictions or decisions without explicit rule programming.\n\n"
                        "Core paradigms include:\n"
                        "• Supervised Learning: Learning from labeled data (Regression, Classification)\n"
                        "• Unsupervised Learning: Discovering hidden patterns in unlabeled data (Clustering, PCA)\n"
                        "• Reinforcement Learning: Learning optimal actions via reward signals\n\n"
                        "Essential libraries include Python, NumPy, Pandas, Scikit-Learn, and PyTorch."
                    )
            elif "data analyst" in combined_text or "data analytics" in combined_text:
                return (
                    "A Data Analyst collects, cleans, and interprets complex data to help organizations make data-driven business decisions.\n\n"
                    "Primary responsibilities include querying databases with SQL, building KPI dashboards in Power BI or Tableau, and exploratory analysis in Excel and Python."
                )
            elif any(k in combined_text for k in ["python", "पाइथन", "पायथन", "పైథాన్"]):
                if is_telugu:
                    return (
                        "పైథాన్ అనేది AI, డేటా సైన్స్, ఆటోమేషన్ మరియు బ్యాకెండ్ డెవలప్‌మెంట్‌లో విస్తృతంగా ఉపయోగించబడే ప్రముఖ ప్రోగ్రామింగ్ భాష. "
                        "ఇందులో Pandas, Scikit-Learn, FastAPI వంటి అనేక లైబ్రరీలు ఉన్నాయి."
                    )
                elif is_hindi:
                    return (
                        "पाइथन एक शक्तिशाली और लोकप्रिय प्रोग्रामिंग भाषा है जो AI, डेटा साइंस, ऑटोमेशन और वेब डेवलपमेंट में व्यापक रूप से उपयोग की जाती है। "
                        "इसके प्रमुख टूल्स में Pandas, Scikit-Learn, FastAPI और PyTorch शामिल हैं।"
                    )
                else:
                    return (
                        "Python is the industry-standard language for AI, data science, automation, and backend development due to its clean syntax and vast ecosystem (Pandas, Scikit-Learn, FastAPI, PyTorch)."
                    )
            elif any(k in combined_text for k in ["java", "जावा", "జావా"]):
                if is_telugu:
                    return (
                        "జావా అనేది ఎంటర్‌ప్రైజ్ బ్యాకెండ్ మరియు స్ప్రింగ్ బూట్ మైక్రోసర్వీసెస్‌లో ఉపయోగించే అత్యంత శక్తివంతమైన ఆబ్జెక్ట్-ఓరియెంటెడ్ భాష."
                    )
                elif is_hindi:
                    return (
                        "जावा एक उच्च-प्रदर्शन, ऑब्जेक्ट-ओरिएंटेड प्रोग्रामिंग भाषा है जिसका उपयोग बड़े पैमाने के एंटरप्राइज़ बैकएंड और Spring Boot माइक्रोसर्विसेज़ में किया जाता है।"
                    )
                else:
                    return (
                        "Java is a high-performance, object-oriented language widely used in enterprise backend architectures, Spring Boot microservices, and distributed cloud applications."
                    )
            else:
                return (
                    f"Regarding {message}:\n\n"
                    f"Focusing on foundational programming, practical project building, and continuous skill verification is key to a successful tech career. "
                    f"Feel free to ask about specific role skills, live job opportunities, ATS resume building, or interview practice!"
                )

        # Default fallback: direct contextual answer without repeating generic menu
        else:
            if is_telugu:
                return f"{role_title} గురించి మీ ప్రశ్నకు సమాధానం అందించడానికి నేను సిద్ధంగా ఉన్నాను. నైపుణ్యాలు, ఉద్యోగాలు లేదా రెజ్యూమ్ గురించి అడగండి."
            elif is_hindi:
                return f"{role_title} के बारे में आपके प्रश्न का उत्तर देने के लिए मैं तैयार हूँ। स्किल्स, जॉब्स या रेज़्यूमे के बारे में पूछें।"
            else:
                return (
                    f"I'm here to assist you with {role_title} and related tech careers. "
                    f"You can ask about required skills, live job search, skill gap analysis against your resume, or mock interview preparation."
                )


# Global singleton instance
gemini_service = GeminiService()
