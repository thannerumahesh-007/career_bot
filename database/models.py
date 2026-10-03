"""
SQLAlchemy ORM Database Models for CareerBot.
Includes User, UserProfile, Resume, JobModel, and ChatHistory.
"""

import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from werkzeug.security import generate_password_hash, check_password_hash
from nlp.skill_dictionary import normalize_skill_list

Base = declarative_base()


class User(Base):
    """User account entity for authentication and data isolation."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(100), nullable=False, default="")
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    chat_history = relationship("ChatHistory", back_populates="user", cascade="all, delete-orphan")
    job_interactions = relationship("UserJobInteraction", back_populates="user", cascade="all, delete-orphan")
    followed_companies = relationship("UserCompanyFollow", back_populates="user", cascade="all, delete-orphan")
    resume_drafts = relationship("ResumeDraft", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Hashes and sets user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies given password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Safe dict representation excluding sensitive fields."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else ""
        }


class UserProfile(Base):
    """Stores persistent user career profile."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(100), default="CareerBot User")
    skills_json = Column(Text, default="[]")
    interests_json = Column(Text, default="[]")
    education = Column(String(100), default="")
    experience = Column(String(100), default="")
    target_roles_json = Column(Text, default="[]")
    location = Column(String(100), default="")
    preferred_job_type = Column(String(50), default="")
    preferred_work_mode = Column(String(50), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="profile")

    @property
    def skills(self) -> list:
        try:
            return json.loads(self.skills_json) if self.skills_json else []
        except Exception:
            return []

    @skills.setter
    def skills(self, val: list):
        normalized = normalize_skill_list(val)
        self.skills_json = json.dumps(normalized)

    @property
    def interests(self) -> list:
        try:
            return json.loads(self.interests_json) if self.interests_json else []
        except Exception:
            return []

    @interests.setter
    def interests(self, val: list):
        self.interests_json = json.dumps(val or [])

    @property
    def target_roles(self) -> list:
        try:
            return json.loads(self.target_roles_json) if self.target_roles_json else []
        except Exception:
            return []

    @target_roles.setter
    def target_roles(self, val: list):
        self.target_roles_json = json.dumps(val or [])

    def replace_profile_data(self, new_data: dict):
        """Completely replaces profile data with new resume extraction (no stale cached skills)."""
        if "skills" in new_data:
            self.skills = new_data.get("skills") or []
        if "interests" in new_data:
            self.interests = new_data.get("interests") or []
        if "education" in new_data:
            self.education = new_data.get("education") or ""
        if "experience" in new_data:
            self.experience = new_data.get("experience") or ""
        if "target_roles" in new_data:
            self.target_roles = new_data.get("target_roles") or []
        if "location" in new_data:
            self.location = new_data.get("location") or ""
        self.updated_at = datetime.now(timezone.utc)

    def merge_profile_data(self, new_data: dict):
        """Merges new profile extraction with existing record without deleting previous info."""
        if "skills" in new_data and new_data["skills"]:
            existing = set(self.skills)
            for s in new_data["skills"]:
                if s:
                    existing.add(s)
            self.skills = list(existing)

        if "interests" in new_data and new_data["interests"]:
            existing = set(self.interests)
            for i in new_data["interests"]:
                if i:
                    existing.add(i)
            self.interests = list(existing)

        if new_data.get("education"):
            self.education = new_data["education"]

        if new_data.get("experience"):
            self.experience = new_data["experience"]

        if "target_roles" in new_data and new_data["target_roles"]:
            existing = set(self.target_roles)
            for r in new_data["target_roles"]:
                if r:
                    existing.add(r)
            self.target_roles = list(existing)

        if new_data.get("location"):
            self.location = new_data["location"]

        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        """Converts model to dict representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "skills": self.skills,
            "interests": self.interests,
            "education": self.education,
            "experience": self.experience,
            "target_roles": self.target_roles,
            "location": self.location,
            "preferred_job_type": self.preferred_job_type,
            "preferred_work_mode": self.preferred_work_mode,
            "updated_at": self.updated_at.isoformat() if self.updated_at else ""
        }


class Resume(Base):
    """Private uploaded resume document records."""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    extracted_text = Column(Text, default="")
    extracted_data_json = Column(Text, default="{}")
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="resumes")

    @property
    def extracted_data(self) -> dict:
        try:
            return json.loads(self.extracted_data_json) if self.extracted_data_json else {}
        except Exception:
            return {}

    @extracted_data.setter
    def extracted_data(self, val: dict):
        self.extracted_data_json = json.dumps(val or {})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else "",
            "extracted_data": self.extracted_data
        }


class JobModel(Base):
    """Database entity for job postings."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(100), unique=True)
    title = Column(String(200))
    company = Column(String(200))
    location = Column(String(100))
    work_mode = Column(String(100), default="Not specified")
    job_type = Column(String(50))
    experience = Column(String(100))
    education = Column(String(200))
    skills = Column(Text)
    preferred_skills = Column(Text)
    responsibilities = Column(Text)
    description = Column(Text)
    keywords = Column(Text)
    salary = Column(String(100))
    source = Column(String(100))
    url = Column(String(500))

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "work_mode": self.work_mode or "Not specified",
            "job_type": self.job_type,
            "experience": self.experience,
            "education": self.education or "Degree in Computer Science or related field",
            "skills": self.skills,
            "preferred_skills": self.preferred_skills or "",
            "responsibilities": self.responsibilities,
            "description": self.description,
            "keywords": self.keywords or "",
            "salary": self.salary or "Competitive Market Standard",
            "source": self.source or "LinkedIn Verified",
            "url": self.url
        }


class ChatHistory(Base):
    """Stores user chatbot interaction history."""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    sender = Column(String(20))
    message = Column(Text)
    intent = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chat_history")


class UserJobInteraction(Base):
    """Stores user job interactions such as saved jobs."""
    __tablename__ = "user_job_interactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, nullable=False, index=True)
    is_saved = Column(Text, default="true")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="job_interactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "job_id": self.job_id,
            "is_saved": self.is_saved,
            "created_at": self.created_at.isoformat() if self.created_at else ""
        }


class Company(Base):
    """Company catalog entity for following and personalized news."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    normalized_name = Column(String(150), index=True)
    industry = Column(String(100), default="Technology")
    website = Column(String(255), default="")
    logo_url = Column(String(500), default="")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "normalized_name": self.normalized_name or self.name.lower(),
            "industry": self.industry,
            "website": self.website,
            "logo_url": self.logo_url,
            "description": self.description
        }


class UserCompanyFollow(Base):
    """Stores companies followed by users for corporate intelligence personalization."""
    __tablename__ = "user_company_follows"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_name = Column(String(150), nullable=False, index=True)
    followed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="followed_companies")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "company_name": self.company_name,
            "followed_at": self.followed_at.isoformat() if self.followed_at else ""
        }


class ResumeDraft(Base):
    """Stores ATS-optimized resumes created or edited using the Resume Builder."""
    __tablename__ = "resume_drafts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(150), default="My ATS Resume")
    target_role = Column(String(150), default="Software Engineer")
    contact_info_json = Column(Text, default="{}")
    summary = Column(Text, default="")
    sections_json = Column(Text, default="[]")
    ats_score = Column(Integer, default=0)
    ats_breakdown_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="resume_drafts")

    @property
    def contact_info(self) -> dict:
        try:
            return json.loads(self.contact_info_json) if self.contact_info_json else {}
        except Exception:
            return {}

    @contact_info.setter
    def contact_info(self, val: dict):
        self.contact_info_json = json.dumps(val or {})

    @property
    def sections(self) -> list:
        try:
            return json.loads(self.sections_json) if self.sections_json else []
        except Exception:
            return []

    @sections.setter
    def sections(self, val: list):
        self.sections_json = json.dumps(val or [])

    @property
    def ats_breakdown(self) -> dict:
        try:
            return json.loads(self.ats_breakdown_json) if self.ats_breakdown_json else {}
        except Exception:
            return {}

    @ats_breakdown.setter
    def ats_breakdown(self, val: dict):
        self.ats_breakdown_json = json.dumps(val or {})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "target_role": self.target_role,
            "contact_info": self.contact_info,
            "summary": self.summary,
            "sections": self.sections,
            "ats_score": self.ats_score,
            "ats_breakdown": self.ats_breakdown,
            "updated_at": self.updated_at.isoformat() if self.updated_at else ""
        }


class InterviewSession(Base):
    """Stores interactive AI mock interview simulation sessions and final reports."""
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_role = Column(String(100), nullable=False)
    interview_type = Column(String(50), default="Technical")
    difficulty = Column(String(50), default="Intermediate")
    status = Column(String(50), default="in_progress")  # in_progress, completed
    current_question_index = Column(Integer, default=0)
    questions_json = Column(Text, default="[]")
    turns_json = Column(Text, default="[]")
    final_report_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="interviews")

    @property
    def questions(self) -> list:
        try:
            return json.loads(self.questions_json) if self.questions_json else []
        except Exception:
            return []

    @questions.setter
    def questions(self, val: list):
        self.questions_json = json.dumps(val or [])

    @property
    def turns(self) -> list:
        try:
            return json.loads(self.turns_json) if self.turns_json else []
        except Exception:
            return []

    @turns.setter
    def turns(self, val: list):
        self.turns_json = json.dumps(val or [])

    @property
    def final_report(self) -> dict:
        try:
            return json.loads(self.final_report_json) if self.final_report_json else {}
        except Exception:
            return {}

    @final_report.setter
    def final_report(self, val: dict):
        self.final_report_json = json.dumps(val or {})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_role": self.target_role,
            "interview_type": self.interview_type,
            "difficulty": self.difficulty,
            "status": self.status,
            "current_question_index": self.current_question_index,
            "questions": self.questions,
            "turns": self.turns,
            "final_report": self.final_report,
            "created_at": self.created_at.isoformat() if self.created_at else ""
        }


