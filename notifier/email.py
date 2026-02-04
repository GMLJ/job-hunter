"""Email notification system using SendGrid."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

import config
from scrapers.base import Job


class EmailNotifier:
    """Send email digest of job matches."""

    def __init__(self):
        """Initialize SendGrid client."""
        self.client = None
        if config.SENDGRID_API_KEY:
            self.client = SendGridAPIClient(api_key=config.SENDGRID_API_KEY)

    def _format_job_html(self, job: Job, include_cover_letter: bool = False) -> str:
        """Format a single job for HTML email."""
        score = job.score or 0

        # Determine badge color
        if score >= 70:
            badge = "HIGH MATCH"
            color = "#22c55e"  # Green
        elif score >= 50:
            badge = "GOOD MATCH"
            color = "#eab308"  # Yellow
        else:
            badge = "MATCH"
            color = "#6b7280"  # Gray

        # Cover letter section
        cover_letter_link = ""
        if include_cover_letter and job.cover_letter_path:
            cover_letter_link = f'<br><a href="{job.cover_letter_path}" style="color: #3b82f6;">View Cover Letter Draft</a>'

        return f"""
        <div style="border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; background: #fff;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                <span style="background: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                    {badge} ({score:.0f}%)
                </span>
            </div>
            <h3 style="margin: 8px 0; color: #1f2937;">
                <a href="{job.url}" style="color: #1f2937; text-decoration: none;">{job.title}</a>
            </h3>
            <p style="margin: 4px 0; color: #4b5563;">
                <strong>{job.organization}</strong>
            </p>
            <p style="margin: 4px 0; color: #6b7280; font-size: 14px;">
                📍 {job.location or 'Location not specified'}
                {f' | ⏰ Deadline: {job.deadline}' if job.deadline else ''}
            </p>
            <div style="margin-top: 12px;">
                <a href="{job.url}" style="background: #3b82f6; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-size: 14px;">
                    View Job
                </a>
                {cover_letter_link}
            </div>
        </div>
        """

    def _build_digest_html(
        self,
        high_matches: list[Job],
        good_matches: list[Job],
        stats: dict
    ) -> str:
        """Build the full HTML email digest."""
        date_str = datetime.now().strftime("%B %d, %Y")

        # High matches section
        high_matches_html = ""
        if high_matches:
            high_matches_html = f"""
            <h2 style="color: #22c55e; border-bottom: 2px solid #22c55e; padding-bottom: 8px;">
                🟢 High Matches - Cover Letters Ready ({len(high_matches)})
            </h2>
            {''.join(self._format_job_html(job, include_cover_letter=True) for job in high_matches)}
            """

        # Good matches section
        good_matches_html = ""
        if good_matches:
            good_matches_html = f"""
            <h2 style="color: #eab308; border-bottom: 2px solid #eab308; padding-bottom: 8px; margin-top: 24px;">
                🟡 Good Matches ({len(good_matches)})
            </h2>
            {''.join(self._format_job_html(job) for job in good_matches)}
            """

        # Stats section
        stats_html = f"""
        <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; margin-top: 24px;">
            <h3 style="margin: 0 0 12px 0; color: #374151;">📊 Stats</h3>
            <ul style="margin: 0; padding-left: 20px; color: #4b5563;">
                <li>Jobs scanned: {stats.get('total_scanned', 0)}</li>
                <li>High matches: {stats.get('high_matches', 0)}</li>
                <li>Good matches: {stats.get('good_matches', 0)}</li>
                <li>Cover letters generated: {stats.get('cover_letters', 0)}</li>
            </ul>
        </div>
        """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 24px; color: white;">
                    <h1 style="margin: 0; font-size: 24px;">🎯 Job Match Digest</h1>
                    <p style="margin: 8px 0 0 0; opacity: 0.9;">{date_str}</p>
                </div>
                <div style="padding: 24px;">
                    {high_matches_html if high_matches_html else '<p style="color: #6b7280;">No high matches today.</p>'}
                    {good_matches_html}
                    {stats_html}
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
                    <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                        This digest was automatically generated by Job Hunter.
                        <br>Manage your preferences in the repository settings.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def send_digest(
        self,
        high_matches: list[Job],
        good_matches: list[Job],
        stats: dict,
        to_email: Optional[str] = None
    ) -> bool:
        """Send the job digest email."""
        if not self.client:
            print("[Email] No SendGrid API key configured")
            return False

        to_email = to_email or config.EMAIL_TO
        if not to_email:
            print("[Email] No recipient email configured")
            return False

        total_matches = len(high_matches) + len(good_matches)
        subject = f"🎯 {total_matches} New Job Matches - {datetime.now().strftime('%b %d, %Y')}"

        html_content = self._build_digest_html(high_matches, good_matches, stats)

        message = Mail(
            from_email=Email(config.EMAIL_FROM, "Job Hunter"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )

        try:
            response = self.client.send(message)
            print(f"[Email] Sent successfully (status: {response.status_code})")
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"[Email] Error sending: {e}")
            return False

    def send_test_email(self, to_email: Optional[str] = None) -> bool:
        """Send a test email to verify configuration."""
        test_job = Job(
            id="test123",
            title="Program Director - Test Position",
            organization="Test Organization",
            location="Addis Ababa, Ethiopia",
            description="This is a test job posting.",
            url="https://example.com/job/test",
            source="test",
            score=85,
        )

        return self.send_digest(
            high_matches=[test_job],
            good_matches=[],
            stats={"total_scanned": 100, "high_matches": 1, "good_matches": 5, "cover_letters": 1},
            to_email=to_email
        )
