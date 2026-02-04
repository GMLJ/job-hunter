"""DevEx jobs scraper."""

from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class DevExScraper(BaseScraper):
    """Scraper for DevEx.com jobs."""

    name = "devex"
    base_url = "https://www.devex.com"

    # Search URLs for target regions and roles
    SEARCH_URLS = [
        "/jobs/search?filter%5Blocation%5D%5B%5D=Ethiopia",
        "/jobs/search?filter%5Blocation%5D%5B%5D=Kenya",
        "/jobs/search?filter%5Bkeyword%5D=program+manager+africa",
        "/jobs/search?filter%5Bkeyword%5D=country+director+africa",
    ]

    def scrape(self) -> list[Job]:
        """Scrape jobs from DevEx."""
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

            # Find job cards
            job_cards = soup.select(
                ".job-card, .search-result, article[class*='job'], .listing"
            )

            for card in job_cards[:25]:
                job = self._parse_job_card(card)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping search: {e}")

        return jobs

    def _parse_job_card(self, card) -> Optional[Job]:
        """Parse a job from a card element."""
        try:
            # Extract title and URL
            title_elem = card.select_one("h2 a, h3 a, a.title, .job-title a")
            if not title_elem:
                # Try finding any link that looks like a job link
                title_elem = card.select_one("a[href*='/jobs/']")

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            url = title_elem.get("href", "")

            if not url.startswith("http"):
                url = urljoin(self.base_url, url)

            if not title or not url:
                return None

            # Extract organization
            org_elem = card.select_one(
                ".organization, .company, .employer, [class*='org']"
            )
            organization = org_elem.get_text(strip=True) if org_elem else "Not specified"

            # Extract location
            loc_elem = card.select_one(
                ".location, [class*='location'], .place"
            )
            location = loc_elem.get_text(strip=True) if loc_elem else ""

            # Extract deadline
            deadline_elem = card.select_one(
                ".deadline, .closing, [class*='date']"
            )
            deadline = deadline_elem.get_text(strip=True) if deadline_elem else ""

            # Extract job type
            type_elem = card.select_one(
                ".job-type, [class*='type'], .category"
            )
            job_type = type_elem.get_text(strip=True) if type_elem else ""

            # Get description from detail page
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
                job_type=job_type,
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
                ".job-description, .description, .job-content, article"
            )

            if desc_elem:
                for script in desc_elem.find_all(["script", "style"]):
                    script.decompose()
                return desc_elem.get_text(separator="\n", strip=True)[:5000]

            return ""

        except Exception as e:
            print(f"[{self.name}] Error fetching description: {e}")
            return ""
