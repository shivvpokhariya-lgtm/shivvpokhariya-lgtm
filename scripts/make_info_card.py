#!/usr/bin/env python3
"""Hand-authored neofetch-style info card SVG.

Reads scripts/info_config.json (rows: Now / Built / Also / Stack / Mode),
renders a terminal card: title bar with traffic-light dots, then colored
key/value rows that fade + slide in on a short stagger.

STATIC=1 env var emits a frozen frame (no animation) for local previews.

Writes info-card.svg

Usage:
    python scripts/make_info_card.py
    STATIC=1 python scripts/make_info_card.py
"""
import json
import os
from xml.sax.saxutils import escape

CFG = "scripts/info_config.json"
OUT = "info-card.svg"

W = 490
PAD = 22
TITLE_H = 46
ROW_H = 27
FONT = 13
VALUE_FILL = "#c9d1d9"
DIM_FILL = "#8b949e"
FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def main() -> None:
    static = os.environ.get("STATIC") == "1"
    with open(CFG, encoding="utf-8") as f:
        cfg = json.load(f)
    rows = cfg["rows"]

    h = TITLE_H + len(rows) * ROW_H + PAD

    p = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" role="img" aria-label="info card">'
    )
    # card body
    p.append(
        f'<rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="8" '
        f'fill="#0d1117" stroke="#30363d"/>'
    )
    # title bar
    p.append(f'<line x1="1" y1="{TITLE_H}" x2="{W - 1}" y2="{TITLE_H}" stroke="#30363d"/>')
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        p.append(
            f'<circle cx="{PAD + i * 18}" cy="{TITLE_H / 2}" r="6" fill="{c}"/>'
        )
    p.append(
        f'<text x="{W / 2}" y="{TITLE_H / 2 + 5}" text-anchor="middle" '
        f'font-family="{FONT_STACK}" font-size="{FONT}" fill="{DIM_FILL}">'
        f'{escape(cfg.get("title", ""))}</text>'
    )

    y = TITLE_H + ROW_H - 6
    begin = 0.25
    step = 0.16

    def line(text_inner: str, at_y: float, delay: float) -> None:
        if static:
            p.append(f'<g opacity="1"><text x="{PAD}" y="{at_y:.0f}" '
                     f'font-family="{FONT_STACK}" font-size="{FONT}">{text_inner}</text></g>')
        else:
            p.append(
                f'<g opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" dur="0.35s" '
                f'begin="{delay:.2f}s" fill="freeze"/>'
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="0 8" to="0 0" dur="0.35s" begin="{delay:.2f}s" fill="freeze"/>'
                f'<text x="{PAD}" y="{at_y:.0f}" font-family="{FONT_STACK}" '
                f'font-size="{FONT}">{text_inner}</text></g>'
            )

    # fake prompt line first, then the key/value rows
    prompt = escape(cfg.get("prompt", ""))
    line(f'<tspan fill="#7ee787">{prompt}</tspan>', y, begin)
    y += ROW_H
    for i, row in enumerate(rows):
        key = escape(row["key"])
        val = escape(row["value"])
        color = row.get("color", VALUE_FILL)
        inner = (f'<tspan fill="{color}" font-weight="bold">{key}</tspan>'
                 f'<tspan fill="{DIM_FILL}">: </tspan>'
                 f'<tspan fill="{VALUE_FILL}">{val}</tspan>')
        line(inner, y, begin + step * (i + 1))
        y += ROW_H

    p.append("</svg>")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(p))
    mode = "static" if static else "animated"
    print(f"wrote {OUT} ({W}x{h}, {len(rows)} rows, {mode})")


if __name__ == "__main__":
    main()
