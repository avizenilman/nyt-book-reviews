#!/usr/bin/env python3
"""Fetch NYT book reviews from RSS, filter to actual reviews, generate static site."""

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

import feedparser
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "reviews.json"
DOCS_DIR = ROOT / "docs"
TEMPLATES_DIR = ROOT / "templates"
RSS_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Books/Review.xml"


def load_reviews() -> list[dict]:
    """Load accumulated reviews from JSON."""
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return []


def save_reviews(reviews: list[dict]) -> None:
    """Save reviews to JSON."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(reviews, indent=2, ensure_ascii=False) + "\n")


def parse_book_title(raw_title: str) -> str:
    """Extract book title from 'Book Review: ...' format.

    Handles patterns like:
      Book Review: 'The Title,' by Author Name
      Book Review: 'The Title' by Author Name
      Book Review: The Title
    """
    # Strip the "Book Review: " prefix
    title = re.sub(r"^Book Review:\s*", "", raw_title)
    return title.strip()


def extract_byline(entry: dict) -> str:
    """Extract reviewer byline from the entry."""
    # feedparser puts dc:creator in author
    return entry.get("author", "")


def fetch_rss() -> str:
    """Fetch RSS feed XML. Uses curl to avoid Python SSL issues on macOS."""
    result = subprocess.run(
        ["curl", "-sS", RSS_URL],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to fetch RSS: {result.stderr}")
    return result.stdout


def fetch_and_filter() -> list[dict]:
    """Fetch RSS feed and return only actual book reviews."""
    xml = fetch_rss()
    feed = feedparser.parse(xml)
    reviews = []

    for entry in feed.entries:
        title = entry.get("title", "")
        if not title.startswith("Book Review:"):
            continue

        # Parse published date
        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            published = dt.strftime("%Y-%m-%d")

        reviews.append({
            "url": entry.get("link", ""),
            "raw_title": title,
            "book_title": parse_book_title(title),
            "byline": extract_byline(entry),
            "description": entry.get("summary", ""),
            "published": published,
        })

    return reviews


def merge_reviews(existing: list[dict], new: list[dict]) -> list[dict]:
    """Merge new reviews into existing, deduplicating by URL."""
    seen_urls = {r["url"] for r in existing}
    merged = list(existing)
    added = 0

    for review in new:
        if review["url"] and review["url"] not in seen_urls:
            merged.append(review)
            seen_urls.add(review["url"])
            added += 1

    # Sort by published date, newest first
    merged.sort(key=lambda r: r.get("published", ""), reverse=True)

    print(f"  {len(new)} reviews in feed, {added} new, {len(merged)} total")
    return merged


def group_by_date(reviews: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group reviews by published date for display."""
    groups: dict[str, list[dict]] = {}
    for r in reviews:
        date = r.get("published", "Unknown")
        if date:
            # Format as readable date
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                display_date = dt.strftime("%B %-d, %Y")
            except ValueError:
                display_date = date
        else:
            display_date = "Unknown"
        groups.setdefault(display_date, []).append(r)

    return list(groups.items())


def generate_site(reviews: list[dict]) -> None:
    """Generate static HTML site."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("index.html")

    now = datetime.now(timezone.utc).strftime("%B %-d, %Y at %-I:%M %p UTC")
    html = template.render(
        reviews=reviews,
        grouped_reviews=group_by_date(reviews),
        last_updated=now,
    )

    (DOCS_DIR / "index.html").write_text(html)
    print(f"  Generated docs/index.html ({len(reviews)} reviews)")


def generate_feed(reviews: list[dict]) -> None:
    """Generate RSS feed XML (last 30 days of reviews)."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "NYT Book Reviews (Filtered)"
    SubElement(channel, "link").text = "https://avizenilman.github.io/nyt-book-reviews/"
    SubElement(channel, "description").text = (
        "Actual book reviews from the New York Times, filtered from the noisy Books RSS feed."
    )
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    # Last 30 days only
    cutoff_str = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    count = 0
    for r in reviews:
        if r.get("published", "") < cutoff_str:
            continue
        item = SubElement(channel, "item")
        SubElement(item, "title").text = r["book_title"]
        SubElement(item, "link").text = r["url"]
        SubElement(item, "description").text = r.get("description", "")
        if r.get("byline"):
            SubElement(item, "author").text = r["byline"]
        if r.get("published"):
            # Convert to RFC 822
            try:
                dt = datetime.strptime(r["published"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                SubElement(item, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
            except ValueError:
                pass
        SubElement(item, "guid", isPermaLink="true").text = r["url"]
        count += 1

    tree = ElementTree(rss)
    feed_path = DOCS_DIR / "feed.xml"
    tree.write(feed_path, encoding="unicode", xml_declaration=True)
    print(f"  Generated docs/feed.xml ({count} recent reviews)")


def main():
    print("NYT Book Reviews Builder")
    print("=" * 40)

    print("\n1. Loading existing reviews...")
    existing = load_reviews()
    print(f"  {len(existing)} reviews in database")

    print("\n2. Fetching NYT RSS feed...")
    new_reviews = fetch_and_filter()

    print("\n3. Merging reviews...")
    all_reviews = merge_reviews(existing, new_reviews)

    print("\n4. Saving database...")
    save_reviews(all_reviews)

    print("\n5. Generating website...")
    generate_site(all_reviews)

    print("\n6. Generating RSS feed...")
    generate_feed(all_reviews)

    print("\nDone!")


if __name__ == "__main__":
    main()
