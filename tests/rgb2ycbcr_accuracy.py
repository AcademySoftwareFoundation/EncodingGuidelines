"""
Measure the accuracy of ffmpeg's RGB to Y'CbCr conversions against the SMPTE RP 219 references.

Converts Resolve's full-range RGB bars (8-, 10- and 16-bit DPX) to BT.709 limited-range Y'CbCr
at 8, 10 and 12 bits, in 4:4:4, 4:2:2 and 4:2:0, with each converter. Output is raw video, so no
codec is involved.

Each result is compared with the ideal conversion of that source's own RGB values, using the
BT.709 formula that sourceimages/rp219/validate_reference.py checks against the SMPTE RP 219
references. A correct converter should therefore match exactly whatever the source bit depth.
Only patch interiors are compared, where chroma is constant, so for 4:2:2 and 4:2:0 the result
does not depend on the chroma filter or siting. See sourceimages/README.md for the references.

Run once per FFmpeg version, each time with that version's ffmpeg on the PATH (or FFMPEG_BIN and
FFPROBE_BIN set), naming the run with --label; then combine the runs into summary.md:
    python tests/rgb2ycbcr_accuracy.py --label 9.0
    python tests/rgb2ycbcr_accuracy.py --summarize
With a rez setup that has an ffmpeg-<version> package per version, --rez runs them all and summarizes:
    python tests/rgb2ycbcr_accuracy.py --rez 6.0 7.0 7.1 8.0.1 8.1 9.0
"""
import argparse
import json
import re
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RP219 = HERE.parent / "sourceimages" / "rp219"
sys.path.insert(0, str(RP219))
from validate_reference import bt709_limited, flat, read_rgb  # noqa: E402

DEFAULT_OUTDIR = HERE / "rgb2ycbcr-accuracy"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")

SOURCES = {"8-bit": "smptehdbars_8_from16.dpx", "10-bit": "smptehdbars_10_resolve.dpx",
           "16-bit": "smptehdbars_16_resolve.dpx"}
# pix_fmt: (bits, horizontal chroma subsampling, vertical chroma subsampling)
TARGETS = {
    "yuv444p": (8, 1, 1), "yuv422p": (8, 2, 1), "yuv420p": (8, 2, 2),
    "yuv444p10le": (10, 1, 1), "yuv422p10le": (10, 2, 1), "yuv420p10le": (10, 2, 2),
    "yuv444p12le": (12, 1, 1), "yuv422p12le": (12, 2, 1), "yuv420p12le": (12, 2, 2),
}
CHROMA = {(1, 1): "4:4:4", (2, 1): "4:2:2", (2, 2): "4:2:0"}

# name: (description, ffmpeg args before the output, needs filter). {fmt} is the output pix_fmt.
CONVERTERS = {
    "scale": ("scale, default flags",
              ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format={fmt}"], None),
    "scale_accurate": ("scale with -sws_flags spline+accurate_rnd+full_chroma_int",
                       ["-sws_flags", "spline+accurate_rnd+full_chroma_int",
                        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format={fmt}"], None),
    "scale_unstable": ("scale with flags=unstable",
                       ["-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=unstable,format={fmt}"], None),
    "zscale": ("zscale",
               ["-vf", "zscale=rangein=full:matrix=709:range=limited,format={fmt}"], "zscale"),
    "auto": ("no filter, -colorspace bt709 -color_range tv (auto-inserted scale)",
             ["-colorspace", "bt709", "-color_range", "tv"], None),
}

# Patches reported by value, as (x, y) in the reference layout.
PATCHES = {"100% white": (343, 675), "75% white": (343, 300), "0% black": (1700, 945)}


def run(cmd):
    return subprocess.run(cmd, capture_output=True)


def ffmpeg_info():
    version = run([FFMPEG, "-hide_banner", "-version"]).stdout.decode().split("\n")[0].split()[2]
    filters = run([FFMPEG, "-hide_banner", "-filters"]).stdout.decode()
    has_zscale = any(line.split()[1:2] == ["zscale"] for line in filters.splitlines() if line.strip())
    return {"version": version, "filters": ["zscale"] if has_zscale else []}


def convert(source, fmt, args, shape):
    """Convert the first frame to raw planes at fmt. Returns ([Y, Cb, Cr], error)."""
    bits, sx, sy = TARGETS[fmt]
    args = [a.format(fmt=fmt) for a in args]
    result = run([FFMPEG, "-v", "error", "-i", str(source), "-frames:v", "1", *args,
                  "-f", "rawvideo", "-pix_fmt", fmt, "-"])
    h, w = shape
    ch, cw = h // sy, w // sx
    dtype = "u1" if bits == 8 else "<u2"
    data = np.frombuffer(result.stdout, dtype)
    if result.returncode or data.size != h * w + 2 * ch * cw:
        return None, result.stderr.decode().strip().splitlines()[-1:] or ["no output"]
    data = data.astype(np.int64)
    return [data[:h * w].reshape(h, w), data[h * w:h * w + ch * cw].reshape(ch, cw),
            data[h * w + ch * cw:].reshape(ch, cw)], None


def measure(outdir, label=None):
    info = ffmpeg_info()
    results = {"ffmpeg": info, "label": label or info["version"], "results": {}}
    for src_name, src_file in SOURCES.items():
        rgb, _ = read_rgb(RP219 / src_file)
        # 8 pixels clear of any edge: wide filters (e.g. -sws_flags spline) ring up to ~8 pixels into a
        # patch when subsampling chroma, which is a filter property rather than a conversion error.
        mask = flat(np.moveaxis(np.round(rgb * 65535), -1, 0), margin=8)
        for fmt, (bits, sx, sy) in TARGETS.items():
            ideal = bt709_limited(rgb, bits)
            # Chroma is constant inside patches, so subsampling the ideal 4:4:4 there is exact.
            ideal_planes = [ideal[0], ideal[1][::sy, ::sx], ideal[2][::sy, ::sx]]
            masks = [mask, mask[::sy, ::sx], mask[::sy, ::sx]]
            for conv, (desc, args, needs) in CONVERTERS.items():
                key = f"{CHROMA[(sx, sy)]} | {src_name} -> {bits}-bit | {conv}"
                if needs and needs not in info["filters"]:
                    results["results"][key] = {"skipped": f"no {needs}"}
                    continue
                planes, err = convert(RP219 / src_file, fmt, args, rgb.shape[:2])
                if err:
                    results["results"][key] = {"error": err}
                    continue
                diffs = [np.abs(p - i)[m] for p, i, m in zip(planes, ideal_planes, masks)]
                results["results"][key] = {
                    "description": desc,
                    "max_per_plane": [int(d.max()) for d in diffs],
                    "mean_per_plane": [round(float(d.mean()), 4) for d in diffs],
                    "patches": {name: int(planes[0][y, x]) for name, (x, y) in PATCHES.items()},
                    "expected": {name: int(ideal[0][y, x]) for name, (x, y) in PATCHES.items()},
                }
    vdir = outdir / (label or info["version"])
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "results.json").write_text(json.dumps(results, indent=2))
    print(f"Wrote {vdir / 'results.json'}")


def summarize(outdir):
    runs = [json.loads(f.read_text()) for f in outdir.glob("*/results.json")]
    runs.sort(key=lambda r: [int(n) if n.isdigit() else 0 for n in re.split(r"[.-]", r.get("label", "99"))])
    versions = [r.get("label") or r["ffmpeg"]["version"] for r in runs]
    builds = ", ".join(f"{r.get('label')} = `{r['ffmpeg']['version']}`" for r in runs if r.get("label"))
    lines = ["# RGB to Y'CbCr accuracy", "",
             "Each cell is the Y' of the 100% white patch (spec: 235 at 8-bit, 940 at 10-bit, 3760 at 12-bit), "
             "then the worst Y/Cb/Cr error over patch interiors, in code values at the output bit depth, against "
             "the ideal BT.709 conversion of the source's RGB. A correct converter is exact (0).", "",
             f"FFmpeg builds: {builds}.", ""]
    keys = []
    for r in runs:
        keys += [k for k in r["results"] if k not in keys]
    for chroma in CHROMA.values():
        lines += ["", f"## {chroma}", "",
                  "| Source -> output | converter | " + " | ".join(versions) + " |",
                  "| :--- | :--- |" + " :--- |" * len(versions)]
        for key in [k for k in keys if k.startswith(chroma)]:
            row = []
            for r in runs:
                e = r["results"].get(key)
                if e is None:
                    row.append("n/a")
                elif "skipped" in e:
                    row.append(e["skipped"])
                elif "error" in e:
                    row.append("error")
                else:
                    row.append(f"{e['patches']['100% white']} · {e['max_per_plane']}")
            _, conversion, conv = key.split(" | ")
            lines.append(f"| {conversion} | {conv} | " + " | ".join(row) + " |")
    text = "\n".join(lines) + "\n"
    (outdir / "summary.md").write_text(text)
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--rez", nargs="+", metavar="VERSION",
                        help="Run once per rez ffmpeg version, then summarize")
    parser.add_argument("--summarize", action="store_true", help="Only rebuild summary.md")
    parser.add_argument("--label", help="Column name for this run in the summary (--rez uses the rez version)")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.rez:
        for version in args.rez:
            print(f"=== ffmpeg-{version}")
            subprocess.run(["rez-env", "encodingguidelines_env", f"ffmpeg-{version}", "--",
                            "python", __file__, "--outdir", str(args.outdir), "--label", version])
        summarize(args.outdir)
    elif args.summarize:
        summarize(args.outdir)
    else:
        measure(args.outdir, args.label)


if __name__ == "__main__":
    main()
