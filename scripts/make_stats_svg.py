#!/usr/bin/env python3
"""Generate an Avi-style GitHub stats panel SVG.

Reads data/contributions.json and renders a terminal-window stats panel:
  $ current streak / $ longest streak
  $ contributions / $ active days
  $ best day / $ avg per active day
  $ contributions / month (bar chart)

Writes stats.svg
"""
import json
from datetime import datetime, timedelta
from collections import defaultdict

DATA = "data/contributions.json"
OUT = "stats.svg"

W, H = 460, 560
BG = "#0d1117"
CARD_BG = "#161b22"
BORDER = "#30363d"
DIM = "#8b949e"
BRIGHT = "#f0f6fc"
GREEN = "#3fb950"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def load_stats():
    data = json.load(open(DATA))
    days = sorted(data["days"], key=lambda d: d["date"])
    date_to_count = {d["date"]: d["count"] for d in days}
    total = data["total"]

    active = [d for d in days if d["count"] > 0]
    best = max(days, key=lambda d: d["count"])

    # current streak
    today = datetime.now().date()
    d = today
    if date_to_count.get(d.isoformat(), 0) == 0:
        d -= timedelta(days=1)
    cur_streak = 0
    sd = d
    while date_to_count.get(sd.isoformat(), 0) > 0:
        cur_streak += 1
        sd -= timedelta(days=1)
    cur_start = sd + timedelta(days=1)

    # longest streak
    longest, cur, best_start, cur_start2 = 0, 0, None, None
    for day in days:
        if day["count"] > 0:
            if cur == 0:
                cur_start2 = day["date"]
            cur += 1
            if cur > longest:
                longest, best_start = cur, cur_start2
        else:
            cur = 0
    ls = datetime.fromisoformat(best_start).date()
    le = ls + timedelta(days=longest - 1)

    # monthly (last 12 months)
    monthly = defaultdict(int)
    for d in days:
        monthly[d["date"][:7]] += d["count"]
    # last 12 months ending this month
    now = datetime.now()
    months = []
    for i in range(11, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y}-{m:02d}"
        label = datetime(y, m, 1).strftime("%b")[0]  # first letter
        months.append((label, monthly.get(key, 0)))

    return {
        "total": total,
        "active_days": len(active),
        "total_days": 365,  # a year, not the 369-day calendar range
        "best_count": best["count"],
        "best_date": datetime.fromisoformat(best["date"]).strftime("%b %d"),
        "cur_streak": cur_streak,
        "cur_range": f"{cur_start.strftime('%b %d')} - {d.strftime('%b %d')}" if cur_streak > 1 else cur_start.strftime("%b %d"),
        "long_streak": longest,
        "long_range": f"{ls.strftime('%b %d')} - {le.strftime('%b %d')}",
        "avg": round(total / len(active), 1) if active else 0,
        "months": months,
    }


def stat_card(x, y, w, h, label, value, sub, value_color=BRIGHT):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{CARD_BG}" stroke="{BORDER}"/>'
        f'<text x="{x+12}" y="{y+22}" font-family="{FONT}" font-size="12" fill="{DIM}">$ {label}</text>'
        f'<text x="{x+12}" y="{y+52}" font-family="{FONT}" font-size="28" font-weight="bold" fill="{value_color}">{value}</text>'
        f'<text x="{x+12}" y="{y+72}" font-family="{FONT}" font-size="11" fill="{DIM}">{sub}</text>'
    )


def build(s):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">']
    parts.append(f'<rect width="{W}" height="{H}" rx="8" fill="{BG}" stroke="{BORDER}"/>')
    # traffic lights
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        parts.append(f'<circle cx="{20+i*18}" cy="20" r="6" fill="{c}"/>')
    parts.append(f'<text x="{W//2}" y="25" font-family="{FONT}" font-size="13" fill="{DIM}" text-anchor="middle">shivansh@github ~ $ whoami</text>')
    parts.append(f'<line x1="0" y1="36" x2="{W}" y2="36" stroke="{BORDER}"/>')

    # stat cards: 2 cols x 3 rows
    pad, top = 14, 50
    cw = (W - pad * 3) // 2
    ch = 92
    gap = 12
    cards = [
        ("current streak", str(s["cur_streak"]), f'{s["cur_streak"]} day{"s" if s["cur_streak"]!=1 else ""}' + f' · {s["cur_range"]}', "#3fb950"),
        ("longest streak", str(s["long_streak"]), f'{s["long_streak"]} days · {s["long_range"]}', "#d2a8ff"),
        ("contributions", f'{s["total"]:,}', "in the last year", "#79c0ff"),
        ("active days", str(s["active_days"]), f'{s["active_days"]} / {s["total_days"]} · {round(s["active_days"]/s["total_days"]*100)}% of the year', "#ffa657"),
        ("best day", str(s["best_count"]), s["best_date"], "#ff7b72"),
        ("avg / active day", str(s["avg"]), "contributions", "#56d4dd"),
    ]
    for i, (label, val, sub, col) in enumerate(cards):
        x = pad + (i % 2) * (cw + gap)
        y = top + (i // 2) * (ch + gap)
        parts.append(stat_card(x, y, cw, ch, label, val, sub, col))

    # monthly bar chart
    chart_y = top + 3 * (ch + gap) + 10
    chart_h = H - chart_y - 30
    parts.append(f'<rect x="{pad}" y="{chart_y}" width="{W-2*pad}" height="{chart_h+14}" rx="6" fill="{CARD_BG}" stroke="{BORDER}"/>')
    parts.append(f'<text x="{pad+12}" y="{chart_y+22}" font-family="{FONT}" font-size="12" fill="{DIM}">$ contributions / month</text>')

    months = s["months"]
    maxv = max(v for _, v in months) or 1
    bw = (W - 2 * pad - 40) / 12
    base = chart_y + chart_h
    for i, (label, val) in enumerate(months):
        x = pad + 20 + i * bw
        bh = (val / maxv) * (chart_h - 50) if val else 2
        y = base - bh
        color = "#3fb950" if val == maxv and val else ("#1f6feb" if val else "#21262d")
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-6:.1f}" height="{bh:.1f}" rx="2" fill="{color}"/>')
        if val == maxv and val:
            parts.append(f'<text x="{x+bw/2-3:.1f}" y="{y-6:.1f}" font-family="{FONT}" font-size="10" fill="{DIM}" text-anchor="middle">{val}</text>')
        parts.append(f'<text x="{x+bw/2-3:.1f}" y="{base+14:.1f}" font-family="{FONT}" font-size="10" fill="{DIM}" text-anchor="middle">{label}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    s = load_stats()
    svg = build(s)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
