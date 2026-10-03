"""
Structured Career Role Knowledge Layer for CareerBot.
Provides canonical roles, exact skill requirements, certifications, tools, and interview topics.
Eliminates role confusion and ensures role-specific answers.
"""

from typing import Dict, List, Optional, Any
import re

CAREER_ROLES: Dict[str, Dict[str, Any]] = {
    "data analyst": {
        "title": "Data Analyst",
        "aliases": [
            "data analyst", "data analytics", "business analyst", "junior data analyst",
            "डेटा एनालिस्ट", "डेटा विश्लेषक", "డేటా అనలిస్ట్"
        ],
        "required_skills": [
            "SQL (Queries, Joins, Aggregations)",
            "Microsoft Excel (VLOOKUP, Pivot Tables, Formulas)",
            "Python (Pandas, NumPy for data manipulation)",
            "Data Visualization (Power BI, Tableau, or Matplotlib/Seaborn)",
            "Descriptive Statistics & Probability",
            "Data Cleaning & Preprocessing",
            "Analytical Thinking & Problem Solving"
        ],
        "preferred_skills": [
            "R Programming",
            "ETL Pipelines & Data Warehousing",
            "A/B Testing & Experimentation",
            "Basic Machine Learning Regression",
            "Storytelling with Data & Executive Dashboards"
        ],
        "certifications": [
            "Google Data Analytics Professional Certificate",
            "Microsoft Certified: Power BI Data Analyst Associate (PL-300)",
            "Tableau Desktop Specialist"
        ],
        "interview_topics": [
            "SQL Joins, Group By, Window Functions (ROW_NUMBER, RANK)",
            "Handling missing values and data outliers in Pandas",
            "Creating impactful business metrics and KPI dashboards",
            "Difference between correlation and causation in metrics"
        ],
        "description": "Translates complex datasets into actionable business intelligence through SQL, Excel, Python, and interactive dashboards."
    },
    "java developer": {
        "title": "Java Developer",
        "aliases": [
            "java developer", "java engineer", "backend java developer", "core java developer",
            "जावा डेवलपर", "जावा", "జావా డెవలపర్", "జావా"
        ],
        "required_skills": [
            "Core Java (OOP, Collections, Multithreading, Streams)",
            "Spring Boot Framework",
            "RESTful API Development & JSON",
            "Relational Databases & SQL (PostgreSQL, MySQL)",
            "Hibernate / JPA ORM",
            "Git Version Control",
            "Maven / Gradle Build Automation",
            "Unit Testing (JUnit 5, Mockito)"
        ],
        "preferred_skills": [
            "Microservices Architecture",
            "Docker & Containerization",
            "Spring Security & JWT Authentication",
            "Message Brokers (Apache Kafka or RabbitMQ)",
            "CI/CD Pipelines & Cloud Basics (AWS/Azure)"
        ],
        "certifications": [
            "Oracle Certified Professional: Java SE Developer",
            "Spring Certified Professional"
        ],
        "interview_topics": [
            "OOP Principles (Polymorphism, Inheritance, Encapsulation, Abstraction)",
            "Java Memory Model, Garbage Collection & String Pool",
            "Spring Boot Dependency Injection and Application Context",
            "Handling Transactions and JPA N+1 Query Problem"
        ],
        "description": "Designs and builds scalable enterprise backend applications and microservices using Java and Spring Boot."
    },
    "python developer": {
        "title": "Python Developer",
        "aliases": [
            "python developer", "python engineer", "backend python developer", "python programmer",
            "पाइथन डेवलपर", "पायथन डेवलपर", "पाइथन", "पायथन", "పైథాన్ డెవలపర్", "పైథాన్"
        ],
        "required_skills": [
            "Python (Data Structures, OOP, Generators, Decorators)",
            "Web Frameworks (FastAPI, Flask, or Django)",
            "RESTful API Design & Integration",
            "Relational Databases & SQL (PostgreSQL/SQLite/MySQL)",
            "Object-Relational Mapping (SQLAlchemy/Django ORM)",
            "Git Version Control",
            "Automated Testing (PyTest, unittest)",
            "Virtual Environments & Package Management (pip, poetry)"
        ],
        "preferred_skills": [
            "Asynchronous Programming (asyncio, Celery)",
            "Docker & Containerization",
            "Redis Caching & Background Task Queues",
            "Cloud Deployment (AWS, GCP, Render)",
            "Basic Frontend Integration (HTML/CSS/JS)"
        ],
        "certifications": [
            "Certified Associate in Python Programming (PCAP)",
            "AWS Certified Developer - Associate"
        ],
        "interview_topics": [
            "Python Memory Management, GIL (Global Interpreter Lock), and Mutability",
            "List Comprehensions, Generators vs Iterators, and Decorators",
            "Building RESTful APIs with FastAPI/Flask and Input Validation (Pydantic)",
            "Database connection pooling and migration strategies"
        ],
        "description": "Develops robust backend services, web applications, and automation scripts using modern Python frameworks."
    },
    "machine learning engineer": {
        "title": "Machine Learning Engineer",
        "aliases": [
            "machine learning engineer", "ml engineer", "machine learning", "ml developer", "ai/ml engineer",
            "मशीन लर्निंग इंजीनियर", "मशीन लर्निंग", "మెషిన్ లెర్నింగ్"
        ],
        "required_skills": [
            "Python (Advanced numerical computing)",
            "Linear Algebra, Calculus & Applied Statistics",
            "NumPy, Pandas & Data Preprocessing",
            "Scikit-Learn (Supervised & Unsupervised Algorithms)",
            "Model Evaluation, Metrics (Precision, Recall, F1, ROC-AUC) & Cross-Validation",
            "Deep Learning Framework (PyTorch or TensorFlow)",
            "Model Deployment & REST APIs (FastAPI/Flask)"
        ],
        "preferred_skills": [
            "MLOps, Experiment Tracking (MLflow, Weights & Biases)",
            "Docker & Containerized Model Serving",
            "Feature Engineering & Dimensionality Reduction (PCA)",
            "Natural Language Processing or Computer Vision",
            "Cloud ML Services (AWS SageMaker, Google Vertex AI)"
        ],
        "certifications": [
            "AWS Certified Machine Learning - Specialty",
            "Google Professional Machine Learning Engineer",
            "DeepLearning.AI Machine Learning Specialization"
        ],
        "interview_topics": [
            "Bias-Variance Tradeoff and Regularization (L1 Lasso, L2 Ridge)",
            "Decision Trees, Random Forests vs Gradient Boosting (XGBoost/LightGBM)",
            "Gradient Descent optimization and Learning Rate tuning",
            "Handling imbalanced datasets (SMOTE, Class Weights, Precision-Recall)"
        ],
        "description": "Architects, trains, validates, and deploys predictive machine learning and deep learning models into production."
    },
    "data scientist": {
        "title": "Data Scientist",
        "aliases": ["data scientist", "data science"],
        "required_skills": [
            "Python or R for Statistical Computing",
            "Advanced SQL & Relational Database Extraction",
            "Probability, Hypothesis Testing & Inferential Statistics",
            "Exploratory Data Analysis (EDA) & Feature Engineering",
            "Machine Learning Algorithms (Scikit-Learn)",
            "Data Storytelling & Visualization (Matplotlib, Seaborn, Tableau)",
            "Business Domain Translation & Experiment Design"
        ],
        "preferred_skills": [
            "A/B Testing Frameworks",
            "Big Data Technologies (Apache Spark, PySpark)",
            "Time Series Forecasting (ARIMA, Prophet)",
            "Deep Learning & NLP Fundamentals",
            "Docker & Cloud Analytical Workspaces"
        ],
        "certifications": [
            "IBM Data Science Professional Certificate",
            "Microsoft Certified: Azure Data Scientist Associate"
        ],
        "interview_topics": [
            "Designing valid A/B tests: Sample size, Statistical Power, and P-values",
            "Feature selection and feature transformation techniques",
            "Interpretable ML: SHAP values, Feature Importance, and Model Fairness",
            "Translating ambiguous business problems into mathematical objectives"
        ],
        "description": "Discovers predictive patterns, builds scientific models, and formulates strategic hypotheses from complex corporate data."
    },
    "frontend developer": {
        "title": "Frontend Developer",
        "aliases": ["frontend developer", "frontend engineer", "ui developer", "react developer", "web developer"],
        "required_skills": [
            "HTML5 (Semantic Web, Accessibility, SEO)",
            "CSS3 (Flexbox, Grid, Responsive Design, CSS Variables)",
            "JavaScript ES6+ (Async/Await, DOM manipulation, Closures)",
            "React.js (Hooks, State Management, Component Lifecycle)",
            "REST API Client Integration (Fetch, Axios)",
            "Git Version Control",
            "Browser Developer Tools & Performance Profiling",
            "Build Tools & Bundlers (Vite, Webpack, npm)"
        ],
        "preferred_skills": [
            "TypeScript",
            "Next.js / Server-Side Rendering (SSR)",
            "Modern CSS Frameworks (Tailwind CSS, Bootstrap)",
            "Frontend Testing (Jest, React Testing Library)",
            "Web Performance & Core Web Vitals Optimization"
        ],
        "certifications": [
            "Meta Front-End Developer Professional Certificate",
            "Certified React Developer Associate"
        ],
        "interview_topics": [
            "JavaScript Event Loop, Promises, and Microtask Queue",
            "React Virtual DOM, Reconciliation, and State Re-rendering optimization",
            "CSS Box Model, Stacking Context, and Responsive Breakpoints",
            "Web Security: XSS, CSRF, and Content Security Policy"
        ],
        "description": "Crafts responsive, interactive, accessible user interfaces and web applications using modern JavaScript and React."
    },
    "backend developer": {
        "title": "Backend Developer",
        "aliases": ["backend developer", "backend engineer", "server-side developer"],
        "required_skills": [
            "Server-side Language (Python, Java, Node.js, or Go)",
            "RESTful API & Microservices Architecture",
            "Relational Databases (PostgreSQL, MySQL) & Indexing",
            "Authentication & Authorization (JWT, OAuth2, Session Security)",
            "SQL & Database Schema Design",
            "Git & Team Workflow",
            "Unit & Integration Testing",
            "Docker & Containerization Fundamentals"
        ],
        "preferred_skills": [
            "Caching Layers (Redis, Memcached)",
            "Message Queues (Kafka, RabbitMQ)",
            "NoSQL Databases (MongoDB, Cassandra)",
            "GraphQL API Design",
            "Cloud Deployment (AWS, GCP, Docker Compose)"
        ],
        "certifications": [
            "AWS Certified Solutions Architect - Associate",
            "Oracle Certified Professional Java SE"
        ],
        "interview_topics": [
            "Database Normalization, ACID Transactions, and Query Optimization",
            "Scalability: Horizontal vs Vertical scaling, Load Balancers, and Caching",
            "RESTful API Status Codes and Idempotency",
            "Authentication security and secure password hashing"
        ],
        "description": "Builds secure, reliable, high-throughput server applications, database architectures, and API backbones."
    },
    "full stack developer": {
        "title": "Full Stack Developer",
        "aliases": ["full stack developer", "full stack engineer", "fullstack developer"],
        "required_skills": [
            "Frontend Fundamentals (HTML5, CSS3, JavaScript ES6+)",
            "Frontend Framework (React.js, Vue, or Angular)",
            "Backend Development (Node.js/Express, Python/FastAPI, or Java/Spring Boot)",
            "Relational & NoSQL Databases (PostgreSQL, MongoDB)",
            "RESTful API Architecture & JSON data exchange",
            "Git & GitHub Workflow",
            "Authentication, User Sessions & Security",
            "Cloud Deployment Basics (Docker, Vercel, Render, AWS)"
        ],
        "preferred_skills": [
            "TypeScript across frontend and backend",
            "Next.js / Full-Stack SSR Frameworks",
            "CI/CD Pipelines",
            "State Management (Redux Toolkit, Zustand)",
            "Automated Testing (E2E & Unit)"
        ],
        "certifications": [
            "Full Stack Web Development Professional Certificate",
            "IBM Full Stack Cloud Developer Certificate"
        ],
        "interview_topics": [
            "End-to-end data lifecycle from browser click to database row and back",
            "Cross-Origin Resource Sharing (CORS) and API token management",
            "Designing relational schemas and managing frontend state sync",
            "Optimizing full-stack web application performance"
        ],
        "description": "Engineers end-to-end web applications bridging rich client-side interfaces with robust server architectures."
    },
    "devops engineer": {
        "title": "DevOps Engineer",
        "aliases": ["devops engineer", "devops", "site reliability engineer", "sre"],
        "required_skills": [
            "Linux System Administration & Shell Scripting (Bash)",
            "Docker & Containerization",
            "Kubernetes Orchestration & Helm",
            "CI/CD Pipelines (GitHub Actions, GitLab CI, or Jenkins)",
            "Infrastructure as Code (Terraform)",
            "Cloud Platforms (AWS, Azure, or GCP)",
            "Version Control & Branching Strategies (Git)",
            "Networking, DNS, SSL/TLS, and Security"
        ],
        "preferred_skills": [
            "Observability & Monitoring (Prometheus, Grafana, ELK Stack)",
            "Configuration Management (Ansible)",
            "Python or Go for Automation",
            "Zero Downtime Deployments (Blue-Green, Canary)",
            "Cloud Security & Compliance"
        ],
        "certifications": [
            "AWS Certified DevOps Engineer - Professional",
            "Certified Kubernetes Administrator (CKA)",
            "HashiCorp Certified: Terraform Associate"
        ],
        "interview_topics": [
            "Containerization vs Virtualization: Cgroups, Namespaces, Docker layers",
            "CI/CD Pipeline design with automated testing, linting, and rollback",
            "Kubernetes Pods, Services, Deployments, and Ingress routing",
            "Terraform State management and drift detection"
        ],
        "description": "Automates software delivery, builds scalable cloud infrastructure, and ensures system reliability and uptime."
    },
    "cloud engineer": {
        "title": "Cloud Engineer",
        "aliases": ["cloud engineer", "cloud architect", "aws engineer", "azure engineer"],
        "required_skills": [
            "Cloud Infrastructure (AWS, Azure, or Google Cloud)",
            "Virtual Networking (VPC, Subnets, Route Tables, NAT)",
            "Identity & Access Management (IAM, Least Privilege)",
            "Compute Services (EC2, Lambda, Virtual Machines)",
            "Storage Services (S3, Block Storage, File Systems)",
            "Infrastructure as Code (Terraform or CloudFormation)",
            "Docker & Container Deployment"
        ],
        "preferred_skills": [
            "Kubernetes & Container Orchestration",
            "Serverless Application Design",
            "Cost Optimization & Billing Analysis",
            "Cloud Security & Network Firewalls",
            "Linux & Python Scripting"
        ],
        "certifications": [
            "AWS Certified Solutions Architect - Associate",
            "Microsoft Certified: Azure Administrator Associate",
            "Google Associate Cloud Engineer"
        ],
        "interview_topics": [
            "High availability and disaster recovery across multi-region architectures",
            "IAM Role-based access control and security best practices",
            "Object storage vs Block storage vs Relational databases in Cloud",
            "Serverless architecture benefits and cold start mitigation"
        ],
        "description": "Architects, provisions, and maintains secure, high-availability cloud systems and scalable environments."
    },
    "nlp engineer": {
        "title": "NLP Engineer",
        "aliases": ["nlp engineer", "natural language processing engineer", "nlp developer"],
        "required_skills": [
            "Python (Advanced)",
            "Natural Language Processing Fundamentals (Tokenization, Lemmatization, POS tagging)",
            "NLP Libraries (NLTK, spaCy, HuggingFace Transformers)",
            "Text Representation (TF-IDF, Word2Vec, Dense Embeddings)",
            "Machine Learning for Text (Classification, Named Entity Recognition)",
            "PyTorch or TensorFlow for Neural Models",
            "Evaluating NLP Models (BLEU, ROUGE, Precision/Recall, Perplexity)"
        ],
        "preferred_skills": [
            "Large Language Models (LLMs, Fine-tuning, LoRA, Prompt Engineering)",
            "Vector Databases (Pinecone, ChromaDB, FAISS)",
            "Retrieval-Augmented Generation (RAG) Architecture",
            "FastAPI for Real-time Inference Serving",
            "Docker & GPU Acceleration (CUDA)"
        ],
        "certifications": [
            "DeepLearning.AI Natural Language Processing Specialization",
            "Hugging Face NLP Course Certification"
        ],
        "interview_topics": [
            "Transformer Architecture: Self-Attention, Multi-Head Attention, Positional Encoding",
            "Handling Out-of-Vocabulary words and Subword Tokenization (BPE, WordPiece)",
            "Fine-Tuning Pre-trained LLMs vs Retrieval-Augmented Generation (RAG)",
            "Text normalization and regular expressions for noisy datasets"
        ],
        "description": "Develops natural language processing pipelines, language models, entity extractors, and conversational AI systems."
    },
    "software engineer": {
        "title": "Software Engineer",
        "aliases": ["software engineer", "software developer", "swe", "sde"],
        "required_skills": [
            "Core Programming (Python, Java, C++, or C#)",
            "Data Structures & Algorithms (Arrays, Hash Maps, Trees, Graphs)",
            "Object-Oriented Programming (OOP) & Clean Code Principles",
            "Relational Databases & SQL Queries",
            "RESTful API Concepts & System Interaction",
            "Git Version Control & Collaboration",
            "Unit Testing & Debugging Skills",
            "Software Development Lifecycle (SDLC)"
        ],
        "preferred_skills": [
            "System Design & Scalability Principles",
            "Docker & Virtualization",
            "CI/CD Automation",
            "Cloud Platform Basics",
            "Design Patterns (Factory, Singleton, Observer)"
        ],
        "certifications": [
            "AWS Certified Cloud Practitioner",
            "Software Engineering Specialization"
        ],
        "interview_topics": [
            "Time and Space Complexity (Big-O analysis)",
            "Object-Oriented Design and SOLID principles",
            "Common Data Structures: Hash Map collisions, Binary Search Trees",
            "Writing maintainable code and automated unit tests"
        ],
        "description": "Designs, writes, tests, and delivers high-quality software solutions using robust algorithms and engineering principles."
    }
}


def extract_role_from_text(text: str) -> Optional[str]:
    """
    Extracts the canonical career role key from user query text.
    Handles compound words, aliases, Indic scripts (Hindi/Telugu), and substring matches accurately.
    Prioritizes longer and more specific role matches (e.g. 'data analyst' before 'data').
    """
    if not text:
        return None

    cleaned = text.strip().lower()

    # Exact multi-word matching ordered by longest alias first
    all_alias_matches = []
    for role_key, role_info in CAREER_ROLES.items():
        for alias in role_info.get("aliases", []):
            alias_lower = alias.lower()
            # If alias contains non-ascii (like Hindi or Telugu), check direct containment
            if any(ord(c) > 127 for c in alias_lower):
                if alias_lower in cleaned:
                    all_alias_matches.append((len(alias_lower), role_key))
            else:
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                if re.search(pattern, cleaned):
                    all_alias_matches.append((len(alias_lower), role_key))

    if all_alias_matches:
        # Pick the most specific (longest) match
        all_alias_matches.sort(key=lambda x: x[0], reverse=True)
        return all_alias_matches[0][1]

    # Specific heuristic fallback keywords
    # 1. Python check (including Hindi 'पाइथन'/'पायथन' and Telugu 'పైథాన్')
    if any(k in cleaned for k in ["python", "पाइथन", "पायथन", "పైథాన్"]):
        return "python developer"

    # 2. Java check (ensure JavaScript is excluded)
    if (("java" in cleaned and "javascript" not in cleaned) or "जावा" in cleaned or "జావా" in cleaned):
        return "java developer"

    # 3. Data Analyst
    if any(k in cleaned for k in ["data analyst", "डेटा एनालिस्ट", "డేటా అనలిస్ట్", "analyst", "analytics", "एनालिस्ट", "అనలిస్ట్"]):
        return "data analyst"

    # 4. Machine Learning
    if any(k in cleaned for k in ["machine learning", "मशीन लर्निंग", "మెషిన్ లెర్నింగ్", "ml"]):
        return "machine learning engineer"

    if "data science" in cleaned or "scientist" in cleaned:
        return "data scientist"
    if "frontend" in cleaned or "react" in cleaned or "angular" in cleaned or "vue" in cleaned:
        return "frontend developer"
    if "backend" in cleaned or "spring boot" in cleaned or "django" in cleaned or "fastapi" in cleaned:
        return "backend developer"
    if "full stack" in cleaned or "fullstack" in cleaned or "फुल स्टैक" in cleaned:
        return "full stack developer"
    if "devops" in cleaned or "kubernetes" in cleaned or "docker" in cleaned or "ci/cd" in cleaned or "डेवऑप्स" in cleaned:
        return "devops engineer"
    if "cloud" in cleaned or "aws" in cleaned or "azure" in cleaned or "gcp" in cleaned or "क्लाउड" in cleaned:
        return "cloud engineer"
    if "nlp" in cleaned or "natural language" in cleaned:
        return "nlp engineer"
    if "software" in cleaned or "engineer" in cleaned or "developer" in cleaned or "डेवलपर" in cleaned or "డెవలపర్" in cleaned:
        return "software engineer"

    return None


def get_role_details(role_key: Optional[str]) -> Dict[str, Any]:
    """Retrieves full details for a given role key with safe defaults."""
    if role_key and role_key.lower() in CAREER_ROLES:
        return CAREER_ROLES[role_key.lower()]
    return CAREER_ROLES["software engineer"]
