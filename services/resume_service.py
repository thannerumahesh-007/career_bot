"""
Resume Parser Service for CareerBot.
Extracts text from PDF, DOCX, and TXT files, parses resume sections,
extracts skills, education, experience, and updates the database user profile.
"""

import re
from pathlib import Path
from nlp.skill_extractor import SkillExtractor


class ResumeService:
    """Parses resumes and extracts structured profile data."""

    def __init__(self):
        self.extractor = SkillExtractor()

    def extract_text_from_file(self, file_path: str) -> str:
        """Extracts raw text from PDF, DOCX, or TXT file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = path.suffix.lower()

        if ext == ".txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text_parts = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt:
                        text_parts.append(txt)
                return "\n".join(text_parts)
            except Exception as e:
                raise ValueError(f"Failed to read PDF file: {str(e)}")

        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(str(path))
                return "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception as e:
                raise ValueError(f"Failed to read DOCX file: {str(e)}")

        else:
            raise ValueError(f"Unsupported file format: {ext}. Allowed formats: .pdf, .docx, .txt")

    def parse_sections(self, text: str) -> dict:
        """Rule-based heading detection to separate resume into logical sections."""
        sections = {
            "skills": "",
            "education": "",
            "experience": "",
            "projects": "",
            "certifications": ""
        }

        if not text:
            return sections

        lines = text.split("\n")
        current_section = "general"

        heading_patterns = {
            "skills": r'^(skills|technical skills|key skills|technologies|core competencies)\b',
            "education": r'^(education|academic background|qualification|academics)\b',
            "experience": r'^(experience|work experience|employment|internships|professional experience)\b',
            "projects": r'^(projects|academic projects|key projects|personal projects)\b',
            "certifications": r'^(certifications|certificates|licenses|courses)\b'
        }

        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue

            line_lower = line_clean.lower()
            matched_heading = False

            # Check if line matches section heading
            for sec_name, pattern in heading_patterns.items():
                if re.search(pattern, line_lower):
                    current_section = sec_name
                    matched_heading = True
                    break

            if not matched_heading and current_section in sections:
                sections[current_section] += " " + line_clean

        return sections

    def parse_resume(self, file_path: str) -> dict:
        """Full pipeline: reads file, extracts text, detects sections, and identifies skills."""
        raw_text = self.extract_text_from_file(file_path)
        sections = self.parse_sections(raw_text)

        # Extract profile attributes from full text + section specific text
        extracted_skills = self.extractor.extract_skills(raw_text)
        education = self.extractor.extract_education(sections["education"] or raw_text)
        experience = self.extractor.extract_experience(sections["experience"] or raw_text)
        target_roles = self.extractor.extract_target_roles(raw_text)

        # Clean project titles snippet
        projects_summary = sections["projects"].strip()[:150] if sections["projects"] else "N/A"
        certs_summary = sections["certifications"].strip()[:150] if sections["certifications"] else "N/A"

        return {
            "raw_text_length": len(raw_text),
            "skills": extracted_skills,
            "education": education or "B.Tech Computer Science",
            "experience": experience or "Fresher",
            "target_roles": target_roles,
            "projects_summary": projects_summary,
            "certifications_summary": certs_summary,
            "sections_detected": [k for k, v in sections.items() if len(v.strip()) > 0]
        }
