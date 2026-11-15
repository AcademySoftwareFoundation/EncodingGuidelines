# Piecewise sRGB or Pure Gamma 2.2? A Display EOTF Test Chart

This folder holds a generator (`make_srgb_vs_gamma22_chart.py`) and a visual test chart that tells whether a display, or the whole viewing pipeline in front of it, follows the **piecewise sRGB EOTF (IEC 61966-2-1)** or a **pure $\gamma = 2.2$ power law**.

The chart shows the word **`sRGB`** on a piecewise sRGB display and the word **`2.2`** on a pure gamma 2.2 display.

## Reading the Chart

View the chart at one image pixel per device pixel (see [Viewing at 1:1](#viewing-at-11)), straight on, then work through three steps:

1. **Checks (top right).** In patch **A** and in patch **B**, the fine left half and the coarse right half must look equally bright.
   - A differs: the image is being resampled. Fix the zoom or scaling.
   - B differs (usually the fine half is brighter): the display or viewer is sharpening. Turn sharpening off.
   - If either check fails, nothing below can be trusted.
2. **Control (column 4).** Both curves agree here, so no word should be readable in either band, and in the ladder the step at the green tick (`135`) should vanish. If a word shows, or a different step vanishes, the display is neither curve (pure gamma 2.4 vanishes near `139`), and the shadow columns do not decide anything.
3. **Result (columns 1–3).** Squint or step back so the dither blends.
   - **Words:** the word you can read names your display. The other band is a flat field.
   - **Ladder:** find the solid step that vanishes into the dither around it. It sits at the cyan tick on a piecewise sRGB display and at the amber tick on a pure gamma 2.2 display. The left half of each column is line dither and the right half is checkerboard dither; both should give the same answer.

If the three shadow columns disagree with each other, or the step vanishes away from both ticks, the display is neither curve in the shadows.

`simulated_on_srgb_display.png` and `simulated_on_gamma22_display.png` show what to expect on each display (with the shadow columns brightened so they are easy to see on any screen).

## What the Result Means

The chart measures everything between the PNG and your eye: the viewer, the operating system's colour management and the panel. On a colour-managed system an sRGB-tagged image can come out as piecewise sRGB on a panel that is itself gamma 2.2, because the system converts between the two.

The two PNGs have identical pixels. If they look different in the same viewer, that viewer treats untagged images differently from sRGB-tagged ones (for example by sending untagged pixels straight to the display).

## Viewing at 1:1

The dither is one pixel wide, so any scaling breaks the test. Check A catches it, but these avoid it:

- **Browser:** open `view.html`. It sizes the chart to one image pixel per device pixel on 2× Retina displays, fractional scaling (such as Windows 150%) and any browser zoom, and switches between the untagged and tagged files. Do not pinch-zoom.
- **Image viewer or player:** use 100% / actual pixels on a display with no scaling. On a 2× display, "100%" in many viewers doubles the image with smoothing; use `view.html` instead.

Also view the screen straight on: VA and TN panels change gamma with viewing angle, which moves the match.

## How the Test Works

A fine dither between black (`0`) and a code value $V_{\text{hi}}$ with duty cycle $d$ is averaged by the eye in **linear light**. A solid patch $V_{\text{solid}}$ matches it when

$$\text{EOTF}(V_{\text{solid}}) = d \cdot \text{EOTF}(V_{\text{hi}})$$

- **Pure $\gamma = 2.2$:** $V_{\text{solid}} = d^{1/2.2} \cdot V_{\text{hi}}$, a constant fraction of $V_{\text{hi}}$ ($0.7297$ for $d = 0.50$, $0.5325$ for $d = 0.25$).
- **Piecewise sRGB:** the linear segment below 8-bit code `10.3` and the $0.055$ offset above it pull the match 3 to 5 code values lower in the shadows.
- At $V_{\text{hi}} = 185$ the two curves give the same match (`135`), which makes it the control.

A black level or screen flare adds the same light to the dither and to the solid, so it does not move the match; it only lowers the contrast you see.

| Column | Dither | Piecewise sRGB match | Pure $\gamma = 2.2$ match | Luminance error of the wrong match |
| :--- | :--- | :---: | :---: | :---: |
| **1. Deep toe** | `0 & 18` (50%) | **10** (`9.96`) | **13** (`13.14`) | 33–45% |
| **2. Upper toe** | `0 & 26` (50%) | **16** (`15.96`) | **19** (`18.97`) | 26–31% |
| **3. 25% shadow** | `0 & 43` (25%) | **18** (`17.98`) | **23** (`22.90`) | 41–42% |
| **4. Control** | `0 & 185` (50%) | **135** (`135.08`) | **135** (`135.00`) | 0% |

The levels are chosen so both matches fall within `0.15` of an 8-bit integer, so rounding does not blur the result. The last column is how far off the other curve's patch is on each display; that is what makes the word readable.

The word `sRGB` is drawn with the gamma 2.2 match, so it vanishes on a gamma 2.2 display and stands out on an sRGB one. The word `2.2` is drawn with the sRGB match.

Highlights are not used: at peak white the two curves differ by about 2% in luminance, which is too little to see reliably.

## Generating the Files

```bash
python tests/srgb-vs-gamma22/make_srgb_vs_gamma22_chart.py
```

Needs `numpy` and `Pillow`. The script checks itself before writing anything and stops if a check fails: both matches near integers, both matches inside the ladder, and, on a simulated display of each kind, the right word visible, the other word and the control column flat, and the right ladder step vanishing.

- `srgb_vs_gamma22_untagged.png`: 8-bit PNG with `IHDR`, `IDAT` and `IEND` only (no colour chunks).
- `srgb_vs_gamma22_tagged_srgb.png`: identical pixels with `cICP` (`1, 13, 0, 1`) and `sRGB` chunks.
- `simulated_on_srgb_display.png`, `simulated_on_gamma22_display.png`: the chart as the eye sees it on each display (4×4 linear-light averaging, shadow columns brightened 3.2×).
- `view.html`: the 1:1 browser viewer (written by hand, not generated).

To change the test levels, edit `COLUMNS` in the script; labels, ticks and the ladder follow from it, but update the table above by hand from the script's printed output.
