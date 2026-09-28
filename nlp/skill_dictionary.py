"""
Centralized Skill Normalization & Canonical Skill Dictionary for CareerBot.
Converts skill aliases into standard canonical names to ensure accurate matching.
"""

# Map lowercase aliases to lowercased canonical names
SKILL_ALIASES = {
    # AI / ML / Data Science
    "ml": "machine learning",
    "machine learning": "machine learning",
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    "dl": "deep learning",
    "deep learning": "deep learning",
    "nlp": "natural language processing",
    "natural language processing": "natural language processing",
    "cv": "computer vision",
    "computer vision": "computer vision",
    "ds": "data science",
    "data science": "data science",
    "sklearn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "scikitlearn": "scikit-learn",
    "pytorch": "pytorch",
    "tf": "tensorflow",
    "tensorflow": "tensorflow",
    "opencv": "opencv",
    "nltk": "nltk",
    "spacy": "spacy",
    "pandas": "pandas",
    "numpy": "numpy",
    "tableau": "tableau",
    "excel": "excel",
    "statistics": "statistics",
    "math": "mathematics",
    "mathematics": "mathematics",
    "spark": "spark",
    "apache spark": "spark",
    "etl": "etl",

    # Programming Languages
    "py": "python",
    "python": "python",
    "java": "java",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "c++": "c++",
    "cpp": "c++",
    "c#": "c#",
    "csharp": "c#",
    "c": "c",
    "bash": "bash",
    "shell": "bash",
    "sql": "sql",

    # Web & Frameworks
    "html": "html",
    "html5": "html",
    "css": "css",
    "css3": "css",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "express": "express",
    "expressjs": "express",
    "rest": "rest api",
    "rest api": "rest api",
    "restful api": "rest api",

    # Databases & Storage
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "mysql": "mysql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "dbms": "database management systems",
    "database": "sql",

    # DevOps, Cloud & Tools
    "git": "git",
    "github": "git",
    "docker": "docker",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "azure": "azure",
    "linux": "linux",
    "selenium": "selenium",
    "pytest": "pytest",
    "wireshark": "wireshark",
    "network security": "network security",
    "cybersecurity": "cybersecurity",
    "dsa": "data structures",
    "data structures": "data structures",
    "algorithms": "algorithms",
}

# Display titles for canonical skills
CANONICAL_DISPLAY = {
    "machine learning": "Machine Learning",
    "artificial intelligence": "Artificial Intelligence",
    "deep learning": "Deep Learning",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
    "data science": "Data Science",
    "scikit-learn": "Scikit-learn",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "opencv": "OpenCV",
    "nltk": "NLTK",
    "spacy": "spaCy",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "tableau": "Tableau",
    "excel": "Excel",
    "statistics": "Statistics",
    "mathematics": "Mathematics",
    "spark": "Spark",
    "etl": "ETL",
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "c++": "C++",
    "c#": "C#",
    "c": "C",
    "bash": "Bash",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "react": "React",
    "nodejs": "Node.js",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "express": "Express",
    "rest api": "REST API",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "database management systems": "DBMS",
    "git": "Git",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "linux": "Linux",
    "selenium": "Selenium",
    "pytest": "PyTest",
    "wireshark": "Wireshark",
    "network security": "Network Security",
    "cybersecurity": "Cybersecurity",
    "data structures": "Data Structures",
    "algorithms": "Algorithms",
}

# Recognized Domain Interests
DOMAIN_INTERESTS = [
    "Artificial Intelligence", "Machine Learning", "Data Science",
    "Web Development", "Cybersecurity", "Cloud Computing", "NLP",
    "Robotics", "Data Engineering", "Software Development"
]

# Recognized Education Degrees
EDUCATION_DEGREES = [
    "B.Tech", "B.E.", "M.Tech", "B.Sc", "MCA", "Diploma", "B.C.A", "M.Sc", "Ph.D", "CSE Student"
]

# Recognized Experience Levels
EXPERIENCE_LEVELS = [
    "Fresher", "Intern", "Entry Level", "Junior", "1-2 years", "2+ years"
]

# Recognized Target Roles
TARGET_ROLES = [
    "Python Developer", "Machine Learning Engineer", "Data Analyst",
    "Data Scientist", "NLP Engineer", "AI Engineer", "AI Intern", "NLP Intern",
    "Frontend Developer", "Backend Developer", "Full Stack Developer",
    "Software Engineer", "DevOps Engineer", "Data Engineer", "Cybersecurity Analyst"
]


def normalize_skill(skill_raw: str) -> str:
    """Converts a skill string into its canonical display name."""
    if not skill_raw:
        return ""
    clean_key = skill_raw.strip().lower()
    canonical_key = SKILL_ALIASES.get(clean_key, clean_key)
    return CANONICAL_DISPLAY.get(canonical_key, canonical_key.title())


def normalize_skill_key(skill_raw: str) -> str:
    """Converts a skill string into its lowercased canonical key for exact matching."""
    if not skill_raw:
        return ""
    clean_key = skill_raw.strip().lower()
    return SKILL_ALIASES.get(clean_key, clean_key)


def normalize_skill_list(skills_list: list) -> list:
    """Takes a list of raw skill strings and returns unique canonical display names."""
    if not skills_list:
        return []
    seen_keys = set()
    result = []
    for raw in skills_list:
        key = normalize_skill_key(raw)
        if key and key not in seen_keys:
            seen_keys.add(key)
            result.append(normalize_skill(raw))
    return result
