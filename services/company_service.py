"""
Company Directory & Following Service for CareerBot.
Manages company catalog, user following/unfollowing, and personalized company news filtering.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import or_

from database.database import SessionLocal
from database.models import Company, UserCompanyFollow, JobModel

# Default curated high-impact tech companies to pre-seed catalog
DEFAULT_COMPANIES = [
    {
        "name": "Google",
        "industry": "Internet & AI",
        "website": "https://careers.google.com",
        "description": "Global technology leader in search, cloud computing, artificial intelligence, and software."
    },
    {
        "name": "Microsoft",
        "industry": "Enterprise Software & Cloud",
        "website": "https://careers.microsoft.com",
        "description": "Developer of Windows, Azure Cloud, Microsoft 365, and AI solutions."
    },
    {
        "name": "Amazon",
        "industry": "E-Commerce & Cloud Computing",
        "website": "https://amazon.jobs",
        "description": "Global e-commerce and cloud infrastructure powerhouse (AWS)."
    },
    {
        "name": "NVIDIA",
        "industry": "Semiconductors & AI Hardware",
        "website": "https://nvidia.com/careers",
        "description": "Pioneer of GPU technology and accelerating AI computing infrastructure."
    },
    {
        "name": "Meta",
        "industry": "Social Media & AI",
        "website": "https://metacareers.com",
        "description": "Leader in social technologies, metaverse innovations, and open-source AI (Llama)."
    },
    {
        "name": "Apple",
        "industry": "Consumer Tech & Hardware",
        "website": "https://apple.com/jobs",
        "description": "Designer of iPhone, Mac, iOS, Apple Silicon, and consumer services."
    },
    {
        "name": "Tata Consultancy Services",
        "industry": "IT Services & Consulting",
        "website": "https://tcs.com/careers",
        "description": "India's largest IT services and digital transformation multinational."
    },
    {
        "name": "Infosys",
        "industry": "IT Services & Enterprise Consulting",
        "website": "https://infosys.com/careers",
        "description": "Next-generation digital services and consulting multinational."
    },
    {
        "name": "Wipro",
        "industry": "IT Services & Solutions",
        "website": "https://wipro.com/careers",
        "description": "Leading global information technology, consulting, and business process services company."
    },
    {
        "name": "HCLTech",
        "industry": "IT Engineering & Cloud",
        "website": "https://hcltech.com/careers",
        "description": "Global tech enterprise specializing in digital, engineering, and cloud solutions."
    },
    {
        "name": "Cognizant",
        "industry": "Digital Transformation & IT",
        "website": "https://cognizant.com/careers",
        "description": "Engineering modern businesses to improve everyday lives through IT consulting."
    },
    {
        "name": "OpenAI",
        "industry": "Generative AI & LLMs",
        "website": "https://openai.com/careers",
        "description": "AI research and deployment company developing ChatGPT and frontier foundation models."
    }
]


class CompanyService:
    """Manages company search, following, and personal feeds."""

    def __init__(self):
        self._ensure_default_companies()

    def _ensure_default_companies(self):
        """Seeds default catalog if empty."""
        db = SessionLocal()
        try:
            count = db.query(Company).count()
            if count == 0:
                for comp_data in DEFAULT_COMPANIES:
                    comp = Company(
                        name=comp_data["name"],
                        normalized_name=comp_data["name"].lower().strip(),
                        industry=comp_data.get("industry", "Technology"),
                        website=comp_data.get("website", ""),
                        description=comp_data.get("description", "")
                    )
                    db.add(comp)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def get_companies(self, user_id: Optional[int] = None, search_query: str = "") -> List[Dict[str, Any]]:
        """Returns companies matching search query, indicating whether user follows each."""
        db = SessionLocal()
        try:
            if db.query(Company).count() == 0:
                self._ensure_default_companies()

            query = db.query(Company)
            if search_query:
                clean_q = f"%{search_query.strip().lower()}%"
                query = query.filter(
                    or_(
                        Company.normalized_name.like(clean_q),
                        Company.industry.like(clean_q),
                        Company.description.like(clean_q)
                    )
                )

            companies = query.order_by(Company.name.asc()).all()

            followed_names = set()
            if user_id:
                follows = db.query(UserCompanyFollow).filter_by(user_id=user_id).all()
                followed_names = {f.company_name.lower().strip() for f in follows}

            results = []
            for comp in companies:
                c_dict = comp.to_dict()
                c_dict["is_following"] = comp.normalized_name in followed_names
                results.append(c_dict)

            return results
        finally:
            db.close()

    def follow_company(self, user_id: int, company_name: str) -> Dict[str, Any]:
        """Follows a company for the given user."""
        if not company_name or not company_name.strip():
            return {"success": False, "error": "Company name is required."}

        clean_name = company_name.strip()
        db = SessionLocal()
        try:
            # Ensure company exists in catalog
            norm_name = clean_name.lower()
            existing_company = db.query(Company).filter_by(normalized_name=norm_name).first()
            if not existing_company:
                existing_company = Company(
                    name=clean_name,
                    normalized_name=norm_name,
                    industry="Technology",
                    description=f"{clean_name} technology & engineering careers."
                )
                db.add(existing_company)
                db.flush()

            # Check if already followed
            existing_follow = db.query(UserCompanyFollow).filter_by(
                user_id=user_id,
                company_name=clean_name
            ).first()

            if existing_follow:
                return {"success": True, "action": "already_following", "company_name": clean_name}

            new_follow = UserCompanyFollow(
                user_id=user_id,
                company_name=clean_name,
                followed_at=datetime.now(timezone.utc)
            )
            db.add(new_follow)
            db.commit()

            return {"success": True, "action": "followed", "company_name": clean_name}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def unfollow_company(self, user_id: int, company_name: str) -> Dict[str, Any]:
        """Unfollows a company for the given user."""
        if not company_name:
            return {"success": False, "error": "Company name is required."}

        clean_name = company_name.strip()
        db = SessionLocal()
        try:
            follow = db.query(UserCompanyFollow).filter(
                UserCompanyFollow.user_id == user_id,
                or_(
                    UserCompanyFollow.company_name == clean_name,
                    UserCompanyFollow.company_name.ilike(clean_name)
                )
            ).first()

            if not follow:
                return {"success": True, "action": "not_following", "company_name": clean_name}

            db.delete(follow)
            db.commit()
            return {"success": True, "action": "unfollowed", "company_name": clean_name}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def get_user_followed_companies(self, user_id: int) -> List[str]:
        """Returns list of company names followed by user."""
        db = SessionLocal()
        try:
            follows = db.query(UserCompanyFollow).filter_by(user_id=user_id).all()
            return [f.company_name for f in follows]
        finally:
            db.close()


company_service = CompanyService()
