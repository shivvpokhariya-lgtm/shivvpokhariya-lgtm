#!/usr/bin/env python3
"""Prep a photo for ASCII conversion (run locally, once per photo).

Pipeline:
  1. rembg background removal (isolate the subject)
  2. OpenCV CLAHE local-contrast boost on the luminance channel
     (this is what gives a flatly-lit face real highlights/shadows)
  3. Composite onto pure white (background maps to the blank end of
     the ASCII ramp: white -> spaces)
  4. Grayscale -> source-prepped.png

Usage:
    python scripts/prep_photo.py <photo-path>
"""
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

OUT = "source-prepped.png"
# Portrait runs on small VMs too: downscale first (the ASCII grid is only
# ~100x53 chars, so full resolution is wasted). Full u2net model for clean
# hair edges (u2netp cuts the top of the head on dark backgrounds).
MAX_DIM = 768
REMBG_MODEL = "u2net"


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/prep_photo.py <photo-path>")
        sys.exit(1)

    # 1. remove the background (downscaled + light model: VM-friendly)
    inp = Image.open(sys.argv[1]).convert("RGB")
    inp.thumbnail((MAX_DIM, MAX_DIM))
    session = new_session(REMBG_MODEL)
    no_bg = remove(inp, session=session)  # RGBA, transparent background

    # 2. CLAHE local-contrast boost on the L channel of LAB
    arr = np.array(no_bg.convert("RGB"))
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    boosted = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)
    boosted_img = Image.fromarray(boosted).convert("RGBA")
    boosted_img.putalpha(no_bg.split()[3])  # keep rembg's alpha

    # 3. composite onto pure white
    white = Image.new("RGBA", boosted_img.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white, boosted_img)

    # 4. grayscale, then a brightness/contrast lift so dimly-lit faces
    # separate cleanly from hair in the ASCII ramp.
    # Face should be near-white (empty in ASCII) like the reference,
    # with only features/hair in dark tones.
    from PIL import ImageEnhance
    gray = composited.convert("L")
    # Reference style: face near-white/empty, hair dense, features outlined.
    # Aggressive lift pushes face skin to white while hair stays black.
    gray = ImageEnhance.Brightness(gray).enhance(2.1)
    gray = ImageEnhance.Contrast(gray).enhance(1.9)
    gray.save(OUT)
    print(f"wrote {OUT} ({gray.size[0]}x{gray.size[1]})")


if __name__ == "__main__":
    main()
