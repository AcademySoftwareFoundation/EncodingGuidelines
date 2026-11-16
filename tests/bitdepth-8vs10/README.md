---
layout: default
nav_order: 6.18
title: 10-Bit vs 8-Bit Signal Path & Encoding Test Chart
parent: Test Output
---

# 10-Bit vs 8-Bit Signal Path & Encoding Test Chart

This folder contains `make_bitdepth_chart.py` and 16-bit RGB / 10-bit video test patterns designed to visually tell whether an encoding pipeline, video player, GPU compositor, or display signal path is **true 10-bit** or **quantized to 8-bit**.

Unlike traditional smooth gradient ramps—which require squinting for faint Mach bands and are easily fooled by spatial/temporal dithering—this chart uses **three gamma-independent optical mechanisms**.

---

## How the Three Sections Work

Between any two consecutive 8-bit integers $K$ and $K+1$ (which correspond to $4K$ and $4K+4$ in 10-bit), there are four 1-LSB 10-bit quarter-steps:

$$q = 0 \;(K.00), \quad q = 1 \;(K.25), \quad q = 2 \;(K.50), \quad q = 3 \;(K.75), \quad q = 4 \;(K + 1.00)$$

### 1. Top Section — Vanishing `8-BIT` Watermark
- **Background**: A 50/50 horizontal-line spatial dither between $q = 0$ (exact 8-bit $K$) and $q = 4$ (exact 8-bit $K+1$).
  - Because $K$ and $K+1$ are already exact 8-bit integers, **an 8-bit bottleneck passes the dither background through 100% untouched**, and your eye averages it to the midpoint $K + 0.5$ ($q = 2$).
  - Over a tiny $1/255$ span, every monitor EOTF ($\gamma = 2.2$, piecewise sRGB, $\gamma = 2.4$) is locally linear to within $0.002$ of a step, so this match is **completely independent of monitor gamma**.
- **Foreground (`8-BIT` watermark & top bars)**: Drawn in **solid 10-bit midpoint $q = 2$ ($K + 0.5$)**.
  - **True 10-bit path**: Solid $q = 2$ matches the optical average of the $(q=0, q=4)$ dither, so **`8-BIT` and the bars vanish into a flat field**.
  - **8-bit path**: Solid $q = 2$ gets quantized to $q = 4$ (nearest rounding) or $q = 0$ (truncation), while the dither background stays at $q = 2$ — so **`8-BIT` pops out clearly**.

### 2. Middle Section — Four 10-Bit Sub-Step Phase Gratings (`A`, `B`, `C`, `D`)
Each column contains four stacked rows of 16-pixel-wide vertical bars (aligned to $16 \times 16$ codec macroblocks/CTUs):
- **Row A**: alternates $q = 0$ and $q = 1$ ($\Delta = 1$ LSB in 10-bit)
- **Row B**: alternates $q = 1$ and $q = 2$ ($\Delta = 1$ LSB in 10-bit; straddles the **8-bit nearest-rounding** threshold)
- **Row C**: alternates $q = 2$ and $q = 3$ ($\Delta = 1$ LSB in 10-bit)
- **Row D**: alternates $q = 3$ and $q = 4$ ($\Delta = 1$ LSB in 10-bit; straddles the **8-bit truncation** threshold)

What you see:
- **True 10-bit path**: All four rows (**A, B, C, D**) show the **exact same faint 1-LSB bar pattern**.
- **8-bit nearest-rounded path**: Rows **A, C, and D collapse to completely flat zero**, while **Row B jumps 4× in contrast** (a full 8-bit step)!
- **8-bit truncated path**: Rows **A, B, and C collapse to completely flat zero**, while **Row D jumps 4× in contrast**!

### 3. Bottom Section — 10-Bit (16-Step) vs 8-Bit (4-Step) Split Staircase
- **Left half of each column**: Steps by $1/1023$ every row (16 quarter-steps spanning 4 8-bit values).
- **Right half of each column**: Steps by $1/255$ every 4 rows (4 coarse 8-bit steps).
- **True 10-bit path**: The left side steps $4\times$ finer than the right side, with a clear sawtooth step difference along the vertical center seam.
- **8-bit path (no dither)**: Every group of 4 steps on the left collapses into the exact same 8-bit value as the right side, **erasing the center seam** so both halves merge into identical 4-step staircases.
- **8-bit + spatial dither**: Zoomed in, the `.25 / .50 / .75` steps on the left show spatial dither grain, whereas on a true 10-bit path every step is a noiseless uniform plateau.

---

## Limited-Range (`tv`) vs Full-Range (`pc`) Columns

- **Columns 1–3 (`TV Shadow`, `TV Low-Mid`, `TV Midtone`)** are calibrated for **Limited-Range (`tv`: 10-bit `64..940` / 8-bit `16..235`)** Y'CbCr video encodes ($876 = 4 \times 219$).
- **Columns 4–6 (`Full Shadow`, `Full Low-Mid`, `Full Midtone`)** are calibrated for **Full-Range (`pc`: 10-bit `0..1023` / 8-bit `0..255`)** direct 16-bit PNG viewing and full-range RGB pipelines.

| Column | Mode | 16-Bit RGB Codes `[q=0, 1, 2, 3, 4]` | 10-Bit Codes | 8-Bit Nearest Round | 8-Bit Truncated |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **1. TV Shadow** | `tv` | `[2394, 2469, 2548, 2618, 2693]` | `[96, 97, 98, 99, 100]` | `[24, 24, 25, 25, 25]` | `[24, 24, 24, 24, 25]` |
| **2. TV Low-Mid** | `tv` | `[4788, 4863, 4942, 5012, 5087]` | `[128, 129, 130, 131, 132]` | `[32, 32, 33, 33, 33]` | `[32, 32, 32, 32, 33]` |
| **3. TV Midtone** | `tv` | `[9576, 9651, 9730, 9800, 9875]` | `[192, 193, 194, 195, 196]` | `[48, 48, 49, 49, 49]` | `[48, 48, 48, 48, 49]` |
| **4. Full Shadow** | `pc` | `[5140, 5204, 5270, 5333, 5397]` | `[80, 81, 82, 83, 84]` | `[20, 20, 21, 21, 21]` | `[20, 20, 20, 20, 21]` |
| **5. Full Low-Mid** | `pc` | `[7196, 7260, 7326, 7389, 7453]` | `[112, 113, 114, 115, 116]` | `[28, 28, 29, 29, 29]` | `[28, 28, 28, 28, 29]` |
| **6. Full Midtone** | `pc` | `[10280, 10344, 10410, 10473, 10537]` | `[160, 161, 162, 163, 164]` | `[40, 40, 41, 41, 41]` | `[40, 40, 40, 40, 41]` |

---

## Usage

Generate the 16-bit PNGs and simulated views:

```bash
python tests/bitdepth-8vs10/make_bitdepth_chart.py
```

Also encode the 10-bit and 8-bit test videos (requires `ffmpeg` via `rez-env`):

```bash
rez-env ffmpeg-8.1 -- python tests/bitdepth-8vs10/make_bitdepth_chart.py --encode
```
