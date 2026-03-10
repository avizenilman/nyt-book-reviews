# NYT Book Reviews

A filtered feed of actual New York Times book reviews, updated daily.

**Live site**: [avizenilman.github.io/nyt-book-reviews](https://avizenilman.github.io/nyt-book-reviews/)

## What This Does

The NYT's Books RSS feed mixes actual book reviews with industry news, obituaries, historical reprints, best-of lists, and feature articles. This project filters it down to just the reviews.

**How it works**: A daily GitHub Actions job fetches the RSS feed, keeps only items with "Book Review:" in the title, and generates a static site served by GitHub Pages.

## Running Locally

```bash
pip install -r requirements.txt
python build.py
open docs/index.html
```
