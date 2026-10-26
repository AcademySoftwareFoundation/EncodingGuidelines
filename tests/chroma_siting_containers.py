"""
Where chroma siting (chroma sample location) is recorded, per codec and container, and whether DNxHR in MXF
gets a label that matches its pixels.

Part 1: encodes a small frame whose chroma location is known (set with zscale chromal=...) with each codec
and container, then reads back the codec's own field (via the trace_headers bitstream filter), the
container's field (Matroska ChromaSitingHorz/Vert, MXF ColorSiting, found in the file bytes), and what
ffprobe reports.

Part 2: encodes sourceimages/chroma_siting_chart.png to DNxHR HQX 4:2:2 in MXF (OP1a and OP-Atom) with the
commands from EncodeDNXHD.md and with zscale, and compares the MXF ColorSiting label with where the chroma
actually is in the decoded DNxHR (measured as in tests/chroma_siting.py).

    rez-env encodingguidelines_env ffmpeg-9.0 -- python tests/chroma_siting_containers.py
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chroma_siting as cs  # noqa: E402

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")
DEFAULT_OUTDIR = HERE / "chroma-siting"

SMALL_SRC = ["-f", "lavfi", "-i", "color=c=0x8080C0:s=320x240,format=rgb48be"]
CODECS = {  # name: (encoder args, chroma formats, containers, encoder name)
    "h264": (["-c:v", "libx264", "-qp", "0"], ["420", "422"], ["mp4", "mkv", "mov"], "libx264"),
    "hevc": (["-c:v", "libx265", "-x265-params", "lossless=1:log-level=error"], ["420", "422"],
             ["mp4", "mkv", "mov"], "libx265"),
    "av1-svt": (["-c:v", "libsvtav1", "-preset", "12"], ["420"], ["mp4", "mkv"], "libsvtav1"),
    "av1-aom": (["-c:v", "libaom-av1", "-cpu-used", "8", "-crf", "30"], ["420", "422"], ["mp4", "mkv"], "libaom-av1"),
    "prores": (["-c:v", "prores_ks", "-profile:v", "3"], ["422"], ["mov", "mkv", "mxf"], "prores_ks"),
    "dnxhr": (["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx"], ["422"], ["mov", "mkv", "mxf"], "dnxhd"),
}
LOCATIONS = {"420": ["left", "center", "topleft"], "422": ["left", "center"]}
H264_LOC = {0: "left", 1: "center", 2: "topleft", 3: "top", 4: "bottomleft", 5: "bottom"}
AV1_LOC = {0: "unknown", 1: "vertical (= left)", 2: "colocated (= topleft)"}
MKV_SITING = {0: "unspecified", 1: "left/top", 2: "half"}
# SMPTE ST 377-1 ColorSiting.
MXF_SITING = {0: "0 co-sited", 1: "1 horizontal midpoint", 2: "2 three tap", 3: "3 quincunx", 4: "4 Rec.601",
              5: "5 line alternating", 6: "6 vertical midpoint", 255: "255 unknown"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, **kw)


def encoders():
    out = run([FFMPEG, "-hide_banner", "-encoders"], text=True).stdout
    return {line.split()[1] for line in out.splitlines() if len(line.split()) > 1}


def bitstream_field(path):
    trace = run([FFMPEG, "-hide_banner", "-i", str(path), "-c", "copy", "-bsf:v", "trace_headers",
                 "-f", "null", "-"], text=True).stderr
    m = re.search(r"chroma_loc_info_present_flag\s+\S+\s*=\s*(\d)", trace)
    if m:
        if m.group(1) == "0":
            return "not written"
        return H264_LOC.get(int(re.search(r"chroma_sample_loc_type_top_field\s+\S+\s*=\s*(\d)", trace).group(1)))
    m = re.search(r"chroma_sample_position\s+\S+\s*=\s*(\d)", trace)
    if m:
        return AV1_LOC.get(int(m.group(1)))
    if re.search(r"seq_profile|subsampling_x", trace):
        return "no field (not 4:2:0)"
    return "no field"


def container_field(path, ext):
    data = Path(path).read_bytes()
    if ext == "mkv":
        h = re.search(rb"\x55\xB7\x81(.)", data, re.S)
        v = re.search(rb"\x55\xB8\x81(.)", data, re.S)
        return (f"H {MKV_SITING.get(h.group(1)[0]) if h else 'not written'}, "
                f"V {MKV_SITING.get(v.group(1)[0]) if v else 'not written'}")
    if ext == "mxf":
        return mxf_siting(data)
    return "no field"


def mxf_siting(data):
    m = re.search(rb"\x33\x03\x00\x01(.)", data, re.S)
    return MXF_SITING.get(m.group(1)[0], str(m.group(1)[0])) if m else "not written"


def part1(available, tmp):
    lines = ["## Where chroma siting is recorded", "",
             "Frames carry the chroma location in the first column (set with `zscale ... chromal=`).", "",
             "| Codec | Chroma | Container | Frames say | Codec field | Container field | ffprobe |",
             "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    for codec, (args, fmts, exts, enc) in CODECS.items():
        if enc not in available:
            lines.append(f"| {codec} | | | | no `{enc}` in this build | | |")
            continue
        for fmt in fmts:
            pix = f"yuv{fmt}p10le"
            for loc in LOCATIONS[fmt]:
                for ext in exts:
                    out = Path(tmp) / f"{codec}_{fmt}_{loc}.{ext}"
                    r = run([FFMPEG, "-v", "error", "-y", *SMALL_SRC, "-frames:v", "1", "-vf",
                             f"zscale=rangein=full:matrix=709:range=limited:chromal={loc},format={pix}",
                             *args, "-pix_fmt", pix, str(out)], text=True)
                    if r.returncode:
                        lines.append(f"| {codec} | 4:{fmt[1]}:{fmt[2]} | {ext} | {loc} | error | | |")
                        continue
                    probe = run([FFPROBE, "-v", "error", "-show_entries", "stream=chroma_location",
                                 "-of", "csv=p=0", str(out)], text=True).stdout.strip()
                    lines.append(f"| {codec} | 4:{fmt[1]}:{fmt[2]} | {ext} | {loc} | {bitstream_field(out)} | "
                                 f"{container_field(out, ext)} | {probe} |")
    return lines


def part2(available, tmp):
    lines = ["", "## DNxHR HQX 4:2:2 in MXF", "",
             "Label is the MXF `ColorSiting`; position is where the chroma actually is in the decoded DNxHR "
             "(0 = co-sited, as the label 0 says; 0.5 = centred), from the chart's single-pixel lines (the mean of "
             "the even- and odd-column results). At 10-bit the tent measurement is only good to about +/-0.05 and "
             "DNxHR compression noise adds to that, so the lines are used here.", "",
             "| Wrapper | Command | MXF ColorSiting | Chroma position | Lines |",
             "| :--- | :--- | :--- | :--- | :--- |"]
    if "dnxhd" not in available:
        return lines + ["| | no `dnxhd` in this build | | | |"]
    dnx = ["-c:v", "dnxhd", "-profile:v", "dnxhr_hqx", "-pix_fmt", "yuv422p10le"]
    scale = "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
    zs = "zscale=rangein=full:matrix=709:range=limited"
    flags = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    commands = {
        "scale (EncodeDNXHD.md before Oct 2026)": ["-vf", scale],
        "scale + out_chroma_loc=left + full_chroma_inp": ["-sws_flags", "bicubic+full_chroma_inp",
                                                         "-vf", scale + ":out_chroma_loc=left"],
        "zscale": ["-vf", zs],
        "zscale chromal=left": ["-vf", zs + ":chromal=left"],
        "zscale chromal=topleft": ["-vf", zs + ":chromal=topleft"],
    }
    w, h = cs.W, cs.H
    for wrapper in ("mxf", "mxf_opatom"):
        for name, args in commands.items():
            out = Path(tmp) / f"dnx_{wrapper}_{re.sub(r'[^a-z]+', '_', name)}.mxf"
            r = run([FFMPEG, "-v", "error", "-y", "-i", str(cs.SOURCE), "-frames:v", "1", *args, *dnx, *flags,
                     "-f", wrapper, str(out)], text=True)
            if r.returncode:
                lines.append(f"| {wrapper} | `{name}` | error | | |")
                continue
            raw = run([FFMPEG, "-v", "error", "-i", str(out), "-f", "rawvideo", "-pix_fmt", "yuv422p10le", "-"]).stdout
            planes = np.frombuffer(raw, "<u2").astype(np.float64)
            cb = planes[w * h:w * h + w // 2 * h].reshape(h, w // 2)
            band = cb[2 * cs.BAND + cs.BAND // 2]
            even, odd = cs.line_offset(band, cs.chart.EVEN_COLUMNS), cs.line_offset(band, cs.chart.ODD_COLUMNS)
            pos = round((even + odd) / 2, 3)
            lines.append(f"| {wrapper} | `{name}` | {mxf_siting(out.read_bytes())} | {cs.describe(pos)} | "
                         f"{cs.lines(even, odd)} |")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--label", help="Name for this run (default: the FFmpeg version)")
    args = parser.parse_args()
    version = run([FFMPEG, "-hide_banner", "-version"], text=True).stdout.split("\n")[0].split()[2]
    label = args.label or version
    available = encoders()
    with tempfile.TemporaryDirectory() as tmp:
        lines = [f"# Chroma siting in codecs and containers ({label})", "", f"FFmpeg build: `{version}`.", ""]
        lines += part1(available, tmp) + part2(available, tmp)
    text = "\n".join(lines) + "\n"
    args.outdir.mkdir(parents=True, exist_ok=True)
    path = args.outdir / f"containers-{label}.md"
    path.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
