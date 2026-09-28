"""
Skill Gap Analyzer & Career Roadmap Generator for CareerBot.
Identifies missing technical skills, normalizes target roles, and generates structured learning roadmaps.
"""

import re
from nlp.skill_dictionary import normalize_skill_key, normalize_skill, normalize_skill_list

ROLE_ALIASES = {
    r'^(python|py|python dev|python programmer|python software engineer)\b': "Python Developer",
    r'^(java|java dev|java programmer|java software engineer)\b': "Java Developer",
    r'^(frontend|frontend dev|frontend engineer|web developer|react dev|ui dev)\b': "Frontend Developer",
    r'^(backend|backend dev|backend engineer|node dev|server developer)\b': "Backend Developer",
    r'^(full stack|fullstack|fullstack dev|full stack developer)\b': "Full Stack Developer",
    r'^(data analyst|data analytics|data analysis|business analyst)\b': "Data Analyst",
    r'^(data scientist|data science|applied scientist)\b': "Data Scientist",
    r'^(machine learning engineer|ml engineer|ml developer|machine learning)\b': "Machine Learning Engineer",
    r'^(ai engineer|artificial intelligence engineer|ai developer|genai engineer)\b': "AI Engineer",
    r'^(nlp engineer|natural language processing engineer|nlp developer)\b': "NLP Engineer",
    r'^(software engineer|software developer|swe|application engineer)\b': "Software Engineer",
    r'^(devops|devops engineer|site reliability engineer|sre)\b': "DevOps Engineer",
    r'^(cloud|cloud engineer|aws engineer|azure engineer)\b': "Cloud Engineer",
}


DEFAULT_ROLE_ROADMAPS = {
    "Python Developer": [
        {"step": 1, "topic": "Python Core & Object-Oriented Programming", "skills": ["Python", "Data Structures", "Algorithms"]},
        {"step": 2, "topic": "Database Design & SQL Querying", "skills": ["SQL", "PostgreSQL", "MySQL"]},
        {"step": 3, "topic": "Web Frameworks & REST API Design", "skills": ["Django", "Flask", "REST API"]},
        {"step": 4, "topic": "Testing, Git Version Control & Deployment", "skills": ["PyTest", "Git", "Docker"]}
    ],
    "Java Developer": [
        {"step": 1, "topic": "Java Core & Object-Oriented Fundamentals", "skills": ["Java", "OOP", "Collections"]},
        {"step": 2, "topic": "Spring Framework & Microservices", "skills": ["Spring Boot", "REST API"]},
        {"step": 3, "topic": "Relational Databases & ORM", "skills": ["SQL", "PostgreSQL", "MySQL"]},
        {"step": 4, "topic": "Build Tools & CI/CD Pipelines", "skills": ["Git", "Maven", "Docker"]}
    ],
    "Frontend Developer": [
        {"step": 1, "topic": "Web Core (HTML5, CSS3, Modern JS)", "skills": ["HTML", "CSS", "JavaScript"]},
        {"step": 2, "topic": "Modern UI Frameworks & Type Safety", "skills": ["React", "TypeScript"]},
        {"step": 3, "topic": "State Management & Styling Systems", "skills": ["Redux", "Tailwind"]},
        {"step": 4, "topic": "Version Control & Performance Optimization", "skills": ["Git", "Webpack"]}
    ],
    "Backend Developer": [
        {"step": 1, "topic": "Server-Side Scripting & Runtimes", "skills": ["Python", "Node.js", "Express"]},
        {"step": 2, "topic": "Database Engineering (Relational & NoSQL)", "skills": ["PostgreSQL", "MongoDB", "SQL"]},
        {"step": 3, "topic": "API Architecture & Security", "skills": ["REST API", "Docker"]},
        {"step": 4, "topic": "System Design & Cloud Deployment", "skills": ["Git", "AWS", "Linux"]}
    ],
    "Full Stack Developer": [
        {"step": 1, "topic": "Frontend Core & Responsive Design", "skills": ["HTML", "CSS", "JavaScript"]},
        {"step": 2, "topic": "Component UI Development", "skills": ["React", "TypeScript"]},
        {"step": 3, "topic": "Backend APIs & Server Logic", "skills": ["Node.js", "Python", "REST API"]},
        {"step": 4, "topic": "Database Persistence & DevOps", "skills": ["PostgreSQL", "Git", "Docker", "AWS"]}
    ],
    "Data Analyst": [
        {"step": 1, "topic": "SQL Querying & Data Extraction", "skills": ["SQL", "PostgreSQL", "MySQL"]},
        {"step": 2, "topic": "Data Wrangling with Python & Pandas", "skills": ["Python", "Pandas", "NumPy", "Excel"]},
        {"step": 3, "topic": "Business Intelligence & Dashboarding", "skills": ["Tableau", "Power BI"]},
        {"step": 4, "topic": "Statistical Problem Solving", "skills": ["Statistics", "Math"]}
    ],
    "Data Scientist": [
        {"step": 1, "topic": "Programming & Data Analysis Core", "skills": ["Python", "SQL", "Pandas", "NumPy"]},
        {"step": 2, "topic": "Statistical Modeling & Hypothesis Testing", "skills": ["Statistics", "Math"]},
        {"step": 3, "topic": "Machine Learning Algorithms & Scikit-learn", "skills": ["Machine Learning", "Scikit-learn"]},
        {"step": 4, "topic": "Data Visualization & Deep Learning", "skills": ["Tableau", "Deep Learning", "PyTorch"]}
    ],
    "Machine Learning Engineer": [
        {"step": 1, "topic": "Python & Data Science Foundations", "skills": ["Python", "SQL", "NumPy", "Pandas"]},
        {"step": 2, "topic": "Core ML Algorithms & Mathematical Foundations", "skills": ["Statistics", "Machine Learning", "Scikit-learn"]},
        {"step": 3, "topic": "Deep Learning & Neural Networks", "skills": ["PyTorch", "TensorFlow", "Deep Learning"]},
        {"step": 4, "topic": "Model Deployment, API Wrapping & MLOps", "skills": ["Docker", "Git", "REST API", "AWS", "MLOps"]}
    ],
    "AI Engineer": [
        {"step": 1, "topic": "Python Core & Mathematical Foundations", "skills": ["Python", "Math", "Statistics"]},
        {"step": 2, "topic": "Deep Learning & Neural Architecture", "skills": ["Deep Learning", "PyTorch", "TensorFlow"]},
        {"step": 3, "topic": "Generative AI, LLMs & Prompt Engineering", "skills": ["LLMs", "Transformers", "Prompt Engineering"]},
        {"step": 4, "topic": "Vector Databases, Vision & API Deployment", "skills": ["Vector DB", "OpenCV", "REST API", "Docker"]}
    ],
    "NLP Engineer": [
        {"step": 1, "topic": "Python Programming & NLP Fundamentals", "skills": ["Python", "NLTK", "spaCy"]},
        {"step": 2, "topic": "Text Processing & Classification Models", "skills": ["Scikit-learn", "Text Processing", "Statistics"]},
        {"step": 3, "topic": "Deep Learning & Transformer Architectures", "skills": ["PyTorch", "Deep Learning", "Transformers", "BERT"]},
        {"step": 4, "topic": "Large Language Models & Production Deployment", "skills": ["LLMs", "Git", "REST API"]}
    ],
    "Software Engineer": [
        {"step": 1, "topic": "Data Structures & Algorithms Core", "skills": ["Data Structures", "Algorithms", "Java", "C++"]},
        {"step": 2, "topic": "Scripting & Database Management", "skills": ["Python", "SQL", "PostgreSQL", "DBMS"]},
        {"step": 3, "topic": "REST API Architecture & Microservices", "skills": ["REST API", "Git"]},
        {"step": 4, "topic": "Containerization & Infrastructure", "skills": ["Docker", "Linux"]}
    ],
    "DevOps Engineer": [
        {"step": 1, "topic": "Linux Systems Administration & Shell Scripting", "skills": ["Linux", "Shell Scripting", "Git"]},
        {"step": 2, "topic": "Containerization & Orchestration", "skills": ["Docker", "Kubernetes"]},
        {"step": 3, "topic": "Infrastructure as Code & Cloud Platforms", "skills": ["Terraform", "AWS"]},
        {"step": 4, "topic": "CI/CD Automation & Monitoring", "skills": ["CI/CD", "Monitoring", "Nginx"]}
    ],
    "Cloud Engineer": [
        {"step": 1, "topic": "Cloud Infrastructure & Networking Core", "skills": ["AWS", "Cloud Computing", "Networking", "Linux"]},
        {"step": 2, "topic": "Infrastructure Provisioning & Automation", "skills": ["Terraform", "Docker", "Python"]},
        {"step": 3, "topic": "Security, IAM & Cloud Architecture", "skills": ["Cloud Security", "IAM"]}
    ]
}


def normalize_role_title(role: str) -> str:
    """Normalizes role query strings to standard canonical title."""
    if not role or not role.strip():
        return "Machine Learning Engineer"

    clean_role = role.strip().lower()
    for pattern, canonical in ROLE_ALIASES.items():
        if re.search(pattern, clean_role):
            return canonical

    # Title case match fallback
    return role.strip().title()


class SkillGapAnalyzer:
    """Analyzes user skill gaps and generates career roadmaps."""

    def analyze_gap(self, user_skills: list, required_skills: list) -> dict:
        """Calculates missing skills: Required skills - User skills."""
        user_keys = {normalize_skill_key(s) for s in user_skills if s}

        matching = []
        missing = []

        for req in required_skills:
            k = normalize_skill_key(req)
            disp = normalize_skill(req)
            if k in user_keys:
                if disp not in matching:
                    matching.append(disp)
            else:
                if disp not in missing:
                    missing.append(disp)

        return {
            "matching_skills": matching,
            "missing_skills": missing,
            "match_count": len(matching),
            "missing_count": len(missing),
            "gap_percentage": round((len(missing) / float(len(required_skills)) * 100), 1) if required_skills else 0.0
        }

    def generate_roadmap(self, user_profile: dict, target_role: str = None, active_resume: dict = None) -> dict:
        """Generates a customized step-by-step career learning roadmap."""
        roles = user_profile.get("target_roles", [])
        raw_role = target_role or (roles[0] if roles else "Machine Learning Engineer")
        normalized_role = normalize_role_title(raw_role)

        template = DEFAULT_ROLE_ROADMAPS.get(normalized_role)
        is_supported = template is not None

        if not template:
            # Fallback advice template for unsupported custom roles
            template = DEFAULT_ROLE_ROADMAPS["Software Engineer"]

        # Aggregate skills from user profile and active resume
        all_user_skills = set(user_profile.get("skills", []))
        if active_resume and isinstance(active_resume.get("extracted_data"), dict):
            resume_skills = active_resume["extracted_data"].get("skills", [])
            all_user_skills.update(resume_skills)

        user_skills_normalized = {normalize_skill_key(s) for s in all_user_skills if s}

        structured_steps = []
        all_missing_skills = []
        all_required_skills = []

        for step in template:
            step_skills = step["skills"]
            completed = []
            pending = []

            for s in step_skills:
                k = normalize_skill_key(s)
                disp = normalize_skill(s)
                all_required_skills.append(disp)
                if k in user_skills_normalized:
                    completed.append(disp)
                else:
                    pending.append(disp)
                    all_missing_skills.append(disp)

            status = "Completed" if len(pending) == 0 else ("In Progress" if len(completed) > 0 else "Recommended")

            structured_steps.append({
                "step_number": step["step"],
                "title": step["topic"],
                "description": f"Focus on mastering {', '.join(pending) if pending else 'advanced concepts'}.",
                "skills": step_skills,
                "completed_skills": completed,
                "pending_skills": pending,
                "status": status
            })

        all_req_unique = list(dict.fromkeys(all_required_skills))
        all_missing_unique = list(dict.fromkeys(all_missing_skills))
        total_req_count = len(all_req_unique)
        missing_count = len(all_missing_unique)
        acquired_count = total_req_count - missing_count
        prep_percentage = int((acquired_count / float(total_req_count)) * 100) if total_req_count > 0 else 0

        return {
            "success": True,
            "target_role": normalized_role,
            "is_supported_role": is_supported,
            "preparedness_percentage": prep_percentage,
            "completion_percentage": prep_percentage,
            "total_required_count": total_req_count,
            "acquired_count": acquired_count,
            "user_current_skills": list(all_user_skills),
            "all_missing_skills": all_missing_unique,
            "steps": structured_steps
        }


def get_role_requirements(role_title: str) -> list:
    """Returns required skills list for a target role."""
    normalized = normalize_role_title(role_title)
    template = DEFAULT_ROLE_ROADMAPS.get(normalized, DEFAULT_ROLE_ROADMAPS["Software Engineer"])
    reqs = []
    for step in template:
        reqs.extend(step.get("skills", []))
    return normalize_skill_list(reqs)


def calculate_roadmap(user_skills: list, target_role: str = None) -> dict:
    """Convenience wrapper for roadmap calculation."""
    analyzer = SkillGapAnalyzer()
    return analyzer.generate_roadmap({"skills": user_skills, "target_roles": [target_role] if target_role else []}, target_role=target_role)

