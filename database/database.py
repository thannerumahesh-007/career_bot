"""
Database Setup & Initialization Manager for CareerBot.
"""

import csv
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from database.models import Base, UserProfile, JobModel

connect_args = {}
if Config.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Returns a new database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from sqlalchemy import create_engine, text

def init_db():
    """Initializes SQLite database tables and seeds verified LinkedIn jobs dataset."""
    db = SessionLocal()
    try:
        # Check if existing jobs table lacks new columns
        try:
            db.execute(text("SELECT work_mode FROM jobs LIMIT 1"))
        except Exception:
            db.rollback()
            db.execute(text("DROP TABLE IF EXISTS jobs"))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        csv_path = Config.JOBS_DATASET_PATH
        if csv_path.exists():
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                if len(reader) > 0:
                    first_job = db.query(JobModel).first()
                    if not first_job or db.query(JobModel).count() < len(reader):
                        db.query(JobModel).delete()
                        db.commit()

                        for row in reader:
                            job = JobModel(
                                job_id=str(row.get("job_id", "")),
                                title=row.get("title", ""),
                                company=row.get("company", ""),
                                location=row.get("location", "India"),
                                work_mode=row.get("work_mode", "Not specified"),
                                job_type=row.get("job_type", "Full-time"),
                                experience=row.get("experience", "Not specified"),
                                education=row.get("education", "Degree in Computer Science or related field"),
                                skills=row.get("skills", ""),
                                preferred_skills=row.get("preferred_skills", ""),
                                responsibilities=row.get("responsibilities", ""),
                                description=row.get("description", ""),
                                keywords=row.get("keywords", ""),
                                salary=row.get("salary", "Competitive Market Standard"),
                                source=row.get("source", "LinkedIn Verified"),
                                url=row.get("url", "")
                            )
                            db.add(job)
                        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

