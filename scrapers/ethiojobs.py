"""EthioJobs scraper."""

from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class EthioJobsScraper(BaseScraper):
    """Scraper for EthioJobs.net."""

    name = "ethiojobs"
    base_url = "https://www.ethiojobs.net"

    # Categories to scrape
    CATEGORIES = [
        "/jobs/ngo-and-development",
        "/jobs/management",
        "/jobs/project-management",
    ]

    def scrape(self) -> list[Job]:
        """Scrape jobs from EthioJobs."""
        jobs = []

        for category in self.CATEGORIES:
            category_jobs = self._scrape_category(category)
            jobs.extend(category_jobs)

        # Remove duplicates
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique_jobs.append(job)

        return unique_jobs

    def _scrape_category(self, category_path: str) -> list[Job]:
        """Scrape jobs from a category page."""
        jobs = []
        url = urljoin(self.base_url, category_path)

        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find job listings
            job_cards = soup.select(".job-listing, .job-item, article.job")

            if not job_cards:
                # Try alternative selectors
                job_cards = soup.select("[class*='job'], .listing-item")

            for card in job_cards[:30]:  # Limit per category
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping {category_path}: {e}")

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a job from a listing card."""
        try:
            # Extract title and URL
            title_elem = card.select_one("h2 a, h3 a, .job-title a, a.title")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            url = urljoin(self.base_url, title_elem.get("href", ""))

            if not title or not url:
                return None

            # Extract organization
            org_elem = card.select_one(".company-name, .employer, .organization")
            organization = org_elem.get_text(strip=True) if org_elem else "Not specified"

            # Extract location
            loc_elem = card.select_one(".location, .job-location, [class*='location']")
            location = loc_elem.get_text(strip=True) if loc_elem else "Ethiopia"

            # Extract deadline
            deadline_elem = card.select_one(".deadline, .closing-date, [class*='deadline']")
            deadline = deadline_elem.get_text(strip=True) if deadline_elem else ""

            # Get full description from job page
            description = self._get_job_description(url)

            return Job(
                id=Job.generate_id(url, title),
                title=title,
                organization=organization,
                location=location,
                description=description,
                url=url,
                source=self.name,
                deadline=deadline,
            )

        except Exception as e:
            print(f"[{self.name}] Error parsing job card: {e}")
            return None

    def _get_job_description(self, url: str) -> str:
        """Fetch full job description from detail page."""
        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find description content
            desc_elem = soup.select_one(
                ".job-description, .description, article, .content, main"
            )

            if desc_elem:
                # Clean up the text
                for script in desc_elem.find_all(["script", "style"]):
                    script.decompose()
                return desc_elem.get_text(separator="\n", strip=True)[:5000]

            return ""

        except Exception as e:
            print(f"[{self.name}] Error fetching description: {e}")
            return ""
