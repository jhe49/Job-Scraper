#!/usr/bin/env python3
"""Daily job scraper.

Checks each configured company's public Greenhouse job board for postings
whose title contains TITLE_FILTER, and emails the owner whenever a new one
appears. State is persisted in jobs_seen.json so we don't re-notify.

Required environment variables:
    EMAIL_USER  - Gmail address that sends the alert
    EMAIL_PASS  - Gmail app password (NOT the account password)
    EMAIL_TO    - (optional) destination address; defaults to EMAIL_USER
"""
from __future__ import annotations

import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

import requests

# ---- Configuration -------------------------------------------------------

# Case-insensitive substring filter applied to job titles.
TITLE_FILTER = "Software Engineer"

# Companies to watch. `slug` is the company's Greenhouse board identifier
# (visit https://boards.greenhouse.io/<slug> to confirm). The Greenhouse
# JSON API is public and doesn't require auth, which makes it far more
# reliable than screen-scraping JS-rendered career pages.
COMPANIES = [
    {"name": "Anthropic", "slug": "anthropic"},
    {"name": "Figma",     "slug": "figma"},
]

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
CACHE_FILE = Path("jobs_seen.json")
REQUEST_TIMEOUT = 30


# ---- Scraping ------------------------------------------------------------

def fetch_jobs(company: dict) -> list[dict]:
    url = GREENHOUSE_API.format(slug=company["slug"])
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def matching_jobs(company: dict) -> list[dict]:
    needle = TITLE_FILTER.lower()
    results = []
    for job in fetch_jobs(company):
        title = job.get("title", "")
        if needle in title.lower():
            results.append({
                "id": str(job["id"]),
                "company": company["name"],
                "title": title,
                "location": (job.get("location") or {}).get("name", ""),
                "url": job.get("absolute_url", ""),
            })
    return results


# ---- Cache ---------------------------------------------------------------

def load_seen() -> set[str]:
    if not CACHE_FILE.exists():
        return set()
    try:
        return set(json.loads(CACHE_FILE.read_text()))
    except (json.JSONDecodeError, ValueError):
        return set()


def save_seen(ids: set[str]) -> None:
    CACHE_FILE.write_text(json.dumps(sorted(ids), indent=2) + "\n")


# ---- Email ---------------------------------------------------------------

def send_email(new_jobs: list[dict]) -> None:
    user = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    to = os.environ.get("EMAIL_TO") or user

    lines = [f"Found {len(new_jobs)} new job(s) matching '{TITLE_FILTER}':", ""]
    for j in new_jobs:
        lines.append(f"- [{j['company']}] {j['title']}")
        if j["location"]:
            lines.append(f"    Location: {j['location']}")
        if j["url"]:
            lines.append(f"    {j['url']}")
        lines.append("")

    msg = EmailMessage()
    msg["Subject"] = f"[Job Alert] {len(new_jobs)} new {TITLE_FILTER} role(s)"
    msg["From"] = user
    msg["To"] = to
    msg.set_content("\n".join(lines))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


# ---- Main ----------------------------------------------------------------

def main() -> int:
    seen = load_seen()
    current_ids: set[str] = set()
    new_jobs: list[dict] = []
    any_failure = False

    for company in COMPANIES:
        try:
            jobs = matching_jobs(company)
        except Exception as exc:
            # Don't drop cached IDs for a company we couldn't reach, or we'd
            # flood the inbox on the next successful run.
            print(f"[warn] failed to scrape {company['name']}: {exc}", file=sys.stderr)
            any_failure = True
            continue

        print(f"{company['name']}: {len(jobs)} matching role(s)")
        for j in jobs:
            current_ids.add(j["id"])
            if j["id"] not in seen:
                new_jobs.append(j)

    if new_jobs:
        print(f"Sending email for {len(new_jobs)} new job(s)...")
        send_email(new_jobs)
    else:
        print("No new jobs.")

    # Union with previous cache so transient API failures don't cause
    # re-notification when a role reappears.
    save_seen(seen | current_ids)

    return 1 if any_failure and not current_ids else 0


if __name__ == "__main__":
    sys.exit(main())
