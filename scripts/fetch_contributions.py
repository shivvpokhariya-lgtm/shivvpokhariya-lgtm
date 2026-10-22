#!/usr/bin/env python3
"""Fetch public contribution data — no token needed.

Scrapes https://github.com/users/<user>/contributions (the same public
HTML fragment the profile page itself uses): day cells carry
data-date / data-level, and each cell's <tool-tip> carries the exact
"N contributions on <date>" text. Writes data/contributions.json with
the raw days plus derived stats.

Writes data/contributions.json

Usage:
    python scripts/fetch_contributions.py
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

USER = "shivvpokhariya-lgtm"
URL = f"https://github.com/users/{USER}/contributions"
OUT = "data/contributions.json"
HEADERS = {"User-Agent": "profile-readme-art/1.0 (+github.com/%s)" % USER}


def parse_count(tip_text: str) -> int:
    tip_text = tip_text.strip()
    if tip_text.startswith("No contributions"):
        return 0
    m = re.match(r"(\d+)\s+contributions?", tip_text)
    return int(m.group(1)) if m else 0


def main() -> None:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    tips = {t.get("for", ""): t.get_text(strip=True)
            for t in soup.select("tool-tip[for]")}

    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        d = td.get("data-date")
        if not d:
            continue
        level = int(td.get("data-level", 0) or 0)
        count = parse_count(tips.get(td.get("id", ""), ""))
        days.append({"date": d, "count": count, "level": level})
    if not days:
        print("ERROR: no contribution day cells found — page layout may have changed",
              file=sys.stderr)
        sys.exit(1)
    days.sort(key=lambda x: x["date"])

    total = sum(d["count"] for d in days)

    # page's own "N contributions in the last year" as a cross-check
    page_total = None
    h2 = soup.find("h2", id="js-contribution-activity-description")
    if h2:
        m = re.search(r"([\d,]+)\s+contributions?\s+in the last year",
                      h2.get_text(" ", strip=True))
        if m:
            page_total = int(m.group(1).replace(",", ""))
    if page_total is not None and page_total != total:
        print(f"WARNING: tooltip sum ({total}) != page total ({page_total})",
              file=sys.stderr)

    # current streak (if today is 0, count back from yesterday)
    tail = days[:-1] if days[-1]["count"] == 0 else days
    current_streak = 0
    for d in reversed(tail):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    # longest streak
    longest_streak, run = 0, 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest_streak = max(longest_streak, run)

    best = max(days, key=lambda d: d["count"])
    monthly = {}
    for d in days:
        m = d["date"][:7]
        monthly[m] = monthly.get(m, 0) + d["count"]

    data = {
        "user": USER,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "total": total,
        "page_total": page_total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly_totals": monthly,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT}: {len(days)} days, {total} contributions, "
          f"streak {current_streak}d (longest {longest_streak}d)")


if __name__ == "__main__":
    main()
