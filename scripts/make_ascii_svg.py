#!/usr/bin/env python3
"""Convert the prepped photo into a self-typing monochrome ASCII SVG.

Reads source-prepped.png (from prep_photo.py), downsamples it to a
~100x53 character grid, and maps each pixel's brightness through a
density ramp (sparse glyphs for bright areas, dense glyphs for dark).

Animation: every row is wrapped in a horizontal clip that wipes
left-to-right, with a small block "cursor" riding the wipe edge,
staggered top-to-bottom. SMIL, plays ONCE, then freezes
(fill="freeze", no repeat) — GitHub plays this inside <img> SVGs.

Writes shivansh-ascii.svg

Usage:
    python scripts/make_ascii_svg.py
"""
from xml.sax.saxutils import escape

from PIL import Image

SRC = "source-prepped.png"
OUT = "portrait-v2.svg"  # renamed 2026-10-23 to bust GitHub camo cache

COLS = 120  # ROWS auto-calculated from image aspect + cell aspect (no squish)
CELL_W = 6.6   # ~0.6em monospace advance at FONT_SIZE
CELL_H = 13.0
RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)
GAMMA = 1.0  # tonal lift is baked into prep_photo.py; keep mapping linear
FILL = "#c9d1d9"        # monochrome light-gray fill
FILL_LIGHT = "#24292f"  # light-mode override
CURSOR_FILL = "#58a6ff"
CURSOR_FILL_LIGHT = "#0969da"

FONT_SIZE = 11
ROW_DUR = 0.9      # seconds per row wipe
ROW_STAGGER = 0.06  # seconds between row starts

FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def get_rows() -> int:
    """Calculate ROWS so the ASCII isn't vertically squished."""
    img = Image.open(SRC)
    iw, ih = img.size
    # rows = cols * (img_h/img_w) * (cell_w/cell_h)
    return round(COLS * (ih / iw) * (CELL_W / CELL_H))


def to_ascii_rows() -> list:
    rows_n = get_rows()
    img = Image.open(SRC).convert("L").resize((COLS, rows_n), Image.LANCZOS)
    px = img.load()
    n = len(RAMP) - 1
    # Face region (rows 20-38, cols 35-85 in 120x74 grid) -> empty like reference
    # Tighter vertical to avoid hair; skin is bright, features stay
    FACE_TOP, FACE_BOTTOM = int(rows_n * 0.27), int(rows_n * 0.51)
    FACE_LEFT, FACE_RIGHT = int(COLS * 0.29), int(COLS * 0.71)
    # Glasses region: exclude from emptying so frames are constructed with dots
    GLASS_TOP, GLASS_BOTTOM = int(rows_n * 0.34), int(rows_n * 0.37)
    GLASS_LEFT, GLASS_RIGHT = int(COLS * 0.33), int(COLS * 0.67)
    rows = []
    for y in range(rows_n):
        chars = []
        for x in range(COLS):
            b = px[x, y]
            # gamma lift before ramp mapping
            b = int(255 * ((b / 255) ** (1 / GAMMA)))
            in_face = (FACE_TOP <= y <= FACE_BOTTOM and FACE_LEFT <= x <= FACE_RIGHT)
            in_glasses = (GLASS_TOP <= y <= GLASS_BOTTOM and GLASS_LEFT <= x <= GLASS_RIGHT)
            # In face region (but NOT glasses): bright skin -> empty (reference style)
            # Skin ~140, features ~50-100, so threshold at 110 keeps features
            if in_face and not in_glasses and b > 110:
                idx = 0
            else:
                idx = int(round((255 - b) / 255 * n))
            chars.append(RAMP[idx])
        # keep full COLS width (no rstrip): textLength below force-fits every
        # row to the viewBox, so rendering never overflows on wide fonts
        rows.append("".join(chars))
    return rows


def trim_empty_rows(rows: list) -> list:
    """Drop leading/trailing all-whitespace rows so the portrait sits at the
    top of its box instead of floating low with empty space above."""
    start = 0
    while start < len(rows) and not rows[start].strip():
        start += 1
    end = len(rows)
    while end > start and not rows[end - 1].strip():
        end -= 1
    return rows[start:end]


def build_svg(rows: list) -> str:
    rows = trim_empty_rows(rows)
    nrows = len(rows)
    w = COLS * CELL_W
    h = nrows * CELL_H
    baseline = FONT_SIZE * 0.82

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" '
        f'viewBox="0 0 {w:.1f} {h:.1f}" role="img" aria-label="ASCII portrait">'
    )
    # Light-mode adaptation (SVG-as-<img> still honors prefers-color-scheme).
    parts.append(
        "<style>"
        f"@media (prefers-color-scheme: light) {{ .art {{ fill: {FILL_LIGHT}; }} "
        f".cur {{ fill: {CURSOR_FILL_LIGHT}; }} }}"
        "</style>"
    )

    for r, row in enumerate(rows):
        begin = r * ROW_STAGGER
        y = r * CELL_H
        clip_id = f"rowclip{r}"

        # Row wipe: clip rect grows 0 -> full width, staggered per row.
        parts.append(
            f'<clipPath id="{clip_id}">'
            f'<rect x="0" y="{y:.1f}" width="0" height="{CELL_H:.1f}">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" '
            f'dur="{ROW_DUR}s" begin="{begin:.2f}s" fill="freeze"/>'
            f"</rect></clipPath>"
        )
        parts.append(
            f'<g clip-path="url(#{clip_id})">'
            f'<text class="art" x="0" y="{y + baseline:.1f}" '
            f'font-family="{FONT_STACK}" font-size="{FONT_SIZE}" fill="{FILL}" '
            f'textLength="{w:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{escape(row)}</text></g>'
        )
        # Cursor block rides the wipe edge, then fades as its row completes.
        parts.append(
            f'<rect class="cur" x="0" y="{y:.1f}" width="{CELL_W:.1f}" '
            f'height="{CELL_H:.1f}" fill="{CURSOR_FILL}">'
            f'<animate attributeName="x" from="0" to="{w:.1f}" '
            f'dur="{ROW_DUR}s" begin="{begin:.2f}s" fill="freeze"/>'
            f'<animate attributeName="opacity" values="1;1;0" '
            f'keyTimes="0;0.97;1" dur="{ROW_DUR}s" begin="{begin:.2f}s" '
            f'fill="freeze"/>'
            f"</rect>"
        )

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    rows = to_ascii_rows()
    svg = build_svg(rows)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    trimmed = len(trim_empty_rows(rows))
    total_s = (trimmed - 1) * ROW_STAGGER + ROW_DUR
    print(f"wrote {OUT} ({COLS}x{trimmed} grid, animation ~{total_s:.1f}s)")


if __name__ == "__main__":
    main()
