"""UNJobs scraper."""

from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class UNJobsScraper(BaseScraper):
    """Scraper for UNJobs.org."""

    name = "unjobs"
    base_url = "https://unjobs.org"

    # Search queries for target locations
    SEARCH_QUERIES = [
        "/duty_stations/addis-ababa",
        "/duty_stations/nairobi",
        "/duty_stations/mogadishu",
        "/search?q=ethiopia",
        "/search?q=kenya",
    ]

    def scrape(self) -> list[Job]:
        """Scrape jobs from UNJobs."""
        jobs = []

        for query in self.SEARCH_QUERIES:
            query_jobs = self._scrape_search(query)
            jobs.extend(query_jobs)

        # Remove duplicates
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique_jobs.append(job)

        return unique_jobs

    def _scrape_search(self, search_path: str) -> list[Job]:
        """Scrape jobs from a search or duty station page."""
        jobs = []
        url = urljoin(self.base_url, search_path)

        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find job listings
            job_rows = soup.select("table tr, .job-listing, .vacancy")

            for row in job_rows[:30]:
                job = self._parse_job_row(row)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping {search_path}: {e}")

        return jobs

    def _parse_job_row(self, row) -> Optional[Job]:
        """Parse a job from a table row or listing."""
        try:
            # Find title link
            link = row.select_one("a[href*='/vacancies/'], a[href*='/job/']")
            if not link:
                return None

            title = link.get_text(strip=True)
            url = urljoin(self.base_url, link.get("href", ""))

            if not title or not url or len(title) < 5:
                return None

            # Extract organization (usually in separate cell/element)
            cells = row.select("td")
            organization = "United Nations"
            location = ""
            deadline = ""

            if len(cells) >= 2:
                # Try to find org name
                for cell in cells:
                    text = cell.get_text(strip=True)
                    if any(un in text.upper() for un in ["UNDP", "UNICEF", "UNHCR", "WFP", "UN", "WHO", "FAO"]):
                        organization = text
                        break

            # Look for location
            loc_elem = row.select_one("[class*='location'], .duty-station")
            if loc_elem:
                location = loc_elem.get_text(strip=True)
            else:
                # Try to extract from title or other text
                for loc in ["Addis Ababa", "Nairobi", "Ethiopia", "Kenya", "Mogadishu"]:
                    if loc.lower() in row.get_text().lower():
                        location = loc
                        break

            # Look for deadline
            date_elem = row.select_one("[class*='date'], .deadline, .closing")
            if date_elem:
                deadline = date_elem.get_text(strip=True)

            # Get full description
            description = self._get_job_description(url)

            return Job(
                id=Job.generate_id(url, title),
                title=title,
                organization=organization,
                location=location or "UN Duty Station",
                description=description,
                url=url,
                source=self.name,
                deadline=deadline,
            )

        except Exception as e:
            print(f"[{self.name}] Error parsing job row: {e}")
            return None

    def _get_job_description(self, url: str) -> str:
        """Fetch full job description."""
        try:
            response = self.fetch(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find description
            desc_elem = soup.select_one(
                ".job-description, .vacancy-description, article, .content"
            )

            if desc_elem:
                for script in desc_elem.find_all(["script", "style"]):
                    script.decompose()
                return desc_elem.get_text(separator="\n", strip=True)[:5000]

            return ""

        except Exception as e:
            print(f"[{self.name}] Error fetching description: {e}")
            return ""
