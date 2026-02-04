"""ReliefWeb job scraper using their API."""

from datetime import datetime
from typing import Optional

from .base import BaseScraper, Job


class ReliefWebScraper(BaseScraper):
    """Scraper for ReliefWeb jobs API."""

    name = "reliefweb"
    base_url = "https://api.reliefweb.int/v1/jobs"

    # Target countries
    COUNTRIES = ["Ethiopia", "Kenya", "Somalia", "South Sudan", "Uganda"]

    def scrape(self) -> list[Job]:
        """Scrape jobs from ReliefWeb API."""
        jobs = []

        for country in self.COUNTRIES:
            country_jobs = self._scrape_country(country)
            jobs.extend(country_jobs)

        # Remove duplicates based on ID
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique_jobs.append(job)

        return unique_jobs

    def _scrape_country(self, country: str) -> list[Job]:
        """Scrape jobs for a specific country."""
        jobs = []

        params = {
            "appname": "job-hunter",
            "limit": 50,
            "filter[field]": "country.name",
            "filter[value]": country,
            "sort[]": "date:desc",
            "fields[include][]": [
                "title", "body", "url", "source", "date",
                "country", "city", "type", "experience",
                "career_categories"
            ],
        }

        try:
            response = self.fetch(f"{self.base_url}?appname=job-hunter&limit=50&filter[field]=country.name&filter[value]={country}&sort[]=date:desc")
            data = response.json()

            for item in data.get("data", []):
                job = self._parse_job(item)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping {country}: {e}")

        return jobs

    def _parse_job(self, item: dict) -> Optional[Job]:
        """Parse a job from API response."""
        try:
            fields = item.get("fields", {})

            title = fields.get("title", "")
            url = fields.get("url", "")

            if not title or not url:
                return None

            # Extract organization
            source = fields.get("source", [])
            organization = source[0].get("name", "Unknown") if source else "Unknown"

            # Extract location
            countries = fields.get("country", [])
            cities = fields.get("city", [])
            location_parts = []
            if cities:
                location_parts.extend([c.get("name", "") for c in cities])
            if countries:
                location_parts.extend([c.get("name", "") for c in countries])
            location = ", ".join(filter(None, location_parts)) or "Not specified"

            # Extract description
            description = fields.get("body", "") or fields.get("body-html", "") or ""

            # Extract dates
            date_info = fields.get("date", {})
            posted_date = date_info.get("created", "")
            deadline = date_info.get("closing", "")

            # Extract job type
            job_types = fields.get("type", [])
            job_type = job_types[0].get("name", "") if job_types else ""

            # Extract experience
            experience = fields.get("experience", [])
            experience_required = experience[0].get("name", "") if experience else ""

            return Job(
                id=Job.generate_id(url, title),
                title=title,
                organization=organization,
                location=location,
                description=description[:5000],  # Limit description length
                url=url,
                source=self.name,
                posted_date=posted_date,
                deadline=deadline,
                job_type=job_type,
                experience_required=experience_required,
            )

        except Exception as e:
            print(f"[{self.name}] Error parsing job: {e}")
            return None
