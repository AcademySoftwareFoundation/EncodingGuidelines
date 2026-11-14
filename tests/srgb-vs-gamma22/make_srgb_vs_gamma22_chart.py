"""
Generate visual test charts to distinguish a Piecewise sRGB (IEC 61966-2-1) display response
from a Pure Power-Law Gamma 2.2 response.

How it works
------------
A spatial dither pattern alternating between black (0) and a reference code value V_hi with duty cycle d
emits an average linear luminance of:

    L_dither = d * EOTF(V_hi)   (assuming zero black lift)

A solid patch of code value V_solid matches the brightness of the dither field when:

    V_solid = EOTF^-1( d * EOTF(V_hi) )

For ANY pure power law EOTF(V) = V^gamma, the matching code value is a constant fraction of V_hi
at every brightness level:

    V_solid(gamma=2.2) = d^(1/2.2) * V_hi

Piecewise sRGB, however, has a linear toe (V / 12.92 for V <= 0.04045, i.e. 8-bit code <= 10.3)
followed by a shifted power curve ((V + 0.055) / 1.055)^2.4. Because of the linear toe:
  - In the shadows (V_hi = 18..26 at 50% dither), Piecewise sRGB matches 3 full 8-bit code values
    LOWER than Gamma 2.2 (and 5 code values lower at 25% dither with V_hi = 43).
  - Around V_hi = 185 (50% dither), the two curves cross (both match at 135).
  - At peak white (V_hi = 255, 50% dither), Piecewise sRGB matches 2 code values HIGHER (188 vs 186).

The reference levels V_hi (18, 22, 26, 43@25%, 74, 185, 255) were chosen so that BOTH the Piecewise
sRGB match and the Pure Gamma 2.2 match land within <= 0.08 of exact 8-bit integers, eliminating
8-bit quantization rounding error.

Outputs (written to tests/srgb-vs-gamma22/)
-------------------------------------------
  * srgb_vs_gamma22_untagged.png     8-bit RGB PNG with IHDR/IDAT/IEND only (no colour chunks),
                                     for raw / pass-through viewing at 1:1 native pixel mapping.
  * srgb_vs_gamma22_tagged_srgb.png  Identical pixels with sRGB + cICP(1,13,0,1) chunks, to test
                                     OS/browser colour management when the source is tagged sRGB.
  * srgb_vs_gamma22_2x_retina.png    Untagged chart with 2x2 pixel dither cells, for apps on 2x
                                     HiDPI/Retina displays that map 1 image pixel to 2x2 panel pixels.
  * simulated_on_srgb_display.png    Simulation of how the chart looks to the eye on a true sRGB monitor.
  * simulated_on_gamma22_display.png Simulation of how the chart looks to the eye on a pure gamma 2.2 monitor.

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
UPPER_H = 340
LOWER_TOP = UPPER_TOP + UPPER_H + 16
LABEL_W = 304

# Columns: (title, subtitle, v_hi, duty_cycle)
# Chosen so sRGB and gamma 2.2 both fall on near-exact 8-bit integers.
COLUMNS = [
    ("Deep Toe",     "0 & 18 (50%)",  18,  0.50),
    ("Low Shadow",   "0 & 22 (50%)",  22,  0.50),
    ("Upper Toe",    "0 & 26 (50%)",  26,  0.50),
    ("25% Shadow",   "0 & 43 (25%)",  43,  0.25),
    ("Low Midtone",  "0 & 74 (50%)",  74,  0.50),
    ("Crossover",    "0 & 185 (50%)", 185, 0.50),
    ("Peak White",   "0 & 255 (50%)", 255, 0.50),
]

OFFSETS = list(range(-5, 6))


def srgb_eotf(v):
    """Piecewise sRGB EOTF (IEC 61966-2-1): code value in [0, 1] -> linear light in [0, 1]."""
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_oetf(lin):
    """Piecewise sRGB inverse EOTF: linear light in [0, 1] -> code value in [0, 1]."""
    lin = np.asarray(lin, dtype=np.float64)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * (np.maximum(lin, 0.0) ** (1.0 / 2.4)) - 0.055)


def match_values(v_hi, duty):
    """Return exact floating-point matching code values (0..255) for sRGB, gamma 2.2, and gamma 2.4."""
    v_norm = v_hi / 255.0
    m_srgb = 255.0 * float(srgb_oetf(duty * srgb_eotf(v_norm)))
    m_g22 = v_hi * (duty ** (1.0 / 2.2))
    m_g24 = v_hi * (duty ** (1.0 / 2.4))
    return m_srgb, m_g22, m_g24


def dither_pattern(h, w, v_hi, duty, mode="lines", cell=1):
    """
    Generate an (h, w) uint8 dither array between 0 and v_hi.
      mode="lines": horizontal lines of height `cell` (for duty=0.5, alternating rows;
                    for duty=0.25, 1 bright row out of 4). Immune to horizontal pixel slewing.
      mode="check": checkerboard of size `cell` (for duty=0.5, 50% checkerboard;
                    for duty=0.25, 1 bright cell per 2x2 block).
    """
    yy, xx = np.mgrid[0:h, 0:w]
    yc, xc = yy // cell, xx // cell
    if abs(duty - 0.5) < 1e-6:
        if mode == "lines":
            mask = (yc % 2) == 0
        else:
            mask = ((yc + xc) % 2) == 0
    elif abs(duty - 0.25) < 1e-6:
        if mode == "lines":
            mask = (yc % 4) == 0
        else:
            mask = ((yc % 2) == 0) & ((xc % 2) == 0)
    else:
        raise ValueError(f"Unsupported duty cycle: {duty}")
    return np.where(mask, v_hi, 0).astype(np.uint8)


# 5x7 bitmap glyphs snapped to 4x4 pixel blocks so every dither cycle outside a glyph is 100% complete
GLYPHS_5X7 = {
    "s": [
        " 1111",
        "1    ",
        "1    ",
        " 111 ",
        "    1",
        "    1",
        "1111 ",
    ],
    "R": [
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
        "1 1  ",
        "1  1 ",
        "1   1",
    ],
    "G": [
        " 111 ",
        "1   1",
        "1    ",
        "1 111",
        "1   1",
        "1   1",
        " 111 ",
    ],
    "B": [
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
        "1   1",
        "1   1",
        "1111 ",
    ],
    "2": [
        " 111 ",
        "1   1",
        "    1",
        "  11 ",
        " 1   ",
        "1    ",
        "11111",
    ],
    ".": [
        "     ",
        "     ",
        "     ",
        "     ",
        "     ",
        " 11  ",
        " 11  ",
    ],
}


def block_aligned_text_mask(h, w, text, block=8):
    """
    Render crisp bitmap text where every pixel of the glyph is a `block x block` square (multiple of 4px).
    This guarantees that no dither period (2x2 or 4x4) is ever partially clipped along a letter edge!
    """
    rows = 7
    cols = sum(5 for _ in text) + (len(text) - 1)
    grid = np.zeros((rows, cols), dtype=bool)
    c_off = 0
    for ch in text:
        g = GLYPHS_5X7[ch]
        for r in range(rows):
            for c in range(5):
                if g[r][c] == "1":
                    grid[r, c_off + c] = True
        c_off += 6
    scaled = np.repeat(np.repeat(grid, block, axis=0), block, axis=1)
    sh, sw = scaled.shape
    mask = np.zeros((h, w), dtype=bool)
    y0 = ((h - sh) // 2 // 4) * 4
    x0 = ((w - sw) // 2 // 4) * 4
    mask[y0:y0 + sh, x0:x0 + sw] = scaled
    return mask


def layout_geometry():
    col_area_w = W - LABEL_W - 8
    n_cols = len(COLUMNS)
    col_w = (col_area_w // n_cols // 8) * 8
    band_h = ((UPPER_H - 12) // 2 // 8) * 8
    n_steps = len(OFFSETS)
    ladder_top = LOWER_TOP + 48
    ladder_bot = H - 12
    step_h = ((ladder_bot - ladder_top) // n_steps // 8) * 8
    ladder_bot = ladder_top + step_h * n_steps
    return col_w, band_h, ladder_top, ladder_bot, step_h


def make_raw_patches(cell_size=1):
    """Build the raw pixel patches (before text annotations) so simulations can integrate clean patches."""
    img = np.full((H, W, 3), 6, dtype=np.uint8)
    img[:HEADER_H, :] = 20
    img[:, :LABEL_W] = 14
    img[UPPER_TOP + UPPER_H:LOWER_TOP, :] = 14

    col_w, band_h, ladder_top, ladder_bot, step_h = layout_geometry()
    ladder_h = ladder_bot - ladder_top

    # --- 1. Scale check in top-right of header (x: 1580..1900, y: 12..100) ---
    sx0, sy0, sx1, sy1 = 1580, 12, 1900, 100
    sxm = (sx0 + sx1) // 2
    yy, xx = np.mgrid[sy0:sy1, sx0:sx1]
    fine = ((yy // cell_size + xx // cell_size) % 2) * 255
    coarse = (((yy - sy0) // 20 + (xx - sxm) // 20) % 2) * 255
    scale_patch = np.where(xx < sxm, fine, coarse).astype(np.uint8)
    img[sy0:sy1, sx0:sx1] = scale_patch[..., None]

    # --- 2. Upper section: Two vanishing-pattern bands (Band 0 = Piecewise sRGB, Band 1 = Pure Gamma 2.2) ---
    for b_idx, is_srgb_band in enumerate([True, False]):
        by0 = UPPER_TOP + b_idx * (band_h + 12)
        by1 = by0 + band_h
        watermark = "sRGB" if is_srgb_band else "2.2"
        for c_idx, (_, _, v_hi, duty) in enumerate(COLUMNS):
            cx0 = LABEL_W + c_idx * col_w + 28
            cx1 = LABEL_W + (c_idx + 1) * col_w - 4
            cw = ((cx1 - cx0) // 8) * 8
            cx1 = cx0 + cw
            ch = band_h

            m_srgb, m_g22, _ = match_values(v_hi, duty)
            v_solid = int(round(m_srgb if is_srgb_band else m_g22))

            # Top half of the band cell: 4 alternating solid/dither macro-squares on horizontal-line dither
            # Bottom half of the band cell: full-width "sRGB" or "2.2" watermark on uniform checkerboard dither
            # (Previously splitting left=lines / right=check down the middle cut "sR|GB" and "2.|2" in half!)
            top_h = (ch // 2 // 8) * 8
            bot_h = ch - top_h
            d_lines = dither_pattern(top_h, cw, v_hi, duty, mode="lines", cell=cell_size)
            d_check = dither_pattern(bot_h, cw, v_hi, duty, mode="check", cell=cell_size)

            _, xx_top = np.mgrid[0:top_h, 0:cw]
            tile_w = (cw // 4 // 8) * 8
            macro_solid = ((xx_top // tile_w) % 2) == 1
            top_patch = np.where(macro_solid, v_solid, d_lines)

            txt_mask = block_aligned_text_mask(bot_h, cw, watermark, block=8)
            bot_patch = np.where(txt_mask, v_solid, d_check)

            patch = np.vstack([top_patch, bot_patch])
            img[by0:by1, cx0:cx1] = patch[..., None]

    # --- 3. Lower section: Precision 1-code-value ladder centered on Gamma 2.2 ---
    for c_idx, (_, _, v_hi, duty) in enumerate(COLUMNS):
        # Leave a 24px label gutter on the left of each column so the optical test area has zero text overlay
        gutter_x0 = LABEL_W + c_idx * col_w + 4
        cx0 = LABEL_W + c_idx * col_w + 28
        cx1 = LABEL_W + (c_idx + 1) * col_w - 4
        cw = ((cx1 - cx0) // 8) * 8
        cx1 = cx0 + cw

        img[ladder_top:ladder_bot, gutter_x0:cx0] = 12

        m_srgb, m_g22, _ = match_values(v_hi, duty)
        v_g22_int = int(round(m_g22))

        # Background dither: left half = horizontal 1px lines, right half = 1x1 checkerboard
        d_lines = dither_pattern(ladder_h, cw, v_hi, duty, mode="lines", cell=cell_size)
        d_check = dither_pattern(ladder_h, cw, v_hi, duty, mode="check", cell=cell_size)
        _, xx_c = np.mgrid[0:ladder_h, 0:cw]
        col_patch = np.where(xx_c < cw // 2, d_lines, d_check)
        img[ladder_top:ladder_bot, cx0:cx1] = col_patch[..., None]

        # Solid step boxes down the center of the optical zone (24% to 76% of cw, 8px aligned)
        sx_l = cx0 + ((int(cw * 0.25)) // 8) * 8
        sx_r = cx0 + ((int(cw * 0.75)) // 8) * 8
        for s_idx, delta in enumerate(OFFSETS):
            sy0 = ladder_top + s_idx * step_h
            sy1 = sy0 + step_h
            v_step = int(np.clip(v_g22_int + delta, 0, 255))
            img[sy0:sy1, sx_l:sx_r] = v_step

    return img


def annotate_chart(raw_img, cell_size=1, is_sim=None):
    """Draw all text labels and row markers outside the optical dither/solid comparison zones."""
    img = raw_img.copy()
    col_w, band_h, ladder_top, ladder_bot, step_h = layout_geometry()
    sx0 = 1580

    # Draw indicator ticks in the 24px column gutter
    for c_idx, (_, _, v_hi, duty) in enumerate(COLUMNS):
        gutter_x0 = LABEL_W + c_idx * col_w + 4
        cx0 = LABEL_W + c_idx * col_w + 28
        m_srgb, m_g22, _ = match_values(v_hi, duty)
        v_srgb_int = int(round(m_srgb))
        v_g22_int = int(round(m_g22))
        for s_idx, delta in enumerate(OFFSETS):
            sy0 = ladder_top + s_idx * step_h
            v_step = int(np.clip(v_g22_int + delta, 0, 255))
            if v_step == v_srgb_int and v_step == v_g22_int:
                img[sy0 + 2:sy0 + step_h - 2, gutter_x0:gutter_x0 + 3] = (80, 195, 130)
            elif v_step == v_srgb_int:
                img[sy0 + 2:sy0 + step_h - 2, gutter_x0:gutter_x0 + 3] = (65, 185, 235)
            elif v_step == v_g22_int:
                img[sy0 + 2:sy0 + step_h - 2, gutter_x0:gutter_x0 + 3] = (230, 165, 55)

    pil_img = Image.fromarray(img)
    draw = ImageDraw.Draw(pil_img)
    f_title = ImageFont.load_default(size=22)
    f_sub = ImageFont.load_default(size=15)
    f_band = ImageFont.load_default(size=19)
    f_col = ImageFont.load_default(size=14)
    f_small = ImageFont.load_default(size=13)
    f_tiny = ImageFont.load_default(size=11)

    if is_sim == "srgb":
        tag_note = " [SIMULATED EYE VIEW ON PIECEWISE sRGB MONITOR - Band 1 vanishes]"
    elif is_sim == "gamma22":
        tag_note = " [SIMULATED EYE VIEW ON PURE GAMMA 2.2 MONITOR - Band 2 vanishes]"
    elif cell_size == 2:
        tag_note = " (2x Retina pixel-doubled dither)"
    else:
        tag_note = " (1:1 native pixel dither)"

    draw.text((20, 12), f"Piecewise sRGB vs Pure Gamma 2.2{tag_note}",
              fill=(235, 235, 235), font=f_title)
    draw.text((20, 44),
              "1. TOP BANDS: Step back or squint. On a Piecewise sRGB monitor, the 'sRGB' text & bars in Band 1 vanish.",
              fill=(190, 190, 190), font=f_sub)
    draw.text((20, 66),
              "   On a Pure Gamma 2.2 monitor, the '2.2' text & bars in Band 2 vanish (while Band 1 stands out clearly).",
              fill=(190, 190, 190), font=f_sub)
    draw.text((20, 88),
              "2. BOTTOM LADDER: Find which center solid step dissolves into the dither (left = horiz lines, right = check).",
              fill=(170, 170, 170), font=f_sub)

    draw.text((sx0 - 150, 24), "1:1 Scale Check ->", fill=(210, 210, 210), font=f_col)
    draw.text((sx0 - 150, 46), "Both halves must", fill=(170, 170, 170), font=f_small)
    draw.text((sx0 - 150, 64), "look equally bright", fill=(170, 170, 170), font=f_small)
    draw.text((sx0 - 150, 82), "(view at 100% zoom)", fill=(170, 170, 170), font=f_small)

    # Upper band labels
    b0_y = UPPER_TOP + 20
    draw.text((16, b0_y), "Band 1: Piecewise sRGB", fill=(90, 200, 240), font=f_band)
    draw.text((16, b0_y + 28), "IEC 61966-2-1 (linear toe <= 10)", fill=(170, 170, 170), font=f_small)
    draw.text((16, b0_y + 48), "'sRGB' vanishes on sRGB monitor.", fill=(140, 190, 210), font=f_small)
    draw.text((16, b0_y + 68), "Solid codes: 10, 13, 16, 18, 52, 135, 188", fill=(140, 140, 140), font=f_small)

    b1_y = UPPER_TOP + band_h + 12 + 20
    draw.text((16, b1_y), "Band 2: Pure Gamma 2.2", fill=(235, 175, 70), font=f_band)
    draw.text((16, b1_y + 28), "Power law V^2.2 (no linear toe)", fill=(170, 170, 170), font=f_small)
    draw.text((16, b1_y + 48), "'2.2' vanishes on Gamma 2.2 monitor.", fill=(210, 180, 130), font=f_small)
    draw.text((16, b1_y + 68), "Solid codes: 13, 16, 19, 23, 54, 135, 186", fill=(140, 140, 140), font=f_small)

    # Lower ladder labels on left margin
    draw.text((16, LOWER_TOP + 4), "Step Ladder (1 code/row)", fill=(225, 225, 225), font=f_band)
    draw.text((16, LOWER_TOP + 28), "Centered on Gamma 2.2 (row 0)", fill=(165, 165, 165), font=f_small)

    for s_idx, delta in enumerate(OFFSETS):
        sy0 = ladder_top + s_idx * step_h
        cy = sy0 + step_h // 2 - 7
        if delta == 0:
            label = "  0  <-- Pure Gamma 2.2 (flat across)"
            col = (235, 175, 70)
        elif delta == -3:
            label = " -3  <-- Piecewise sRGB toe (cols 1-3)"
            col = (90, 200, 240)
        elif delta == -5:
            label = " -5  <-- Piecewise sRGB 25% (col 4)"
            col = (90, 200, 240)
        elif delta == -2:
            label = " -2  <-- Piecewise sRGB low-mid (col 5)"
            col = (90, 200, 240)
        elif delta == 2:
            label = " +2  <-- Piecewise sRGB white (col 7)"
            col = (90, 200, 240)
        else:
            label = f"{delta:+3d} code steps"
            col = (135, 135, 135)
        draw.text((16, cy), label, fill=col, font=f_small)

    # Column headers and gutter code numbers
    for c_idx, (title, sub, v_hi, duty) in enumerate(COLUMNS):
        gutter_x0 = LABEL_W + c_idx * col_w + 4
        m_srgb, m_g22, _ = match_values(v_hi, duty)
        v_srgb_int = int(round(m_srgb))
        v_g22_int = int(round(m_g22))

        draw.text((gutter_x0, LOWER_TOP + 4), f"{c_idx + 1}. {title} ({sub})", fill=(220, 220, 220), font=f_col)
        draw.text((gutter_x0, LOWER_TOP + 24),
                  f"sRGB: {v_srgb_int} ({m_srgb:.1f}) | g2.2: {v_g22_int} ({m_g22:.1f})",
                  fill=(170, 170, 170), font=f_tiny)

        for s_idx, delta in enumerate(OFFSETS):
            sy0 = ladder_top + s_idx * step_h
            v_step = int(np.clip(v_g22_int + delta, 0, 255))
            if v_step == v_srgb_int and v_step == v_g22_int:
                col = (100, 220, 150)
            elif v_step == v_srgb_int:
                col = (90, 205, 250)
            elif v_step == v_g22_int:
                col = (240, 180, 70)
            else:
                col = (120, 120, 120)
            draw.text((gutter_x0 + 5, sy0 + step_h // 2 - 6), f"{v_step:3d}", fill=col, font=f_tiny)

    return np.asarray(pil_img, dtype=np.uint8)


def png_chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def write_png(path, rgb_u8, tagged_srgb=False):
    """
    Write an 8-bit RGB PNG directly.
      tagged_srgb=False: IHDR + IDAT + IEND only (completely untagged).
      tagged_srgb=True:  adds cICP (1, 13, 0, 1) and sRGB (0 = perceptual) chunks.
    """
    h, w, _ = rgb_u8.shape
    raw = b"".join(b"\x00" + row.tobytes() for row in rgb_u8)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunks = [png_chunk(b"IHDR", ihdr)]
    if tagged_srgb:
        # cICP: primaries=1 (BT.709/sRGB), transfer=13 (IEC 61966-2-1 sRGB), matrix=0 (RGB), full_range=1
        chunks.append(png_chunk(b"cICP", struct.pack("BBBB", 1, 13, 0, 1)))
        chunks.append(png_chunk(b"sRGB", b"\x00"))
    chunks.append(png_chunk(b"IDAT", zlib.compress(raw, 9)))
    chunks.append(png_chunk(b"IEND", b""))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))
    print(f"Wrote {path.name:36s} ({path.stat().st_size:,} bytes, tagged_srgb={tagged_srgb})")


def simulate_eye_view(raw_patches_u8, display_eotf="srgb", shadow_boost=3.2):
    """
    Simulate how the human eye perceives the raw patches on a display with the given EOTF:
      1. Convert code values to linear light using the display's actual EOTF (sRGB or pure gamma 2.2).
      2. Average each aligned 4x4 pixel block in linear light (exact period of both 50% and 25% dithers).
      3. Convert linear light back to encoded values (boosting shadow display gain on columns 1-4 so the
         dark toe match/mismatch is clearly visible at normal room brightness), then add crisp annotations.
    """
    v = raw_patches_u8.astype(np.float64) / 255.0
    if display_eotf == "srgb":
        lin = srgb_eotf(v)
    elif display_eotf == "gamma22":
        lin = v ** 2.2
    else:
        raise ValueError(display_eotf)

    blurred = lin.copy()
    sub = blurred[UPPER_TOP:, LABEL_W:, :]
    sh, sw, _ = sub.shape
    sh4, sw4 = (sh // 4) * 4, (sw // 4) * 4
    blocks = sub[:sh4, :sw4, :].reshape(sh4 // 4, 4, sw4 // 4, 4, 3).mean(axis=(1, 3), keepdims=True)
    sub[:sh4, :sw4, :] = np.broadcast_to(blocks, (sh4 // 4, 4, sw4 // 4, 4, 3)).reshape(sh4, sw4, 3)

    if display_eotf == "srgb":
        out = srgb_oetf(blurred)
    else:
        out = np.maximum(blurred, 0.0) ** (1.0 / 2.2)

    if shadow_boost > 1.0:
        col_w, _, _, _, _ = layout_geometry()
        for c_idx in range(4):
            cx0 = LABEL_W + c_idx * col_w + 28
            cx1 = LABEL_W + (c_idx + 1) * col_w - 4
            out[UPPER_TOP:, cx0:cx1, :] = np.clip(out[UPPER_TOP:, cx0:cx1, :] * shadow_boost, 0.0, 1.0)

    sim_u8 = np.round(np.clip(out * 255.0, 0, 255)).astype(np.uint8)
    return annotate_chart(sim_u8, cell_size=1, is_sim=display_eotf)


def print_table():
    print("\nReference Dither Levels & Matching Solid Code Values (8-bit 0..255):")
    print(f"{'Column':<15} {'Dither':<14} {'sRGB exact':>12} {'sRGB int':>9} "
          f"{'g2.2 exact':>12} {'g2.2 int':>9} {'Diff (sRGB-g2.2)':>18}")
    print("-" * 95)
    for title, sub, v_hi, duty in COLUMNS:
        m_srgb, m_g22, _ = match_values(v_hi, duty)
        print(f"{title:<15} {sub:<14} {m_srgb:12.2f} {round(m_srgb):9d} "
              f"{m_g22:12.2f} {round(m_g22):9d} {m_srgb - m_g22:+18.2f}")
    print()


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    print_table()

    raw_1x = make_raw_patches(cell_size=1)
    chart_1x = annotate_chart(raw_1x, cell_size=1)
    write_png(HERE / "srgb_vs_gamma22_untagged.png", chart_1x, tagged_srgb=False)
    write_png(HERE / "srgb_vs_gamma22_tagged_srgb.png", chart_1x, tagged_srgb=True)

    raw_2x = make_raw_patches(cell_size=2)
    chart_2x = annotate_chart(raw_2x, cell_size=2)
    write_png(HERE / "srgb_vs_gamma22_2x_retina.png", chart_2x, tagged_srgb=False)

    sim_srgb = simulate_eye_view(raw_1x, display_eotf="srgb", shadow_boost=3.2)
    write_png(HERE / "simulated_on_srgb_display.png", sim_srgb, tagged_srgb=True)

    sim_g22 = simulate_eye_view(raw_1x, display_eotf="gamma22", shadow_boost=3.2)
    write_png(HERE / "simulated_on_gamma22_display.png", sim_g22, tagged_srgb=True)


if __name__ == "__main__":
    main()
