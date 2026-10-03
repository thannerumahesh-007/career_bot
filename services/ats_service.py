"""
ATS Analysis, Resume Optimization, and ATS-Friendly PDF Generation Service.
Implements deterministic, measurable ATS scoring, target-job keyword comparison,
bullet point enhancement, and single-column PDF export via ReportLab.
"""

import re
import io
from typing import Dict, List, Any, Optional
from nlp.skill_extractor import SkillExtractor
from services.career_knowledge import CAREER_ROLES, extract_role_from_text, get_role_details
from services.model_router import model_router

ACTION_VERBS = {
    "architected", "built", "created", "designed", "developed", "deployed", "engineered",
    "implemented", "optimized", "spearheaded", "orchestrated", "automated", "streamlined",
    "scaled", "integrated", "analyzed", "reduced", "increased", "accelerated", "resolved",
    "led", "formulated", "established", "configured", "transformed", "delivered"
}


class ATSService:
    """Service providing ATS scoring, keyword comparison, and resume generation."""

    def __init__(self):
        self.skill_extractor = SkillExtractor()

    def enhance_bullet_point(self, bullet: str, target_role: str = "Software Engineer") -> str:
        """Enhances a resume bullet point with action verbs, metrics, and technical keywords."""
        if not bullet or not bullet.strip():
            return bullet

        cleaned = re.sub(r'^[•\-\*\s]+', '', bullet.strip())
        role_info = get_role_details(extract_role_from_text(target_role))
        req_skills = role_info.get("required_skills", [])
        keyword_hint = req_skills[0] if req_skills else "Python"

        system_instruction = (
            "You are a professional executive resume writer and ATS specialist. "
            "Rewrite the given resume bullet point to be impactful, quantifiable, and ATS-optimized. "
            "Start with a strong past-tense action verb (e.g., Architected, Optimized, Engineered, Spearheaded). "
            "Include realistic quantifiable metrics (percentages, throughput, or latency reduction). "
            "Keep it to exactly one concise, professional sentence. Do NOT add markdown symbols."
        )

        prompt = (
            f"Target Role: {target_role}\n"
            f"Key Skill/Tool: {keyword_hint}\n"
            f"Original Bullet Point:\n\"{cleaned}\"\n\n"
            "Enhanced Bullet Point:"
        )

        try:
            enhanced = model_router.generate_content(
                task="resume",
                prompt=prompt,
                system_instruction=system_instruction
            )
            if enhanced and len(enhanced.strip()) > 10:
                res = re.sub(r'^[•\-\*\s"]+|["]+$', '', enhanced.strip())
                return res
        except Exception:
            pass

        # Offline fallback enhancement
        words = cleaned.split()
        first_word = words[0].lower() if words else ""
        if first_word not in ACTION_VERBS:
            action_verb = "Engineered" if "software" in target_role.lower() else ("Analyzed" if "analyst" in target_role.lower() else "Implemented")
            return f"{action_verb} {cleaned[0].lower() + cleaned[1:] if len(cleaned) > 1 else cleaned}, improving overall operational efficiency by 25%."
        else:
            return f"{cleaned.rstrip('.')}, optimizing workflow execution time by 20%."

    def calculate_ats_score(
        self,
        resume_data: dict,
        target_role: Optional[str] = None,
        job_description: Optional[str] = None,
        target_job_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates a deterministic, explainable ATS score (0-100) based on 5 measurable criteria:
        1. Keyword Coverage (25%)
        2. Skills Coverage (25%)
        3. Section Completeness (20%)
        4. Role Relevance (15%)
        5. Action Verbs & Formatting (15%)
        """
        job_description = job_description or target_job_description or ""
        # Determine target role information
        role_key = extract_role_from_text(target_role or resume_data.get("target_role", ""))
        role_info = get_role_details(role_key)
        target_role_title = role_info["title"]

        # Extract all text from resume
        resume_text = self._aggregate_resume_text(resume_data).lower()

        # 1. Section Completeness (20 points max)
        section_scores = self._score_sections(resume_data)
        section_pct = section_scores["percentage"]

        # 2. Skills Coverage (25 points max)
        required_role_skills = role_info.get("required_skills", [])
        resume_skills = [s.lower() for s in self._extract_all_skills(resume_data)]

        matched_skills = []
        missing_skills = []
        for req in required_role_skills:
            # Check if skill keyword occurs in resume text or resume skills list
            req_clean = req.lower().split("(")[0].strip()
            if any(req_clean in s for s in resume_skills) or req_clean in resume_text:
                matched_skills.append(req)
            else:
                missing_skills.append(req)

        skills_pct = int((len(matched_skills) / len(required_role_skills) * 100)) if required_role_skills else 80

        # 3. Keyword Coverage (from Target Role or Job Description) (25 points max)
        if job_description and job_description.strip():
            target_keywords = self._extract_job_description_keywords(job_description)
        else:
            target_keywords = self._get_role_target_keywords(role_key)

        matched_keywords = []
        missing_keywords = []
        for kw in target_keywords:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', resume_text):
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)

        keyword_pct = int((len(matched_keywords) / len(target_keywords) * 100)) if target_keywords else 75

        # 4. Role Relevance (15 points max)
        role_words = target_role_title.lower().split()
        role_in_title_or_summary = any(w in resume_text for w in role_words)
        experience_relevance = 80 if role_in_title_or_summary else 45
        role_relevance_pct = min(100, experience_relevance + (20 if keyword_pct >= 60 else 0))

        # 5. Action Verbs & Quantifiable Metrics (15 points max)
        action_verb_count = sum(1 for verb in ACTION_VERBS if re.search(r'\b' + verb + r'\b', resume_text))
        has_metrics = bool(re.search(r'(\d+%\s*|\$\s*\d+|\b\d+\b\s*(?:users|clients|requests|ms|seconds|nodes|features))', resume_text))

        formatting_score = 40
        if action_verb_count >= 3:
            formatting_score += 30
        elif action_verb_count >= 1:
            formatting_score += 15
        if has_metrics:
            formatting_score += 30
        formatting_pct = min(100, formatting_score)

        # Weighted Composite Score (0 - 100)
        total_score = round(
            (keyword_pct * 0.25) +
            (skills_pct * 0.25) +
            (section_pct * 0.20) +
            (role_relevance_pct * 0.15) +
            (formatting_pct * 0.15)
        )
        total_score = max(0, min(100, total_score))

        # Actionable feedback and improvement suggestions
        suggestions = []
        if missing_skills:
            suggestions.append(f"Add key technical skills for {target_role_title}: {', '.join(missing_skills[:4])}.")
        if missing_keywords:
            suggestions.append(f"Incorporate targeted keywords: {', '.join(missing_keywords[:5])}.")
        if action_verb_count < 3:
            suggestions.append("Begin project and experience bullet points with strong action verbs (e.g. Architected, Engineered, Optimized, Deployed).")
        if not has_metrics:
            suggestions.append("Include quantifiable achievements (e.g., 'improved query performance by 35%', 'supported 10,000+ daily requests').")
        if not section_scores.get("has_summary"):
            suggestions.append("Add a targeted 2-3 line Professional Summary aligned with your career role.")

        breakdown_dict = {
            "keyword_coverage": keyword_pct,
            "skills_match": skills_pct,
            "skills_coverage": skills_pct,
            "section_completeness": section_pct,
            "role_relevance": role_relevance_pct,
            "formatting_action_verbs": formatting_pct,
            "action_verbs_formatting": formatting_pct
        }

        return {
            "overall_score": total_score,
            "target_role": target_role_title,
            "breakdown": breakdown_dict,
            "subscores": breakdown_dict,
            "matched_skills": matched_skills,
            "matching_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_keywords": matched_keywords,
            "matching_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "action_verbs_found": action_verb_count,
            "has_metrics": has_metrics,
            "suggestions": suggestions,
            "recommendations": suggestions,
            "disclaimer": "This score evaluates ATS keyword density, section structure, and role alignment based on measurable criteria. It does not guarantee employment or hiring decisions."
        }

    def optimize_bullet_points(self, bullets: List[str], target_role: str) -> List[str]:
        """
        Enhances bullet points to use strong action verbs and professional ATS phrasing
        without fabricating false credentials or experience.
        """
        if not bullets:
            return []

        # Try Gemini ModelRouter for professional ATS phrasing
        prompt = f"""You are an expert ATS Resume Optimization Specialist.
Improve the following resume bullet points for a candidate targeting a '{target_role}' role.

RULES:
1. Begin every bullet with a powerful action verb (Engineered, Developed, Architected, Optimized, Implemented).
2. Strengthen clarity, technical precision, and professional tone.
3. DO NOT invent false numbers, fake companies, or unmentioned skills.
4. Keep each bullet concise and impactful (1 to 2 lines).
5. Output ONLY the improved bullet points, one per line starting with '• '.

Original Bullets:
{chr(10).join(bullets)}"""

        gemini_result = model_router.generate_content("resume", prompt)
        if gemini_result:
            improved = [line.strip().lstrip("•-* ").strip() for line in gemini_result.split("\n") if line.strip()]
            if improved:
                return improved

        # Deterministic rule-based fallback bullet enhancement
        enhanced = []
        for b in bullets:
            clean = b.strip().lstrip("•-* ").strip()
            if not clean:
                continue
            words = clean.split()
            first_word = words[0].lower()
            if first_word not in ACTION_VERBS and len(words) > 1:
                clean = "Engineered and " + clean[0].lower() + clean[1:]
            enhanced.append(clean)
        return enhanced or bullets

    def generate_ats_pdf(self, resume_data: dict) -> bytes:
        """
        Generates an ATS-compliant, single-column PDF using ReportLab.
        Adheres to standard ATS conventions: clean fonts, standard margins, no multi-column traps.
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        name_style = ParagraphStyle(
            'ATS_Name',
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#18181B')
        )
        contact_style = ParagraphStyle(
            'ATS_Contact',
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#4B5563')
        )
        section_heading = ParagraphStyle(
            'ATS_Heading',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#18181B'),
            spaceBefore=10,
            spaceAfter=3
        )
        body_style = ParagraphStyle(
            'ATS_Body',
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#1F2937')
        )
        bullet_style = ParagraphStyle(
            'ATS_Bullet',
            fontName='Helvetica',
            fontSize=9.5,
            leading=13.5,
            leftIndent=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#374151')
        )
        item_title_style = ParagraphStyle(
            'ATS_ItemTitle',
            fontName='Helvetica-Bold',
            fontSize=10.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#111827')
        )

        elements = []

        # 1. Contact Header
        contact = resume_data.get("contact_info", {})
        name = contact.get("name") or resume_data.get("name") or "Candidate Name"
        elements.append(Paragraph(name, name_style))
        elements.append(Spacer(1, 4))

        contact_parts = []
        if contact.get("email"):
            contact_parts.append(contact["email"])
        if contact.get("phone"):
            contact_parts.append(contact["phone"])
        if contact.get("location"):
            contact_parts.append(contact["location"])
        if contact.get("linkedin"):
            contact_parts.append(contact["linkedin"])
        if contact.get("github"):
            contact_parts.append(contact["github"])

        if contact_parts:
            elements.append(Paragraph(" | ".join(contact_parts), contact_style))
        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#D1D5DB'), spaceAfter=8))

        # 2. Professional Summary
        summary = resume_data.get("summary")
        if summary and summary.strip():
            elements.append(Paragraph("PROFESSIONAL SUMMARY", section_heading))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E5E7EB'), spaceAfter=5))
            elements.append(Paragraph(summary.strip(), body_style))
            elements.append(Spacer(1, 8))

        # 3. Technical Skills
        skills = resume_data.get("skills", [])
        if skills:
            elements.append(Paragraph("TECHNICAL SKILLS", section_heading))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E5E7EB'), spaceAfter=5))
            if isinstance(skills, list):
                skills_text = ", ".join(skills)
            else:
                skills_text = str(skills)
            elements.append(Paragraph(f"<b>Core Technologies:</b> {skills_text}", body_style))
            elements.append(Spacer(1, 8))

        # 4. Sections (Experience, Projects, Education, Certifications)
        sections = resume_data.get("sections", [])
        for section in sections:
            sec_title = section.get("title", "").upper()
            sec_items = section.get("items", [])
            if not sec_title or not sec_items:
                continue

            elements.append(Paragraph(sec_title, section_heading))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E5E7EB'), spaceAfter=5))

            for item in sec_items:
                header_line = f"<b>{item.get('title', '')}</b>"
                if item.get("subtitle"):
                    header_line += f" | {item.get('subtitle')}"
                if item.get("date"):
                    header_line += f" <font color='#6B7280'>({item.get('date')})</font>"

                elements.append(Paragraph(header_line, item_title_style))

                bullets = item.get("bullets", [])
                if isinstance(bullets, str):
                    bullets = [b.strip() for b in bullets.split("\n") if b.strip()]

                for bullet in bullets:
                    clean_b = bullet.lstrip("•-* ").strip()
                    if clean_b:
                        elements.append(Paragraph(f"• {clean_b}", bullet_style))
                elements.append(Spacer(1, 5))
            elements.append(Spacer(1, 4))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _aggregate_resume_text(self, resume_data: dict) -> str:
        """Flattens all text inside a resume dict into a searchable string."""
        parts = []
        parts.append(resume_data.get("summary", ""))
        skills_val = resume_data.get("skills", [])
        if isinstance(skills_val, list):
            parts.append(" ".join(skills_val))
        elif isinstance(skills_val, str):
            parts.append(skills_val)
        parts.append(resume_data.get("education", ""))
        parts.append(resume_data.get("experience", ""))
        for sec in resume_data.get("sections", []):
            parts.append(sec.get("title", ""))
            parts.append(sec.get("heading", ""))
            parts.append(sec.get("content", ""))
            for item in sec.get("items", []):
                parts.append(item.get("title", ""))
                parts.append(item.get("organization", ""))
                parts.append(item.get("subtitle", ""))
                for b in item.get("bullets", []):
                    parts.append(b)
        return " ".join(parts)

    def _extract_all_skills(self, resume_data: dict) -> List[str]:
        """Extracts skills from dedicated list and scans text for normalized skills."""
        explicit = []
        raw_skills = resume_data.get("skills", [])
        if isinstance(raw_skills, str):
            explicit.extend([s.strip() for s in raw_skills.split(",") if s.strip()])
        elif isinstance(raw_skills, list):
            explicit.extend(raw_skills)

        # Also extract skills from sections where type == 'skills' or heading has 'skill'
        for sec in resume_data.get("sections", []):
            sec_type = sec.get("type", "").lower()
            sec_heading = (sec.get("heading") or sec.get("title") or "").lower()
            if sec_type == "skills" or "skill" in sec_heading:
                content = sec.get("content", "")
                if content:
                    explicit.extend([s.strip() for s in content.split(",") if s.strip()])

        return list(set(explicit))

    def _score_sections(self, resume_data: dict) -> Dict[str, Any]:
        """Evaluates presence of essential ATS resume sections."""
        contact = resume_data.get("contact_info", {})
        has_contact = bool(contact.get("email") and (contact.get("phone") or contact.get("location")))
        has_summary = bool(resume_data.get("summary", "").strip())
        has_skills = bool(self._extract_all_skills(resume_data))

        sections = resume_data.get("sections", [])
        section_names = []
        for s in sections:
            name = (s.get("heading") or s.get("title") or s.get("type") or "").lower()
            section_names.append(name)

        has_experience = any("experience" in t or "work" in t or "employment" in t for t in section_names) or bool(resume_data.get("experience"))
        has_education = any("education" in t or "academic" in t for t in section_names) or bool(resume_data.get("education"))
        has_projects = any("project" in t for t in section_names)

        score = 0
        if has_contact: score += 20
        if has_summary: score += 15
        if has_skills: score += 20
        if has_experience: score += 20
        if has_education: score += 15
        if has_projects: score += 10

        pct = min(100, score)
        return {
            "percentage": pct,
            "has_contact": has_contact,
            "has_summary": has_summary,
            "has_skills": has_skills,
            "has_experience": has_experience,
            "has_education": has_education,
            "has_projects": has_projects
        }

    def _get_role_target_keywords(self, role_key: Optional[str]) -> List[str]:
        """Returns standard industry keywords for a given role."""
        if role_key and role_key in CAREER_ROLES:
            info = CAREER_ROLES[role_key]
            keywords = []
            for s in info.get("required_skills", []):
                keywords.append(s.split("(")[0].strip())
            for s in info.get("preferred_skills", []):
                keywords.append(s.split("(")[0].strip())
            return keywords[:12]
        return ["python", "sql", "api", "git", "database", "testing", "docker", "agile"]

    def _extract_job_description_keywords(self, job_description: str) -> List[str]:
        """Extracts technical keywords and tools from a job description text."""
        extracted = self.skill_extractor.extract_skills(job_description)
        if len(extracted) < 5:
            # Fallback keyword extraction using regex for common tech terms
            tech_patterns = re.findall(r'\b[A-Z][a-zA-Z0-9+#.-]{1,15}\b', job_description)
            combined = list(set(extracted + tech_patterns[:10]))
            return combined[:12]
        return extracted[:12]


# Global singleton instance
ats_service = ATSService()
