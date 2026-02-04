"""Configuration for Job Hunter automation system."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Data files
JOBS_FILE = DATA_DIR / "jobs.json"
MATCHES_FILE = DATA_DIR / "matches.json"
APPLIED_FILE = DATA_DIR / "applied.json"
CV_PROFILE_FILE = DATA_DIR / "cv_profile.json"

# API Keys (from environment/GitHub Secrets)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_TO = os.getenv("EMAIL_TO", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "jobhunter@noreply.com")

# Scraping settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 2  # seconds between requests to same domain
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Matching settings
SCORE_THRESHOLD_HIGH = 70  # Generate cover letter
SCORE_THRESHOLD_LOW = 50   # Include in digest

# Scoring weights
SCORING_WEIGHTS = {
    "title_match": 0.30,
    "location_match": 0.20,
    "skills_overlap": 0.25,
    "experience_fit": 0.15,
    "donor_match": 0.10,
}

# Location scoring
LOCATION_SCORES = {
    "ethiopia": 100,
    "addis ababa": 100,
    "kenya": 90,
    "nairobi": 90,
    "east africa": 80,
    "africa": 70,
    "remote": 70,
    "global": 60,
}

# Gemini API settings
GEMINI_MODEL = "gemini-pro"
MAX_COVER_LETTERS_PER_RUN = 10

# Salary filtering
MIN_SALARY_USD = 3000  # Minimum monthly salary in USD
EXCLUDE_NO_SALARY = False  # If True, exclude jobs without salary info
