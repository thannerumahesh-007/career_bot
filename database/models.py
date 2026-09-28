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


