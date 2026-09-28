"""
Job Provider Services for CareerBot.
Abstracts job loading allowing seamless future extension to external APIs.
"""

from abc import ABC, abstractmethod
from database.models import JobModel


class JobProvider(ABC):
    """Abstract interface for fetching job postings."""

    @abstractmethod
    def get_all_jobs(self, db_session) -> list:
        pass

    @abstractmethod
    def get_job_by_id(self, db_session, job_id: int) -> dict:
        pass


class LocalDatasetProvider(JobProvider):
    """Loads job postings from local SQLite database."""

    def get_all_jobs(self, db_session) -> list:
        jobs = db_session.query(JobModel).all()
        return [j.to_dict() for j in jobs]

    def get_job_by_id(self, db_session, job_id) -> dict:
        job_id_str = str(job_id)
        job = db_session.query(JobModel).filter_by(job_id=job_id_str).first()
        if not job:
            try:
                job = db_session.query(JobModel).filter_by(id=int(job_id)).first()
            except Exception:
                pass
        return job.to_dict() if job else None


class ExternalAPIProvider(JobProvider):
    """Stub for future external job API integrations (e.g. LinkedIn, Indeed APIs)."""

    def get_all_jobs(self, db_session) -> list:
        return []

    def get_job_by_id(self, db_session, job_id: int) -> dict:
        return None
