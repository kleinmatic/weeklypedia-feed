#!/usr/bin/env python3
"""Generate an RSS feed from the Weeklypedia archive."""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from html import escape
from urllib.request import urlopen

ARCHIVE_URL = "https://weekly.hatnote.com/archive/en/index.html"
BASE_URL = "https://weekly.hatnote.com/archive/en/"
FEED_TITLE = "Weeklypedia"
FEED_DESCRIPTION = "The most edited Wikipedia articles and discussions from the last week"
FEED_LINK = "https://weekly.hatnote.com/"

# Number of recent issues to fetch full content for
FETCH_CONTENT_COUNT = 10


def fetch_url(url):
    """Fetch a URL and return its content."""
    with urlopen(url) as response:
        return response.read().decode("utf-8")


def parse_issues(html):
    """Extract issue links and dates from the archive HTML."""
    pattern = r'<a href="(\d{8}/weeklypedia_\d{8}\.html)">([^<]+)</a>'
    matches = re.findall(pattern, html)

    issues = []
    for path, date_text in matches:
        date_match = re.search(r"(\d{8})", path)
        if date_match:
            date_str = date_match.group(1)
            try:
                pub_date = datetime.strptime(date_str, "%Y%m%d")
                issues.append({
                    "url": BASE_URL + path,
                    "title": f"Weeklypedia - {date_text.strip()}",
                    "date": pub_date,
                    "date_text": date_text.strip(),
                })
            except ValueError:
                continue

    return issues


def extract_content(html):
    """Extract the main content sections from an issue page."""
    # Extract content between <body> tags
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if not body_match:
        return None

    body = body_match.group(1)
    sections = []

    # Pattern: <h2 id="articles">Articles</h2> ... <ol>...</ol>
    # The <ol> may not immediately follow <h2>, so we capture everything up to </ol>
    section_pattern = r'<h2[^>]*>([^<]+)</h2>(.*?<ol[^>]*>.*?</ol>)'
    matches = re.findall(section_pattern, body, re.DOTALL)

    for title, content in matches:
        title = title.strip()
        if title in ['Articles', 'New Articles', 'Discussions']:
            # Extract just the <ol>...</ol> part
            ol_match = re.search(r'<ol[^>]*>.*?</ol>', content, re.DOTALL)
            if ol_match:
                sections.append(f"<h3>{title}</h3>\n{ol_match.group(0)}")

    if sections:
        return "\n".join(sections)

    return None


def fetch_issue_content(url):
    """Fetch an issue page and extract its content."""
    try:
        html = fetch_url(url)
        return extract_content(html)
    except Exception as e:
        print(f"  Warning: Failed to fetch {url}: {e}")
        return None


def generate_rss(issues, max_items=50):
    """Generate RSS 2.0 XML from issue list."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = FEED_TITLE
    ET.SubElement(channel, "link").text = FEED_LINK
    ET.SubElement(channel, "description").text = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text = "en"

    if issues:
        last_build = issues[0]["date"].strftime("%a, %d %b %Y 12:00:00 GMT")
        ET.SubElement(channel, "lastBuildDate").text = last_build

    for issue in issues[:max_items]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = issue["title"]
        ET.SubElement(item, "link").text = issue["url"]
        ET.SubElement(item, "guid").text = issue["url"]
        pub_date = issue["date"].strftime("%a, %d %b %Y 12:00:00 GMT")
        ET.SubElement(item, "pubDate").text = pub_date

        content = issue.get("content")
        if content:
            # Wrap in CDATA for RSS
            desc = ET.SubElement(item, "description")
            desc.text = content
        else:
            ET.SubElement(item, "description").text = (
                f"Weekly summary of the most edited Wikipedia articles and discussions "
                f"for the week ending {issue['date_text']}."
            )

    # Convert to string - we need custom handling for CDATA
    xml_str = ET.tostring(rss, encoding="unicode")

    # Add XML declaration
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str


def main():
    print("Fetching Weeklypedia archive...")
    html = fetch_url(ARCHIVE_URL)

    print("Parsing issues...")
    issues = parse_issues(html)
    print(f"Found {len(issues)} issues")

    # Fetch content for recent issues
    print(f"Fetching content for {FETCH_CONTENT_COUNT} most recent issues...")
    for i, issue in enumerate(issues[:FETCH_CONTENT_COUNT]):
        print(f"  [{i+1}/{FETCH_CONTENT_COUNT}] {issue['date_text']}")
        issue["content"] = fetch_issue_content(issue["url"])
        time.sleep(0.2)  # Be polite to the server

    print("Generating RSS feed...")
    rss_xml = generate_rss(issues)

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_xml)

    print("Written to feed.xml")


if __name__ == "__main__":
    main()
