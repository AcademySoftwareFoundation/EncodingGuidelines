#!/usr/bin/env python3
"""Make sourceimages/testrgb.png for the RGB rows of tests/codec_web_tests/web_compatibility.html.

It is test444.png with the "4:4:4" label replaced by "RGB": the bars are copied back over the label rows from a
clean row, and the new label is drawn at the same size and position. Like test444.png, it has no color chunks.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

src = np.array(Image.open(HERE / "test444.png").convert("RGB"))
out = src.copy()
out[95:190] = src[60]                      # bars only, no label
white = src[:240][src[:240].min(axis=2) >= 230]  # the label's colour
text_colour = tuple(int(v) for v in white.max(axis=0))

img = Image.fromarray(out)
draw = ImageDraw.Draw(img)
cap_top, cap_bottom, centre_x = 105, 175, 220.5   # measured from test444.png's "4:4:4"
size = 100
font = ImageFont.truetype(FONT, size)
l, t, r, b = draw.textbbox((0, 0), "RGB", font=font)
size = round(size * (cap_bottom - cap_top + 1) / (b - t))
font = ImageFont.truetype(FONT, size)
l, t, r, b = draw.textbbox((0, 0), "RGB", font=font)
draw.text((centre_x - (l + r) / 2, cap_top - t), "RGB", font=font, fill=text_colour)
img.save(HERE / "testrgb.png")
print("wrote", HERE / "testrgb.png", "font size", size)
