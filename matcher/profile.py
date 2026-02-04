"""CV Profile management."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import config


@dataclass
class CVProfile:
    """Structured CV profile for job matching."""

    name: str = ""
    target_roles: list[str] = field(default_factory=list)
    target_locations: list[str] = field(default_factory=list)
    years_experience: int = 0
    skills: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    organizations_worked: list[str] = field(default_factory=list)
    donors_experience: list[str] = field(default_factory=list)
    keywords_boost: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "CVProfile":
        """Load CV profile from JSON file."""
        path = path or config.CV_PROFILE_FILE

        if not path.exists():
            raise FileNotFoundError(f"CV profile not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        return cls(
            name=data.get("name", ""),
            target_roles=data.get("target_roles", []),
            target_locations=data.get("target_locations", []),
            years_experience=data.get("years_experience", 0),
            skills=data.get("skills", []),
            certifications=data.get("certifications", []),
            languages=data.get("languages", []),
            sectors=data.get("sectors", []),
            organizations_worked=data.get("organizations_worked", []),
            donors_experience=data.get("donors_experience", []),
            keywords_boost=data.get("keywords_boost", []),
        )

    def get_all_keywords(self) -> list[str]:
        """Get all keywords for matching."""
        keywords = []
        keywords.extend(self.target_roles)
        keywords.extend(self.skills)
        keywords.extend(self.sectors)
        keywords.extend(self.donors_experience)
        keywords.extend(self.keywords_boost)
        keywords.extend(self.certifications)
        return [k.lower() for k in keywords]

    def get_skills_text(self) -> str:
        """Get skills as text for TF-IDF."""
        parts = []
        parts.extend(self.skills)
        parts.extend(self.sectors)
        parts.extend(self.donors_experience)
        parts.extend([f"{role} experience" for role in self.target_roles])
        parts.extend(self.keywords_boost)
        return " ".join(parts)
