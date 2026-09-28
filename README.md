# CareerBot — NLP-Based Intelligent Career & Job Recommendation System

**CareerBot** is a modern, intelligent conversational career assistant and job recommendation system designed for college students, freshers, entry-level candidates, and junior developers. It processes natural language inputs to extract career profiles, analyze job postings, compute transparent match scores, identify skill gaps, and generate customized career roadmaps.

---

## Key Features

1. **Conversational Career Chatbot**: Real-time natural language interaction with intent classification and contextual responses.
2. **NLP Profile Extraction**: Extracts skills, interests, education degrees, experience levels, and target roles from user chat messages and uploaded resumes.
3. **Skill Normalization & Alias Engine**: Centralized canonical skill dictionary mapping skill variations (e.g. `ML` $\rightarrow$ `Machine Learning`, `JS` $\rightarrow$ `JavaScript`, `Postgres` $\rightarrow$ `PostgreSQL`).
4. **Transparent Multi-Factor Job Matching**:
   - **Skill Score** ($50\%$): $\text{Matching Required Skills} / \text{Total Required Skills}$
   - **TF-IDF Semantic Similarity** ($25\%$): Cosine similarity between profile and job vectors
   - **Interest Alignment** ($15\%$): Domain overlap
   - **Experience Fit** ($10\%$): Career level alignment
5. **Explainable Recommendations**: Detailed breakdown displaying matching skills, missing skills, and score components.
6. **"No Strong Match" Banding**: Classifies recommendations into **Strong Match** ($\ge 75\%$), **Moderate Match** ($50\% - 74\%$), and **Limited Match** ($< 50\%$).
7. **Skill Gap Analysis & Career Roadmap**: Generates step-by-step career learning paths for target roles (e.g. Machine Learning Engineer, Data Scientist).
8. **Resume Parser**: Extracts text and sections from PDF, DOCX, and TXT resumes to auto-populate user profiles.
9. **`/api/health` Endpoint**: Standardized API health monitor reporting database, NLP, and Gemini status.
10. **Optional Gemini LLM Integration**: Uses Gemini API when configured, with robust local template fallbacks.

---

## Core Matching Algorithm Explained

The system uses a transparent, explainable scoring formula bounded between $0.0$ and $1.0$ ($0\%$ to $100\%$):

$$\text{OverallScore} = 0.50 \times \text{SkillScore} + 0.25 \times \text{SemanticScore} + 0.15 \times \text{InterestScore} + 0.10 \times \text{ExperienceScore}$$

### Component Definitions:
1. **SkillScore** ($50\%$):
   $$\text{SkillScore} = \frac{\text{Count of User Skills matching Job Required Skills}}{\text{Total Count of Job Required Skills}}$$
2. **SemanticScore** ($25\%$):
   $$\text{CosineSimilarity}(\vec{V}_{\text{user\_profile}}, \vec{V}_{\text{job\_description}})$$
   Calculated using scikit-learn `TfidfVectorizer`.
3. **InterestScore** ($15\%$):
   Overlap ratio between user domain interests and job title/description keywords.
4. **ExperienceScore** ($10\%$):
   Fit metric comparing candidate experience level against job entry requirement.

---

## Project Structure

```
c:\project_nlp\
├── app.py                      # Flask entry point & API routes
├── config.py                   # App configuration & thresholds
├── requirements.txt            # Python dependencies
├── Procfile                    # Production process definition (Gunicorn)
├── README.md                   # Full documentation & viva guide
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore rules
├── data/
│   └── jobs.csv                # Verified job dataset
├── database/
│   ├── database.py             # SQLAlchemy session & DB connection
│   └── models.py               # ORM Models (User, UserProfile, Resume, JobModel, etc.)
├── nlp/
│   ├── preprocessing.py        # Text cleaning, NLTK tokenization & lemmatization
│   ├── skill_dictionary.py     # Canonical skill catalog & alias normalization
│   ├── skill_extractor.py      # Skill, interest, education & experience extractor
│   ├── intent_classifier.py    # Intent classifier returning 11 standard intents
│   ├── job_analyzer.py         # Job description attribute parser
│   └── semantic_similarity.py  # TF-IDF + Cosine similarity calculator
├── recommender/
│   ├── matcher.py              # Normalized 4-component score calculator
│   ├── ranking.py              # Filter-first job ranking engine
│   └── skill_gap.py            # Skill gap analysis & career roadmap generator
├── services/
│   ├── career_service.py       # Profile & recommendation coordinator
│   ├── resume_service.py       # PDF/DOCX/TXT resume section parser
│   ├── job_service.py          # Abstract JobProvider & dataset loader
│   ├── news_service.py         # Real-time corporate & IT industry news provider
│   └── gemini_service.py       # Gemini API client with safe local fallback
├── templates/                  # Jinja2 HTML templates
├── static/                     # CSS & JS assets
├── uploads/                    # Resume upload storage (gitignored with .gitkeep)
└── tests/                      # Automated test suite
```

---

## Technology Stack

- **Backend Framework**: Python 3.10+, Flask 3.0+
- **Production WSGI Server**: Gunicorn
- **Database**: SQLite (default) / PostgreSQL (production-ready via SQLAlchemy ORM)
- **NLP & ML**: NLTK (Tokenization, Lemmatization, Stop-words), Scikit-Learn (TF-IDF, Cosine Similarity)
- **Document Parsing**: `pypdf`, `python-docx`
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (AJAX)
- **Testing**: Python `unittest` / `pytest`

---

## Installation & Setup (Local Development)

### 1. Clone & Enter Directory
```bash
git clone <repository_url>
cd project_nlp
```

### 2. Create & Activate Virtual Environment
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows PowerShell:
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate your environment variables (e.g. `SECRET_KEY`, optional `GEMINI_API_KEY`, optional `NEWS_API_KEY`).

---

## How to Run the Application

### Local Development:
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

### Production Server:
```bash
gunicorn app:app
```
Or binding to all interfaces and custom port:
```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
```

---

## How to Run Tests

Run all unit and integration tests using `pytest`:
```bash
python -m pytest -v
```
Or with Python's built-in `unittest`:
```bash
python -m unittest discover tests
```

---

## Production Deployment Guide

### Deployment Options:
1. **Render / Railway / Fly.io / Heroku**:
   - The included `Procfile` instructs the build runner to start: `web: gunicorn app:app`.
   - Set environment variables in the platform dashboard:
     - `SECRET_KEY`: Set to a strong random key (e.g., `openssl rand -hex 32`).
     - `FLASK_ENV`: `production`
     - `FLASK_DEBUG`: `false`
     - `GEMINI_API_KEY`: (Optional) Your Google Gemini API key.
     - `NEWS_API_KEY`: (Optional) Your News API key.
     - `DATABASE_URL`: (Optional) If attaching managed PostgreSQL. If omitted, CareerBot runs with local SQLite.
2. **Persistent Storage Note**:
   - If deploying with SQLite and local file uploads on ephemeral cloud containers (e.g. free Render dynos), resumes and SQLite data reset on dyno sleep/restart.
   - For permanent multi-user deployments, attach a managed PostgreSQL database URL and cloud object storage (e.g., AWS S3).


---

## API Health Check Endpoint

```bash
curl http://127.0.0.1:5000/api/health
```
**Sample JSON Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "nlp": "ready",
  "gemini": "unavailable",
  "fallback_mode": true
}
```

---

## Viva & Academic Explanation Guide

1. **NLP Concepts**:
   - **Tokenization**: Breaking raw text strings into word tokens.
   - **Lemmatization**: Reducing words to base morphological roots using `WordNetLemmatizer`.
   - **Skill Normalization**: Mapping colloquial skill abbreviations (`ML`, `JS`, `Postgres`) to standardized keys (`machine learning`, `javascript`, `postgresql`).
   - **Intent Classification**: Mapping natural queries into 11 distinct intent categories.
2. **ML & Recommendation Concepts**:
   - **TF-IDF (Term Frequency-Inverse Document Frequency)**: Transforms profile and job text into vector representations.
   - **Cosine Similarity**: Measures vector angle cosine distance normalized between $0.0$ and $1.0$.
3. **Software Architecture**:
   - Modular architecture separating database, NLP processing, recommender formulas, domain services, and presentation routes.
