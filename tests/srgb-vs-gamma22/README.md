# Piecewise sRGB vs Pure Gamma 2.2 — Display EOTF Test Chart

This folder contains a generator (`make_srgb_vs_gamma22_chart.py`) and visual test charts designed to tell whether a display (or viewing pipeline) follows the **piecewise sRGB EOTF (IEC 61966-2-1)** or a **pure $\gamma = 2.2$ power law**.

## How the Test Works

A fine spatial dither alternating between black (`0`) and a reference 8-bit code value $V_{\text{hi}}$ with duty cycle $d \in \{0.50, 0.25\}$ is optically averaged by the human eye in **linear luminance**:

$$L_{\text{dither}} = d \cdot \text{EOTF}(V_{\text{hi}})$$

A solid patch of code value $V_{\text{solid}}$ matches the dither field when $\text{EOTF}(V_{\text{solid}}) = L_{\text{dither}}$:

- **Pure $\gamma = 2.2$** ($\text{EOTF}(V) = V^{2.2}$):
  $$V_{2.2} = d^{1/2.2} \cdot V_{\text{hi}}$$
  The ratio $V_{2.2} / V_{\text{hi}}$ is constant across the entire tonal range ($0.7297$ for $d = 0.50$, $0.5325$ for $d = 0.25$).
- **Piecewise sRGB** ($\text{EOTF}(V) = V / 12.92$ for $V \le 0.04045$, else $((V + 0.055)/1.055)^{2.4}$):
  Because of the linear toe below 8-bit code value `10.3` and the $0.055$ offset above it, the matching solid code value shifts strongly across the tonal range relative to $\gamma = 2.2$:
  - **3 to 5 code values LOWER** than $\gamma = 2.2$ in the shadows ($V_{\text{hi}} \in [18..43]$),
  - **Identical** at the crossover ($V_{\text{hi}} = 185 \to 135$),
  - **2 code values HIGHER** at peak white ($V_{\text{hi}} = 255 \to 188$ vs $186$).

The seven reference columns are chosen so that **both** the piecewise sRGB match and the pure $\gamma = 2.2$ match fall within $\le 0.08$ of exact 8-bit integers, eliminating 8-bit quantization rounding error:

| Column | Dither ($0$ & $V_{\text{hi}}$) | Piecewise sRGB Match | Pure $\gamma = 2.2$ Match | Difference ($\text{sRGB} - \gamma 2.2$) |
| :--- | :--- | :---: | :---: | :---: |
| **1. Deep Toe** | `0 & 18` (50%) | **10** (`9.96`) | **13** (`13.14`) | **−3.17** |
| **2. Low Shadow** | `0 & 22` (50%) | **13** (`12.96`) | **16** (`16.05`) | **−3.09** |
| **3. Upper Toe** | `0 & 26` (50%) | **16** (`15.96`) | **19** (`18.97`) | **−3.01** |
| **4. 25% Shadow** | `0 & 43` (25%) | **18** (`17.98`) | **23** (`22.90`) | **−4.92** |
| **5. Low Midtone** | `0 & 74` (50%) | **52** (`51.92`) | **54** (`54.00`) | **−2.08** |
| **6. Crossover** | `0 & 185` (50%) | **135** (`135.08`) | **135** (`135.00`) | **+0.07** |
| **7. Peak White** | `0 & 255` (50%) | **188** (`187.52`) | **186** (`186.08`) | **+1.43** |

## Reading the Chart

1. **1:1 Scale Check (Top Right)**:
   Both halves of the scale check patch (1-pixel checkerboard on the left, 20-pixel checkerboard on the right) must look **equally bright**. If the left half is darker or shows moiré, the viewer or OS is resampling the image.
2. **Upper Section — Vanishing Watermarks (`Band 1: Piecewise sRGB` vs `Band 2: Pure Gamma 2.2`)**:
   - Each column contains four alternating solid/dither bars on top and a block-aligned `sRGB` or `2.2` watermark on the bottom.
   - On a **Piecewise sRGB** display, the **`sRGB`** text and bars in **Band 1** vanish into a flat field, while **`2.2`** in **Band 2** stands out clearly.
   - On a **Pure $\gamma = 2.2$** display, the **`2.2`** text and bars in **Band 2** vanish into a flat field, while **`sRGB`** in **Band 1** stands out clearly.
3. **Lower Section — Precision 1-Code-Value Step Ladder**:
   - Each column shows 11 solid steps ($\pm 5$ code values around the $\gamma = 2.2$ match), flanked by **horizontal-line dither** on the left (immune to horizontal pixel rise/fall slewing) and **checkerboard dither** on the right.
   - On a **Pure $\gamma = 2.2$** display, the matching solid steps form a **flat horizontal line across the middle row (`0` / amber ticks)**.
   - On a **Piecewise sRGB** display, the matching solid steps follow the **cyan ticks** (`-3` in columns 1–3, `-5` in column 4, `-2` in column 5, `0` in column 6, `+2` in column 7).

## Generated Files

Run:

```bash
python tests/srgb-vs-gamma22/make_srgb_vs_gamma22_chart.py
```

- `srgb_vs_gamma22_untagged.png` — Raw 8-bit PNG (`IHDR`, `IDAT`, `IEND` only; no colour chunks) for pass-through / non-colour-managed viewers at 1:1 native pixel mapping.
- `srgb_vs_gamma22_tagged_srgb.png` — Identical pixels with `cICP` (`1, 13, 0, 1`) and `sRGB` chunks to test OS/browser colour management when the image is explicitly tagged as sRGB.
- `srgb_vs_gamma22_2x_retina.png` — Untagged chart with $2 \times 2$ pixel-doubled dither cells for viewing at 100% logical zoom on 2× Retina/HiDPI displays.
- `simulated_on_srgb_display.png` & `simulated_on_gamma22_display.png` — Simulated human-eye views (4×4 linear-light spatial integration with shadow gain boost) demonstrating how the chart responds on each display type.
