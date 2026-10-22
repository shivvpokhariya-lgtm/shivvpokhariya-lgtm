#!/usr/bin/env python3
"""Render data/contributions.json as an animated 53-week heatmap SVG.

Classic week-columns x 7-day calendar of rounded boxes in GitHub's
green palette. Boxes reveal once with a diagonal, line-after-line
slide-down (CSS keyframes that play on load, then freeze — no looping
glow). Includes month labels, a Less->More legend, and a stats footer
("N contributions in the last year").

Writes contrib-heatmap.svg

Usage:
    python scripts/render_heatmap_svg.py
"""
import json
from datetime import date
from xml.sax.saxutils import escape

SRC = "data/contributions.json"
OUT = "contrib-heatmap.svg"

# Show only the recent stretch (Shivansh's call, 2026-10-23): the full-year
# view was 8 empty months plus a busy tail. July 2026 -> today.
START_DATE = "2026-07-01"
START_LABEL = "Jul 2026"

# none -> brightest (level 5 is a neon top end)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL = 10
GAP = 3
PITCH = CELL + GAP
TOP = 22     # room for month labels
LEFT = 2
FOOTER_H = 52   # stats line + legend line
RX = 2.5
DIAG_STEP = 0.022  # seconds per diagonal — the reveal sweep
DROP_DUR = 0.45

FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
LABEL_FILL = "#8b949e"
LABEL_FILL_LIGHT = "#57606a"
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    days = [d for d in data["days"] if d["date"] >= START_DATE]
    if not days:
        raise SystemExit("no days in " + SRC + " on/after " + START_DATE)

    # Group into week columns; columns start on Sunday like GitHub's.
    first = date.fromisoformat(days[0]["date"])
    first_sunday_ord = first.toordinal() - (first.weekday() + 1) % 7
    weeks = {}
    for d in days:
        dd = date.fromisoformat(d["date"])
        w = (dd.toordinal() - first_sunday_ord) // 7
        row = (dd.weekday() + 1) % 7  # Sunday=0 .. Saturday=6
        weeks.setdefault(w, {})[row] = d
    n_weeks = max(weeks) + 1

    grid_w = n_weeks * PITCH - GAP
    grid_h = 7 * PITCH - GAP
    w = LEFT * 2 + grid_w
    h = TOP + grid_h + FOOTER_H

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="contribution heatmap">'
    )
    p.append(
        "<style>"
        ".cell { animation: drop %.2fs both; }" % DROP_DUR +
        "@keyframes drop { from { opacity: 0; transform: translateY(-7px); } "
        "to { opacity: 1; transform: translateY(0); } }"
        f"@media (prefers-color-scheme: light) {{ .lbl {{ fill: {LABEL_FILL_LIGHT}; }} }}"
        "</style>"
    )

    # month labels (first column where a new month appears)
    seen_month = None
    for wi in range(n_weeks):
        col = weeks.get(wi, {})
        if not col:
            continue
        first_day = min(col.values(), key=lambda d: d["date"])
        m = int(first_day["date"][5:7])
        if m != seen_month:
            seen_month = m
            x = LEFT + wi * PITCH
            p.append(
                f'<text class="lbl" x="{x}" y="12" font-family="{FONT_STACK}" '
                f'font-size="10" fill="{LABEL_FILL}">{MONTHS[m]}</text>'
            )

    # day cells — diagonal reveal: delay grows with (week + row)
    cell_count = 0
    for wi in range(n_weeks):
        for row in range(7):
            d = weeks.get(wi, {}).get(row)
            if d is None:
                continue
            x = LEFT + wi * PITCH
            y = TOP + row * PITCH
            level = max(0, min(d.get("level", 0), len(PALETTE) - 1))
            fill = PALETTE[level]
            delay = (wi + row) * DIAG_STEP
            title = f'{d["count"]} contributions on {d["date"]}'
            p.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RX}" fill="{fill}" style="animation-delay:{delay:.2f}s">'
                f"<title>{escape(title)}</title></rect>"
            )
            cell_count += 1

    # footer: stats on one line, Less->More legend on the next (the July+
    # view is narrow, so a single line would collide)
    fy = TOP + grid_h + 20
    total = sum(d.get("count", 0) for d in days)
    p.append(
        f'<text class="lbl" x="{LEFT}" y="{fy}" font-family="{FONT_STACK}" '
        f'font-size="11" fill="{LABEL_FILL}">'
        f'{total:,} contributions since {START_LABEL}</text>'
    )
    ly = fy + 18
    p.append(
        f'<text class="lbl" x="{LEFT}" y="{ly}" font-family="{FONT_STACK}" '
        f'font-size="11" fill="{LABEL_FILL}">Less</text>'
    )
    sx = LEFT + 34
    for i in range(1, 6):
        p.append(
            f'<rect x="{sx + (i - 1) * (CELL + 2)}" y="{ly - 9}" '
            f'width="{CELL}" height="{CELL}" rx="{RX}" fill="{PALETTE[i]}"/>'
        )
    p.append(
        f'<text class="lbl" x="{sx + 5 * (CELL + 2) + 6}" y="{ly}" '
        f'font-family="{FONT_STACK}" font-size="11" fill="{LABEL_FILL}">More</text>'
    )

    p.append("</svg>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(p))
    print(f"wrote {OUT} ({w}x{h}, {n_weeks} weeks, {cell_count} cells)")


if __name__ == "__main__":
    main()
