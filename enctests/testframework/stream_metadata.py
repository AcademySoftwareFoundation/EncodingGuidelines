"""
What FFmpeg wrote for an encode, and how it got there, read from the file and the encode logs, for every
encode whatever the comparison. These are flat result fields, so versionChanges.py reports a change in any of
them between FFmpeg versions, whether or not an assert covers it.

Fields (each only when it applies; values are strings):

    pix_fmt, profile, color_range, color_space,     -- ffprobe's view of the stream. ffprobe reports some of
    color_primaries, color_transfer, chroma_location   these from decoder defaults when nothing is written.
    colr                 -- the MOV/MP4 colr atom, e.g. "nclx 1/1/1 tv", or "none".
    bitstream_colour     -- the colour fields in the bitstream itself (H.264/HEVC VUI, AV1 and VP9 headers,
                            APV frame header, MPEG-2), as "primaries/transfer/matrix range", e.g. "1/1/1 tv",
                            with "-" for a part that is not written, or "not written". VP9 has only its own
                            colour space number and range: "vp9 color_space 2 tv".
    bitstream_chroma_loc -- the chroma location in the bitstream: H.264/HEVC chroma_sample_loc_type, AV1
                            chroma_sample_position, or "not written".
    prores_header        -- primaries/transfer/matrix from the first ProRes frame header, e.g. "1/1/1".
    container_chroma_siting -- MKV ChromaSitingHorz/Vert, e.g. "H left, V half", or the MXF descriptor value.
    auto_conversions     -- conversions FFmpeg inserted itself that change the colour space or range, from the
                            verbose report, e.g. "rgb48be gbr pc -> yuv444p10le bt709 tv", or "none". A change
                            of pixel format alone (rgb48be -> gbrp16le) is left out. Not recorded for FFmpeg 6.1
                            and earlier, which do not log the colour space and range.
    encoder_library      -- the encoder library's version, as it logs it, e.g. "x265 3.6+1-aa7f602f7".
    decoder              -- the decoder FFmpeg picks for the file, and "(fails)" if it cannot decode the first
                            frame.

The verbose report is written by setting FFREPORT for the encode (see report_env), so the stored command
and the ordinary log are unchanged.
"""
import json
import re
import subprocess
from pathlib import Path

H264_LOC = {0: "left", 1: "center", 2: "topleft", 3: "top", 4: "bottomleft", 5: "bottom"}
AV1_LOC = {0: "unknown", 1: "vertical (left)", 2: "colocated (topleft)"}
MKV_SITING = {0: "unspecified", 1: "left", 2: "half"}
MKV_SITING_V = {0: "unspecified", 1: "top", 2: "half"}
MXF_SITING = {0: "co-sited", 1: "horizontal midpoint", 2: "three tap", 3: "quincunx", 4: "Rec.601",
              5: "line alternating", 6: "vertical midpoint", 255: "unknown"}

# (pattern, name) for the version line each encoder library logs.
LIBRARY_VERSIONS = [
    (r"x265 \[info\]: HEVC encoder version (\S+)", "x265"),
    (r"\[libx264 @ [^]]+\] .*core (\d+(?: r\d+)?)", "x264 core"),
    (r"SVT-AV1 Encoder Lib (v\S+)", "SVT-AV1"),
    (r"\[libaom-av1 @ [^]]+\] (v\S+)", "libaom"),
    (r"\[libvpx(?:-vp9)? @ [^]]+\] (v\S+)", "libvpx"),
    (r"\[librav1e @ [^]]+\] .*?(\d+\.\d+\.\d+)", "rav1e"),
    (r"\[libopenjpeg @ [^]]+\] .*?(\d+\.\d+\.\d+)", "OpenJPEG"),
]

PROBE_FIELDS = ("pix_fmt", "profile", "color_range", "color_space", "color_primaries", "color_transfer",
                "chroma_location")

# FFmpeg's verbose log for a conversion it inserted, e.g.
# [auto_scale_0 @ 0x...] w:1920 h:1080 fmt:rgb48be csp:gbr range:pc sar:0/1 -> w:1920 h:1080 fmt:yuv444p10le ...
AUTO_SCALE = re.compile(r"\[auto_scale_\d+ @ [^]]+\] .*?fmt:(\S+) csp:(\S+) range:(\S+).*?->"
                        r".*?fmt:(\S+) csp:(\S+) range:(\S+)")


def report_path(out_file):
    return Path(out_file.parent, out_file.stem + ".report.log")


def report_env(out_file):
    """Environment for an encode that also writes its verbose log next to it (FFREPORT, level 40 = verbose)."""
    path = report_path(out_file).as_posix().replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    return {"FFREPORT": f"file={path}:level=40"}


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None


def probe(ffprobe, path):
    result = _run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=" + ",".join(PROBE_FIELDS), "-of", "json", str(path)])
    try:
        stream = json.loads(result.stdout)["streams"][0]
    except (AttributeError, ValueError, KeyError, IndexError):
        return {}
    return {k: str(stream[k]) for k in PROBE_FIELDS if k in stream}


def read_colr(path):
    """The MOV/MP4 colr atom as e.g. 'nclx 1/13/1 tv', or 'none'. Other containers return None."""
    if Path(path).suffix.lower() not in (".mov", ".mp4", ".m4v"):
        return None
    data = Path(path).read_bytes()
    i = data.find(b"colr")
    if i < 0:
        return "none"
    kind = data[i + 4:i + 8].decode("latin-1")
    if kind not in ("nclx", "nclc"):
        return kind
    p, t, m = (int.from_bytes(data[i + 8 + 2 * n:i + 10 + 2 * n], "big") for n in range(3))
    text = f"{kind} {p}/{t}/{m}"
    if kind == "nclx":
        text += " pc" if data[i + 14] & 0x80 else " tv"
    return text


def prores_header(data):
    """primaries/transfer/matrix from the first ProRes frame header, or None. The ProRes encoder writes these
    from the frame properties, separately from the container's colr atom."""
    i = data.find(b"icpf")
    if i < 0:
        return None
    header = data[i + 4:i + 21]
    return f"{header[14]}/{header[15]}/{header[16]}" if len(header) == 17 else None


def container_chroma_siting(data, suffix):
    """The MKV Colour element's chroma siting, or the MXF picture descriptor's. Only the headers are searched (the
    MKV track header before the first Cluster, the MXF header partition), as the same bytes turn up by chance in
    the compressed frames."""
    if suffix == ".mkv" or suffix == ".webm":
        cluster = data.find(b"\x1F\x43\xB6\x75")
        data = data[:cluster] if cluster > 0 else data[:1 << 16]
        h = re.search(rb"\x55\xB7\x81(.)", data, re.S)
        v = re.search(rb"\x55\xB8\x81(.)", data, re.S)
        if not h and not v:
            return "not written"
        return (f"H {MKV_SITING.get(h.group(1)[0], h.group(1)[0]) if h else 'not written'}, "
                f"V {MKV_SITING_V.get(v.group(1)[0], v.group(1)[0]) if v else 'not written'}")
    if suffix == ".mxf":
        # The header partition ends where the body partition pack, or the first essence element, starts.
        ends = [i for i in (data.find(b"\x06\x0E\x2B\x34\x02\x05\x01\x01\x0D\x01\x02\x01\x01\x03", 16),
                            data.find(b"\x06\x0E\x2B\x34\x01\x02\x01\x01\x0D\x01\x03\x01")) if i > 0]
        data = data[:min(ends)] if ends else data[:1 << 16]
        m = re.search(rb"\x33\x03\x00\x01(.)", data, re.S)
        return MXF_SITING.get(m.group(1)[0], str(m.group(1)[0])) if m else "not written"
    return None


def _trace_value(trace, name):
    m = re.search(rf"\b{name}\s+\S+\s*=\s*(\d+)", trace)
    return int(m.group(1)) if m else None


def bitstream_fields(ffmpeg, path):
    """bitstream_colour and bitstream_chroma_loc, read with the trace_headers bitstream filter."""
    result = _run([ffmpeg, "-hide_banner", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-frames:v", "1",
                   "-bsf:v", "trace_headers", "-f", "null", "-"])
    trace = result.stderr if result else ""
    if "trace_headers" not in trace or not re.search(r"\[trace_headers @ [^]]+\] +\d+ +\w+", trace):
        # Not a codec trace_headers can read (ProRes, DNxHD, FFV1, ...).
        return {}
    fields = {}
    primaries = _trace_value(trace, "colour_primaries")
    if primaries is None:
        primaries = _trace_value(trace, "color_primaries")
    transfer = _trace_value(trace, "transfer_characteristics")
    matrix = _trace_value(trace, "matrix_coefficients")
    vp9_space = _trace_value(trace, "color_space") if matrix is None else None
    full = None
    for name in ("video_full_range_flag", "full_range_flag", "color_range"):
        full = _trace_value(trace, name)
        if full is not None:
            break
    parts = [primaries, transfer, matrix]
    if vp9_space is not None:
        # VP9 has its own colour space numbers (2 is BT.709) and no primaries or transfer.
        fields["bitstream_colour"] = f"vp9 color_space {vp9_space} {'pc' if full else 'tv'}"
    elif all(p is None for p in parts) and full is None:
        fields["bitstream_colour"] = "not written"
    else:
        text = "/".join("-" if p is None else str(p) for p in parts)
        fields["bitstream_colour"] = f"{text} {'-' if full is None else ('pc' if full else 'tv')}"

    present = _trace_value(trace, "chroma_loc_info_present_flag")
    if present is not None:
        if present:
            fields["bitstream_chroma_loc"] = H264_LOC.get(_trace_value(trace, "chroma_sample_loc_type_top_field"),
                                                          "unknown")
        else:
            fields["bitstream_chroma_loc"] = "not written"
    else:
        position = _trace_value(trace, "chroma_sample_position")
        if position is not None:
            fields["bitstream_chroma_loc"] = AV1_LOC.get(position, str(position))
    return fields


def decoder_used(ffmpeg, path):
    """The decoder FFmpeg picks for the first video stream, with "(fails)" if it cannot decode the first frame."""
    result = _run([ffmpeg, "-hide_banner", "-v", "verbose", "-i", str(path), "-map", "0:v:0", "-frames:v", "1",
                   "-f", "null", "-"])
    if result is None:
        return None
    m = re.search(r"\[dec:([\w-]+) @", result.stderr)
    if m:
        name = m.group(1)
    else:
        # FFmpeg 6.1 and earlier: "Stream #0:0 -> #0:0 (png (native) -> ...)", or "(av1 (libdav1d) -> ...)".
        m = re.search(r"Stream #0:\d+ -> #0:\d+ \((\w+) \(([\w-]+)\)", result.stderr)
        name = (m.group(1) if m.group(2) == "native" else m.group(2)) if m else "unknown"
    counts = re.search(r"\(video\): .*?(\d+) frames decoded; (\d+) decode errors", result.stderr)
    if result.returncode != 0 or not counts or counts.group(1) == "0" or counts.group(2) != "0":
        name += " (fails)"
    return name


def auto_conversions(report_text):
    """Conversions FFmpeg inserted that change the colour space or range, joined with "; ", or "none". None when
    the log does not give them (FFmpeg 6.1 and earlier log only the pixel formats)."""
    if re.search(r"\[auto_scale_\d+ @ [^]]+\] w:\d+ h:\d+ fmt:\S+ sar:", report_text):
        return None
    found = []
    for m in AUTO_SCALE.finditer(report_text):
        fmt_in, csp_in, range_in, fmt_out, csp_out, range_out = m.groups()
        if (csp_in, range_in) != (csp_out, range_out):
            text = f"{fmt_in} {csp_in} {range_in} -> {fmt_out} {csp_out} {range_out}"
            if text not in found:
                found.append(text)
    return "; ".join(found) or "none"


def encoder_library(log_text):
    for pattern, name in LIBRARY_VERSIONS:
        m = re.search(pattern, log_text)
        if m:
            return f"{name} {m.group(1)}"
    return None


def stream_metadata(ffmpeg, ffprobe, path, log_file=None):
    """The fields above for one encode; empty if the file does not exist."""
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return {}
    fields = probe(ffprobe, path)
    colr = read_colr(path)
    if colr is not None:
        fields["colr"] = colr
    fields.update(bitstream_fields(ffmpeg, path))
    data = path.read_bytes()
    header = prores_header(data)
    if header:
        fields["prores_header"] = header
    siting = container_chroma_siting(data, path.suffix.lower())
    if siting:
        fields["container_chroma_siting"] = siting
    decoder = decoder_used(ffmpeg, path)
    if decoder:
        fields["decoder"] = decoder

    if log_file is not None:
        log_file = Path(log_file)
        if log_file.exists():
            library = encoder_library(log_file.read_text(errors="replace"))
            if library:
                fields["encoder_library"] = library
    report = report_path(path)
    if report.exists():
        conversions = auto_conversions(report.read_text(errors="replace"))
        if conversions is not None:
            fields["auto_conversions"] = conversions
    return fields


def build_info(ffmpeg):
    """Per run: the ffmpeg version line, its configure options and, for a dynamically linked build, the
    libraries it links (with their versions where the platform reports them)."""
    info = {}
    result = _run([ffmpeg, "-hide_banner", "-version"])
    if result and result.stdout:
        lines = result.stdout.splitlines()
        info["ffmpeg_version_line"] = lines[0]
        info["ffmpeg_configuration"] = next((l.split(":", 1)[1].strip() for l in lines
                                             if l.startswith("configuration:")), "")
    binary = _run(["which", ffmpeg]) if "/" not in ffmpeg else None
    binary = binary.stdout.strip() if binary and binary.returncode == 0 else ffmpeg
    linked = _run(["otool", "-L", binary]) or _run(["ldd", binary])
    if linked and linked.returncode == 0:
        libraries = []
        for line in linked.stdout.splitlines()[1:]:
            m = re.match(r"\s*(\S+)(?: \(compatibility version \S+, current version ([^)]+)\))?", line)
            if not m:
                continue
            name = Path(m.group(1)).name
            if re.match(r"lib(System|c\+\+|objc|resolv|iconv|z|bz2)\.", name) or "/System/" in m.group(1):
                continue
            libraries.append(f"{name} {m.group(2)}" if m.group(2) else name)
        info["ffmpeg_libraries"] = libraries
    return info
