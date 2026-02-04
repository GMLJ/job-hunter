"""ReliefWeb job scraper using RSS feeds."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import feedparser
from bs4 import BeautifulSoup

from .base import BaseScraper, Job


class ReliefWebScraper(BaseScraper):
    """Scraper for ReliefWeb jobs via RSS."""

    name = "reliefweb"
    base_url = "https://reliefweb.int"

    # RSS feed URLs for target countries
    RSS_FEEDS = [
        "https://reliefweb.int/jobs/rss.xml?search=country.exact%3A%22Ethiopia%22",
        "https://reliefweb.int/jobs/rss.xml?search=country.exact%3A%22Kenya%22",
        "https://reliefweb.int/jobs/rss.xml?search=country.exact%3A%22Somalia%22",
        "https://reliefweb.int/jobs/rss.xml?search=country.exact%3A%22South%20Sudan%22",
        "https://reliefweb.int/jobs/rss.xml?search=country.exact%3A%22Uganda%22",
    ]

    def scrape(self) -> list[Job]:
        """Scrape jobs from ReliefWeb RSS feeds."""
        jobs = []

        for feed_url in self.RSS_FEEDS:
            feed_jobs = self._scrape_feed(feed_url)
            jobs.extend(feed_jobs)

        # Remove duplicates based on ID
        seen = set()
        unique_jobs = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                unique_jobs.append(job)

        return unique_jobs

    def _scrape_feed(self, feed_url: str) -> list[Job]:
        """Scrape jobs from a single RSS feed."""
        jobs = []

        try:
            # Use session to fetch with proper headers
            response = self.fetch(feed_url)
            feed = feedparser.parse(response.text)

            for entry in feed.entries[:30]:  # Limit per feed
                job = self._parse_entry(entry)
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"[{self.name}] Error scraping feed: {e}")

        return jobs

    def _parse_entry(self, entry) -> Optional[Job]:
        """Parse a job from RSS entry."""
        try:
            title = entry.get("title", "")
            url = entry.get("link", "")

            if not title or not url:
                return None

            # Parse description HTML
            description_html = entry.get("description", "")
            soup = BeautifulSoup(description_html, "lxml")

            # Extract organization
            org_elem = soup.find("div", class_="tag source")
            organization = "Unknown"
            if org_elem:
                org_text = org_elem.get_text()
                if "Organization:" in org_text:
                    organization = org_text.replace("Organization:", "").strip()

            # Extract location
            country_elem = soup.find("div", class_="tag country")
            location = ""
            if country_elem:
                loc_text = country_elem.get_text()
                if "Countries:" in loc_text:
                    location = loc_text.replace("Countries:", "").strip()
                elif "Country:" in loc_text:
                    location = loc_text.replace("Country:", "").strip()

            # Extract deadline
            deadline_elem = soup.find("div", class_="date closing")
            deadline = ""
            if deadline_elem:
                deadline_text = deadline_elem.get_text()
                if "Closing date:" in deadline_text:
                    deadline = deadline_text.replace("Closing date:", "").strip()

            # Get full description text
            description = soup.get_text(separator="\n", strip=True)

            # Posted date
            posted_date = entry.get("published", "")

            return Job(
                id=Job.generate_id(url, title),
                title=title,
                organization=organization,
                location=location or "Not specified",
                description=description[:5000],
                url=url,
                source=self.name,
                posted_date=posted_date,
                deadline=deadline,
            )

        except Exception as e:
            print(f"[{self.name}] Error parsing entry: {e}")
            return None
