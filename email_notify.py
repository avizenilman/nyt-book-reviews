#!/usr/bin/env python3
"""Send email notifications for new NYT book reviews."""

import argparse
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
NEW_REVIEWS_FILE = ROOT / "data" / "new_reviews.json"
TEMPLATES_DIR = ROOT / "templates"


def load_new_reviews() -> list[dict]:
    """Load new reviews written by build.py."""
    if NEW_REVIEWS_FILE.exists():
        return json.loads(NEW_REVIEWS_FILE.read_text())
    return []


def build_email_html(new_reviews: list[dict], today: str) -> str:
    """Render the email HTML template."""
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("email.html")
    return template.render(reviews=new_reviews, date=today)


def send_email(
    html: str,
    subject: str,
    sender_email: str,
    app_password: str,
    subscribers: list[str],
) -> None:
    """Send HTML email via Gmail SMTP SSL."""
    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)

            for recipient in subscribers:
                msg = MIMEText(html, "html")
                msg["Subject"] = subject
                msg["From"] = f"NYT Book Reviews <{sender_email}>"
                msg["To"] = recipient
                server.sendmail(sender_email, recipient, msg.as_string())
                print(f"  Sent to {recipient[:3]}***")
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Gmail authentication failed. Check SENDER_EMAIL and GMAIL_APP_PASSWORD.", file=sys.stderr)
        sys.exit(1)
    except smtplib.SMTPException as e:
        print(f"ERROR: Failed to send email: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Send NYT book review email notifications")
    parser.add_argument("--dry-run", action="store_true", help="Print email HTML instead of sending")
    args = parser.parse_args()

    print("NYT Book Reviews Email Notifier")
    print("=" * 40)

    # Load new reviews (written by build.py)
    new_reviews = load_new_reviews()
    print(f"\n1. {len(new_reviews)} new reviews found")

    if not new_reviews:
        print("\n   No new reviews — skipping email.")
        return

    # Parse subscribers
    subscribers_raw = os.environ.get("SUBSCRIBERS", "")
    subscribers = [s.strip() for s in subscribers_raw.split(",") if s.strip()]

    if not subscribers:
        print("\nNo subscribers configured. Set SUBSCRIBERS env var (comma-separated emails).")
        return

    # Build email
    now = datetime.now(timezone.utc)
    today = now.strftime("%B %-d, %Y")
    html = build_email_html(new_reviews, today)
    subject = f"NYT Book Reviews: {len(new_reviews)} new review{'s' if len(new_reviews) != 1 else ''} — {today}"

    if args.dry_run:
        print(f"\n2. DRY RUN — Subject: {subject}")
        print(f"   Would send to: {len(subscribers)} subscriber(s)")
        print("\n--- EMAIL HTML ---")
        print(html)
        print("--- END ---")
        return

    # Send
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender_email or not app_password:
        print("\nERROR: SENDER_EMAIL and GMAIL_APP_PASSWORD environment variables required.", file=sys.stderr)
        sys.exit(1)

    print(f"\n2. Sending to {len(subscribers)} subscriber(s)...")
    send_email(html, subject, sender_email, app_password, subscribers)

    print("\nDone!")


if __name__ == "__main__":
    main()
