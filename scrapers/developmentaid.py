"""DevelopmentAid jobs scraper."""

from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class DevelopmentAidScraper(BaseScraper):
    """Scraper for DevelopmentAid.org jobs."""

    name = "developmentaid"
    base_url = "https://www.developmentaid.org"

    # Search URLs for target regions
    SEARCH_URLS = [
        "/jobs?country[]=Ethiopia",
        "/jobs?country[]=Kenya",
        "/jobs?country[]=Somalia",
        "/jobs?keyword=program+manager",
        "/jobs?keyword=country+director",
    ]

    def scrape(self) -> list[Job]:
        """Scrape jobs from DevelopmentAid."""
        jobs = []

        for search_url in self.SEARCH_URLS:
            search_jobs = self._scrape_search(search_url)
            jobs.extend(search_jobs)

        # Remove duplicates
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique_jobs.append(job)

        return unique_jobs

    def _scrape_search(self, search_path: str) -> list[Job]:
        """Scrape jobs from a search results page."""
        jobs = []
        url = urljoin(self.base_url, search_path)

        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find job listings
            job_items = soup.select(
                ".job-item, .listing-item, article.job, .search-result"
            )

            for item in job_items[:25]:
                job = self._parse_job_item(item)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping search: {e}")

        return jobs

    def _parse_job_item(self, item) -> Optional[Job]:
        """Parse a job from a listing item."""
        try:
            # Extract title and URL
            title_elem = item.select_one("h2 a, h3 a, a.title, .job-title a")
            if not title_elem:
                title_elem = item.select_one("a[href*='/jobs/']")

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            url = title_elem.get("href", "")

            if not url.startswith("http"):
                url = urljoin(self.base_url, url)

            if not title or not url:
                return None

            # Extract organization
            org_elem = item.select_one(
                ".organization, .company, .employer"
            )
            organization = org_elem.get_text(strip=True) if org_elem else "Not specified"

            # Extract location
            loc_elem = item.select_one(".location, .country")
            location = loc_elem.get_text(strip=True) if loc_elem else ""

            # Extract deadline
            deadline_elem = item.select_one(".deadline, .closing-date, .date")
            deadline = deadline_elem.get_text(strip=True) if deadline_elem else ""

            # Get description
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
            print(f"[{self.name}] Error parsing job item: {e}")
            return None

    def _get_job_description(self, url: str) -> str:
        """Fetch full job description from detail page."""
        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            desc_elem = soup.select_one(
                ".job-description, .description, .content, article"
            )

            if desc_elem:
                for script in desc_elem.find_all(["script", "style"]):
                    script.decompose()
                return desc_elem.get_text(separator="\n", strip=True)[:5000]

            return ""

        except Exception as e:
            print(f"[{self.name}] Error fetching description: {e}")
            return ""
