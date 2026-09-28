"""
Gemini API Service for CareerBot.
Provides natural conversational LLM responses using Google GenAI SDK,
grounded strictly in local database matching results, with robust model fallbacks
and rich local intelligent fallback when offline or unavailable.
"""

import os
import re
from typing import Optional, Dict, List, Any
from config import Config

CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash"
]

LANGUAGE_NAMES = {
    "en-IN": "English",
    "en-US": "English",
    "hi-IN": "Hindi",
    "te-IN": "Telugu"
}

ROLE_SKILL_DATABASE = {
    "java": ["Core Java", "Object-Oriented Programming (OOP)", "Spring Boot", "Hibernate / JPA", "RESTful APIs", "Microservices", "SQL (PostgreSQL/MySQL)", "Maven / Gradle", "Git", "JUnit", "Docker"],
    "python": ["Python", "Object-Oriented Programming (OOP)", "RESTful API Development (FastAPI/Flask/Django)", "SQL / Relational Databases", "Data Structures & Algorithms", "Git", "Docker", "PyTest", "AsyncIO"],
    "data science": ["Python", "SQL", "Statistical Analysis & Probability", "Machine Learning (Scikit-Learn)", "Data Wrangling (Pandas, NumPy)", "Exploratory Data Analysis (EDA)", "Data Visualization (Tableau/PowerBI/Matplotlib)", "Feature Engineering"],
    "data scientist": ["Python", "SQL", "Statistical Analysis & Probability", "Machine Learning (Scikit-Learn)", "Data Wrangling (Pandas, NumPy)", "Exploratory Data Analysis (EDA)", "Data Visualization (Tableau/PowerBI/Matplotlib)", "Feature Engineering"],
    "machine learning": ["Python", "Linear Algebra & Calculus", "Machine Learning Algorithms", "Deep Learning (PyTorch or TensorFlow)", "Pandas & NumPy", "Scikit-Learn", "Model Evaluation & Tuning", "MLOps & Docker"],
    "frontend": ["JavaScript (ES6+)", "HTML5 & Semantic Web", "CSS3 / Modern Styling (Flexbox/Grid)", "React or Vue.js", "Responsive Web Design", "REST API Integration", "Git / Version Control", "Webpack / Vite"],
    "backend": ["Server-side language (Python / Java / Node.js / Go)", "RESTful API & GraphQL Design", "Relational Databases (PostgreSQL / MySQL)", "Database Indexing & Query Optimization", "Authentication & Security (JWT, OAuth)", "Microservices Architecture", "Docker & Containerization", "Git"],
    "full stack": ["Frontend (HTML5, CSS3, JavaScript, React)", "Backend (Node.js / Python / Java)", "RESTful API Design", "Databases (SQL & NoSQL)", "Authentication & Security", "Git & CI/CD", "Docker"],
    "devops": ["Linux System Administration", "Docker & Containerization", "Kubernetes Orchestration", "CI/CD Pipelines (GitHub Actions / Jenkins)", "Infrastructure as Code (Terraform)", "Cloud Platforms (AWS / Azure / GCP)", "Monitoring (Prometheus, Grafana)", "Shell Scripting"],
    "cloud": ["Cloud Architecture (AWS / Azure / GCP)", "Networking & Security (VPC, IAM)", "Containerization (Docker & Kubernetes)", "Serverless Computing", "Infrastructure as Code", "Database Services"]
}


class GeminiService:
    """Handles conversational responses with Gemini API or rich local AI fallback."""

    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if self.api_key:
            os.environ["GEMINI_API_KEY"] = self.api_key
            os.environ["GOOGLE_API_KEY"] = self.api_key

        self.client = None
        self._init_client()

    def _init_client(self):
        """Initializes Google GenAI client safely."""
        if not self.api_key:
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_available(self) -> bool:
        """Returns True if Gemini API key is configured and client loaded."""
        if not self.client:
            self._init_client()
        return self.client is not None

    def generate_chat_response(self, intent: str, message: str, profile: dict, match_data: dict = None, history: list = None, language: str = "en-IN") -> str:
        """Generates natural language response. Uses Gemini if available, else rich local fallback."""
        if self.is_available():
            prompt = self._build_grounded_prompt(intent, message, profile, match_data, history, language=language)
            for model_name in CANDIDATE_MODELS:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text and response.text.strip():
                        return response.text.strip()
                except Exception:
                    continue

        return self.generate_fallback_response(intent, message, profile, match_data, language=language)

    def generate_text(self, prompt: str, max_tokens: int = 150) -> Optional[str]:
        """Generates raw text using Gemini API with candidate model fallbacks."""
        if self.is_available():
            for model_name in CANDIDATE_MODELS:
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    if response and response.text and response.text.strip():
                        return response.text.strip()
                except Exception:
                    continue
        return None

    def _build_grounded_prompt(self, intent: str, message: str, profile: dict, match_data: dict, history: list = None, language: str = "en-IN") -> str:
        skills = ", ".join(profile.get("skills", [])) or "None (No resume uploaded yet)"
        has_resume = profile.get("has_resume", False) or bool(profile.get("skills"))
        target_roles = ", ".join(profile.get("target_roles", [])) or "Software Engineering"
        lang_name = LANGUAGE_NAMES.get(language, "English")

        jobs_detail_lines = []
        if match_data and "results" in match_data:
            for j in match_data["results"][:5]:
                jobs_detail_lines.append(
                    f"Job ID: {j.get('job_id')}\n"
                    f"Title: {j.get('title')}\n"
                    f"Company: {j.get('company')}\n"
                    f"Location: {j.get('location')}\n"
                    f"Work Mode: {j.get('work_mode', 'Not specified')}\n"
                    f"Experience Required: {j.get('experience')}\n"
                    f"Education: {j.get('education')}\n"
                    f"Required Skills: {j.get('skills')}\n"
                    f"Preferred Skills: {j.get('preferred_skills')}\n"
                    f"Responsibilities: {j.get('responsibilities')}\n"
                    f"Description: {j.get('description')}\n"
                    f"Match Score: {j.get('match_percentage') if j.get('has_match') else 'Not calculated (no resume)'}\n"
                    f"Matching Skills: {', '.join(j.get('matching_skills', []))}\n"
                    f"Missing Skills: {', '.join(j.get('missing_skills', []))}\n"
                    f"Apply URL: {j.get('url')}\n"
                )
        jobs_summary = "\n---\n".join(jobs_detail_lines) if jobs_detail_lines else "No verified jobs matching."

        history_str = ""
        if history:
            recent_history = history[-4:]
            history_str = "Recent Conversation History:\n" + "\n".join([f"{h.get('sender', 'user').capitalize()}: {h.get('message', '')}" for h in recent_history])

        return f"""You are CareerBot, an expert AI Career Assistant and mentor.

TARGET LANGUAGE: {lang_name}
CRITICAL LANGUAGE INSTRUCTION: The user has selected {lang_name}. You MUST answer ENTIRELY in {lang_name}. Do NOT respond in English if the user selected Hindi or Telugu!

USER QUESTION: "{message}"
INTENT DETECTED: {intent}

USER CONTEXT:
- Has Uploaded Resume: {has_resume}
- Verified Resume Skills: {skills}
- Target Roles: {target_roles}

VERIFIED ACTIVE JOB LISTINGS IN DATABASE:
{jobs_summary}

{history_str}

STRICT BEHAVIOR RULES:
1. Answer the user's specific question directly, thoroughly, and contextually. Do NOT repeat generic canned intros like 'Your profile currently highlights...'.
2. If asked "What skills do I need for [Role]?" or "What skills are required for [Role]?", list the essential technical skills, frameworks, and modern tools for that role clearly with bullet points.
3. If asked "What skills am I missing for [Role]?", compare the role requirements against the user's VERIFIED RESUME SKILLS ({skills}). If the user has not uploaded a resume (skills is None), clearly state what skills are required for the role and encourage them to upload their resume on the Resume tab to see their personalized skill gap!
4. If asked a technical concept question (e.g. "What is Data Science?"), provide an insightful, practical explanation without listing irrelevant jobs.
5. Only list job openings when the user explicitly searches for jobs or vacancies. For job listings, use ONLY the verified job data and apply URLs above without inventing fake links.
6. Remember: Output strictly in {lang_name}!"""

    def generate_fallback_response(self, intent: str, message: str, profile: dict, match_data: dict = None, language: str = "en-IN") -> str:
        """Intelligent, contextual local AI response generator honoring intent and language."""
        msg_lower = message.lower()
        skills = profile.get("skills", [])
        has_resume = profile.get("has_resume", False) or bool(skills)
        skills_str = ", ".join(skills) if skills else "No resume uploaded yet"
        results = match_data.get("results", []) if match_data else []
        is_telugu = language.startswith("te")
        is_hindi = language.startswith("hi")

        # Detect role mentioned in query
        matched_role = None
        for role_key in ROLE_SKILL_DATABASE:
            if role_key in msg_lower:
                matched_role = role_key
                break

        # 1. Role Skills: "What skills do I need for [Role]?" / "What skills are required for [Role]?"
        if intent == "role_skills" or any(kw in msg_lower for kw in ["skills do i need", "skills are required", "skills needed for", "required skills for", "skills for"]):
            target = matched_role or "software engineering"
            skill_list = ROLE_SKILL_DATABASE.get(target, [
                "Programming Language (Python / Java / C++)",
                "Data Structures & Algorithms",
                "Relational Databases & SQL",
                "RESTful APIs & Web Architecture",
                "Version Control with Git",
                "Testing & Clean Code Principles",
                "Docker & Cloud Fundamentals"
            ])
            skills_formatted = "\n".join([f"• **{s}**" for s in skill_list])

            if is_telugu:
                return (
                    f"### **{target.title()}** పాత్రకు అవసరమైన ముఖ్యమైన సాంకేతిక నైపుణ్యాలు:\n\n"
                    f"{skills_formatted}\n\n"
                    f"💡 *సూచన:* మీ రెజ్యూమ్‌ను **Resume** ట్యాబ్‌లో అప్‌లోడ్ చేసి, మీ ప్రస్తుత నైపుణ్యాల అంతరాన్ని (Skill Gap) తనిఖీ చేయండి!"
                )
            elif is_hindi:
                return (
                    f"### **{target.title()}** रोल के लिए आवश्यक प्रमुख तकनीकी कौशल:\n\n"
                    f"{skills_formatted}\n\n"
                    f"💡 *सलाह:* अपनी स्किल्स का विश्लेषण करने के लिए **Resume** टैब पर अपना रेज़्यूमे अपलोड करें!"
                )
            else:
                return (
                    f"### Key Technical Skills Required for a **{target.title()}** Role:\n\n"
                    f"{skills_formatted}\n\n"
                    f"💡 *Next Steps:* Upload your resume on the **Resume** tab to automatically see your matching skills and personalized skill gaps for verified postings!"
                )

        # 2. Skill Gap: "What skills am I missing for [Role]?"
        elif intent == "skill_gap" or any(kw in msg_lower for kw in ["missing skills", "skill gap", "what am i missing", "skills am i missing"]):
            target = matched_role or "Software Engineering"
            target_skills = ROLE_SKILL_DATABASE.get(target, ["Python", "SQL", "Git", "Docker", "REST APIs"])

            if not has_resume or not skills:
                # User has not uploaded a resume yet
                req_formatted = "\n".join([f"• **{s}**" for s in target_skills])
                if is_telugu:
                    return (
                        f"మీరు ఇంకా మీ రెజ్యూమ్‌ను అప్‌లోడ్ చేయలేదు, కాబట్టి వ్యక్తిగత నైపుణ్య అంతరాన్ని లెక్కించలేము.\n\n"
                        f"**{target.title()}** పాత్రకు సాధారణంగా అవసరమైన నైపుణ్యాలు:\n"
                        f"{req_formatted}\n\n"
                        f"👉 మీ ఖచ్చితమైన స్కిల్ గ్యాప్‌ను చూడటానికి **Resume** ట్యాబ్‌లో మీ రెజ్యూమ్‌ను అప్‌లోడ్ చేయండి!"
                    )
                elif is_hindi:
                    return (
                        f"आपने अभी तक अपना रेज़्यूमे अपलोड नहीं किया है, इसलिए व्यक्तिगत स्किल गैप की गणना नहीं की जा सकती।\n\n"
                        f"**{target.title()}** रोल के लिए आमतौर पर आवश्यक स्किल्स:\n"
                        f"{req_formatted}\n\n"
                        f"👉 अपना सटीक स्किल गैप देखने के लिए **Resume** टैब पर अपना रेज़्यूमे अपलोड करें!"
                    )
                else:
                    return (
                        f"You haven't uploaded a resume yet, so I cannot compare your personal skills.\n\n"
                        f"For a **{target.title()}** role, the primary required skills are:\n"
                        f"{req_formatted}\n\n"
                        f"👉 Please upload your resume on the **Resume** tab to see your personalized missing skills gap!"
                    )
            else:
                # Compare current resume skills vs target role
                user_skills_lower = [s.lower() for s in skills]
                missing = [s for s in target_skills if not any(k in s.lower() for k in user_skills_lower)]
                matching = [s for s in target_skills if any(k in s.lower() for k in user_skills_lower)]

                missing_str = ", ".join(missing) if missing else "None! You meet all core requirements."
                matching_str = ", ".join(matching) if matching else "None yet from this specific role list."

                if is_telugu:
                    return (
                        f"### **{target.title()}** కోసం మీ స్కిల్ గ్యాప్ విశ్లేషణ:\n\n"
                        f"• **మీ రెజ్యూమ్‌లో ఉన్న సరిపోలే నైపుణ్యాలు:** {matching_str}\n"
                        f"• **మీరు నేర్చుకోవలసిన మిస్సింగ్ నైపుణ్యాలు:** **{missing_str}**\n\n"
                        f"💡 మరింత వివరణ కోసం **Roadmap** ట్యాబ్‌ను చూడండి!"
                    )
                elif is_hindi:
                    return (
                        f"### **{target.title()}** के लिए आपका स्किल गैप विश्लेषण:\n\n"
                        f"• **आपके रेज़्यूमे के मैचिंग स्किल्स:** {matching_str}\n"
                        f"• **सीखने के लिए मिसिंग स्किल्स:** **{missing_str}**\n\n"
                        f"💡 स्टेप-बाय-स्टेप माइलस्टोन्स के लिए **Roadmap** टैब देखें!"
                    )
                else:
                    return (
                        f"### Skill Gap Analysis for **{target.title()}** (Based on Your Resume):\n\n"
                        f"• **Your Matching Skills:** {matching_str}\n"
                        f"• **Missing Skills to Learn:** **{missing_str}**\n\n"
                        f"💡 *Tip:* Check out the **Roadmap** tab to follow step-by-step milestones to master these missing skills!"
                    )

        # 3. General Career / Technical Concepts: "What is Data Science?", "Explain Machine Learning"
        elif intent == "general_career_question" or any(kw in msg_lower for kw in ["what is", "what are", "difference between", "how does"]):
            if "data science" in msg_lower:
                return (
                    "### What is Data Science?\n\n"
                    "**Data Science** is an interdisciplinary field that extracts actionable insights and knowledge from structured and unstructured data. It combines:\n\n"
                    "1. **Computer Science & Programming:** Writing clean code in Python or R, and querying relational databases with SQL.\n"
                    "2. **Math & Statistics:** Probability, hypothesis testing, linear algebra, and statistical inference.\n"
                    "3. **Machine Learning:** Building predictive algorithms (regression, classification, clustering) with libraries like Scikit-Learn.\n"
                    "4. **Business Domain Knowledge:** Translating analytical findings into strategic decision-making.\n\n"
                    "To enter Data Science, focus on mastering Python, SQL, Pandas, statistical modeling, and hands-on portfolio projects!"
                )
            elif "machine learning" in msg_lower:
                return (
                    "### What is Machine Learning?\n\n"
                    "**Machine Learning (ML)** is a subset of Artificial Intelligence where computer systems learn from data patterns without being explicitly programmed.\n\n"
                    "• **Supervised Learning:** Learning from labeled examples (e.g. price prediction, spam classification).\n"
                    "• **Unsupervised Learning:** Discovering hidden groupings or patterns (e.g. customer segmentation, clustering).\n"
                    "• **Reinforcement Learning:** Learning optimal actions through rewards and penalties.\n\n"
                    "Core tools include Python, NumPy, Pandas, Scikit-Learn, PyTorch, and TensorFlow."
                )
            elif "java" in msg_lower:
                return (
                    "### About Java Development\n\n"
                    "**Java** is a robust, object-oriented, cross-platform programming language widely used in enterprise backend software, Android applications, and financial systems.\n\n"
                    "Key tools for modern Java Developers include **Spring Boot, Hibernate, RESTful Web Services, Docker, and PostgreSQL/MySQL**."
                )
            else:
                return (
                    f"Regarding your query *'{message}'*:\n\n"
                    f"In modern tech careers, combining solid foundational programming with practical domain frameworks and cloud skills is key. "
                    f"You can ask me to **list required skills for a role**, **analyze your skill gaps**, or **recommend verified jobs**!"
                )

        # 4. Job Details
        elif intent == "job_details" or "view job" in msg_lower or "job details" in msg_lower:
            if results:
                j = results[0]
                matching_str = ", ".join(j.get("matching_skills", [])) or "None detected"
                missing_str = ", ".join(j.get("missing_skills", [])) or "None"
                match_txt = f"{j['match_percentage']}% Match" if j.get("has_match") and j.get("match_percentage") is not None else "Upload resume to calculate match"

                return (
                    f"### **{j['title']}** at **{j['company']}** ({match_txt})\n\n"
                    f"• **Location / Mode:** {j.get('location')} ({j.get('work_mode', 'Full-time')})\n"
                    f"• **Experience:** {j.get('experience')}\n"
                    f"• **Education:** {j.get('education')}\n\n"
                    f"**Required Technical Skills:**\n{j.get('skills')}\n\n"
                    f"**Matching Skills:** {matching_str}\n"
                    f"**Missing Skills:** {missing_str}\n\n"
                    f"**Responsibilities:**\n{j.get('responsibilities')}\n\n"
                    f"👉 [Click here to Apply directly on LinkedIn]({j.get('url', '#')})"
                )
            else:
                return "Please specify the job title or ID you want to inspect, or browse the **Jobs** tab to explore all active listings!"

        # 5. Explicit Job Search
        elif intent == "job_search" or any(kw in msg_lower for kw in ["find job", "find jobs", "search job", "search jobs", "show jobs", "recommend jobs", "vacancies"]):
            if results:
                lines = ["Here are verified job listings from our database matching your request:\n"]
                for i, j in enumerate(results[:4], 1):
                    match_str = f"({j['match_percentage']}% Match)" if j.get("has_match") and j.get("match_percentage") is not None else "(Upload resume to calculate match)"
                    lines.append(
                        f"**{i}. {j['title']}** at **{j['company']}** {match_str}\n"
                        f"• **Location:** {j.get('location', 'India')} | {j.get('work_mode', 'Full-time')}\n"
                        f"• **Required Skills:** {j.get('skills')}\n"
                        f"• [Apply on LinkedIn]({j['url']})\n"
                    )
                lines.append("\nVisit the **Jobs** tab to explore all listings!")
                return "\n".join(lines)
            else:
                return f"No open positions matched your specific search criteria in our verified database. Browse the **Jobs** tab to view all 26 verified opportunities!"

        # 6. Roadmap
        elif intent == "learning_roadmap" or "roadmap" in msg_lower:
            target_role = profile.get("target_roles", ["Software Engineer"])[0] if profile.get("target_roles") else "Software Engineering"
            return (
                f"### Personalized Career Roadmap for **{target_role}**\n\n"
                f"1. **Phase 1 (Foundations):** Core Data Structures, Algorithms & Clean Code\n"
                f"2. **Phase 2 (Specialization):** Advanced Frameworks & Cloud Architecture\n"
                f"3. **Phase 3 (Production Readiness):** CI/CD, Containerization & Microservices\n\n"
                f"Explore the interactive milestones on the **Roadmap** tab!"
            )

        # 7. Greeting / Help
        elif intent == "greeting" or any(kw in msg_lower for kw in ["hello", "hi", "hey"]):
            if is_telugu:
                return "నమస్కారం! 👋 నేను CareerBot, మీ AI కెరీర్ అసిస్టెంట్. ఉద్యోగాలు శోధించడం, నైపుణ్యాల విశ్లేషణ మరియు కెరీర్ రోడ్‌మ్యాప్ తయారీలో మీకు సహాయం చేయగలను. నేను మీకు ఎలా సహాయపడగలను?"
            elif is_hindi:
                return "नमस्ते! 👋 मैं CareerBot हूँ, आपका AI करियर सहायक। मैं जॉब सर्च, स्किल गैप एनालिसिस और करियर रोडमैप में आपकी मदद कर सकता हूँ। मैं आज आपकी क्या सहायता कर सकता हूँ?"
            else:
                return (
                    "Hello! 👋 I'm **CareerBot**, your AI Career Assistant.\n\n"
                    "I can help you with:\n"
                    "• 🔍 Finding jobs matching your career goals\n"
                    "• ⚡ Answering required skills for any role (e.g. *What skills do I need for Java Developer?*)\n"
                    "• 📊 Analyzing skill gaps against your resume\n"
                    "• 🗺️ Generating step-by-step career learning roadmaps\n\n"
                    "How can I help you today?"
                )

        # Default fallback
        else:
            return (
                f"I'm here to assist your career journey! You can ask me:\n\n"
                f"• *'What skills do I need for Java Developer?'*\n"
                f"• *'What skills am I missing for Data Science?'*\n"
                f"• *'Find Python developer jobs'*\n"
                f"• *'Show career roadmap for Machine Learning'* "
            )


# Global singleton instance
gemini_service = GeminiService()

