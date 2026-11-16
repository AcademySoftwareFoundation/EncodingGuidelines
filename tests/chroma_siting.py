"""
Measure where FFmpeg puts the chroma samples when converting RGB to 4:2:2 and 4:2:0, and what chroma
location it tags the result with, across FFmpeg versions.

Chroma siting (chroma sample location) is where each subsampled chroma sample sits relative to the luma
samples. Professional 4:2:2 (SDI, ProRes, DNxHD) and H.264/HEVC 4:2:0 put the chroma co-sited
horizontally with the even luma samples ("left"); JPEG/MPEG-1 style centres it between two luma samples.

The source is sourceimages/chroma_siting_chart.png (see sourceimages/make_chroma_siting_chart.py). Two
measurements, both in luma samples, 0 = co-sited with the even luma sample (left / top), 0.5 = centred:

  * Tent: the chart's blue tents rise linearly to a peak exactly between two columns (rows). A symmetric
    filter applied to a linear ramp returns the ramp's value at the filter's centre, so intersecting lines
    fitted to both sides of the tent in the chroma plane gives the chroma sample position, independent of
    filter, gain or offset.
  * Lines: the centroid of each single-pixel line's chroma response, for lines on even and on odd columns
    (rows). A correct filter gives the same position for both. If they differ by about 1, the converter
    averaged pairs of pixels before filtering (libswscale does this for RGB input unless full_chroma_inp
    is set), which throws away the real siting.

Run once per FFmpeg version, each time with that version's ffmpeg on the PATH (or FFMPEG_BIN and
FFPROBE_BIN set), naming the run with --label; then combine the runs into summary.md:
    python tests/chroma_siting.py --label 9.0
    python tests/chroma_siting.py --summarize
With a rez setup that has an ffmpeg-<version> package per version, --rez runs them all and summarizes:
    python tests/chroma_siting.py --rez 6.0 7.0 7.1 8.0.1 8.1 9.0
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sourceimages"))
import make_chroma_siting_chart as chart  # noqa: E402

SOURCE = HERE.parent / "sourceimages" / "chroma_siting_chart.png"
DEFAULT_OUTDIR = HERE / "chroma-siting"
FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
W, H, BAND = chart.W, chart.H, chart.BAND

SCALE = "scale=out_color_matrix=bt709:out_range=tv"
FULL_INP = ["-sws_flags", "bicubic+full_chroma_inp"]
# name: (description, ffmpeg args before the output, needs). {fmt} is the output pix_fmt.
CONVERTERS = {
    "scale": ("scale, no chroma options", ["-vf", SCALE + ",format={fmt}"], None),
    "auto": ("no filter, -colorspace bt709 -color_range tv (auto-inserted scale)",
             ["-colorspace", "bt709", "-color_range", "tv"], None),
    "scale_chr_pos": ("scale, out_h_chr_pos=0:out_v_chr_pos=128 (co-sited, centred vertically)",
                      ["-vf", SCALE + ":out_h_chr_pos=0:out_v_chr_pos=128,format={fmt}"], None),
    "scale_chr_pos+full_chroma_inp": ("as scale_chr_pos, with -sws_flags bicubic+full_chroma_inp",
                                      [*FULL_INP, "-vf", SCALE + ":out_h_chr_pos=0:out_v_chr_pos=128,format={fmt}"],
                                      None),
    "scale_chroma_loc_left": ("scale, out_chroma_loc=left",
                              ["-vf", SCALE + ":out_chroma_loc=left,format={fmt}"], "out_chroma_loc"),
    "scale_chroma_loc_left+full_chroma_inp": ("as scale_chroma_loc_left, with -sws_flags bicubic+full_chroma_inp",
                                              [*FULL_INP, "-vf", SCALE + ":out_chroma_loc=left,format={fmt}"],
                                              "out_chroma_loc"),
    "auto+chroma_sample_location": ("no filter, -colorspace/-color_range + -chroma_sample_location left",
                                    ["-colorspace", "bt709", "-color_range", "tv",
                                     "-chroma_sample_location", "left"], None),
    "zscale": ("zscale, no chroma options",
               ["-vf", "zscale=rangein=full:matrix=709:range=limited,format={fmt}"], "zscale"),
    "zscale_chromal_center": ("zscale, chromal=center",
                              ["-vf", "zscale=rangein=full:matrix=709:range=limited:chromal=center,format={fmt}"],
                              "zscale"),
}
TARGETS = {"4:2:2": "yuv422p16le", "4:2:0": "yuv420p16le"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def ffmpeg_info():
    version = run([FFMPEG, "-hide_banner", "-version"]).stdout.decode().split("\n")[0].split()[2]
    filters = run([FFMPEG, "-hide_banner", "-filters"]).stdout.decode()
    scale_help = run([FFMPEG, "-hide_banner", "-h", "filter=scale"]).stdout.decode()
    has = []
    if any(line.split()[1:2] == ["zscale"] for line in filters.splitlines() if line.strip()):
        has.append("zscale")
    if "out_chroma_loc" in scale_help:
        has.append("out_chroma_loc")
    return {"version": version, "features": has}


def convert(fmt, args):
    """Convert the chart to raw planes at fmt. Returns the Cb plane, or (None, error)."""
    args = [a.format(fmt=fmt) for a in args]
    result = run([FFMPEG, "-v", "error", "-i", str(SOURCE), "-frames:v", "1", *args,
                  "-f", "rawvideo", "-pix_fmt", fmt, "-"])
    data = np.frombuffer(result.stdout, "<u2").astype(np.float64)
    sy = 2 if fmt.startswith("yuv420") else 1
    cw, ch = W // 2, H // sy
    if result.returncode or data.size != W * H + 2 * cw * ch:
        return None, result.stderr.decode().strip().splitlines()[-1:] or ["no output"]
    return data[W * H:W * H + cw * ch].reshape(ch, cw), None


def tent_offset(profile, first_luma, n_luma):
    """Chroma position offset (luma samples) from where the two sides of a tent meet.

    profile is the chroma samples covering luma samples first_luma .. first_luma + n_luma."""
    n = len(profile)
    k = np.arange(n)
    edge, gap = max(2, n // 20), max(4, n // 10)
    left = (k > edge) & (k < n // 2 - gap)
    right = (k > n // 2 + gap) & (k < n - edge)
    b1, a1 = np.polyfit(k[left], profile[left], 1)
    b2, a2 = np.polyfit(k[right], profile[right], 1)
    k_apex = (a2 - a1) / (b1 - b2)
    return round(float(first_luma + (n_luma - 1) / 2 - (first_luma + 2 * k_apex)), 3)


def line_offset(profile, positions, first=0):
    """Mean chroma position offset (luma samples) of single-pixel lines at the given luma positions.

    profile is the chroma samples from chroma index first onwards, within the band holding the lines."""
    background = np.median(profile)
    offsets = []
    for pos in positions:
        k0 = pos // 2 - first
        if k0 < 3 or k0 + 4 > len(profile):
            continue
        k = np.arange(k0 - 3, k0 + 4)
        r = profile[k] - background
        offsets.append(pos - 2 * (first + float((k * r).sum() / r.sum())))
    return round(float(np.mean(offsets)), 3)


def measure_one(fmt, args):
    cb, err = convert(fmt, args)
    if cb is None:
        return {"error": err}
    sy = 2 if fmt.startswith("yuv420") else 1
    entry = {
        "tent_h": tent_offset(cb[BAND // 2 // sy], 0, W),
        "lines_h_even": line_offset(cb[(2 * BAND + BAND // 2) // sy], chart.EVEN_COLUMNS),
        "lines_h_odd": line_offset(cb[(2 * BAND + BAND // 2) // sy], chart.ODD_COLUMNS),
    }
    if sy == 2:
        entry["tent_v"] = tent_offset(cb[BAND // 2:BAND, W // 4], BAND, BAND)
        first = 3 * BAND // 2
        entry["lines_v_even"] = line_offset(cb[first:, W // 8], chart.EVEN_ROWS, first)
        entry["lines_v_odd"] = line_offset(cb[first:, 3 * W // 8], chart.ODD_ROWS, first)
    return entry


def chroma_tag(fmt, args):
    """Chroma location written to the H.264 stream by a lossless encode of the chart.

    Read from the bitstream, since ffprobe reports `left` (the H.264 default) when nothing is written. The
    filter chain outputs the encode format directly, so no extra conversion drops the frame's chroma location."""
    enc_fmt = fmt.replace("16le", "10le")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "tag.mp4"
        args = [a.format(fmt=enc_fmt) for a in args]
        r = run([FFMPEG, "-v", "error", "-y", "-i", str(SOURCE), "-frames:v", "1", *args,
                 "-c:v", "libx264", "-qp", "0", "-pix_fmt", enc_fmt, str(out)])
        if r.returncode:
            return "error"
        trace = run([FFMPEG, "-hide_banner", "-i", str(out), "-c", "copy", "-bsf:v", "trace_headers",
                     "-f", "null", "-"]).stderr.decode()
        present = re.search(r"chroma_loc_info_present_flag\s+\S+\s*=\s*(\d)", trace)
        loc = re.search(r"chroma_sample_loc_type_top_field\s+\S+\s*=\s*(\d)", trace)
        if not present or present.group(1) == "0":
            return "not written"
        names = {0: "left", 1: "center", 2: "topleft", 3: "top", 4: "bottomleft", 5: "bottom"}
        return names.get(int(loc.group(1)), loc.group(1)) if loc else "?"


def measure(outdir, label):
    info = ffmpeg_info()
    results = {"ffmpeg": info, "label": label or info["version"], "source": str(SOURCE), "results": {}}
    for chroma, fmt in TARGETS.items():
        for conv, (desc, args, needs) in CONVERTERS.items():
            key = f"{chroma} | {conv}"
            if needs and needs not in info["features"]:
                results["results"][key] = {"skipped": f"no {needs}"}
                continue
            entry = {"description": desc, **measure_one(fmt, args)}
            if "error" not in entry:
                entry["tag"] = chroma_tag(fmt, args)
            results["results"][key] = entry
    vdir = outdir / results["label"]
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / "results.json").write_text(json.dumps(results, indent=2))
    print(f"Wrote {vdir / 'results.json'}")


def describe(offset):
    if abs(offset) < 0.1:
        name = "co-sited"
    elif abs(offset - 0.5) < 0.1:
        name = "centre"
    else:
        return f"{offset:g}"
    exact = abs(offset) < 0.01 or abs(offset - 0.5) < 0.01
    return name if exact else f"{name} ({offset:g})"


def lines(even, odd):
    if abs(even - odd) > 0.5:
        return f"**pair-averaged** ({even:g} / {odd:g})"
    return f"consistent ({even:g} / {odd:g})"


def summarize(outdir):
    runs = [json.loads(f.read_text()) for f in outdir.glob("*/results.json")]
    runs.sort(key=lambda r: [int(n) if n.isdigit() else 0 for n in re.split(r"[.-]", r.get("label", "99"))])
    versions = [r["label"] for r in runs]
    builds = ", ".join(f"{r['label']} = `{r['ffmpeg']['version']}`" for r in runs)
    out = ["# Chroma siting when converting RGB to 4:2:2 and 4:2:0", "",
           "Each converter converts `sourceimages/chroma_siting_chart.png` (16-bit RGB, untagged) to 16-bit "
           "4:2:2 or 4:2:0. Positions are in luma samples: **co-sited** (0) means the chroma sample sits on the "
           "even luma sample, as professional 4:2:2 and H.264/HEVC 4:2:0 expect (`left`); **centre** (0.5) means "
           "half way between two luma samples (JPEG/MPEG-1 style). H.264/HEVC 4:2:0 (`left`) is co-sited "
           "horizontally and centred vertically. Each cell has these lines:", "",
           "| Line | Example | What it is | Correct for pro 4:2:2 / H.264 4:2:0 |",
           "| :--- | :--- | :--- | :--- |",
           "| Position | `co-sited` / `centre` | Measured from the chart's tents: where the chroma samples "
           "actually are. For 4:2:0, horizontal / vertical. | `co-sited` (4:2:0: `co-sited / centre`) |",
           "| Lines | `consistent (0 / 0)` | The position measured from single-pixel lines on even and on odd "
           "columns (rows). A correct filter gives the same for both. **pair-averaged** means they differ by "
           "about 1: the converter averaged pairs of pixels before filtering, which loses the real siting "
           "(libswscale does this for RGB input unless `full_chroma_inp` is set). | `consistent` |",
           "| Tag | `tag not written` | The chroma location written to the H.264 stream by a lossless encode. "
           "`not written` means readers use the H.264 default, `left` (ffprobe also shows `left`). H.264 only "
           "signals this for 4:2:0; 4:2:2 has no field and is assumed co-sited. ProRes and DNxHD have no field "
           "at all. | `left` or `not written` |", "",
           f"FFmpeg builds: {builds}.", ""]
    keys = []
    for r in runs:
        keys += [k for k in r["results"] if k not in keys]
    out += ["| Output | Converter | " + " | ".join(versions) + " |",
            "| :--- | :--- |" + " :--- |" * len(versions)]
    for key in keys:
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
                pos = describe(e["tent_h"])
                lns = lines(e["lines_h_even"], e["lines_h_odd"])
                if "tent_v" in e:
                    pos += " / " + describe(e["tent_v"])
                    lns += "<br>rows: " + lines(e["lines_v_even"], e["lines_v_odd"])
                row.append(f"{pos}<br>{lns}<br>tag {e['tag']}")
        chroma, conv = key.split(" | ")
        out.append(f"| {chroma} | `{conv}` | " + " | ".join(row) + " |")
    text = "\n".join(out) + "\n"
    (outdir / "summary.md").write_text(text)
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--rez", nargs="+", metavar="VERSION", help="Run once per rez ffmpeg version, then summarize")
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
