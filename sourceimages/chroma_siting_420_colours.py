"""
Check, or search for, the band colours of the 4:2:0 chroma siting player chart
(make_chroma_siting_player_chart_420.py), for SDR (BT.709, display gamma 2.4) or HDR10 (BT.2020, PQ).

Each band repeats a four-pixel cycle along one direction (across or down): luma Y0..Y3 and chroma samples X and Z,
which alternate, one per two pixels. A player rebuilds the chroma at each pixel in one of two ways:

  co-sited  sample j sits on pixel 2j: pixel 2j gets mid +- s*d, pixel 2j+1 gets mid, where mid = (X+Z)/2,
            d = (X-Z)/2, and s is 1 for an interpolating filter, down to 0.75 for a smoothing one
  centred   sample j sits between pixels 2j and 2j+1: both get mid +- a*d, a = 0.5 (linear) to 1 (sample repeat)

The mirror block has the same chroma and the luma permuted. Mirrored through a sample, the co-sited family gives
the same set of pixels in both blocks; mirrored between two pixels, the centred family does. Seen from a distance,
the eye compares the linear-light means of the two blocks, so a band's contrast for a player is the Oklab
distance between those means. For each band this gives the smallest contrast over the wrong family (it should be
large) and over the right one (it should be 0), checks that every pixel is in gamut for every player, and the
distance between the bands' uniform colours.

    python sourceimages/chroma_siting_420_colours.py            # check the SDR and PQ colours in the chart script
    python sourceimages/chroma_siting_420_colours.py --search --seed 3   # search for PQ colours (the chart uses seed 3)
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

MIRROR = {"co-sited": [0, 3, 2, 1], "centred": [1, 0, 3, 2]}
COSITED_S = np.linspace(0.75, 1.0, 6)
CENTRED_A = np.linspace(0.5, 1.0, 6)
GAMUT_TOL = 0.003          # the colours touch the gamut edge; allow for the rounding of the published values
M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
               [0.0883024619, 0.2817188376, 0.6299787005]])
M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
               [0.0259040371, 0.7827717662, -0.8086757660]])
# Linear BT.2020 to linear BT.709 (Oklab's M1 expects linear sRGB/BT.709 primaries).
BT2020_TO_709 = np.array([[1.6605, -0.5876, -0.0728], [-0.1246, 1.1329, -0.0083], [-0.0182, -0.1006, 1.1187]])


def pq_eotf(e):
    """PQ signal (0..1) to luminance in cd/m^2."""
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    p = np.power(np.clip(e, 0, 1), 1 / m2)
    return 10000 * np.power(np.maximum(p - c1, 0) / (c2 - c3 * p), 1 / m1)


def pq_oetf(nits):
    m1, m2, c1, c2, c3 = 0.1593017578125, 78.84375, 0.8359375, 18.8515625, 18.6875
    y = np.power(np.asarray(nits) / 10000, m1)
    return np.power((c1 + c2 * y) / (1 + c3 * y), m2)


class Mode:
    """How Y'CbCr becomes light: matrix, transfer, and the range of R'G'B' allowed. For PQ the range applies to
    R'G'B' re-expressed in BT.709 primaries, which every HDR display can show, so no display gamut maps it."""

    def __init__(self, kr, kb, to_linear, rgb_max, to_709=None, rgb_min=0.0):
        self.kr, self.kb, self.to_linear, self.rgb_max, self.to_709 = kr, kb, to_linear, rgb_max, to_709
        self.rgb_min = rgb_min

    def rgb(self, y, cb, cr):
        kr, kb = self.kr, self.kb
        r = y + 2 * (1 - kr) * cr
        b = y + 2 * (1 - kb) * cb
        g = (y - kr * r - kb * b) / (1 - kr - kb)
        return np.stack([r, g, b], -1)

    def linear709(self, rgb):
        lin = self.to_linear(rgb)
        return lin @ self.to_709.T if self.to_709 is not None else lin

    def gamut_signal(self, rgb):
        """The values to check against rgb_min..rgb_max."""
        if self.to_709 is None:
            return rgb
        nits = self.linear709(rgb) * 100
        return np.where(nits < 0, -1.0, pq_oetf(np.maximum(nits, 0)))


SDR = Mode(0.2126, 0.0722, lambda e: np.clip(e, 0, 1) ** 2.4, 1.0)
PQ_MAX_NITS = 100.0         # keep every pixel at or below this, so no display tone maps it and screenshots do not clip
PQ_MIN_NITS = 1.0          # and at or above this, so the result does not depend on how a display handles near-black
PQ = Mode(0.2627, 0.0593, lambda e: pq_eotf(e) / 100.0, float(pq_oetf(PQ_MAX_NITS)), BT2020_TO_709,
          float(pq_oetf(PQ_MIN_NITS)))


def oklab(lin):
    return np.cbrt(np.maximum(lin, 0) @ M1.T) @ M2.T


def chroma(family, p, X, Z):
    """Chroma (cb, cr) at pixels u = 0..3 for one player."""
    mid, d = (X + Z) / 2, (X - Z) / 2
    if family == "co-sited":
        return np.array([mid + p * d, mid, mid - p * d, mid])
    return np.array([mid + p * d, mid + p * d, mid - p * d, mid - p * d])


def evaluate(mode, mirror, X, Z, lumas, tol=GAMUT_TOL):
    """(wrong-family contrast, right-family contrast, in gamut, uniform colour as Oklab) for one band."""
    X, Z, lumas = np.asarray(X, float), np.asarray(Z, float), np.asarray(lumas, float)
    lum_m = lumas[MIRROR[mirror]]
    contrast = {}
    in_gamut = True
    uniform = None
    for family, params in (("co-sited", COSITED_S), ("centred", CENTRED_A)):
        cs = []
        for p in params:
            c = chroma(family, p, X, Z)
            a = mode.rgb(lumas, c[:, 0], c[:, 1])
            b = mode.rgb(lum_m, c[:, 0], c[:, 1])
            ga, gb = mode.gamut_signal(a), mode.gamut_signal(b)
            lo, hi = min(ga.min(), gb.min()), max(ga.max(), gb.max())
            in_gamut &= bool(lo >= mode.rgb_min - tol and hi <= mode.rgb_max + tol)
            la, lb = mode.linear709(a).mean(0), mode.linear709(b).mean(0)
            cs.append(np.linalg.norm(oklab(la) - oklab(lb)))
            if family == mirror and uniform is None:
                uniform = oklab(la)
        contrast[family] = min(cs) if family != mirror else max(cs)
    wrong = "centred" if mirror == "co-sited" else "co-sited"
    return contrast[wrong], contrast[mirror], in_gamut, uniform


def report(name, mode, bands):
    print(name)
    uniforms = []
    for label, _, _, mirror, (X, Z, lumas) in bands:
        wrong, right, ok, uni = evaluate(mode, mirror, X, Z, lumas)
        uniforms.append(uni)
        print(f"  {label:30s} wrong band >= {wrong:.3f}   right band <= {right:.4f}   in gamut: {ok}")
    sep = min(np.linalg.norm(uniforms[i] - uniforms[j]) for i in range(4) for j in range(i + 1, 4))
    print(f"  smallest distance between the uniform colours: {sep:.3f}")


def search(mirror, rng, others=(), min_sep=0.12, iters=60000):
    """Random search, then hill climbing, for the largest wrong-family contrast, with every pixel in gamut (strictly,
    after rounding to three decimals) and the band's uniform colour at least min_sep from the others' (Oklab)."""
    def score(v):
        v = np.round(v, 3)
        wrong, _, ok, uni = evaluate(PQ, mirror, v[0:2], v[2:4], v[4:8], tol=0.0)
        if not ok or any(np.linalg.norm(uni - o) < min_sep for o in others):
            return -1, None
        return wrong, uni

    best, best_s, best_u = None, -1, None
    for _ in range(iters):
        v = np.concatenate([rng.uniform(-0.25, 0.25, 4), rng.uniform(PQ.rgb_min, PQ.rgb_max, 4)])
        s, u = score(v)
        if s > best_s:
            best, best_s, best_u = v, s, u
    if best is None:
        raise SystemExit("no colours found that meet the constraints; try another --seed")
    step = 0.02
    while step > 1e-4:
        improved = False
        for _ in range(400):
            v = best + rng.normal(0, step, 8)
            s, u = score(v)
            if s > best_s:
                best, best_s, best_u, improved = v, s, u, True
        if not improved:
            step /= 2
    return np.round(best, 3), best_s, best_u


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--search", action="store_true", help="Search for PQ band colours")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    from make_chroma_siting_player_chart_420 import BANDS, BANDS_PQ
    if args.search:
        rng = np.random.default_rng(args.seed)
        found = []
        for label, _, _, mirror, _ in BANDS_PQ:
            v, s, u = search(mirror, rng, found)
            found.append(u)
            print(f"{label}: (({v[0]}, {v[1]}), ({v[2]}, {v[3]}), ({v[4]}, {v[5]}, {v[6]}, {v[7]}))  wrong >= {s:.3f}")
        return
    report("SDR (BT.709, gamma 2.4)", SDR, BANDS)
    report(f"HDR10 (BT.2020, PQ, {PQ_MIN_NITS:g} to {PQ_MAX_NITS:g} cd/m^2)", PQ, BANDS_PQ)


if __name__ == "__main__":
    main()
