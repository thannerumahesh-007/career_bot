"""
CareerBot Flask Web Application Entry Point.
Secure Multi-Tenant Authentication, Data Privacy, and RESTful API Endpoints.
"""

import os
import re
import uuid
import time
from functools import wraps
from pathlib import Path
from flask import (
    Flask, render_template, request, jsonify, redirect, url_for, flash, session, g, send_from_directory, make_response
)
from werkzeug.utils import secure_filename

from config import Config
from database.database import init_db, SessionLocal
from database.models import User, UserProfile, Resume, JobModel, ChatHistory, UserJobInteraction
from services.career_service import CareerService
from services.resume_service import ResumeService
from services.job_service import CombinedJobProvider, job_provider
from recommender.ranking import JobRanker
from recommender.skill_gap import SkillGapAnalyzer
from nlp.skill_extractor import SkillExtractor

app = Flask(__name__)
app.config.from_object(Config)

# Register custom Jinja filters
app.jinja_env.filters['nl2br'] = lambda text: text.replace('\n', '<br>') if text else ''

# Ensure required runtime directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
Config.JOBS_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

# Initialize database
init_db()

career_service = CareerService()
resume_service = ResumeService()
job_provider = CombinedJobProvider()
ranker = JobRanker()
gap_analyzer = SkillGapAnalyzer()
skill_extractor = SkillExtractor()

from services.news_service import news_service, NEWS_CATEGORIES


# --- RATE LIMITING MIDDLEWARE ---
class SimpleRateLimiter:
    """Sliding window rate limiter to prevent API abuse and brute force attacks."""
    def __init__(self):
        self.requests = {}

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        timestamps = self.requests.get(key, [])
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            self.requests[key] = timestamps
            return False
        timestamps.append(now)
        self.requests[key] = timestamps
        return True

rate_limiter = SimpleRateLimiter()


# --- FILE SECURITY HELPER ---
def allowed_file(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


# --- AUTHENTICATION & SESSION HELPERS ---
@app.before_request
def load_logged_in_user():
    """Populates g.current_user from session before each request."""
    g.current_user = None
    user_id = session.get("user_id")
    if user_id:
        db = SessionLocal()
        try:
            g.current_user = db.query(User).filter_by(id=user_id).first()
        finally:
            db.close()


def login_required(f):
    """Decorator enforcing authentication for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.current_user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in.", "status": 401}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function


# --- CSRF PROTECTION ---
@app.context_processor
def inject_csrf_token():
    """Injects CSRF token into Jinja2 template contexts."""
    if "csrf_token" not in session:
        session["csrf_token"] = uuid.uuid4().hex
    return dict(csrf_token=session["csrf_token"])


@app.before_request
def verify_csrf():
    """Verifies CSRF token for state-changing requests."""
    if app.config.get("TESTING") or app.config.get("WTF_CSRF_ENABLED") is False:
        return

    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected_token = session.get("csrf_token")
        if not expected_token or token != expected_token:
            if request.path.startswith("/api/"):
                return jsonify({"error": "CSRF validation failed. Invalid token."}), 400
            flash("Session expired or invalid form request. Please try again.", "error")
            return redirect(request.referrer or url_for("index"))


# --- SECURITY HEADERS MIDDLEWARE ---
@app.after_request
def set_security_headers(response):
    """Sets modern HTTP security headers on all outgoing responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self';"
    )
    if g.current_user:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# --- AUTHENTICATION ROUTES ---

@app.route("/register", methods=["GET", "POST"])
def register():
    """User Registration Route."""
    if g.current_user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        client_ip = request.remote_addr or "127.0.0.1"
        if not rate_limiter.is_allowed(f"register_{client_ip}", max_requests=10, window_seconds=300):
            flash("Too many registration attempts. Please wait a few minutes.", "error")
            return render_template("register.html")

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not username or not password:
            flash("All required fields must be filled out.", "error")
            return render_template("register.html")

        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email):
            flash("Please enter a valid email address.", "error")
            return render_template("register.html")

        if len(username) < 3 or not username.isalnum():
            flash("Username must be at least 3 alphanumeric characters.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        weak_passwords = {"12345678", "password", "password123", "123456789", "qwerty123", "admin123"}
        if password.lower() in weak_passwords or password.lower() == username:
            flash("Please choose a stronger password.", "error")
            return render_template("register.html")

        db = SessionLocal()
        try:
            existing_user = db.query(User).filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash("Registration failed. An account with this username or email already exists.", "error")
                return render_template("register.html")

            new_user = User(full_name=full_name, username=username, email=email)
            new_user.set_password(password)
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            career_service.get_or_create_user_profile(db, new_user.id)

            session["user_id"] = new_user.id
            session["username"] = new_user.username
            session["full_name"] = new_user.full_name
            session.permanent = True

            flash("Account created successfully! Welcome to CareerBot.", "success")
            return redirect(url_for("dashboard"))
        except Exception as e:
            db.rollback()
            flash("An error occurred during registration. Please try again.", "error")
            return render_template("register.html")
        finally:
            db.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """User Login Route."""
    if g.current_user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        client_ip = request.remote_addr or "127.0.0.1"
        if not rate_limiter.is_allowed(f"login_{client_ip}", max_requests=15, window_seconds=300):
            flash("Too many login attempts. Please wait 5 minutes before trying again.", "error")
            return render_template("login.html")

        login_id = request.form.get("login_id", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not login_id or not password:
            flash("Please enter both username/email and password.", "error")
            return render_template("login.html")

        db = SessionLocal()
        try:
            user = db.query(User).filter((User.username == login_id) | (User.email == login_id)).first()

            if not user or not user.check_password(password):
                flash("Invalid username/email or password.", "error")
                return render_template("login.html")

            session.clear()
            session["csrf_token"] = uuid.uuid4().hex
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name
            if remember:
                session.permanent = True

            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))
        finally:
            db.close()

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Secure Logout Route."""
    session.clear()
    flash("You have been logged out safely.", "success")
    resp = make_response(redirect(url_for("login")))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# --- HTML PAGE ROUTES (PROTECTED) ---

@app.route("/")
def index():
    """Landing / Home Page."""
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():
    """Profile & System Metrics Dashboard."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        all_jobs = job_provider.get_all_jobs(db)
        profile_dict = profile.to_dict()

        # Requirement 1: Resume is the ONLY source of profile skills
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        has_resume = active_resume is not None and bool(active_resume.extracted_data and active_resume.extracted_data.get("skills"))
        profile_dict["has_resume"] = has_resume

        if has_resume:
            r_skills = active_resume.extracted_data.get("skills", [])
            profile_dict["skills"] = r_skills
        else:
            profile_dict["skills"] = []

        match_data = ranker.rank_recommendations(profile_dict, all_jobs)
        skills_count = len(profile_dict.get("skills", []))
        total_jobs = len(all_jobs)
        top_matches = [j for j in match_data.get("results", []) if j.get("has_match") and j.get("overall_score", 0) >= Config.MODERATE_MATCH_THRESHOLD]

        comp_fields = [profile_dict.get("skills"), profile_dict.get("interests"), profile_dict.get("education"), profile_dict.get("experience"), profile_dict.get("target_roles")]
        filled = sum(1 for f in comp_fields if f and len(f) > 0)
        completion_percentage = int((filled / float(len(comp_fields))) * 100) if has_resume else 0

        roadmap = gap_analyzer.generate_roadmap(profile_dict, active_resume=active_resume.to_dict() if active_resume else None)
        missing_count = len(roadmap.get("all_missing_skills", []))

        return render_template("dashboard.html",
                               user=g.current_user.to_dict(),
                               profile=profile_dict,
                               total_jobs=total_jobs,
                               has_resume=has_resume,
                               matching_jobs_count=len(top_matches),
                               skills_count=skills_count,
                               missing_count=missing_count,
                               completion_percentage=completion_percentage,
                               top_recommendations=match_data.get("results", [])[:4],
                               has_strong_match=match_data.get("has_strong_match", False) if has_resume else False,
                               latest_resume=active_resume.to_dict() if active_resume else None)
    finally:
        db.close()


@app.route("/chat")
@login_required
def chat():
    """Interactive Conversational Chatbot Interface."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        history = db.query(ChatHistory).filter_by(user_id=g.current_user.id).order_by(ChatHistory.created_at.asc()).all()
        return render_template("chat.html", profile=profile.to_dict(), history=history)
    finally:
        db.close()


@app.route("/jobs")
@login_required
def jobs():
    """Job Recommendations Catalog with Filters & Tabs."""
    tab = request.args.get("tab", "all").strip().lower()
    role_query = request.args.get("role", "").strip()
    loc_query = request.args.get("location", "").strip()
    exp_query = request.args.get("experience", "").strip()
    work_mode_query = request.args.get("work_mode", "").strip()
    source_query = request.args.get("source", "").strip().lower()

    # Determine source filtering (all, live, database)
    if tab == "live" or source_query == "live":
        active_source = "live"
    elif tab == "database" or source_query == "database":
        active_source = "database"
    else:
        active_source = "all"

    filters = {}
    if role_query: filters["role"] = role_query
    if loc_query: filters["location"] = loc_query
    if exp_query: filters["experience"] = exp_query
    if work_mode_query: filters["work_mode"] = work_mode_query

    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        has_resume = active_resume is not None and bool(active_resume.extracted_data and active_resume.extracted_data.get("skills"))

        profile_dict = profile.to_dict()
        profile_dict["has_resume"] = has_resume
        if has_resume:
            profile_dict["skills"] = active_resume.extracted_data.get("skills", [])
        else:
            profile_dict["skills"] = []

        all_jobs = job_provider.get_all_jobs(db, source=active_source, filters=filters, profile_dict=profile_dict)

        # Build saved job_ids set for user
        saved_records = db.query(UserJobInteraction).filter_by(user_id=g.current_user.id, is_saved="true").all()
        saved_job_ids = {str(r.job_id) for r in saved_records}

        match_data = ranker.rank_recommendations(profile_dict, all_jobs, filters)
        results = match_data.get("results", [])

        # Filter by tab
        if tab == "recommended":
            results = [j for j in results if j.get("has_match") and j.get("overall_score", 0) >= Config.MODERATE_MATCH_THRESHOLD]
        elif tab == "saved":
            results = [j for j in results if str(j.get("job_id")) in saved_job_ids]
        elif tab == "resume-matches":
            results = [j for j in results if j.get("has_match") and j.get("overall_score", 0) >= 0.40]
        elif tab == "live":
            results = [j for j in results if j.get("is_live")]
        elif tab == "database":
            results = [j for j in results if not j.get("is_live")]

        # Attach saved indicator
        for j in results:
            j["is_saved"] = str(j.get("job_id")) in saved_job_ids

        return render_template("jobs.html",
                               active_tab=tab,
                               active_source=active_source,
                               results=results,
                               has_resume=has_resume,
                               message=match_data.get("message", ""),
                               has_strong_match=match_data.get("has_strong_match", False) if has_resume else False,
                               filters=filters,
                               profile=profile_dict,
                               active_resume=active_resume.to_dict() if active_resume else None)
    finally:
        db.close()


@app.route("/jobs/resume-matches")
@login_required
def jobs_resume_matches():
    """Dedicated Page: Jobs Matched Specifically to User's Active Resume."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        has_resume = active_resume is not None and bool(active_resume.extracted_data and active_resume.extracted_data.get("skills"))

        profile_dict = profile.to_dict()
        profile_dict["has_resume"] = has_resume
        if has_resume:
            profile_dict["skills"] = active_resume.extracted_data.get("skills", [])
        else:
            profile_dict["skills"] = []

        all_jobs = job_provider.get_all_jobs(db, source="all", profile_dict=profile_dict)
        match_data = ranker.rank_recommendations(profile_dict, all_jobs)
        results = [j for j in match_data.get("results", []) if j.get("has_match")]

        # Saved status
        saved_records = db.query(UserJobInteraction).filter_by(user_id=g.current_user.id, is_saved="true").all()
        saved_job_ids = {str(r.job_id) for r in saved_records}
        for j in results:
            j["is_saved"] = str(j.get("job_id")) in saved_job_ids

        return render_template("jobs_resume_matches.html",
                               results=results,
                               has_resume=has_resume,
                               active_resume=active_resume.to_dict() if active_resume else None,
                               profile=profile_dict)
    finally:
        db.close()


@app.route("/jobs/<job_id>")
@login_required
def job_details(job_id):
    """Detailed Match Breakdown and Explainability for a specific job."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        job = job_provider.get_job_by_id(db, job_id)
        if not job:
            flash("Job posting not found.", "error")
            return redirect("/jobs")

        raw_skills = job.get("skills", "")
        if isinstance(raw_skills, str):
            job["required_skills"] = [s.strip() for s in raw_skills.split(",") if s.strip()]
        else:
            job["required_skills"] = raw_skills

        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        has_resume = active_resume is not None and bool(active_resume.extracted_data and active_resume.extracted_data.get("skills"))

        profile_dict = profile.to_dict()
        profile_dict["has_resume"] = has_resume
        if has_resume:
            profile_dict["skills"] = active_resume.extracted_data.get("skills", [])
        else:
            profile_dict["skills"] = []

        match_result = ranker.matcher.match_job(profile_dict, job)

        try:
            numeric_id = int(job_id)
        except (ValueError, TypeError):
            numeric_id = abs(hash(str(job_id))) % 1000000000
        saved = db.query(UserJobInteraction).filter_by(user_id=g.current_user.id, job_id=numeric_id, is_saved="true").first()
        job["is_saved"] = saved is not None

        return render_template("job_details.html",
                               job=job,
                               match=match_result,
                               has_resume=has_resume,
                               profile=profile_dict)


    finally:
        db.close()


@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():
    """Resume Upload and Section Analyzer Page."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        resumes = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).all()
        analysis_result = None

        if request.method == "POST":
            if 'resume_file' not in request.files:
                flash("No file selected.", "error")
                return redirect(request.url)

            file = request.files['resume_file']
            if file.filename == '':
                flash("No file selected.", "error")
                return redirect(request.url)

            if file and allowed_file(file.filename):
                orig_filename = secure_filename(file.filename) or "resume"
                ext = Path(orig_filename).suffix.lower()
                stored_filename = f"{uuid.uuid4().hex}{ext}"

                user_dir = Config.UPLOAD_FOLDER / f"user_{g.current_user.id}"
                os.makedirs(user_dir, exist_ok=True)
                save_path = user_dir / stored_filename
                file.save(save_path)

                try:
                    analysis_result = resume_service.parse_resume(save_path)
                    raw_text = resume_service.extract_text_from_file(save_path)

                    # Delete previous resume records & physical files for single active resume replacement
                    old_resumes = db.query(Resume).filter_by(user_id=g.current_user.id).all()
                    for old_r in old_resumes:
                        old_file = user_dir / old_r.stored_filename
                        if old_file.exists():
                            try:
                                os.remove(old_file)
                            except Exception:
                                pass
                        db.delete(old_r)

                    resume_record = Resume(
                        user_id=g.current_user.id,
                        original_filename=orig_filename,
                        stored_filename=stored_filename,
                        extracted_text=raw_text,
                        extracted_data=analysis_result
                    )
                    db.add(resume_record)

                    # Replace user profile skills completely with newly extracted resume skills
                    career_service.replace_user_profile(db, g.current_user.id, {
                        "skills": analysis_result.get("skills", []),
                        "education": analysis_result.get("education", ""),
                        "experience": analysis_result.get("experience", ""),
                        "target_roles": analysis_result.get("target_roles", [])
                    })
                    db.commit()

                    resumes = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).all()
                    flash("Resume uploaded and parsed successfully! Profile skills replaced.", "success")
                except Exception as e:
                    db.rollback()
                    flash(f"Error parsing resume: {str(e)}", "error")

        return render_template("resume.html", profile=profile.to_dict(), resumes=[r.to_dict() for r in resumes], analysis=analysis_result)
    finally:
        db.close()


@app.route("/roadmap")
@login_required
def roadmap():
    """Career Learning Roadmap Page."""
    target_role = request.args.get("role", "").strip()
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        profile_dict = profile.to_dict()

        roadmap_data = gap_analyzer.generate_roadmap(profile_dict, target_role if target_role else None, active_resume=active_resume.to_dict() if active_resume else None)
        return render_template("roadmap.html", profile=profile_dict, roadmap=roadmap_data)
    finally:
        db.close()


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User Profile Management Page."""
    db = SessionLocal()
    try:
        user_profile = career_service.get_or_create_user_profile(db, g.current_user.id)

        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            education = request.form.get("education", "").strip()
            experience = request.form.get("experience", "").strip()
            skills_raw = request.form.get("skills", "").strip()
            interests_raw = request.form.get("interests", "").strip()
            target_roles_raw = request.form.get("target_roles", "").strip()

            if full_name:
                g.current_user.full_name = full_name

            skills_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
            interests_list = [i.strip() for i in interests_raw.split(",") if i.strip()]
            roles_list = [r.strip() for r in target_roles_raw.split(",") if r.strip()]

            user_profile.skills = skills_list
            user_profile.interests = interests_list
            user_profile.target_roles = roles_list
            user_profile.education = education
            user_profile.experience = experience
            db.commit()

            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile"))

        return render_template("profile.html", user=g.current_user.to_dict(), profile=user_profile.to_dict())
    finally:
        db.close()


@app.route("/news")
def news():
    """Corporate & Technology News Page."""
    category = request.args.get("category", "all").strip().lower()
    query = request.args.get("q", "").strip()
    news_data = news_service.fetch_corporate_news(category=category, search_query=query)
    return render_template(
        "news.html",
        articles=news_data.get("articles", []),
        total_articles=news_data.get("total", 0),
        active_category=category,
        categories=NEWS_CATEGORIES,
        search_query=query,
        news_status=news_data.get("status", "ok"),
        error_message=news_data.get("message", ""),
        error_type=news_data.get("error_type", ""),
        last_updated=news_data.get("last_updated", "")
    )


# --- REST API ENDPOINTS ---

@app.route("/api/news", methods=["GET"])
def api_news():
    """API endpoint for live filtering, searching, and refreshing corporate news."""
    category = request.args.get("category", "all").strip().lower()
    query = request.args.get("q", "").strip()
    force_refresh = request.args.get("refresh", "false").lower() in ("true", "1")
    news_data = news_service.fetch_corporate_news(category=category, search_query=query, force_refresh=force_refresh)
    return jsonify(news_data)


@app.route("/api/news/ai-summary", methods=["POST"])
def api_news_ai_summary():
    """Generates grounded Gemini executive takeaway for a corporate news article."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    content = data.get("content", "").strip()
    if not title:
        return jsonify({"status": "error", "message": "Article title is required."}), 400

    summary = news_service.generate_ai_summary(title, description, content)
    return jsonify({"status": "ok", "summary": summary})


@app.route("/api/health", methods=["GET"])
def api_health():
    """Public health check endpoint indicating DB, NLP, and Gemini status."""
    db = SessionLocal()
    db_status = "connected"
    try:
        db.query(JobModel).first()
    except Exception:
        db_status = "error"
    finally:
        db.close()

    gemini_available = career_service.gemini_service.is_available()

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "nlp": "ready",
        "resume_parser": "ready",
        "auth": "ready",
        "gemini": "available" if gemini_available else "unavailable",
        "fallback_mode": not gemini_available
    }), 200


@app.route("/api/jobs/resume-matches", methods=["GET"])
@login_required
def api_jobs_resume_matches():
    """JSON API endpoint for jobs matched to authenticated user's resume."""
    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        all_jobs = job_provider.get_all_jobs(db)

        profile_dict = profile.to_dict()
        if active_resume and active_resume.extracted_data:
            profile_dict["skills"] = list(set(profile_dict.get("skills", []) + active_resume.extracted_data.get("skills", [])))

        match_data = ranker.rank_recommendations(profile_dict, all_jobs)
        return jsonify({
            "status": "success",
            "active_resume": active_resume.to_dict() if active_resume else None,
            "results": match_data.get("results", [])
        }), 200
    finally:
        db.close()


@app.route("/api/jobs/save/<job_id>", methods=["POST", "DELETE"])
@login_required
def api_job_save_toggle(job_id):
    """Saves or unsaves a job for current authenticated user."""
    try:
        numeric_id = int(job_id)
    except (ValueError, TypeError):
        numeric_id = abs(hash(str(job_id))) % 1000000000

    db = SessionLocal()
    try:
        record = db.query(UserJobInteraction).filter_by(user_id=g.current_user.id, job_id=numeric_id).first()

        if request.method == "POST":
            if not record:
                record = UserJobInteraction(user_id=g.current_user.id, job_id=numeric_id, is_saved="true")
                db.add(record)
            else:
                record.is_saved = "true"
            db.commit()
            return jsonify({"status": "success", "is_saved": True, "message": "Job saved successfully."}), 200
        else:
            if record:
                record.is_saved = "false"
                db.commit()
            return jsonify({"status": "success", "is_saved": False, "message": "Job removed from saved list."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Failed to update saved job status."}), 500
    finally:
        db.close()


@app.route("/api/roadmap", methods=["POST"])
@login_required
def api_roadmap():
    """JSON API endpoint returning personalized role-specific learning roadmap."""
    data = request.get_json() or {}
    target_role = data.get("target_role", "").strip()

    db = SessionLocal()
    try:
        profile = career_service.get_or_create_user_profile(db, g.current_user.id)
        active_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()

        roadmap_data = gap_analyzer.generate_roadmap(
            profile.to_dict(),
            target_role=target_role if target_role else None,
            active_resume=active_resume.to_dict() if active_resume else None
        )
        return jsonify(roadmap_data), 200
    finally:
        db.close()


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    """JSON API endpoint for real-time chatbot interaction."""
    client_ip = request.remote_addr or "127.0.0.1"
    rate_key = f"chat_{g.current_user.id}_{client_ip}"
    if not rate_limiter.is_allowed(rate_key, max_requests=40, window_seconds=60):
        return jsonify({"error": "Rate limit exceeded. Please wait a moment before sending more messages."}), 429

    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    language = data.get("language", "en-IN")

    if not user_message:
        return jsonify({
            "error": "Empty message provided.",
            "response": "Please enter a valid message.",
            "intent": "unknown"
        }), 400

    db = SessionLocal()
    try:
        result = career_service.process_chat_message(db, g.current_user.id, user_message, language=language)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "error": "An error occurred processing your request.",
            "response": "Sorry, I could not process your request right now.",
            "intent": "unknown"
        }), 500
    finally:
        db.close()



@app.route("/api/chat/clear", methods=["POST"])
@login_required
def api_chat_clear():
    """Clears chat history for the logged-in user."""
    db = SessionLocal()
    try:
        db.query(ChatHistory).filter_by(user_id=g.current_user.id).delete()
        db.commit()
        return jsonify({"status": "success", "message": "Chat history cleared."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Failed to clear chat history."}), 500
    finally:
        db.close()


@app.route("/api/profile", methods=["GET", "POST"])
@login_required
def api_profile():
    """JSON API endpoint to fetch or update authenticated user's profile."""
    db = SessionLocal()
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            profile = career_service.update_user_profile(db, g.current_user.id, data)
            return jsonify({"status": "success", "profile": profile.to_dict()}), 200
        else:
            profile = career_service.get_or_create_user_profile(db, g.current_user.id)
            return jsonify(profile.to_dict()), 200
    finally:
        db.close()


@app.route("/api/resume/upload", methods=["POST"])
@login_required
def api_resume_upload():
    """JSON API endpoint for secure resume upload and parsing."""
    client_ip = request.remote_addr or "127.0.0.1"
    if not rate_limiter.is_allowed(f"upload_{g.current_user.id}_{client_ip}", max_requests=10, window_seconds=300):
        return jsonify({"error": "Rate limit exceeded. Too many upload attempts."}), 429

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename."}), 400

    if file and allowed_file(file.filename):
        orig_filename = secure_filename(file.filename) or "resume"
        ext = Path(orig_filename).suffix.lower()
        stored_filename = f"{uuid.uuid4().hex}{ext}"

        user_dir = Config.UPLOAD_FOLDER / f"user_{g.current_user.id}"
        os.makedirs(user_dir, exist_ok=True)
        save_path = user_dir / stored_filename
        file.save(save_path)

        db = SessionLocal()
        try:
            analysis = resume_service.parse_resume(save_path)
            raw_text = resume_service.extract_text_from_file(save_path)

            # Clean up old resumes
            old_resumes = db.query(Resume).filter_by(user_id=g.current_user.id).all()
            for old_r in old_resumes:
                old_file = user_dir / old_r.stored_filename
                if old_file.exists():
                    try:
                        os.remove(old_file)
                    except Exception:
                        pass
                db.delete(old_r)

            resume_record = Resume(
                user_id=g.current_user.id,
                original_filename=orig_filename,
                stored_filename=stored_filename,
                extracted_text=raw_text,
                extracted_data=analysis
            )
            db.add(resume_record)

            profile = career_service.replace_user_profile(db, g.current_user.id, {
                "skills": analysis.get("skills", []),
                "education": analysis.get("education", ""),
                "experience": analysis.get("experience", ""),
                "target_roles": analysis.get("target_roles", [])
            })
            db.commit()

            return jsonify({
                "status": "success",
                "analysis": analysis,
                "profile": profile.to_dict(),
                "resume": resume_record.to_dict()
            }), 200
        except Exception as e:
            db.rollback()
            return jsonify({"error": f"Failed to parse resume: {str(e)}"}), 500
        finally:
            db.close()

    return jsonify({"error": "Unsupported file format. Allowed formats: .pdf, .docx, .txt"}), 400


@app.route("/api/resume/file/<int:resume_id>", methods=["GET"])
@login_required
def api_resume_file(resume_id):
    """Secure, authenticated endpoint for downloading private user resume files."""
    db = SessionLocal()
    try:
        resume_record = db.query(Resume).filter_by(id=resume_id, user_id=g.current_user.id).first()
        if not resume_record:
            return jsonify({"error": "Resume not found or access denied."}), 404

        user_dir = Config.UPLOAD_FOLDER / f"user_{g.current_user.id}"
        file_path = user_dir / resume_record.stored_filename
        if not file_path.exists():
            return jsonify({"error": "File not found on disk."}), 404

        return send_from_directory(
            directory=user_dir,
            path=resume_record.stored_filename,
            as_attachment=True,
            download_name=resume_record.original_filename
        )
    finally:
        db.close()


@app.route("/api/resume/<int:resume_id>", methods=["DELETE"])
@login_required
def api_resume_delete(resume_id):
    """Deletes a specific private resume record, syncs/clears profile skills, and removes physical file."""
    db = SessionLocal()
    try:
        resume_record = db.query(Resume).filter_by(id=resume_id, user_id=g.current_user.id).first()
        if not resume_record:
            return jsonify({"error": "Resume not found or access denied."}), 404

        user_dir = Config.UPLOAD_FOLDER / f"user_{g.current_user.id}"
        file_path = user_dir / resume_record.stored_filename
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception:
                pass

        db.delete(resume_record)
        db.commit()

        # Update or clear user profile skills
        latest_resume = db.query(Resume).filter_by(user_id=g.current_user.id).order_by(Resume.uploaded_at.desc()).first()
        if latest_resume and latest_resume.extracted_data:
            ex_data = latest_resume.extracted_data
            profile = career_service.replace_user_profile(db, g.current_user.id, {
                "skills": ex_data.get("skills", []),
                "education": ex_data.get("education", ""),
                "experience": ex_data.get("experience", ""),
                "target_roles": ex_data.get("target_roles", [])
            })
        else:
            profile = career_service.replace_user_profile(db, g.current_user.id, {
                "skills": [],
                "education": "",
                "experience": "",
                "target_roles": []
            })
        db.commit()

        return jsonify({
            "status": "success",
            "message": "Resume deleted successfully. Profile skills updated.",
            "profile": profile.to_dict()
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": "Failed to delete resume record."}), 500
    finally:
        db.close()


# --- ERROR HANDLERS ---

@app.errorhandler(400)
def bad_request_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request.", "status": 400}), 400
    return render_template("error.html", code=400, title="Bad Request", message="Your request could not be processed."), 400


@app.errorhandler(401)
def unauthorized_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Authentication required.", "status": 401}), 401
    return redirect(url_for("login"))


@app.errorhandler(403)
def forbidden_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Access denied.", "status": 403}), 403
    return render_template("error.html", code=403, title="Access Denied", message="You do not have permission to access this resource."), 403


@app.errorhandler(404)
def not_found_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found.", "status": 404}), 404
    return render_template("error.html", code=404, title="Page Not Found", message="The requested page could not be found."), 404


@app.errorhandler(413)
def request_entity_too_large(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Uploaded file exceeds maximum limit (16 MB).", "status": 413}), 413
    flash("File size exceeds maximum allowed limit (16 MB).", "error")
    return redirect(request.referrer or url_for("dashboard")), 413


@app.errorhandler(429)
def too_many_requests_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Too many requests. Please slow down.", "status": 429}), 429
    return render_template("error.html", code=429, title="Too Many Requests", message="You have made too many requests. Please wait a moment."), 429


@app.errorhandler(500)
def internal_server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error.", "status": 500}), 500
    return render_template("error.html", code=500, title="Server Error", message="An unexpected error occurred. Please try again later."), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true") or os.environ.get("FLASK_ENV") == "development"
    app.run(host=host, port=port, debug=debug)
