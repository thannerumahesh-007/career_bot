"""
Skill, Interest, Education, and Experience Extractor module for CareerBot.
Parses natural language text and returns canonical structured profile information.
"""

import re
from nlp.skill_dictionary import (
    SKILL_ALIASES, CANONICAL_DISPLAY, DOMAIN_INTERESTS,
    EDUCATION_DEGREES, EXPERIENCE_LEVELS, TARGET_ROLES,
    normalize_skill, normalize_skill_key
)

LOCATIONS = ["Bangalore", "Hyderabad", "Chennai", "Remote", "Pune", "Mumbai", "Delhi", "India"]


class SkillExtractor:
    """Natural Language Skill & Attribute Extractor."""

    def __init__(self):
        # Sort keys by length descending to match multi-word phrases first (e.g. "machine learning" before "learning")
        self.skill_phrases = sorted(SKILL_ALIASES.keys(), key=lambda x: len(x), reverse=True)

    def extract_skills(self, text: str) -> list:
        """Extracts canonical skill names from natural language text."""
        if not text:
            return []
        
        text_lower = f" {text.lower()} "
        # Replace common delimiters with spaces for clean phrase matching
        text_normalized = re.sub(r'[,;\n\t\/\(\)]', ' ', text_lower)
        
        found_keys = set()

        for phrase in self.skill_phrases:
            # Check for word boundary surrounded matching
            escaped_phrase = re.escape(phrase)
            pattern = rf'(?:\b|\s){escaped_phrase}(?:\b|\s)'
            if re.search(pattern, text_normalized):
                canonical_key = SKILL_ALIASES[phrase]
                found_keys.add(canonical_key)

        # Convert canonical keys to standard display names
        return [CANONICAL_DISPLAY.get(k, k.title()) for k in sorted(list(found_keys))]

    def extract_interests(self, text: str) -> list:
        """Extracts domain interests from text."""
        if not text:
            return []
        found = []
        text_lower = text.lower()
        for interest in DOMAIN_INTERESTS:
            if interest.lower() in text_lower:
                found.append(interest)
        return found

    def extract_education(self, text: str) -> str:
        """Extracts highest education level or degree from text."""
        if not text:
            return ""
        text_lower = text.lower()
        for degree in EDUCATION_DEGREES:
            if degree.lower() in text_lower or (degree == "CSE Student" and "cse" in text_lower):
                return degree
        if "student" in text_lower or "college" in text_lower:
            return "Student"
        return ""

    def extract_experience(self, text: str) -> str:
        """Extracts experience level from text."""
        if not text:
            return ""
        text_lower = text.lower()
        if "fresher" in text_lower or "no experience" in text_lower or "college student" in text_lower:
            return "Fresher"
        if "intern" in text_lower or "internship" in text_lower:
            return "Intern"
        if "1 year" in text_lower or "1-2 years" in text_lower or "one year" in text_lower:
            return "1-2 years"
        if "2 year" in text_lower or "2+ years" in text_lower or "two year" in text_lower:
            return "2+ years"
        return ""

    def extract_target_roles(self, text: str) -> list:
        """Extracts desired career target roles from text."""
        if not text:
            return []
        found = []
        text_lower = text.lower()
        for role in TARGET_ROLES:
            if role.lower() in text_lower:
                found.append(role)
        return found

    def extract_location(self, text: str) -> str:
        """Extracts location preference from text."""
        if not text:
            return ""
        text_lower = text.lower()
        for loc in LOCATIONS:
            if loc.lower() in text_lower:
                return loc
        return ""

    def extract_profile_data(self, text: str) -> dict:
        """Runs complete extraction pipeline and returns profile dict."""
        return {
            "skills": self.extract_skills(text),
            "interests": self.extract_interests(text),
            "education": self.extract_education(text),
            "experience": self.extract_experience(text),
            "target_roles": self.extract_target_roles(text),
            "location": self.extract_location(text)
        }
