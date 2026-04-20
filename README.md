# Job Scraper

Watches the career pages of companies I'm interested in and emails me when a
role matching a target title appears. Runs automatically via GitHub Actions
four times a day.

## How it works

- `scraper.py` queries the public [Greenhouse job board API](https://developers.greenhouse.io/job-board.html)
  for each configured company and filters titles by a substring.
- New postings (never seen before) trigger a Gmail SMTP alert.
- Seen job IDs are persisted to `jobs_seen.json`, which the workflow commits
  back to the repo so state carries across runs.
- `.github/workflows/job_scraper.yaml` runs the scraper on cron four times a
  day (and on demand via "Run workflow").

## Configuration

Edit the top of `scraper.py`:

```python
TITLE_FILTER = "Software Engineer"   # case-insensitive substring match

COMPANIES = [
    {"name": "Anthropic", "slug": "anthropic"},
    {"name": "Figma",     "slug": "figma"},
]
```

The `slug` is the company's Greenhouse board id — you can confirm a slug by
opening `https://boards.greenhouse.io/<slug>` in a browser. Any company that
uses Greenhouse (e.g. Anthropic, Figma, Discord, Notion, Databricks, OpenAI)
works out of the box.

## GitHub Secrets

Add these under **Settings → Secrets and variables → Actions → New repository secret**:

| Name         | Value                                                                       |
| ------------ | --------------------------------------------------------------------------- |
| `EMAIL_USER` | The Gmail address that sends the alert (e.g. `you@gmail.com`)               |
| `EMAIL_PASS` | A Gmail **App Password** — not your account password. [Create one here](https://myaccount.google.com/apppasswords) (requires 2-Step Verification). |
| `EMAIL_TO`   | *(optional)* address that receives alerts. Defaults to `EMAIL_USER`.        |

## Schedule

Cron: `0 1,13,17,21 * * *` — runs at 01:00, 13:00, 17:00, 21:00 UTC
(roughly 6 AM / 10 AM / 2 PM / 6 PM US Pacific). Adjust the cron string in
`.github/workflows/job_scraper.yaml` to taste.

## Testing locally

```bash
pip install -r requirements.txt
EMAIL_USER=you@gmail.com EMAIL_PASS='app-password' python scraper.py
```

Delete `jobs_seen.json` to force every current match to count as "new".
