"""Cover letter generator using Claude API."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

import config
from scrapers.base import Job
from matcher.profile import CVProfile


class CoverLetterGenerator:
    """Generate tailored cover letters using Claude API."""

    def __init__(self, profile: Optional[CVProfile] = None):
        """Initialize with CV profile."""
        self.profile = profile or CVProfile.load()
        self.client = None
        if config.ANTHROPIC_API_KEY:
            self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

        # Ensure output directory exists
        self.output_dir = config.DATA_DIR / "cover_letters"
        self.output_dir.mkdir(exist_ok=True)

    def _get_prompt(self, job: Job) -> str:
        """Generate the prompt for Claude."""
        return f"""You are a professional cover letter writer. Write a compelling cover letter for the following job application.

## Candidate Profile
- Name: {self.profile.name}
- Years of Experience: {self.profile.years_experience}
- Key Skills: {', '.join(self.profile.skills[:10])}
- Sectors: {', '.join(self.profile.sectors)}
- Languages: {', '.join(self.profile.languages)}
- Certifications: {', '.join(self.profile.certifications)}
- Previous Organizations: {', '.join(self.profile.organizations_worked)}
- Donor Experience: {', '.join(self.profile.donors_experience)}

## Job Details
- Title: {job.title}
- Organization: {job.organization}
- Location: {job.location}
- Job Description:
{job.description[:3000]}

## Instructions
1. Write a professional cover letter (300-400 words)
2. Address specific requirements from the job description
3. Highlight relevant experience from the candidate's background
4. Show enthusiasm for the organization's mission
5. Be specific - avoid generic statements
6. Use a professional but warm tone
7. Include a strong opening and closing

Format the letter with proper structure:
- Opening paragraph (why this role/organization)
- 1-2 body paragraphs (relevant experience and skills)
- Closing paragraph (call to action)

Do NOT include:
- Placeholder brackets like [Organization Name]
- Generic phrases like "I am writing to apply"
- The date or address header

Start directly with "Dear Hiring Manager," or "Dear [Position] Selection Committee,"
"""

    def generate(self, job: Job) -> Optional[str]:
        """Generate a cover letter for a job."""
        if not self.client:
            print("[CoverLetter] No API key configured, skipping generation")
            return None

        try:
            message = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": self._get_prompt(job)}
                ]
            )

            cover_letter = message.content[0].text
            return cover_letter

        except Exception as e:
            print(f"[CoverLetter] Error generating: {e}")
            return None

    def generate_and_save(self, job: Job) -> Optional[Path]:
        """Generate cover letter and save to file."""
        cover_letter = self.generate(job)

        if not cover_letter:
            return None

        # Generate filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in job.title)
        safe_title = safe_title[:50].strip().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d")
        filename = f"{timestamp}_{safe_title}_{job.id}.md"

        filepath = self.output_dir / filename

        # Write cover letter with metadata
        content = f"""# Cover Letter: {job.title}

**Organization:** {job.organization}
**Location:** {job.location}
**Job URL:** {job.url}
**Generated:** {datetime.now().isoformat()}
**Match Score:** {job.score}%

---

{cover_letter}

---
*This cover letter was auto-generated. Please review and customize before submitting.*
"""

        with open(filepath, "w") as f:
            f.write(content)

        return filepath

    def generate_for_high_matches(
        self, jobs: list[Job], threshold: float = None
    ) -> list[tuple[Job, Optional[Path]]]:
        """Generate cover letters for jobs above threshold."""
        threshold = threshold or config.SCORE_THRESHOLD_HIGH
        results = []
        generated_count = 0

        for job in jobs:
            if (job.score or 0) < threshold:
                continue

            if generated_count >= config.MAX_COVER_LETTERS_PER_RUN:
                print(f"[CoverLetter] Reached max {config.MAX_COVER_LETTERS_PER_RUN} letters per run")
                break

            print(f"[CoverLetter] Generating for: {job.title} ({job.score}%)")
            filepath = self.generate_and_save(job)

            if filepath:
                job.cover_letter_path = str(filepath)
                generated_count += 1

            results.append((job, filepath))

        return results
