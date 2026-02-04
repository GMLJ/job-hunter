"""Job scoring engine using TF-IDF and keyword matching."""

import re
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

import config
from scrapers.base import Job
from .profile import CVProfile


class JobScorer:
    """Score jobs against CV profile."""

    def __init__(self, profile: Optional[CVProfile] = None):
        """Initialize scorer with CV profile."""
        self.profile = profile or CVProfile.load()
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        self._fit_vectorizer()

    def _fit_vectorizer(self):
        """Fit the TF-IDF vectorizer on profile keywords."""
        profile_text = self.profile.get_skills_text()
        # Fit on profile to establish vocabulary
        self.vectorizer.fit([profile_text])
        self.profile_vector = self.vectorizer.transform([profile_text])

    def score_job(self, job: Job) -> float:
        """
        Score a job against the CV profile.
        Returns score 0-100.
        """
        scores = {}

        # Title match (30%)
        scores["title"] = self._score_title_match(job.title)

        # Location match (20%)
        scores["location"] = self._score_location_match(job.location)

        # Skills overlap via TF-IDF (25%)
        scores["skills"] = self._score_skills_overlap(job.description)

        # Experience fit (15%)
        scores["experience"] = self._score_experience_fit(job)

        # Donor match (10%)
        scores["donor"] = self._score_donor_match(job.description, job.organization)

        # Calculate weighted score
        weights = config.SCORING_WEIGHTS
        total_score = (
            scores["title"] * weights["title_match"] +
            scores["location"] * weights["location_match"] +
            scores["skills"] * weights["skills_overlap"] +
            scores["experience"] * weights["experience_fit"] +
            scores["donor"] * weights["donor_match"]
        )

        return round(total_score, 1)

    def _score_title_match(self, title: str) -> float:
        """Score based on job title matching target roles."""
        title_lower = title.lower()
        best_score = 0

        for role in self.profile.target_roles:
            role_lower = role.lower()
            role_words = role_lower.split()

            # Exact match
            if role_lower in title_lower:
                return 100

            # Partial match (all words present)
            if all(word in title_lower for word in role_words):
                best_score = max(best_score, 90)
                continue

            # Most words match
            matching_words = sum(1 for word in role_words if word in title_lower)
            if matching_words > 0:
                word_score = (matching_words / len(role_words)) * 80
                best_score = max(best_score, word_score)

        # Check for senior/leadership indicators
        leadership_terms = ["director", "head", "chief", "lead", "senior", "manager"]
        if any(term in title_lower for term in leadership_terms):
            best_score = max(best_score, 50)

        return best_score

    def _score_location_match(self, location: str) -> float:
        """Score based on location matching preferences."""
        if not location:
            return 40  # Unknown location gets neutral score

        location_lower = location.lower()

        # Check against location scores
        for loc, score in config.LOCATION_SCORES.items():
            if loc in location_lower:
                return score

        # Check against target locations
        for target_loc in self.profile.target_locations:
            if target_loc.lower() in location_lower:
                return 90

        return 30  # Default for non-matching locations

    def _score_skills_overlap(self, description: str) -> float:
        """Score based on TF-IDF similarity with job description."""
        if not description:
            return 30

        try:
            # Transform job description
            job_vector = self.vectorizer.transform([description])

            # Calculate cosine similarity
            similarity = cosine_similarity(self.profile_vector, job_vector)[0][0]

            # Scale to 0-100
            return min(100, similarity * 150)  # Boost factor

        except Exception:
            return 30

    def _score_experience_fit(self, job: Job) -> float:
        """Score based on experience requirements."""
        exp_text = (job.experience_required or "") + " " + (job.description or "")
        exp_text_lower = exp_text.lower()

        # Extract years mentioned
        years_pattern = r"(\d+)\+?\s*(?:years?|yrs?)"
        matches = re.findall(years_pattern, exp_text_lower)

        if not matches:
            return 70  # No explicit requirement

        required_years = [int(m) for m in matches]
        min_years = min(required_years) if required_years else 0
        max_years = max(required_years) if required_years else 100

        my_years = self.profile.years_experience

        # Perfect fit
        if min_years <= my_years <= max_years + 2:
            return 100

        # Slightly over/under qualified
        if my_years >= min_years - 2:
            return 80

        # Under qualified
        if my_years < min_years - 2:
            return 40

        return 60

    def _score_donor_match(self, description: str, organization: str) -> float:
        """Score based on donor/funder experience match."""
        text = f"{description} {organization}".lower()
        matched_donors = 0

        for donor in self.profile.donors_experience:
            if donor.lower() in text:
                matched_donors += 1

        if matched_donors >= 2:
            return 100
        elif matched_donors == 1:
            return 70
        else:
            return 30

    def _extract_salary(self, job: Job) -> Optional[float]:
        """
        Extract monthly salary in USD from job description.
        Returns None if salary not found or not parseable.
        """
        text = f"{job.salary or ''} {job.description or ''}".lower()

        # Common salary patterns
        patterns = [
            # USD amounts: $5,000, $5000, USD 5000, 5000 USD
            r'(?:\$|usd)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/\s*month|monthly|p\.?m\.?)?',
            r'([\d,]+(?:\.\d{2})?)\s*(?:usd|dollars?)\s*(?:per\s*month|/\s*month|monthly|p\.?m\.?)?',
            # EUR amounts (convert roughly)
            r'(?:€|eur)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*month|/\s*month|monthly|p\.?m\.?)?',
            r'([\d,]+(?:\.\d{2})?)\s*(?:eur|euros?)\s*(?:per\s*month|/\s*month|monthly|p\.?m\.?)?',
            # Annual salary patterns
            r'(?:\$|usd)\s*([\d,]+(?:\.\d{2})?)\s*(?:per\s*(?:year|annum)|/\s*(?:year|annum)|annually|p\.?a\.?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:usd|dollars?)\s*(?:per\s*(?:year|annum)|/\s*(?:year|annum)|annually|p\.?a\.?)',
        ]

        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    amount = float(match.replace(',', ''))

                    # Convert EUR to USD (rough estimate)
                    if i in [2, 3]:
                        amount *= 1.1

                    # Convert annual to monthly
                    if i in [4, 5] or amount > 20000:
                        amount /= 12

                    # Sanity check: reasonable salary range
                    if 500 <= amount <= 50000:
                        return amount
                except ValueError:
                    continue

        return None

    def _meets_salary_requirement(self, job: Job) -> bool:
        """Check if job meets minimum salary requirement."""
        salary = self._extract_salary(job)

        if salary is not None:
            job.salary = f"~${salary:,.0f}/month"
            return salary >= config.MIN_SALARY_USD

        # No salary found - include unless configured to exclude
        return not config.EXCLUDE_NO_SALARY

    def score_jobs(self, jobs: list[Job]) -> list[Job]:
        """Score multiple jobs and add scores to them."""
        for job in jobs:
            job.score = self.score_job(job)
        return jobs

    def filter_matches(self, jobs: list[Job], min_score: float = None) -> list[Job]:
        """Filter jobs by minimum score and salary."""
        min_score = min_score or config.SCORE_THRESHOLD_LOW
        filtered = []

        for job in jobs:
            if (job.score or 0) < min_score:
                continue
            if not self._meets_salary_requirement(job):
                print(f"[Scorer] Excluded (salary < ${config.MIN_SALARY_USD}): {job.title}")
                continue
            filtered.append(job)

        return filtered
