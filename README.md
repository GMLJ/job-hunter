# Job Hunter

Automated job discovery and application preparation system.

## Features

- **Multi-source scraping**: Monitors 10+ job boards including ReliefWeb, UNJobs, DevEx, and more
- **Smart matching**: Scores jobs against your CV profile using TF-IDF similarity
- **Cover letter generation**: Uses Claude AI to generate tailored cover letters
- **Email digests**: Daily notifications of new matching positions
- **GitHub Actions**: Fully automated with free tier services

## Quick Start

### 1. Clone and Install

```bash
cd job-hunter
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Your Profile

Edit `data/cv_profile.json` with your details:
- Target roles and locations
- Skills and experience
- Previous organizations and donors

### 3. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="your-key"
export SENDGRID_API_KEY="your-key"
export EMAIL_TO="your@email.com"
```

### 4. Run Locally

```bash
# Full pipeline
python main.py run

# Individual commands
python main.py scrape    # Scrape all sources
python main.py match     # Score jobs
python main.py generate  # Create cover letters
python main.py notify    # Send email digest
python main.py test-email  # Test email configuration
```

## GitHub Actions Setup

1. Create a new GitHub repository
2. Push this code to the repository
3. Add the following secrets in Settings > Secrets:
   - `ANTHROPIC_API_KEY`
   - `SENDGRID_API_KEY`
   - `EMAIL_TO`
   - `EMAIL_FROM` (optional)

The workflows will:
- Scrape jobs every 6 hours
- Send daily digest at 7am EAT

## Job Sources

| Source | Type | Coverage |
|--------|------|----------|
| ReliefWeb | API | Global humanitarian |
| EthioJobs | Web | Ethiopia |
| UNJobs | Web | UN system |
| DevEx | Web | Development sector |
| DevelopmentAid | Web | Development sector |

## Scoring Algorithm

Jobs are scored 0-100 based on:

| Factor | Weight |
|--------|--------|
| Title match | 30% |
| Location match | 20% |
| Skills overlap (TF-IDF) | 25% |
| Experience fit | 15% |
| Donor match | 10% |

**Thresholds:**
- ≥70%: High match, cover letter generated
- 50-69%: Good match, included in digest
- <50%: Skipped

## Project Structure

```
job-hunter/
├── .github/workflows/    # GitHub Actions
├── scrapers/             # Job scrapers
├── matcher/              # Scoring engine
├── generator/            # Cover letter AI
├── notifier/             # Email system
├── data/                 # Job database
├── templates/            # Email templates
├── config.py             # Configuration
└── main.py               # Entry point
```

## Cost

**$0/month** using free tiers:
- GitHub Actions: Free for public repos
- SendGrid: 100 emails/day free
- Claude API: ~$0.01 per cover letter (pay as you go)

Estimated Claude API cost: $1-3/month for ~100 cover letters

## License

MIT
