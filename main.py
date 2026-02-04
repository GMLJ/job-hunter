#!/usr/bin/env python3
"""
Job Hunter - Automated job discovery and application preparation system.

Usage:
    python main.py scrape      # Scrape all job sources
    python main.py match       # Score and filter jobs
    python main.py generate    # Generate cover letters for high matches
    python main.py notify      # Send email digest
    python main.py run         # Run full pipeline
    python main.py test-email  # Send test email
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import config
from scrapers import get_all_scrapers, Job
from matcher import JobScorer, CVProfile
from generator import CoverLetterGenerator
from notifier import EmailNotifier


def load_jobs() -> list[Job]:
    """Load jobs from JSON file."""
    if not config.JOBS_FILE.exists():
        return []

    with open(config.JOBS_FILE, "r") as f:
        data = json.load(f)

    return [Job.from_dict(j) for j in data.get("jobs", [])]


def save_jobs(jobs: list[Job]):
    """Save jobs to JSON file."""
    data = {
        "jobs": [job.to_dict() for job in jobs],
        "last_updated": datetime.utcnow().isoformat()
    }

    with open(config.JOBS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_matches() -> list[Job]:
    """Load matched jobs from JSON file."""
    if not config.MATCHES_FILE.exists():
        return []

    with open(config.MATCHES_FILE, "r") as f:
        data = json.load(f)

    return [Job.from_dict(j) for j in data.get("matches", [])]


def save_matches(jobs: list[Job]):
    """Save matched jobs to JSON file."""
    data = {
        "matches": [job.to_dict() for job in jobs],
        "last_updated": datetime.utcnow().isoformat()
    }

    with open(config.MATCHES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def cmd_scrape():
    """Scrape jobs from all sources."""
    print("=" * 60)
    print("SCRAPING JOBS")
    print("=" * 60)

    # Load existing jobs for deduplication
    existing_jobs = load_jobs()
    existing_ids = {job.id for job in existing_jobs}

    all_jobs = []
    scrapers = get_all_scrapers()

    for scraper in scrapers:
        jobs = scraper.run()
        all_jobs.extend(jobs)

    # Deduplicate
    new_jobs = []
    for job in all_jobs:
        if job.id not in existing_ids:
            new_jobs.append(job)
            existing_ids.add(job.id)

    print(f"\nTotal jobs scraped: {len(all_jobs)}")
    print(f"New jobs: {len(new_jobs)}")

    # Merge with existing
    all_jobs = existing_jobs + new_jobs
    save_jobs(all_jobs)

    print(f"Total jobs in database: {len(all_jobs)}")
    return new_jobs


def cmd_match():
    """Score and filter jobs."""
    print("=" * 60)
    print("MATCHING JOBS")
    print("=" * 60)

    jobs = load_jobs()
    if not jobs:
        print("No jobs to match. Run 'scrape' first.")
        return []

    scorer = JobScorer()
    scored_jobs = scorer.score_jobs(jobs)

    # Save all jobs with scores
    save_jobs(scored_jobs)

    # Filter matches
    matches = scorer.filter_matches(scored_jobs)
    matches.sort(key=lambda j: j.score or 0, reverse=True)

    save_matches(matches)

    high_matches = [j for j in matches if (j.score or 0) >= config.SCORE_THRESHOLD_HIGH]
    good_matches = [j for j in matches if config.SCORE_THRESHOLD_LOW <= (j.score or 0) < config.SCORE_THRESHOLD_HIGH]

    print(f"\nTotal jobs scored: {len(jobs)}")
    print(f"High matches (>={config.SCORE_THRESHOLD_HIGH}%): {len(high_matches)}")
    print(f"Good matches (>={config.SCORE_THRESHOLD_LOW}%): {len(good_matches)}")

    # Print top matches
    print("\nTop 10 Matches:")
    for i, job in enumerate(matches[:10], 1):
        print(f"  {i}. [{job.score:.0f}%] {job.title} - {job.organization}")

    return matches


def cmd_generate():
    """Generate cover letters for high-scoring jobs."""
    print("=" * 60)
    print("GENERATING COVER LETTERS")
    print("=" * 60)

    matches = load_matches()
    if not matches:
        print("No matches found. Run 'match' first.")
        return []

    generator = CoverLetterGenerator()
    results = generator.generate_for_high_matches(matches)

    # Update matches with cover letter paths
    save_matches(matches)

    generated = [r for r in results if r[1] is not None]
    print(f"\nCover letters generated: {len(generated)}")

    for job, path in generated:
        print(f"  - {job.title}: {path}")

    return results


def cmd_notify():
    """Send email digest of job matches."""
    print("=" * 60)
    print("SENDING EMAIL DIGEST")
    print("=" * 60)

    matches = load_matches()
    if not matches:
        print("No matches to notify about.")
        return False

    jobs = load_jobs()

    high_matches = [j for j in matches if (j.score or 0) >= config.SCORE_THRESHOLD_HIGH]
    good_matches = [j for j in matches if config.SCORE_THRESHOLD_LOW <= (j.score or 0) < config.SCORE_THRESHOLD_HIGH]

    stats = {
        "total_scanned": len(jobs),
        "high_matches": len(high_matches),
        "good_matches": len(good_matches),
        "cover_letters": len([j for j in matches if j.cover_letter_path]),
    }

    notifier = EmailNotifier()
    success = notifier.send_digest(high_matches[:10], good_matches[:10], stats)

    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")

    return success


def cmd_run():
    """Run the full pipeline."""
    print("=" * 60)
    print("JOB HUNTER - FULL PIPELINE")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 60)

    # Step 1: Scrape
    new_jobs = cmd_scrape()
    print()

    # Step 2: Match
    matches = cmd_match()
    print()

    # Step 3: Generate cover letters
    results = cmd_generate()
    print()

    # Step 4: Send notification (only if there are matches)
    if matches:
        cmd_notify()

    print()
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print(f"Finished at: {datetime.now().isoformat()}")
    print("=" * 60)


def cmd_test_email():
    """Send a test email."""
    print("Sending test email...")
    notifier = EmailNotifier()
    success = notifier.send_test_email()

    if success:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email. Check your SENDGRID_API_KEY and EMAIL_TO settings.")


def main():
    parser = argparse.ArgumentParser(
        description="Job Hunter - Automated job discovery system"
    )
    parser.add_argument(
        "command",
        choices=["scrape", "match", "generate", "notify", "run", "test-email"],
        help="Command to run"
    )

    args = parser.parse_args()

    commands = {
        "scrape": cmd_scrape,
        "match": cmd_match,
        "generate": cmd_generate,
        "notify": cmd_notify,
        "run": cmd_run,
        "test-email": cmd_test_email,
    }

    try:
        commands[args.command]()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
