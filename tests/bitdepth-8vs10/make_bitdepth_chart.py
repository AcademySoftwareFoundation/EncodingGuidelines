"""
Generate 16-bit RGB test charts and animated 10-bit / 8-bit motion test videos to visually
determine whether an encoding pipeline, media player (e.g. OpenRV, xStudio), GPU compositor,
or display signal path is 10-bit or 8-bit.

How Color (4:2:0-safe) and Motion Amplify a 1-LSB Step
------------------------------------------------------
1. RGB Opponent Color Lever (Columns 1-3 — tests 8-bit OpenGL / Display bottlenecks):
   * State 0 has (R=q_lo, G=q_hi, B=q_lo); State 1 has (R=q_hi, G=q_lo, B=q_hi).
   * On a 10-bit path, they differ by only 1/1023 (0.25 of an 8-bit step).
   * Across an 8-bit RGB boundary, State 0 quantizes to Green (K, K+1, K) while State 1
     quantizes to Magenta (K+1, K, K+1) — a 2-step opponent Green-vs-Magenta jump!

2. 4:2:0-Safe Y'CbCr 3-Channel Matrix Lever (Columns 4-5 — tests 8-bit Y'CbCr video encodes):
   * In 10-bit BT.709 limited-range Y'CbCr, State 0 sets (Y = 4*K + q_hi, Cb = 512 + q_lo, Cr = 512 + q_lo)
     and State 1 sets (Y = 4*K + q_lo, Cb = 512 + q_hi, Cr = 512 + q_hi).
   * In 10-bit: the -1 step in Y cancels out most of the +1 step in Cb/Cr, so in 10-bit RGB the two
     states differ by only +0.16 step in R, +0.24 step in B, and -0.48 step in G (nearly invisible!).
   * In 8-bit Y'CbCr (even 4:2:0, because all bars and 8x8 glyph blocks are multiples of 2x2 pixels!):
     Y rounds one way while Cb and Cr both round the opposite way. When decoded through the BT.709
     matrix (1.8556*Cb, 1.5748*Cr), this produces a 2.86-STEP Green-to-Magenta RGB jump!

3. Motion / Temporal Strobe & Marching Bars (in the encoded videos):
   * The human visual system is 5x-10x more sensitive to 3-6 Hz temporal flicker and lateral motion
     than to a static 1-LSB edge (which fades due to retinal Troxler adaptation).
   * In the animated videos (`bitdepth_motion_10bit_hevc.mp4`, `bitdepth_motion_8bit_hevc.mp4`,
     `bitdepth_motion_10bit_prores.mov`), Band S sweeps the quarter-step phase q(t) = (t // 2) % 4:
     - On a TRUE 10-BIT path: the difference is a constant 1/1023 on every frame — ZERO flashing
       and ZERO marching bars!
     - On ANY 8-BIT path: every time q(t) crosses the 8-bit cliff (3 times per second at 24 fps),
       "8-BIT" FLASHES ON in Green/Magenta, and every 4th vertical bar lights up and MARCHES
       horizontally across the column!

Usage:
    python tests/bitdepth-8vs10/make_bitdepth_chart.py
    rez-env ffmpeg-8.1 -- python tests/bitdepth-8vs10/make_bitdepth_chart.py --encode
"""
import argparse
import os
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1920, 1080
HEADER_H = 96
BANDS_TOP = HEADER_H
BAND_H = 154
BAND_GAP = 6
LABEL_W = 328

# 6 Columns in the photopic sweet spot (K = 32..64):
#   Cols 1-3: RGB Opponent (Green vs Magenta) — catches 8-bit OpenGL / GPU / display bottlenecks
#   Cols 4-5: Y'CbCr 4:2:0 3-Channel Lever    — produces a 2.9-step RGB jump on 8-bit Y'CbCr video encodes
#   Col  6:   Neutral Grey TV Luma            — pure achromatic reference
COLUMNS = [
    ("1. RGB Opp Dark",   "pc_opp",    32),
    ("2. RGB Opp Mid",    "pc_opp",    48),
    ("3. RGB Opp Brt",    "pc_opp",    64),
    ("4. YCbCr 420 Dark", "ycbcr_opp", 36),
    ("5. YCbCr 420 Mid",  "ycbcr_opp", 52),
    ("6. Neutral TV Mid", "tv",        48),
]

GLYPHS_5X7 = {
    "8": [" 111 ", "1   1", "1   1", " 111 ", "1   1", "1   1", " 111 "],
    "-": ["     ", "     ", "     ", "11111", "     ", "     ", "     "],
    "B": ["1111 ", "1   1", "1   1", "1111 ", "1   1", "1   1", "1111 "],
    "I": [" 111 ", "  1  ", "  1  ", "  1  ", "  1  ", "  1  ", " 111 "],
    "T": ["11111", "  1  ", "  1  ", "  1  ", "  1  ", "  1  ", "  1  "],
    "1": ["  1  ", " 11  ", "  1  ", "  1  ", "  1  ", "  1  ", " 111 "],
    "2": [" 111 ", "1   1", "    1", "  11 ", " 1   ", "1    ", "11111"],
    "X": ["1   1", "1   1", " 1 1 ", "  1  ", " 1 1 ", "1   1", "1   1"],
    " ": ["     ", "     ", "     ", "     ", "     ", "     ", "     "],
}


def code16_for_quarter_step(mode, k8, q):
    """
    Return the exact 16-bit scalar (0..65535) for 8-bit integer `k8` + `q`/4:
      * "tv": maps via limited-range (64 + round(c16/65535 * 876)) to exact 10-bit code 4*k8 + q.
      * "pc" / "pc_opp": guarantees Band B (q=1->2) is the 8-bit nearest-rounding boundary and
        Band D (q=3->4) is both the 8-bit bit-shift (c16 >> 8) and floor boundary.
    """
    q_mod = q % 4
    k_adj = k8 + (q // 4)
    if mode == "tv":
        target_y10 = 4 * k_adj + q_mod
        bias = 0.08 if q_mod == 2 else (0.04 if q_mod == 0 else 0.0)
        return int(round(((target_y10 - 64 + bias) / 876.0) * 65535.0))
    elif mode in ("pc", "pc_opp"):
        if q_mod == 0:
            return 257 * k_adj + 16
        elif q_mod == 1:
            return 257 * k_adj + 80
        elif q_mod == 2:
            return 257 * k_adj + 144
        else:
            return 256 * (k_adj + 1) - 16
    else:
        raise ValueError(mode)


def ycbcr10_to_rgb16(y10, cb10, cr10):
    """Convert exact 10-bit limited-range BT.709 (Y, Cb, Cr) to 16-bit full-range RGB."""
    y = (y10 - 64.0) / 876.0
    cb = (cb10 - 512.0) / 896.0
    cr = (cr10 - 512.0) / 896.0
    r = y + 1.5748 * cr
    b = y + 1.8556 * cb
    g = (y - 0.2126 * r - 0.0722 * b) / 0.7152
    return np.round(np.clip(np.array([r, g, b]), 0.0, 1.0) * 65535.0).astype(np.uint16)


def rgb16_pair(mode, k8, q_lo, q_hi):
    """
    Return (rgb_lo, rgb_hi) as 3-element uint16 arrays:
      * "tv" / "pc": neutral grey (c_lo, c_lo, c_lo) and (c_hi, c_hi, c_hi).
      * "pc_opp": Green/Magenta RGB opponent:
          rgb_lo = (c_lo, c_hi, c_lo)  -> Green on 8-bit RGB boundary
          rgb_hi = (c_hi, c_lo, c_hi)  -> Magenta on 8-bit RGB boundary
      * "ycbcr_opp": 4:2:0-safe BT.709 Y'CbCr 3-channel opponent lever:
          rgb_lo has (Y10 = 4*k8 + q_hi, Cb10 = 512 + q_lo, Cr10 = 512 + q_lo)
          rgb_hi has (Y10 = 4*k8 + q_lo, Cb10 = 512 + q_hi, Cr10 = 512 + q_hi)
          In 10-bit, -dY cancels +dCb/+dCr so RGB diff is < 0.5 step.
          In 8-bit Y'CbCr, Y rounds opposite to Cb/Cr, producing a 2.86-step Green/Magenta RGB jump!
    """
    if mode == "ycbcr_opp":
        b_lo = 0.08 if (q_lo % 4) == 2 else (0.04 if (q_lo % 4) == 0 else 0.0)
        b_hi = 0.08 if (q_hi % 4) == 2 else (0.04 if (q_hi % 4) == 0 else 0.0)
        rgb_lo = ycbcr10_to_rgb16(4 * k8 + q_hi + b_hi, 512 + q_lo + b_lo, 512 + q_lo + b_lo)
        rgb_hi = ycbcr10_to_rgb16(4 * k8 + q_lo + b_lo, 512 + q_hi + b_hi, 512 + q_hi + b_hi)
        return rgb_lo, rgb_hi

    c_lo = code16_for_quarter_step(mode, k8, q_lo)
    c_hi = code16_for_quarter_step(mode, k8, q_hi)
    if mode == "pc_opp":
        return np.array([c_lo, c_hi, c_lo], dtype=np.uint16), np.array([c_hi, c_lo, c_hi], dtype=np.uint16)
    return np.array([c_lo, c_lo, c_lo], dtype=np.uint16), np.array([c_hi, c_hi, c_hi], dtype=np.uint16)


def block_aligned_text_mask(h, w, text, block=8):
    """Render glyph mask where every pixel is an 8x8 block (exact multiple of 2x2 4:2:0 chroma blocks!)."""
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
    y0 = max(0, ((h - sh) // 2 // 4) * 4)
    x0 = max(0, ((w - sw) // 2 // 4) * 4)
    mask[y0:y0 + min(h, sh), x0:x0 + min(w, sw)] = scaled[:min(h, sh), :min(w, sw)]
    return mask


def layout_geometry():
    col_area_w = W - LABEL_W - 12
    n_cols = len(COLUMNS)
    col_w = (col_area_w // n_cols // 16) * 16
    return col_w


def make_band_cell(h, w, mode, k8, q_lo, q_hi, text="8-BIT", cell_kind="substep", frame_idx=0):
    """
    Build a single (h, w, 3) uint16 cell:
      * cell_kind == "ref":
          Left half = 2-step 8-bit control ("2X", q=0 vs q=8).
          Right half = 1-step 8-bit control ("1X", q=0 vs q=4).
      * cell_kind == "motion":
          Top 44px: Marching 4-phase vertical bar wave where bar m has phase q = (m - frame_idx // 2) % 4.
                    On an 8-bit path, every 4th bar lights up and marches left-to-right!
          Bottom:   6 Hz Strobing "8-BIT" sign whose phase sweeps q(t) = (frame_idx // 2) % 4.
                    On an 8-bit path, "8-BIT" flashes ON every 4th beat! On 10-bit it stays steady!
      * cell_kind == "substep":
          Top 40px: 16px-wide vertical bars of (q_lo, q_hi).
          Bottom:   Bold 8x8-block-aligned "8-BIT" watermark of (q_lo, q_hi).
    """
    cell = np.empty((h, w, 3), dtype=np.uint16)
    bar_h = 44
    txt_h = h - bar_h
    _, xx = np.mgrid[0:bar_h, 0:w]
    bars = (((xx // 16) % 2) == 1)[..., None]

    if cell_kind == "ref":
        hw = (w // 2 // 16) * 16
        lo_2x, hi_2x = rgb16_pair(mode, k8, 0, 8)
        lo_1x, hi_1x = rgb16_pair(mode, k8, 0, 4)
        cell[:bar_h, :hw] = np.where(bars[:, :hw], hi_2x, lo_2x)
        cell[:bar_h, hw:] = np.where(bars[:, hw:], hi_1x, lo_1x)
        mask_2x = block_aligned_text_mask(txt_h, hw, "2X", block=6)
        mask_1x = block_aligned_text_mask(txt_h, w - hw, "1X", block=6)
        cell[bar_h:, :hw] = np.where(mask_2x[..., None], hi_2x, lo_2x)
        cell[bar_h:, hw:] = np.where(mask_1x[..., None], hi_1x, lo_1x)
    elif cell_kind == "motion":
        # Top 44px: Marching 16px bar wave (each 16px bar m tests phase q_m = (m - frame_idx // 2) % 4)
        n_bars = w // 16
        for m in range(n_bars):
            qm = (m - (frame_idx // 2)) % 4
            lo_m, hi_m = rgb16_pair(mode, k8, qm, qm + 1)
            # Top half of bar is hi_m, bottom half is lo_m (so the bar lights up when qm crosses 8-bit cliff)
            cell[:bar_h // 2, m * 16:(m + 1) * 16] = hi_m
            cell[bar_h // 2:bar_h, m * 16:(m + 1) * 16] = lo_m
        # Bottom: Strobing "8-BIT" sign sweeping q(t) = (frame_idx // 2) % 4
        qt = (frame_idx // 2) % 4
        lo_t, hi_t = rgb16_pair(mode, k8, qt, qt + 1)
        mask = block_aligned_text_mask(txt_h, w, text, block=6)
        cell[bar_h:] = np.where(mask[..., None], hi_t, lo_t)
    else:
        rgb_lo, rgb_hi = rgb16_pair(mode, k8, q_lo, q_hi)
        cell[:bar_h] = np.where(bars, rgb_hi, rgb_lo)
        mask = block_aligned_text_mask(txt_h, w, text, block=6)
        cell[bar_h:] = np.where(mask[..., None], rgb_hi, rgb_lo)

    return cell


def make_raw_patches_16bit(frame_idx=0, is_motion_layout=False):
    """Build the 1920x1080 16-bit RGB array (uint16, 0..65535) before text labels."""
    img16 = np.full((H, W, 3), 18 * 257, dtype=np.uint16)
    img16[:HEADER_H, :] = 24 * 257
    img16[:, :LABEL_W] = 20 * 257

    col_w = layout_geometry()

    # Dimmed Scale Check in top-right of header (uses code 20 and code 90 to avoid glare)
    sx0, sy0, sx1, sy1 = 1580, 10, 1900, 86
    sxm = (sx0 + sx1) // 2
    yy, xx = np.mgrid[sy0:sy1, sx0:sx1]
    fine = np.where(((yy + xx) % 2) == 1, 90 * 257, 20 * 257)
    coarse = np.where((((yy - sy0) // 20 + (xx - sxm) // 20) % 2) == 1, 90 * 257, 20 * 257)
    scale_patch = np.where(xx < sxm, fine, coarse).astype(np.uint16)
    img16[sy0:sy1, sx0:sx1] = scale_patch[..., None]

    # 6 Bands:
    #   Band 0: Reference ("2X | 1X" 8-bit positive control)
    #   Band 1: Motion Strobe & Marching Wave (or in static PNG, 4-phase spatial wave across the 4 letters of 8-BIT!)
    #   Bands 2..5: Static Pigeonhole Sub-Steps A (0/1), B (1/2), C (2/3), D (3/4)
    band_specs = [
        (0, 4, "ref"),
        (1, 2, "motion"),
        (0, 1, "substep"),
        (1, 2, "substep"),
        (2, 3, "substep"),
        (3, 4, "substep"),
    ]

    for c_idx, (_, mode, k8) in enumerate(COLUMNS):
        cx0 = LABEL_W + c_idx * col_w + 8
        cx1 = LABEL_W + (c_idx + 1) * col_w - 8
        cw = ((cx1 - cx0) // 16) * 16
        cx1 = cx0 + cw

        for b_idx, (q_lo, q_hi, kind) in enumerate(band_specs):
            by0 = BANDS_TOP + b_idx * (BAND_H + BAND_GAP) + 16
            by1 = by0 + BAND_H - 16
            bh = by1 - by0
            img16[by0:by1, cx0:cx1] = make_band_cell(
                bh, cw, mode, k8, q_lo, q_hi, text="8-BIT", cell_kind=kind, frame_idx=frame_idx
            )

    return img16


def build_annotation_overlay():
    """Pre-compute the static text annotation overlay once so rendering 48 video frames is fast."""
    dummy8 = np.zeros((H, W, 3), dtype=np.uint8)
    pil_img = Image.fromarray(dummy8)
    draw = ImageDraw.Draw(pil_img)

    f_title = ImageFont.load_default(size=19)
    f_sub = ImageFont.load_default(size=13)
    f_sec = ImageFont.load_default(size=15)
    f_col = ImageFont.load_default(size=13)
    f_small = ImageFont.load_default(size=12)
    f_tiny = ImageFont.load_default(size=11)

    draw.text((18, 8), "10-Bit vs 8-Bit Signal Path Test (Color-Amplified + Motion Strobe & 4-Band Pigeonhole)",
              fill=(190, 190, 190), font=f_title)
    draw.text((18, 34),
              "1. TOP BAND R ('2X | 1X'): '2X' is a 2-step 8-bit control; '1X' is a 1-step 8-bit control. Cols 1-3 test RGB OpenGL; Cols 4-5 test 4:2:0 Y'CbCr.",
              fill=(155, 155, 155), font=f_sub)
    draw.text((18, 52),
              "2. BAND S (Motion Strobe & Wave): In the video, '8-BIT' FLASHES at 3 Hz and every 4th bar MARCHES across the screen on an 8-bit path!",
              fill=(215, 175, 85), font=f_sub)
    draw.text((18, 70),
              "3. BANDS A, B, C, D (Static Pigeonhole): On any 8-bit path, ONE band lights up with '8-BIT' matching '1X', while the other 3 are blank!",
              fill=(155, 155, 155), font=f_sub)

    sx0 = 1580
    draw.text((sx0 - 148, 16), "1:1 Scale Check ->", fill=(150, 150, 150), font=f_col)
    draw.text((sx0 - 148, 36), "Both halves must", fill=(125, 125, 125), font=f_tiny)
    draw.text((sx0 - 148, 52), "look equally bright", fill=(125, 125, 125), font=f_tiny)

    band_labels = [
        ("Band R: 8-Bit Control ('2X | 1X')",
         "Left='2X' (2 steps), Right='1X' (1 step)",
         "Always visible anchor. Any 8-bit path makes",
         "one band below match '1X'!",
         (215, 175, 85)),
        ("Band S: Motion Strobe & Marching Bars",
         "Top: 4-phase wave (every 4th bar lights on 8b!)",
         "Video: '8-BIT' STROBES at 3 Hz & bars MARCH",
         "on an 8-bit path; calm & steady on 10-bit!",
         (120, 215, 145)),
        ("Band A: +0/4 vs +1/4 (.00 -> .25)",
         "1 LSB in 10-bit (4*K vs 4*K+1)",
         "Lights up if shader/LUT shifts 8b boundary",
         "to the first quarter-step.",
         (150, 150, 150)),
        ("Band B: +1/4 vs +2/4 (.25 -> .50)",
         "8-Bit NEAREST-ROUNDING Boundary!",
         "Lights up with '8-BIT' if pipeline rounds",
         "to nearest 8-bit integer.",
         (215, 165, 75)),
        ("Band C: +2/4 vs +3/4 (.50 -> .75)",
         "1 LSB in 10-bit (4*K+2 vs 4*K+3)",
         "Lights up if shader/LUT shifts 8b boundary",
         "to the third quarter-step.",
         (150, 150, 150)),
        ("Band D: +3/4 vs +4/4 (.75 -> 1.00)",
         "8-Bit TRUNCATION / OpenGL uint8 Boundary!",
         "Lights up with '8-BIT' if pipeline truncates",
         "(c16 >> 8 or floor) to 8-bit!",
         (95, 185, 225)),
    ]

    for b_idx, (title, l1, l2, l3, col) in enumerate(band_labels):
        by0 = BANDS_TOP + b_idx * (BAND_H + BAND_GAP) + 16
        draw.text((16, by0 + 2), title, fill=col, font=f_sec)
        draw.text((16, by0 + 24), l1, fill=(140, 140, 140), font=f_small)
        draw.text((16, by0 + 42), l2, fill=(120, 120, 120), font=f_tiny)
        draw.text((16, by0 + 58), l3, fill=(120, 120, 120), font=f_tiny)

    col_w = layout_geometry()
    for c_idx, (title, mode, k8) in enumerate(COLUMNS):
        cx0 = LABEL_W + c_idx * col_w + 8
        c_col = (195, 140, 205) if mode == "pc_opp" else ((95, 205, 175) if mode == "ycbcr_opp" else (95, 175, 215))
        tag = "RGB Grn/Mag" if mode == "pc_opp" else ("4:2:0 3x Lever" if mode == "ycbcr_opp" else "Neutral TV")
        header = f"{title} ({tag}, K={k8})"
        draw.text((cx0, BANDS_TOP + 1), header, fill=c_col, font=f_tiny)

    annot8 = np.asarray(pil_img, dtype=np.uint8)
    mask = (annot8[..., 0] > 0) | (annot8[..., 1] > 0) | (annot8[..., 2] > 0)
    return mask, annot8.astype(np.uint16) * 257


OVERLAY_MASK, OVERLAY_RGB16 = build_annotation_overlay()


def annotate_chart_16bit(raw_img16, title_suffix=""):
    out16 = raw_img16.copy()
    out16[OVERLAY_MASK] = OVERLAY_RGB16[OVERLAY_MASK]
    if title_suffix:
        base8 = (out16[:40, :, :] >> 8).astype(np.uint8)
        base8[:32, :1420] = 24
        pil_img = Image.fromarray(base8)
        draw = ImageDraw.Draw(pil_img)
        f_title = ImageFont.load_default(size=19)
        draw.text((18, 8), f"10-Bit vs 8-Bit Test Chart{title_suffix}", fill=(205, 205, 205), font=f_title)
        out16[:40, :, :] = np.asarray(pil_img, dtype=np.uint16) * 257
    return out16


def png_chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def write_png_16bit(path, rgb_u16, tagged_srgb=False):
    """Write a 16-bit big-endian RGB PNG (with or without sRGB/cICP chunks)."""
    h, w, _ = rgb_u16.shape
    be = rgb_u16.astype(">u2")
    raw = b"".join(b"\x00" + row.tobytes() for row in be)
    ihdr = struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0)
    chunks = [png_chunk(b"IHDR", ihdr)]
    if tagged_srgb:
        chunks.append(png_chunk(b"cICP", struct.pack("BBBB", 1, 13, 0, 1)))
        chunks.append(png_chunk(b"sRGB", b"\x00"))
    chunks.append(png_chunk(b"IDAT", zlib.compress(raw, 9)))
    chunks.append(png_chunk(b"IEND", b""))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))
    print(f"Wrote 16-bit {path.name:38s} ({path.stat().st_size:,} bytes, tagged_srgb={tagged_srgb})")


def write_png_8bit(path, rgb_u8):
    h, w, _ = rgb_u8.shape
    raw = b"".join(b"\x00" + row.tobytes() for row in rgb_u8)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunks = [
        png_chunk(b"IHDR", ihdr),
        png_chunk(b"cICP", struct.pack("BBBB", 1, 13, 0, 1)),
        png_chunk(b"sRGB", b"\x00"),
        png_chunk(b"IDAT", zlib.compress(raw, 9)),
        png_chunk(b"IEND", b""),
    ]
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"".join(chunks))
    print(f"Wrote 8-bit  {path.name:38s} ({path.stat().st_size:,} bytes)")


def simulate_pipeline(raw_img16, pipeline="10bit", amplify=6.0):
    """
    Simulate passing the 16-bit chart through:
      * pipeline="10bit":         true 10-bit quantization
      * pipeline="8bit_rounded":  8-bit nearest-rounding bottleneck (lights up Band B & Band S!)
      * pipeline="8bit_truncated":8-bit truncation / GL_UNSIGNED_BYTE bottleneck (lights up Band D!)
    """
    v = raw_img16.astype(np.float64) / 65535.0
    col_w = layout_geometry()
    out = v.copy()

    for c_idx, (_, mode, k8) in enumerate(COLUMNS):
        cx0 = LABEL_W + c_idx * col_w + 8
        cx1 = LABEL_W + (c_idx + 1) * col_w - 8
        cw = ((cx1 - cx0) // 16) * 16
        cx1 = cx0 + cw

        sub = v[BANDS_TOP:, cx0:cx1, :].copy()
        if mode in ("tv", "ycbcr_opp"):
            # Convert to BT.709 limited-range YCbCr, quantize in YCbCr (10-bit vs 8-bit), and decode back to RGB
            r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
            y = 0.2126 * r + 0.7152 * g + 0.0722 * b
            cb = (b - y) / 1.8556
            cr = (r - y) / 1.5748
            if pipeline == "10bit":
                yq = np.round(y * 876.0) / 876.0
                cbq = np.round(cb * 896.0) / 896.0
                crq = np.round(cr * 896.0) / 896.0
            elif pipeline == "8bit_rounded":
                yq = np.floor(y * 219.0 + 0.5) / 219.0
                cbq = np.floor(cb * 224.0 + 0.5) / 224.0
                crq = np.floor(cr * 224.0 + 0.5) / 224.0
            elif pipeline == "8bit_truncated":
                y10 = np.round(y * 876.0).astype(int) + 64
                cb10 = np.round(cb * 896.0).astype(int) + 512
                cr10 = np.round(cr * 896.0).astype(int) + 512
                yq = ((y10 >> 2) - 16) / 219.0
                cbq = ((cb10 >> 2) - 128) / 224.0
                crq = ((cr10 >> 2) - 128) / 224.0
            else:
                raise ValueError(pipeline)
            rq = yq + 1.5748 * crq
            bq = yq + 1.8556 * cbq
            gq = (yq - 0.2126 * rq - 0.0722 * bq) / 0.7152
            q_val = np.stack([rq, gq, bq], axis=-1)
            base_norm = (k8 - 16 + 0.5) / 219.0
        else:
            if pipeline == "10bit":
                q_val = (np.round(sub * 1020.0) / 1020.0)
            elif pipeline == "8bit_rounded":
                q_val = (np.floor(sub * 255.0 + 0.5) / 255.0)
            elif pipeline == "8bit_truncated":
                q_val = ((raw_img16[BANDS_TOP:, cx0:cx1, :] >> 8).astype(np.float64)) / 255.0
            else:
                raise ValueError(pipeline)
            base_norm = (k8 + 0.5) / 255.0

        r0 = raw_img16[BANDS_TOP:, cx0:cx1, 0]
        is_patch = (r0 != 18 * 257) & (r0 != 20 * 257)
        vis = base_norm + (q_val - base_norm) * amplify
        out_col = out[BANDS_TOP:, cx0:cx1, :]
        out[BANDS_TOP:, cx0:cx1, :] = np.where(is_patch[..., None], np.clip(vis, 0.05, 0.95), out_col)

    sim16 = np.round(np.clip(out * 65535.0, 0, 65535)).astype(np.uint16)
    labels = {
        "10bit": " [SIMULATED TRUE 10-BIT PATH (6x contrast boost)]",
        "8bit_rounded": " [SIMULATED 8-BIT ROUNDED PATH -> Band S & Band B light up! (6x boost)]",
        "8bit_truncated": " [SIMULATED 8-BIT TRUNCATED / uint8 PATH -> Band D lights up! (6x boost)]",
    }
    annot16 = annotate_chart_16bit(sim16, title_suffix=labels[pipeline])
    return (annot16 >> 8).astype(np.uint8)


def encode_videos():
    """
    Encode 48-frame (2 s @ 24 fps, looped to 4 s) animated motion test videos where Band S strobes
    "8-BIT" at 3 Hz and marches every 4th bar across the column whenever an 8-bit bottleneck is present!
    """
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    n_unique = 8  # 8 frames = 1 full cycle of the 4 quarter-steps at 2 frames per step
    frames_bytes = []
    for f in range(n_unique):
        raw16 = make_raw_patches_16bit(frame_idx=f)
        annot16 = annotate_chart_16bit(raw16)
        frames_bytes.append(annot16.tobytes())

    # Repeat the 8-frame cycle 9 times = 72 frames (3.0 seconds at 24 fps)
    raw_stream = b"".join(frames_bytes * 9)

    zscale_tv = (
        "zscale=matrix=709:range=limited:dither=none,"
        "setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709"
    )
    src_args = [
        "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}", "-r", "24", "-i", "-"
    ]
    jobs = [
        ("bitdepth_test_10bit_hevc.mp4", [
            *src_args,
            "-vf", f"{zscale_tv},format=yuv420p10le",
            "-c:v", "libx265", "-crf", "0", "-preset", "ultrafast", "-tag:v", "hvc1",
            "-x265-params", "lossless=1:log-level=error",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1",
        ]),
        ("bitdepth_test_8bit_hevc.mp4", [
            *src_args,
            "-vf", f"{zscale_tv},format=yuv420p",
            "-c:v", "libx265", "-crf", "0", "-preset", "ultrafast", "-tag:v", "hvc1",
            "-x265-params", "lossless=1:log-level=error",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1",
        ]),
        ("bitdepth_test_10bit_prores.mov", [
            *src_args,
            "-vf", f"{zscale_tv},format=yuv422p10le",
            "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "iec61966-2-1",
        ]),
    ]
    for name, args in jobs:
        out = HERE / name
        subprocess.run([ffmpeg, "-v", "error", "-y", *args, str(out)], input=raw_stream, check=True)
        print(f"Encoded animated video {out.name:30s} ({out.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--encode", action="store_true", help="Also encode 10-bit and 8-bit motion test videos with FFmpeg")
    args = parser.parse_args()

    HERE.mkdir(parents=True, exist_ok=True)

    # Frame 2 puts Band S at qt = 1 (the .25 -> .50 nearest-rounding boundary) for the static PNG
    raw16 = make_raw_patches_16bit(frame_idx=2)
    chart16 = annotate_chart_16bit(raw16)

    write_png_16bit(HERE / "bitdepth_8vs10_16bit_untagged.png", chart16, tagged_srgb=False)
    write_png_16bit(HERE / "bitdepth_8vs10_16bit_tagged_srgb.png", chart16, tagged_srgb=True)

    for pipe in ["10bit", "8bit_rounded", "8bit_truncated"]:
        sim8 = simulate_pipeline(raw16, pipeline=pipe, amplify=6.0)
        write_png_8bit(HERE / f"simulated_{pipe}_path.png", sim8)

    if args.encode:
        encode_videos()


if __name__ == "__main__":
    main()
