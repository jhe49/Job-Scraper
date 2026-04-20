import requests
from bs4 import BeautifulSoup
import smtplib
import os
from email.message import EmailMessage

# Configuration
COMPANIES = [
    {"name": "Stripe", "url": "https://stripe.com/jobs/search?q=Software+Engineer"},
    {"name": "Airbnb", "url": "https://careers.airbnb.com/positions/software-engineering/"}
]
CACHE_FILE = "jobs_seen.txt"

def send_email(new_jobs):
    msg = EmailMessage()
    msg.set_content(f"New jobs found:\n\n" + "\n".join(new_jobs))
    msg['Subject'] = "New Job Postings Alert!"
    msg['From'] = os.environ['EMAIL_USER']
    msg['To'] = os.environ['EMAIL_USER']

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(os.environ['EMAIL_USER'], os.environ['EMAIL_PASS'])
        smtp.send_message(msg)

def scrape():
    # Load previously seen jobs
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            seen = set(f.read().splitlines())
    else:
        seen = set()

    found_new = []
    current_titles = []

    for company in COMPANIES:
        response = requests.get(company['url'])
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Note: You'll need to inspect the specific HTML tags for each site
        # This is a generic example; Stripe/Airbnb may require specific selectors
        for job in soup.find_all(['h2', 'h3', 'a']): 
            title = job.get_text().strip()
            if "Engineer" in title and title not in seen:
                found_new.append(f"{company['name']}: {title}")
            current_titles.append(title)

    if found_new:
        send_email(found_new)
        # Update the cache
        with open(CACHE_FILE, "w") as f:
            f.write("\n".join(current_titles))
        return True
    return False

if __name__ == "__main__":
    scrape()