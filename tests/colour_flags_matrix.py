"""
Check how ffmpeg colour arguments behave across FFmpeg versions.

For each recipe this encodes an untagged 16-bit RGB PNG to 10-bit 4:4:4 YCbCr, then reports:
  * the CICP tags ffprobe sees, plus the MOV/MP4 'colr' atom,
  * which matrix/range the pixels were actually converted with. The decoded
    planes are read raw (no ffmpeg colour conversion) and compared in code
    values against BT.709 and BT.601 expectations computed here in numpy.

They also report the Y' of 100% white (940 at 10-bit), which shows libswscale's white level error for
high-bit-depth sources.

Run every version through rez and summarize:
    rez-env encodingguidelines_env -- python tests/colour_flags_matrix.py --rez 6.0 7.0 7.1 8.0.1 8.1 9.0

Or run with whatever ffmpeg is on the PATH:
    python tests/colour_flags_matrix.py --outdir tests/colour-flags-matrix
"""
import argparse
import json
import re
import os
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np
import OpenImageIO as oiio

HERE = Path(__file__).resolve().parent
# 16-bit, no colour chunks (so nothing is picked up as frame properties). A 16-bit source is used because the
# libswscale white level error only shows with high-bit-depth input.
DEFAULT_SOURCE = HERE.parent / "sourceimages" / "chip-chart-1080-16bit-noicc.png"
sys.path.insert(0, str(HERE.parent / "sourceimages" / "rp219"))
from validate_reference import flat  # noqa: E402
DEFAULT_OUTDIR = HERE / "colour-flags-matrix"

FFMPEG = os.getenv("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.getenv("FFPROBE_BIN", "ffprobe")

# Encode at 10-bit 4:4:4. Decoders may return a different depth (ProRes 4444 decodes as
# 12-bit), so planes are read at their native depth and compared at that depth.
PIX_FMT = "yuv444p10le"
NATIVE_FMTS = {"yuv444p10le": 10, "yuv444p12le": 12}

# Colour tagging flags, as they appear in most guides.
FLAGS = ["-color_range", "tv", "-colorspace", "bt709",
         "-color_primaries", "bt709", "-color_trc", "iec61966-2-1"]
# setparams only sets primaries/transfer. Setting range/matrix here would relabel
# the RGB input frames, which is not what we want.
SETPARAMS = "setparams=color_primaries=bt709:color_trc=iec61966-2-1"
SCALE = "scale=out_color_matrix=bt709:out_range=tv"
# After scale/zscale the frames are YCbCr, so setparams can also label the matrix and range.
# Needed for 6.0, where scale does not set them on its output frames.
SETPARAMS_YUV = SETPARAMS + ":colorspace=bt709:range=tv"
ZSCALE = "zscale=rangein=full:matrix=709:range=limited"

CODECS = {
    "prores": {"encoder": "prores_ks", "ext": ".mov",
               "args": ["-c:v", "prores_ks", "-profile:v", "4444xq", "-qscale:v", "1"]},
    "x264": {"encoder": "libx264", "ext": ".mp4",
             "args": ["-c:v", "libx264", "-qp", "0", "-movflags", "+write_colr"]},
}

# name: (description, -vf chain or None, extra args, needs, codecs)
RECIPES = {
    "minimal": ("no colour arguments", None, [], [], None),
    "flags": ("colour flags only", None, FLAGS, [], None),
    "flags_bsf": ("colour flags + h264_metadata bsf", None,
                  FLAGS + ["-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=13"],
                  [], ["x264"]),
    "setparams_flags": ("setparams + colour flags", SETPARAMS, FLAGS, ["setparams"], None),
    "scale_flags": ("scale + colour flags", SCALE, FLAGS, [], None),
    "scale_setparams_flags": ("scale + setparams + colour flags", SCALE + "," + SETPARAMS, FLAGS,
                              ["setparams"], None),
    "scale_setparams_all_flags": ("scale + setparams incl. matrix/range + colour flags",
                                  SCALE + "," + SETPARAMS_YUV, FLAGS, ["setparams"], None),
    "zscale_setparams_flags": ("zscale + setparams + colour flags", ZSCALE + "," + SETPARAMS, FLAGS,
                               ["zscale", "setparams"], None),
    "setparams_csrange": ("setparams + -colorspace/-color_range only (7.1+ form)", SETPARAMS,
                          ["-color_range", "tv", "-colorspace", "bt709"], ["setparams"], None),
    "zscale_setparams_noflags": ("zscale + setparams, no colour flags", ZSCALE + "," + SETPARAMS, [],
                                 ["zscale", "setparams"], None),
}

KR_KB = {"bt709": (0.2126, 0.0722), "bt601": (0.299, 0.114)}


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ffmpeg_info():
    version = run([FFMPEG, "-hide_banner", "-version"]).stdout.split("\n")[0].split()[2]
    encoders = run([FFMPEG, "-hide_banner", "-encoders"]).stdout
    filters = run([FFMPEG, "-hide_banner", "-filters"]).stdout
    has = lambda text, name: any(line.split()[1:2] == [name] for line in text.splitlines() if line.strip())
    return {"version": version,
            "encoders": [c["encoder"] for c in CODECS.values() if has(encoders, c["encoder"])],
            "filters": [f for f in ("zscale", "setparams") if has(filters, f)]}


def expected_planes(rgb, matrix, full_range, bits):
    """Ideal Y'CbCr code values for full-range R'G'B' (0-1) input, per the matrix and range."""
    kr, kb = KR_KB[matrix]
    kg = 1.0 - kr - kb
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = kr * r + kg * g + kb * b
    cb = (b - y) / (2 * (1 - kb))
    cr = (r - y) / (2 * (1 - kr))
    scale = 1 << (bits - 8)
    if full_range:
        top = (1 << bits) - 1
        planes = (y * top, cb * top + (1 << (bits - 1)), cr * top + (1 << (bits - 1)))
    else:
        planes = (y * 219 * scale + 16 * scale, cb * 224 * scale + 128 * scale, cr * 224 * scale + 128 * scale)
    return np.stack([np.round(p) for p in planes])


def read_rgb(path):
    """Full-range R'G'B' as 0-1 floats, whatever the source bit depth."""
    buf = oiio.ImageBuf(str(path))
    pixels = buf.get_pixels(oiio.FLOAT)
    if pixels is None:
        sys.exit(f"Cannot read {path}: {buf.geterror()}")
    return pixels[..., :3].astype(np.float64)


def probe(path):
    out = run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=pix_fmt,color_range,color_space,color_primaries,color_transfer",
               "-of", "json", str(path)])
    stream = json.loads(out.stdout or "{}").get("streams", [{}])[0]
    return {k: stream.get(k, "unknown") for k in
            ("pix_fmt", "color_range", "color_space", "color_primaries", "color_transfer")}


def colr_atom(path):
    """Return the MOV/MP4 colr atom as 'type primaries/transfer/matrix', or None."""
    data = Path(path).read_bytes()
    i = data.find(b"colr")
    if i < 0:
        return None
    kind = data[i + 4:i + 8].decode("latin-1")
    if kind not in ("nclc", "nclx"):
        return kind
    p, t, m = struct.unpack(">HHH", data[i + 8:i + 14])
    return f"{kind} {p}/{t}/{m}"


def prores_header(path):
    """Return the primaries/transfer/matrix bytes from the first ProRes frame header, or None.

    The ProRes encoder writes these from the frame properties, independently of the colr atom."""
    data = Path(path).read_bytes()
    i = data.find(b"icpf")
    if i < 0:
        return None
    hdr = data[i + 4:]
    return f"{hdr[14]}/{hdr[15]}/{hdr[16]}"


def decode_planes(path, shape):
    """Decode the first frame to raw planes at its own pix_fmt, so ffmpeg does no conversion.

    Returns (planes, bits), or (None, None) if the decoded format is not one we read raw."""
    pix_fmt = probe(path)["pix_fmt"]
    if pix_fmt not in NATIVE_FMTS:
        return None, None
    out = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", pix_fmt, "-"], capture_output=True)
    h, w = shape
    if len(out.stdout) != 3 * h * w * 2:
        return None, None
    return np.frombuffer(out.stdout, dtype="<u2").reshape(3, h, w).astype(np.float64), NATIVE_FMTS[pix_fmt]


def classify(planes, bits, rgb):
    """Score the decoded planes against each matrix/range candidate, best match first.

    Errors are reported in 10-bit code values whatever the decoded depth."""
    to10 = 1 << (bits - 10)
    scores = []
    for m in ("bt709", "bt601"):
        for full in (False, True):
            name = f"{m}/{'pc' if full else 'tv'}"
            ref = expected_planes(rgb, m, full, bits)
            diff = np.abs(planes - ref) / to10
            scores.append({"candidate": name, "mean": round(float(diff.mean()), 3),
                           "max": round(float(diff.max()), 2),
                           "max_per_plane": [round(float(d.max()), 2) for d in diff]})
    return sorted(scores, key=lambda s: s["mean"])


def white_and_interior_error(planes, bits, rgb, interior):
    """Y' of the 100% white pixels, and the worst BT.709 limited-range error inside patches, in 10-bit units."""
    to10 = 1 << (bits - 10)
    white = np.all(rgb >= 1.0, axis=-1)
    values, counts = np.unique(planes[0][white], return_counts=True)
    ideal = expected_planes(rgb, "bt709", False, bits)
    err = np.abs(planes - ideal)[:, interior] / to10
    return {"white_y": round(float(values[np.argmax(counts)]) / to10, 2),
            "interior_max": [round(float(e.max()), 2) for e in err]}


def encode(src, dst, vf, extra, codec, input_args=()):
    cmd = [FFMPEG, "-y", "-v", "error", *input_args, "-i", str(src), "-frames:v", "1"]
    if vf:
        cmd += ["-vf", vf]
    cmd += [*CODECS[codec]["args"], "-pix_fmt", PIX_FMT, *extra, str(dst)]
    result = run(cmd)
    return cmd, (result.stderr.strip() if result.returncode else None)


def run_matrix(source, outdir, label=None):
    info = ffmpeg_info()
    vdir = outdir / (label or info["version"])
    vdir.mkdir(parents=True, exist_ok=True)
    rgb = read_rgb(source)
    interior = flat(np.moveaxis(np.round(rgb * 65535), -1, 0), margin=8)
    results = {"ffmpeg": info, "label": label or info["version"], "source": str(source), "encodes": {}}

    def measure(path, cmd, err):
        if err:
            return {"cmd": cmd, "error": err}
        entry = {"cmd": cmd, "tags": probe(path), "colr": colr_atom(path), "prores_hdr": prores_header(path)}
        planes, bits = decode_planes(path, rgb.shape[:2])
        if planes is not None:
            entry["decoded_bits"] = bits
            entry["match"] = classify(planes, bits, rgb)
            entry.update(white_and_interior_error(planes, bits, rgb, interior))
        return entry

    for codec in CODECS:
        for name, (desc, vf, extra, needs, codecs) in RECIPES.items():
            if codecs and codec not in codecs:
                continue
            key = f"{codec}/{name}"
            if CODECS[codec]["encoder"] not in info["encoders"]:
                results["encodes"][key] = {"skipped": f"no {CODECS[codec]['encoder']}"}
                continue
            missing = [n for n in needs if n not in info["filters"]]
            if missing:
                results["encodes"][key] = {"skipped": "no " + ", ".join(missing)}
                continue
            dst = vdir / f"{codec}_{name}{CODECS[codec]['ext']}"
            cmd, err = encode(source, dst, vf, extra, codec)
            results["encodes"][key] = {"description": desc, **measure(dst, cmd, err)}

    out = vdir / "results.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"Wrote {out}")
    return out


SHORT = {"unknown": "?", "iec61966-2-1": "srgb", "bt2020nc": "2020nc", "smpte2084": "pq"}
TAG_KEYS = ("color_range", "color_space", "color_transfer", "color_primaries")
# Intended tags for the encodes, as range/matrix/transfer/primaries.
ENCODE_EXPECTED = ("tv", "bt709", "srgb", "bt709")



def bold(text, ok):
    return f"**{text}**" if ok else text


def tag_summary(tags, expected):
    vals = [SHORT.get(tags.get(k, "?"), tags.get(k, "?")) for k in TAG_KEYS]
    return "/".join(bold(v, e is not None and v == e) for v, e in zip(vals, expected))


def display_command(cmd):
    """The command with the run-specific input/output paths replaced, so it is comparable across versions."""
    source, output = cmd[cmd.index("-i") + 1], cmd[-1]
    out = []
    for arg in cmd:
        if arg == source:
            arg = "input" + Path(source).suffix
        elif arg == output:
            arg = "output" + Path(output).suffix
        elif "=" in arg or "," in arg:
            arg = f'"{arg}"'
        out.append(arg)
    return " ".join(out)


def commands_for(runs, section, key):
    """Return the display command for key, plus a note if versions disagree."""
    cmds = set()
    for r in runs:
        e = r[section].get(key)
        if e and "cmd" in e:
            cmds.add(display_command(e["cmd"]))
    if not cmds:
        return ""
    text = sorted(cmds)[0]
    return f"`{text}`" + (" (differs between versions)" if len(cmds) > 1 else "")


def summarize(outdir):
    runs = []
    for f in sorted(outdir.glob("*/results.json")):
        runs.append(json.loads(f.read_text()))
    runs.sort(key=lambda r: [int(n) if n.isdigit() else 0 for n in re.split(r"[.-]", r.get("label", "99"))])
    versions = [r.get("label") or r["ffmpeg"]["version"] for r in runs]
    builds = ", ".join(f"{r.get('label')} = `{r['ffmpeg']['version']}`" for r in runs if r.get("label"))
    lines = ["# Colour flag behaviour across FFmpeg versions", "",
             "Each recipe encodes an untagged 16-bit RGB PNG (`sourceimages/chip-chart-1080-16bit-noicc.png`) to "
             "10-bit 4:4:4 Y'CbCr, as you would when making a movie from an image sequence, with the command in "
             "the last column. Each cell has these lines, in this order:", "",
             "| Line | Example | What it is | Correct value |",
             "| :--- | :--- | :--- | :--- |",
             "| Pixels | `bt709/tv (0.244)` | The matrix and range the encoded pixels actually match, out of "
             "BT.709/BT.601 and limited (`tv`)/full (`pc`), with the mean error in 10-bit code values. The planes "
             "are read without any FFmpeg colour conversion and compared with ideal conversions computed in numpy. "
             "| `bt709/tv` |",
             "| Stream tags | `tv/bt709/srgb/bt709` | What `ffprobe` reports as `range/matrix/transfer/primaries`. "
             "`?` is unspecified. | `tv/bt709/srgb/bt709` |",
             "| `colr` | `colr 1/13/1` | The MOV/MP4 `colr` atom, as CICP codes `primaries/transfer/matrix` "
             "(1 = BT.709, 13 = sRGB, 2 = unspecified). `no colr` means none was written. | `1/13/1` |",
             "| `prores frame` | `prores frame 1/13/1` | ProRes only: the colour description in the ProRes "
             "frame header itself, as CICP codes `primaries/transfer/matrix`. ProRes stores it separately "
             "from the `colr` atom, and the two can disagree. | `1/13/1` |",
             "| White and max error | `white 943`<br>`max 4/2/2` | The Y' of the 100% white chips (the source's "
             "65535 white), then the worst Y'/Cb/Cr error against the ideal BT.709 limited-range conversion, "
             "measured inside the chips (8 pixels clear of any edge). Both in 10-bit code values. This is where "
             "the libswscale white level error shows: 943 instead of 940. | `white 940`, max 0 for lossless H.264 "
             "(ProRes adds up to about 2 of compression error) |", "",
             "Values that match the correct result are **bold**.", "",
             f"FFmpeg builds: {builds}.", "",
             "* ProRes has no range field, so its range shows as `?` before 8.1, where the decoder started "
             "reporting it as `tv`. That is a change in what is reported, not in the file.",
             "* The H.264 encodes use `-qp 0`, which is lossless in x264 at every bit depth (`-crf 0` is only "
             "lossless at 8-bit), so their pixel error is the colour conversion alone. The ProRes 4444 XQ "
             "encodes add a little compression loss (about 0.2 code values mean, a few code values at worst).",
             "* With a 16-bit source, `scale` (including the one ffmpeg inserts when there is no filter) puts 100% "
             "white at 943 instead of 940; `zscale` gets 940. See FFmpegChanges.md.",
             "* `prores_ks` only accepts 10-bit input, but FFmpeg's ProRes decoder always outputs 12-bit for "
             "4444 and 4444 XQ (it picks the depth from the codec tag). ProRes is DCT based and 4444 "
             "reconstructs at up to 12 bits, so a 10-bit source comes back as roughly 4x its 10-bit values plus "
             "compression error. The pixel comparison scales this back to 10-bit code values.", ""]
    keys = []
    for r in runs:
        keys += [k for k in r["encodes"] if k not in keys]
    lines += ["| Recipe | " + " | ".join(versions) + " | Command |",
              "| :--- |" + " :--- |" * len(versions) + " :--- |"]
    for key in keys:
        row = []
        for r in runs:
            e = r["encodes"].get(key)
            if e is None:
                row.append("n/a")
            elif "skipped" in e:
                row.append(e["skipped"])
            elif "error" in e:
                row.append("error")
            else:
                best = e["match"][0] if e.get("match") else None
                pix = bold(f"{best['candidate']} ({best['mean']})", best["candidate"] == "bt709/tv") if best else "?"

                colr = e.get("colr")
                colr = f"<br>colr {bold(colr.split()[-1], colr.split()[-1] == '1/13/1')}" if colr else "<br>no colr"
                hdr = e.get("prores_hdr")
                hdr = f"<br>prores frame {bold(hdr, hdr == '1/13/1')}" if hdr else ""
                white = ""
                if "white_y" in e:
                    white_y = e["white_y"]
                    white = "<br>" + bold(f"white {white_y:g}", white_y == 940)
                    white += "<br>max " + "/".join(f"{v:g}" for v in e["interior_max"])
                row.append(f"{pix}<br>{tag_summary(e['tags'], ENCODE_EXPECTED)}{colr}{hdr}{white}")
        cmd = commands_for(runs, "encodes", key)
        lines.append(f"| `{key}` | " + " | ".join(row) + f" | {cmd} |")

    text = "\n".join(lines) + "\n"
    (outdir / "summary.md").write_text(text)
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
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
                            "python", __file__, "--source", str(args.source), "--outdir", str(args.outdir), "--label", version])
        summarize(args.outdir)
    elif args.summarize:
        summarize(args.outdir)
    else:
        run_matrix(args.source, args.outdir, args.label)


if __name__ == "__main__":
    main()
