# NYT Book Reviews

A filtered feed of actual New York Times book reviews, updated daily.

**Live site**: [avizenilman.github.io/nyt-book-reviews](https://avizenilman.github.io/nyt-book-reviews/)

## What This Does

The NYT's Books RSS feed mixes actual book reviews with industry news, obituaries, historical reprints, best-of lists, and feature articles. This project filters it down to just the reviews.

**How it works**: A daily GitHub Actions job fetches the RSS feed, keeps only items with "Book Review:" in the title, and generates a static site served by GitHub Pages. When new reviews are found, subscribers get an email.

## Email Notifications

Subscribers receive a daily email whenever new reviews are found. No email is sent on days with nothing new.

Emails are sent via Gmail SMTP. Three GitHub Actions secrets are required:

- `SENDER_EMAIL` — Gmail address to send from
- `GMAIL_APP_PASSWORD` — [Gmail app password](https://myaccount.google.com/apppasswords)
- `SUBSCRIBERS` — comma-separated recipient emails

To add or remove subscribers, update the `SUBSCRIBERS` secret in the repo's Settings > Secrets > Actions.

## Running Locally

```bash
pip install -r requirements.txt
python build.py
open docs/index.html
```

To test email locally:

```bash
export SUBSCRIBERS="you@example.com"
python email_notify.py --dry-run
```
