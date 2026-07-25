"""
Flight deal digest.
Reads RSS feeds, keeps posts that match your keywords, skips ones
you've already seen, and writes the result to digest.md
"""

import json
import os
import sys
from datetime import datetime, timezone

import feedparser

# ---------------------------------------------------------------
# EDIT THIS SECTION - everything else you can leave alone
# ---------------------------------------------------------------

FEEDS = [
    "https://www.theflightdeal.com/feed/",
    "https://thriftytraveler.com/feed/",
    "https://www.secretflying.com/feed/",
    "https://www.reddit.com/r/flightdeals/new/.rss",
    "https://www.reddit.com/r/awardtravel/new/.rss",
]

# Keep a post if its title or summary mentions ANY of these.
# Leave the list empty ( KEYWORDS = [] ) to keep everything.
KEYWORDS = [
    "ATL", "Atlanta",
    "Europe", "Portugal", "Lisbon", "Spain", "Italy", "Japan", "Mexico",
]

MAX_ITEMS = 40  # safety cap so one bad feed can't flood the digest

# ---------------------------------------------------------------

SEEN_FILE = "seen.json"
OUT_FILE = "digest.md"
AGENT = "flight-digest/1.0 (personal use)"


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f:
                return set(json.load(f))
        except (json.JSONDecodeError, ValueError):
            print("seen.json was unreadable, starting fresh")
    return set()


def save_seen(seen):
    # keep the file from growing forever
    trimmed = list(seen)[-3000:]
    with open(SEEN_FILE, "w") as f:
        json.dump(trimmed, f, indent=0)


def matches(entry):
    if not KEYWORDS:
        return True
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    return any(k.lower() in text for k in KEYWORDS)


def entry_id(entry, feed_url):
    return entry.get("id") or entry.get("link") or f"{feed_url}:{entry.get('title','')}"


def main():
    seen = load_seen()
    found = {}
    broken = []

    for url in FEEDS:
        try:
            parsed = feedparser.parse(url, agent=AGENT)
        except Exception as e:
            broken.append(f"{url} ({e})")
            continue

        if parsed.bozo and not parsed.entries:
            broken.append(f"{url} (no readable entries)")
            continue

        source = parsed.feed.get("title", url)
        kept = []

        for entry in parsed.entries:
            uid = entry_id(entry, url)
            if uid in seen:
                continue
            if not matches(entry):
                seen.add(uid)  # mark it so we don't re-check forever
                continue
            kept.append({
                "title": entry.get("title", "(no title)").strip(),
                "link": entry.get("link", ""),
            })
            seen.add(uid)

        if kept:
            found[source] = kept[:MAX_ITEMS]

    save_seen(seen)

    total = sum(len(v) for v in found.values())
    if total == 0:
        print("Nothing new today.")
        if broken:
            print("Feeds that failed:", "; ".join(broken))
        sys.exit(0)  # exit 0 = success, just nothing to report

    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    lines = [f"Found {total} new deal post(s).", ""]

    for source, items in found.items():
        lines.append(f"### {source}")
        for item in items:
            lines.append(f"- [{item['title']}]({item['link']})")
        lines.append("")

    if broken:
        lines.append("---")
        lines.append("_Feeds that failed this run:_")
        for b in broken:
            lines.append(f"- {b}")

    with open(OUT_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote {total} items to {OUT_FILE} for {today}")


if __name__ == "__main__":
    main()
