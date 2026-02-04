"""Base scraper class with common functionality."""

import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

import config


@dataclass
class Job:
    """Represents a job posting."""

    id: str
    title: str
    organization: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    deadline: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Part-time, Consultant
    experience_required: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    score: Optional[float] = None
    cover_letter_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @staticmethod
    def generate_id(url: str, title: str) -> str:
        """Generate unique ID from URL and title."""
        content = f"{url}:{title}".encode()
        return hashlib.md5(content).hexdigest()[:12]


class BaseScraper(ABC):
    """Base class for all job scrapers."""

    name: str = "base"
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self._last_request_time = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < config.REQUEST_DELAY:
            time.sleep(config.REQUEST_DELAY - elapsed)
        self._last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(config.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def fetch(self, url: str) -> requests.Response:
        """Fetch URL with rate limiting and retries."""
        self._rate_limit()
        response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    @abstractmethod
    def scrape(self) -> list[Job]:
        """Scrape jobs from the source. Must be implemented by subclasses."""
        pass

    def run(self) -> list[Job]:
        """Run the scraper with error handling."""
        try:
            print(f"[{self.name}] Starting scrape...")
            jobs = self.scrape()
            print(f"[{self.name}] Found {len(jobs)} jobs")
            return jobs
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
            return []
