"""
Generate a visual test chart that tells a piecewise sRGB (IEC 61966-2-1) display response from a pure
gamma 2.2 power law.

How it works
------------
A fine dither between black (0) and a code value V_hi with duty cycle d is averaged by the eye in linear
light. A solid patch V_solid matches it when

    EOTF(V_solid) = d * EOTF(V_hi)

An additive black level or flare adds equally to both sides, so it does not move the match (it only lowers
the visible contrast).

  * Pure gamma 2.2:   V_solid = d^(1/2.2) * V_hi, a constant fraction of V_hi.
  * Piecewise sRGB:   the linear toe (below 8-bit code 10.3) and the 0.055 offset pull the match 3 to 5 code
                      values lower in the shadows, a 26-45% luminance difference.
  * At V_hi = 185 (50%) both curves give 135. That column is the control: it must match on either display.

Every column in COLUMNS has both matches close to an 8-bit integer (checked by self_check), so rounding does
not blur the result.

Reading it
----------
  1. Checks (top right): fine and coarse halves must look equally bright (A: scaling, B: sharpening).
  2. Control column: no word readable, and the ladder step that vanishes is at the green tick.
  3. Shadow columns: the word you can read ("sRGB" or "2.2") names the display. In the ladder, the step that
     vanishes sits at the tick of that curve.

The word "sRGB" is drawn with the gamma 2.2 match, so it vanishes on a gamma 2.2 display and shows on an sRGB
display; "2.2" is drawn with the sRGB match.

Outputs (written next to this script)
-------------------------------------
  * srgb_vs_gamma22_untagged.png     8-bit RGB PNG with IHDR/IDAT/IEND only.
  * srgb_vs_gamma22_tagged_srgb.png  Identical pixels with cICP (1, 13, 0, 1) and sRGB chunks.
  * simulated_on_srgb_display.png    What the eye sees on a piecewise sRGB display (shadows brightened).
  * simulated_on_gamma22_display.png What the eye sees on a pure gamma 2.2 display (shadows brightened).

view.html (not generated) shows the chart at one image pixel per device pixel in a browser.

Usage:
    python tests/srgb-vs-gamma22/make_srgb_vs_gamma22_chart.py
"""
import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1920, 1080
HEADER_H = 112
UPPER_TOP = HEADER_H
UPPER_H = 300
BAND_GAP = 12
LOWER_TOP = UPPER_TOP + UPPER_H + 16
LABEL_W = 304
GUTTER = 28          # per-column strip for ladder code values and ticks

# (title, v_hi, duty cycle, is_control)
COLUMNS = [
    ("Deep toe",   18,  0.50, False),
    ("Upper toe",  26,  0.50, False),
    ("25% shadow", 43,  0.25, False),
    ("Control",    185, 0.50, True),
]

LADDER_HALF = 5                 # ladder shows centre +/- this many code values
INTEGER_TOLERANCE = 0.15        # both matches must be this close to an 8-bit integer
MIN_SHADOW_DIFFERENCE = 3       # code values between the two matches in a non-control column
SIM_SHADOW_BOOST = 3.2

CYAN = (90, 200, 240)           # piecewise sRGB
AMBER = (235, 175, 70)          # pure gamma 2.2
GREEN = (100, 220, 150)         # both (control)

# Check patches in the header: (x0, y0, x1, y1), each split into a fine left half and a coarse right half.
CHECK_SCALE = (1484, 36, 1676, 100)     # 0 & 255 checkerboard, 1 px vs 16 px
CHECK_SHARP = (1708, 36, 1900, 100)     # 0 & 185 horizontal lines, 1 px vs 8 px
CHECK_SHARP_LEVEL = 185


def srgb_eotf(v):
    """Piecewise sRGB EOTF (IEC 61966-2-1): code value in [0, 1] -> linear light in [0, 1]."""
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_oetf(lin):
    """Piecewise sRGB inverse EOTF: linear light in [0, 1] -> code value in [0, 1]."""
    lin = np.asarray(lin, dtype=np.float64)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * (np.maximum(lin, 0.0) ** (1.0 / 2.4)) - 0.055)


def match_values(v_hi, duty):
    """Exact matching code values (0..255, float) on a piecewise sRGB and on a pure gamma 2.2 display."""
    m_srgb = 255.0 * float(srgb_oetf(duty * srgb_eotf(v_hi / 255.0)))
    m_g22 = v_hi * (duty ** (1.0 / 2.2))
    return m_srgb, m_g22


def match_ints(v_hi, duty):
    m_srgb, m_g22 = match_values(v_hi, duty)
    return int(round(m_srgb)), int(round(m_g22))


def ladder_values(v_hi, duty):
    """Code values of the ladder rows, centred between the two matches so both are bracketed."""
    v_srgb, v_g22 = match_ints(v_hi, duty)
    centre = (v_srgb + v_g22 + 1) // 2
    return [centre + d for d in range(-LADDER_HALF, LADDER_HALF + 1)]


def dither_pattern(h, w, v_hi, duty, mode="lines"):
    """
    (h, w) uint8 dither between 0 and v_hi.
      mode="lines": horizontal 1 px lines (1 row in 2, or 1 in 4). Immune to horizontal pixel slewing.
      mode="check": 1 px checkerboard (50%), or 1 bright pixel per 2x2 block (25%).
    """
    yy, xx = np.mgrid[0:h, 0:w]
    if abs(duty - 0.5) < 1e-6:
        mask = (yy % 2) == 0 if mode == "lines" else ((yy + xx) % 2) == 0
    elif abs(duty - 0.25) < 1e-6:
        mask = (yy % 4) == 0 if mode == "lines" else ((yy % 2) == 0) & ((xx % 2) == 0)
    else:
        raise ValueError(f"Unsupported duty cycle: {duty}")
    return np.where(mask, v_hi, 0).astype(np.uint8)


GLYPHS_5X7 = {
    "s": [" 1111", "1    ", "1    ", " 111 ", "    1", "    1", "1111 "],
    "R": ["1111 ", "1   1", "1   1", "1111 ", "1 1  ", "1  1 ", "1   1"],
    "G": [" 111 ", "1   1", "1    ", "1 111", "1   1", "1   1", " 111 "],
    "B": ["1111 ", "1   1", "1   1", "1111 ", "1   1", "1   1", "1111 "],
    "2": [" 111 ", "1   1", "    1", "  11 ", " 1   ", "1    ", "11111"],
    ".": ["     ", "     ", "     ", "     ", "     ", " 11  ", " 11  "],
}


def text_mask(h, w, text, block=12):
    """
    Bitmap text where each glyph pixel is a block x block square, placed on a 4 px grid. `block` must be a
    multiple of 4 so that no dither period (2 or 4 px) is cut by a letter edge.
    """
    assert block % 4 == 0
    grid = np.zeros((7, 6 * len(text) - 1), dtype=bool)
    for i, ch in enumerate(text):
        for r, row in enumerate(GLYPHS_5X7[ch]):
            for c, bit in enumerate(row):
                grid[r, 6 * i + c] = bit == "1"
    scaled = np.repeat(np.repeat(grid, block, axis=0), block, axis=1)
    sh, sw = scaled.shape
    assert sh <= h and sw <= w, "text does not fit the band"
    mask = np.zeros((h, w), dtype=bool)
    y0 = ((h - sh) // 2 // 4) * 4
    x0 = ((w - sw) // 2 // 4) * 4
    mask[y0:y0 + sh, x0:x0 + sw] = scaled
    return mask


class Layout:
    """Pixel geometry. Everything in the optical areas is aligned to 8 px."""

    def __init__(self):
        n = len(COLUMNS)
        self.col_w = ((W - LABEL_W - 8) // n // 8) * 8
        self.patch_w = ((self.col_w - GUTTER - 4) // 8) * 8
        self.band_h = ((UPPER_H - BAND_GAP) // 2 // 8) * 8
        self.rows = 2 * LADDER_HALF + 1
        self.ladder_top = LOWER_TOP + 48
        self.step_h = ((H - 12 - self.ladder_top) // self.rows // 8) * 8
        self.ladder_bot = self.ladder_top + self.step_h * self.rows

    def gutter_x(self, c):
        return LABEL_W + c * self.col_w + 4

    def patch_x(self, c):
        x0 = LABEL_W + c * self.col_w + GUTTER
        return x0, x0 + self.patch_w

    def band_y(self, b):
        y0 = UPPER_TOP + b * (self.band_h + BAND_GAP)
        return y0, y0 + self.band_h

    def step_x(self, c):
        """Solid ladder steps occupy the middle half of the column."""
        x0, _ = self.patch_x(c)
        return x0 + (self.patch_w // 4 // 8) * 8, x0 + (3 * self.patch_w // 4 // 8) * 8


# Band 0 shows the word "sRGB" drawn with the gamma 2.2 match: readable on an sRGB display.
# Band 1 shows the word "2.2" drawn with the sRGB match: readable on a gamma 2.2 display.
BANDS = [("sRGB", "g22"), ("2.2", "srgb")]


def band_solid(band, v_hi, duty):
    v_srgb, v_g22 = match_ints(v_hi, duty)
    return v_g22 if BANDS[band][1] == "g22" else v_srgb


def make_raw_patches():
    """The chart without text, so the simulations can integrate clean patches."""
    lay = Layout()
    img = np.full((H, W, 3), 6, dtype=np.uint8)
    img[:HEADER_H, :] = 20
    img[:, :LABEL_W] = 14
    img[UPPER_TOP + UPPER_H:LOWER_TOP, :] = 14

    # Check A: scaling. 0 & 255 checkerboard, 1 px (left) vs 16 px (right).
    x0, y0, x1, y1 = CHECK_SCALE
    xm = (x0 + x1) // 2
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    fine = ((yy + xx) % 2) * 255
    coarse = ((yy // 16 + xx // 16) % 2) * 255
    img[y0:y1, x0:x1] = np.where(xx < xm - x0, fine, coarse).astype(np.uint8)[..., None]

    # Check B: sharpening. 0 & 185 horizontal lines, 1 px (left) vs 8 px (right). Unlike 0 & 255, overshoot
    # is not clipped at this level, so a sharpening filter brightens the fine half.
    x0, y0, x1, y1 = CHECK_SHARP
    xm = (x0 + x1) // 2
    yy, xx = np.mgrid[0:y1 - y0, 0:x1 - x0]
    fine = ((yy + 1) % 2) * CHECK_SHARP_LEVEL
    coarse = ((yy // 8 + 1) % 2) * CHECK_SHARP_LEVEL
    img[y0:y1, x0:x1] = np.where(xx < xm - x0, fine, coarse).astype(np.uint8)[..., None]

    # Upper section: words on checkerboard dither.
    for b, (word, _) in enumerate(BANDS):
        by0, by1 = lay.band_y(b)
        mask = text_mask(lay.band_h, lay.patch_w, word)
        for c, (_, v_hi, duty, _) in enumerate(COLUMNS):
            cx0, cx1 = lay.patch_x(c)
            dither = dither_pattern(lay.band_h, lay.patch_w, v_hi, duty, mode="check")
            img[by0:by1, cx0:cx1] = np.where(mask, band_solid(b, v_hi, duty), dither)[..., None]

    # Lower section: 1-code-value ladder. Left half line dither, right half checkerboard dither.
    ladder_h = lay.ladder_bot - lay.ladder_top
    for c, (_, v_hi, duty, _) in enumerate(COLUMNS):
        cx0, cx1 = lay.patch_x(c)
        img[lay.ladder_top:lay.ladder_bot, lay.gutter_x(c):cx0] = 12
        lines = dither_pattern(ladder_h, lay.patch_w, v_hi, duty, mode="lines")
        check = dither_pattern(ladder_h, lay.patch_w, v_hi, duty, mode="check")
        _, xx = np.mgrid[0:ladder_h, 0:lay.patch_w]
        img[lay.ladder_top:lay.ladder_bot, cx0:cx1] = np.where(xx < lay.patch_w // 2, lines, check)[..., None]
        sx0, sx1 = lay.step_x(c)
        for r, v in enumerate(ladder_values(v_hi, duty)):
            sy0 = lay.ladder_top + r * lay.step_h
            img[sy0:sy0 + lay.step_h, sx0:sx1] = v
    return img


def tick_colour(v, v_srgb, v_g22):
    if v == v_srgb and v == v_g22:
        return GREEN
    if v == v_srgb:
        return CYAN
    if v == v_g22:
        return AMBER
    return None


def annotate_chart(raw_img, sim=None):
    """Draw labels and ticks, all outside the dither/solid comparison areas."""
    lay = Layout()
    img = raw_img.copy()

    for c, (_, v_hi, duty, _) in enumerate(COLUMNS):
        v_srgb, v_g22 = match_ints(v_hi, duty)
        gx = lay.gutter_x(c)
        for r, v in enumerate(ladder_values(v_hi, duty)):
            colour = tick_colour(v, v_srgb, v_g22)
            if colour:
                sy0 = lay.ladder_top + r * lay.step_h
                img[sy0 + 2:sy0 + lay.step_h - 2, gx:gx + 3] = colour

    pil_img = Image.fromarray(img)
    draw = ImageDraw.Draw(pil_img)
    f_title = ImageFont.load_default(size=22)
    f_sub = ImageFont.load_default(size=15)
    f_band = ImageFont.load_default(size=19)
    f_col = ImageFont.load_default(size=14)
    f_small = ImageFont.load_default(size=13)
    f_tiny = ImageFont.load_default(size=11)
    grey = (170, 170, 170)

    control = next(i + 1 for i, col in enumerate(COLUMNS) if col[3])
    shadows = [i + 1 for i, col in enumerate(COLUMNS) if not col[3]]
    shadow_txt = f"{shadows[0]}-{shadows[-1]}"

    note = {
        None: "",
        "srgb": "   [SIMULATED: piecewise sRGB display, shadows brightened]",
        "gamma22": "   [SIMULATED: pure gamma 2.2 display, shadows brightened]",
    }[sim]
    draw.text((20, 12), f"Piecewise sRGB or pure gamma 2.2?{note}", fill=(235, 235, 235), font=f_title)
    draw.text((20, 44), "1. CHECKS (top right): in A and in B both halves must look equally bright. "
                        "If not, the image is being scaled or sharpened.",
              fill=(190, 190, 190), font=f_sub)
    draw.text((20, 66), f"2. CONTROL (column {control}): no word is readable and the step at the green tick "
                        "vanishes. If not, the display is neither curve.",
              fill=(190, 190, 190), font=f_sub)
    draw.text((20, 88), f"3. RESULT (columns {shadow_txt}): squint. The word you can read names your display. "
                        "In the ladder, the step that vanishes is at its tick.",
              fill=(190, 190, 190), font=f_sub)

    draw.text((CHECK_SCALE[0], 12), "A. Scaling: halves equal?", fill=(210, 210, 210), font=f_col)
    draw.text((CHECK_SHARP[0], 12), "B. Sharpening: halves equal?", fill=(210, 210, 210), font=f_col)

    # Band labels
    for b, (word, _) in enumerate(BANDS):
        y = lay.band_y(b)[0] + 16
        if word == "sRGB":
            colour, display, drawn = CYAN, "piecewise sRGB", "gamma 2.2"
        else:
            colour, display, drawn = AMBER, "pure gamma 2.2", "sRGB"
        codes = ", ".join(str(band_solid(b, v_hi, duty)) for _, v_hi, duty, _ in COLUMNS)
        draw.text((16, y), f"Reads \"{word}\"", fill=colour, font=f_band)
        draw.text((16, y + 28), f"on a {display} display.", fill=colour, font=f_small)
        draw.text((16, y + 52), f"Text is the {drawn} match:", fill=grey, font=f_small)
        draw.text((16, y + 70), f"codes {codes}", fill=grey, font=f_small)
        draw.text((16, y + 94), f"Column {control} stays blank on both.", fill=(140, 140, 140), font=f_small)

    # Ladder legend
    y = LOWER_TOP + 4
    draw.text((16, y), "Step ladder", fill=(225, 225, 225), font=f_band)
    draw.text((16, y + 28), "1 code value per row", fill=grey, font=f_small)
    y = lay.ladder_top + 8
    draw.text((16, y), "Find the solid step that vanishes", fill=grey, font=f_small)
    draw.text((16, y + 18), "into the dither around it.", fill=grey, font=f_small)
    for i, (colour, label) in enumerate([(CYAN, "at cyan tick: piecewise sRGB"),
                                         (AMBER, "at amber tick: pure gamma 2.2"),
                                         (GREEN, "at green tick: control, both curves")]):
        ly = y + 52 + i * 24
        draw.rectangle((16, ly, 18, ly + 15), fill=colour)
        draw.text((28, ly), label, fill=colour, font=f_small)
    draw.text((16, y + 140), "Left half: line dither.", fill=grey, font=f_small)
    draw.text((16, y + 158), "Right half: checkerboard dither.", fill=grey, font=f_small)
    draw.text((16, y + 176), "Both halves should agree.", fill=grey, font=f_small)
    draw.text((16, y + 210), "Vanishes somewhere else, or not", fill=(140, 140, 140), font=f_small)
    draw.text((16, y + 228), "the same in every column:", fill=(140, 140, 140), font=f_small)
    draw.text((16, y + 246), "the display is neither curve.", fill=(140, 140, 140), font=f_small)

    # Column headers and ladder code values
    for c, (title, v_hi, duty, _) in enumerate(COLUMNS):
        gx = lay.gutter_x(c)
        m_srgb, m_g22 = match_values(v_hi, duty)
        v_srgb, v_g22 = match_ints(v_hi, duty)
        draw.text((gx, LOWER_TOP + 4), f"{c + 1}. {title}: dither 0 & {v_hi} ({duty:.0%})",
                  fill=(220, 220, 220), font=f_col)
        draw.text((gx, LOWER_TOP + 26), f"sRGB match {v_srgb} ({m_srgb:.2f})   gamma 2.2 match {v_g22} ({m_g22:.2f})",
                  fill=grey, font=f_tiny)
        for r, v in enumerate(ladder_values(v_hi, duty)):
            sy0 = lay.ladder_top + r * lay.step_h
            colour = tick_colour(v, v_srgb, v_g22) or (120, 120, 120)
            draw.text((gx + 5, sy0 + lay.step_h // 2 - 6), f"{v:3d}", fill=colour, font=f_tiny)

    return np.asarray(pil_img, dtype=np.uint8)


def png_chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def png_chunk_names(path):
    data = path.read_bytes()
    names, pos = [], 8
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        names.append(kind.decode())
        pos += 12 + length
    return names


def write_png(path, rgb_u8, tagged_srgb=False):
    """
    Write an 8-bit RGB PNG directly, so no library adds colour chunks.
      tagged_srgb=False: IHDR + IDAT + IEND only.
      tagged_srgb=True:  adds cICP (1, 13, 0, 1) and sRGB chunks.
    """
    h, w, _ = rgb_u8.shape
    raw = b"".join(b"\x00" + row.tobytes() for row in rgb_u8)
    chunks = [png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))]
    if tagged_srgb:
        # cICP: primaries 1 (BT.709), transfer 13 (IEC 61966-2-1), matrix 0 (RGB), full range
        chunks.append(png_chunk(b"cICP", struct.pack("BBBB", 1, 13, 0, 1)))
        chunks.append(png_chunk(b"sRGB", b"\x00"))
    chunks.append(png_chunk(b"IDAT", zlib.compress(raw, 9)))
    chunks.append(png_chunk(b"IEND", b""))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))
    expected = ["IHDR", "cICP", "sRGB", "IDAT", "IEND"] if tagged_srgb else ["IHDR", "IDAT", "IEND"]
    assert png_chunk_names(path) == expected
    print(f"Wrote {path.name:34s} {path.stat().st_size:>9,} bytes  chunks: {' '.join(expected)}")


def simulate_eye_view(raw_u8, display, shadow_boost=1.0):
    """
    What the eye sees on a display with the given EOTF ("srgb" or "gamma22"): code values to linear light,
    average each aligned 4x4 block (a whole period of both dithers), back to code values with the same curve.
    shadow_boost multiplies the code values of the non-control columns so the result is easy to see.
    Returns the image without annotations.
    """
    v = raw_u8.astype(np.float64) / 255.0
    if display == "srgb":
        lin = srgb_eotf(v)
    elif display == "gamma22":
        lin = v ** 2.2
    else:
        raise ValueError(display)

    sub = lin[UPPER_TOP:, LABEL_W:, :]
    sh, sw = (sub.shape[0] // 4) * 4, (sub.shape[1] // 4) * 4
    blocks = sub[:sh, :sw].reshape(sh // 4, 4, sw // 4, 4, 3).mean(axis=(1, 3), keepdims=True)
    sub[:sh, :sw] = np.broadcast_to(blocks, (sh // 4, 4, sw // 4, 4, 3)).reshape(sh, sw, 3)

    out = srgb_oetf(lin) if display == "srgb" else lin ** (1.0 / 2.2)

    if shadow_boost != 1.0:
        lay = Layout()
        for c, (_, _, _, is_control) in enumerate(COLUMNS):
            if is_control:
                continue
            cx0, cx1 = lay.patch_x(c)
            rows = [lay.band_y(0), lay.band_y(1), (lay.ladder_top, lay.ladder_bot)]
            for y0, y1 in rows:
                out[y0:y1, cx0:cx1] *= shadow_boost

    return np.round(np.clip(out * 255.0, 0, 255)).astype(np.uint8)


def self_check(raw):
    """Fail loudly if the chart would not behave as the README says."""
    lay = Layout()
    assert sum(col[3] for col in COLUMNS) == 1, "exactly one control column"

    for title, v_hi, duty, is_control in COLUMNS:
        m_srgb, m_g22 = match_values(v_hi, duty)
        v_srgb, v_g22 = match_ints(v_hi, duty)
        for name, exact in (("sRGB", m_srgb), ("gamma 2.2", m_g22)):
            assert abs(exact - round(exact)) <= INTEGER_TOLERANCE, \
                f"{title}: {name} match {exact:.2f} is not close to an integer"
        if is_control:
            assert v_srgb == v_g22, f"{title}: control matches differ ({v_srgb} vs {v_g22})"
        else:
            assert abs(v_srgb - v_g22) >= MIN_SHADOW_DIFFERENCE, f"{title}: matches too close"
        ladder = ladder_values(v_hi, duty)
        for v in (v_srgb, v_g22):
            assert ladder[0] < v < ladder[-1], f"{title}: match {v} is not bracketed by the ladder"
        assert 0 <= ladder[0] and ladder[-1] <= 255

    # Both halves of each check patch emit the same light on any display (compare mean code value: two levels).
    for x0, y0, x1, y1 in (CHECK_SCALE, CHECK_SHARP):
        xm = (x0 + x1) // 2
        assert raw[y0:y1, x0:xm].mean() == raw[y0:y1, xm:x1].mean(), "check patch halves differ"

    # Simulated displays: the right word shows, the other vanishes, the control column is blank.
    for display, shown in (("srgb", "sRGB"), ("gamma22", "2.2")):
        sim = simulate_eye_view(raw, display)[..., 0].astype(int)
        for b, (word, _) in enumerate(BANDS):
            by0, by1 = lay.band_y(b)
            for c, (title, _, _, is_control) in enumerate(COLUMNS):
                cx0, cx1 = lay.patch_x(c)
                spread = int(np.ptp(sim[by0:by1, cx0:cx1]))
                if word == shown and not is_control:
                    assert spread >= 2, f"{display}: '{word}' not visible in {title} (spread {spread})"
                else:
                    assert spread <= 1, f"{display}: '{word}' should vanish in {title} (spread {spread})"
        # Ladder: the step at this display's match equals the dither around it.
        for c, (title, v_hi, duty, _) in enumerate(COLUMNS):
            v_srgb, v_g22 = match_ints(v_hi, duty)
            target = v_srgb if display == "srgb" else v_g22
            r = ladder_values(v_hi, duty).index(target)
            sy0 = lay.ladder_top + r * lay.step_h
            cx0, cx1 = lay.patch_x(c)
            spread = int(np.ptp(sim[sy0:sy0 + lay.step_h, cx0:cx1]))
            assert spread <= 1, f"{display}: ladder step {target} does not vanish in {title} (spread {spread})"
    print("Self-check passed.")


def print_table():
    print(f"{'Column':<12} {'Dither':<14} {'sRGB match':>12} {'g2.2 match':>12} {'Diff':>7}")
    print("-" * 60)
    for title, v_hi, duty, _ in COLUMNS:
        m_srgb, m_g22 = match_values(v_hi, duty)
        dither = f"0 & {v_hi} ({duty:.0%})"
        print(f"{title:<12} {dither:<14} {round(m_srgb):4d} ({m_srgb:6.2f}) {round(m_g22):4d} ({m_g22:6.2f}) "
              f"{m_srgb - m_g22:+7.2f}")
    print()


def main():
    print_table()
    raw = make_raw_patches()
    self_check(raw)

    chart = annotate_chart(raw)
    write_png(HERE / "srgb_vs_gamma22_untagged.png", chart, tagged_srgb=False)
    write_png(HERE / "srgb_vs_gamma22_tagged_srgb.png", chart, tagged_srgb=True)

    for display in ("srgb", "gamma22"):
        sim = annotate_chart(simulate_eye_view(raw, display, SIM_SHADOW_BOOST), sim=display)
        write_png(HERE / f"simulated_on_{display}_display.png", sim, tagged_srgb=True)


if __name__ == "__main__":
    main()
