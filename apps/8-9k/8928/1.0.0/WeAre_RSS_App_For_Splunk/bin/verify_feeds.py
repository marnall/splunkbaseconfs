#!/usr/bin/env python3
"""Verify RSS and ATOM feed parsing for the modular input helper."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import feedparser
import requests

# Allow importing helper when run from repo root or package/bin
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rss_feed_input_helper import ADDON_NAME, ADDON_VERSION, _entry_id, _serialize_entry  # noqa: E402

FEEDS = {
    "rss": "https://feeds.bbci.co.uk/news/rss.xml",
    "atom": (
        "https://en.wikipedia.org/w/api.php"
        "?action=featuredfeed&feed=featured&feedformat=atom"
    ),
}


def verify_feed(label: str, url: str) -> None:
    print(f"==> Verifying {label.upper()} feed: {url}")
    response = requests.get(url, timeout=30, headers={"User-Agent": f"{ADDON_NAME}/{ADDON_VERSION}"})
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    feed_format = getattr(feed, "version", None) or "unknown"
    print(f"    feed_format={feed_format} entries={len(feed.entries)}")

    if not feed.entries:
        raise RuntimeError(f"{label} feed returned no entries")

    for entry in feed.entries:
        entry_id = _entry_id(entry)
        payload = _serialize_entry(entry, feed_format=feed_format)
        if not entry_id:
            raise RuntimeError(f"{label} entry missing id")
        if not payload.get("title"):
            raise RuntimeError(f"{label} entry missing title: id={entry_id}")

    sample = _serialize_entry(feed.entries[0], feed_format=feed_format)
    print(f"    sample event: {json.dumps(sample, ensure_ascii=False)[:500]}...")
    print(f"    OK: {len(feed.entries)} entries parsed")


def main() -> int:
    for label, url in FEEDS.items():
        verify_feed(label, url)
    print("All feed verifications passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
