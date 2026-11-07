"""
Compare an encoded movie with the ideal conversion of its RGB source, without letting FFmpeg convert it.

The first frame is decoded at the stream's own pixel format (``-f rawvideo -pix_fmt <native>``), so FFmpeg
does no colour conversion, and compared with the ideal R'G'B' to Y'CbCr conversion of the source image, done
here in numpy. RGB encodes (e.g. DNxHR 444, gbrp) are compared with the source RGB directly.

This replaces extracting the movie to a PNG with ``scale`` and comparing it with ``idiff``: that adds a second
libswscale conversion, and the PNG references it compared against were themselves made with libswscale, so
the test could not see libswscale's errors.

Errors are in code values at the decoded bit depth. They are measured away from edges (by default more than
8 pixels from any step in the ideal image), so for 4:2:2 and 4:2:0 the result does not depend on the chroma
filter or siting; ``max_error_all`` covers the whole frame. ``p99_error`` is the 99th percentile error (worst
plane): with lossy codecs ``max_error`` is a single pixel set by compression, which this is far less sensitive to. ``white_error`` is the average Y' error over the
brightest areas: lossy codecs add noise that can hide a white level error in ``max_error``, but not in this.

It also records which matrix and range the pixels match (``pixels_match``), and for 4:2:2 and 4:2:0 where the
chroma samples actually sit (``chroma_siting_measured``), so both can be checked against the tags.

The ideal conversion matches sourceimages/rp219/validate_reference.py, which is checked against the values
published in SMPTE RP 219.
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

# Kr, Kb for each matrix, named as ffmpeg/ffprobe name them.
MATRICES = {
    "bt709": (0.2126, 0.0722),
    "bt2020nc": (0.2627, 0.0593),
    "bt470bg": (0.299, 0.114),
    "smpte170m": (0.299, 0.114),
}
RANGES = {"tv": "tv", "limited": "tv", "mpeg": "tv", "pc": "pc", "full": "pc", "jpeg": "pc"}
# The rawvideo pix_fmt to read each decoded RGB format as: a lossless repack to planes.
RGB_PLANAR = {"rgb24": "gbrp", "bgr24": "gbrp", "rgba": "gbrp", "bgra": "gbrp", "argb": "gbrp", "abgr": "gbrp",
              "rgb48be": "gbrp16le", "rgb48le": "gbrp16le", "rgba64be": "gbrp16le", "rgba64le": "gbrp16le",
              "bgr48be": "gbrp16le", "bgr48le": "gbrp16le"}
YUV_RE = re.compile(r"^yuva?j?(444|422|420|440|411|410)p(\d+)?(le|be)?$")
GBR_RE = re.compile(r"^gbra?p(\d+)?(le|be)?$")
SUBSAMPLING = {"444": (1, 1), "422": (2, 1), "420": (2, 2), "440": (1, 2), "411": (4, 1), "410": (4, 2)}


def read_source_rgb(path):
    """Source frame as R'G'B' normalised to 0-1, and its bit depth. Exact code values for integer images."""
    import OpenImageIO as oiio
    buf = oiio.ImageBuf(str(path))
    if buf.has_error:
        raise RuntimeError(f"Unable to read {path}: {buf.geterror()}")
    pixels = buf.get_pixels(oiio.FLOAT)[..., :3].astype(np.float64)
    if buf.spec().format.basetype in (oiio.HALF, oiio.FLOAT, oiio.DOUBLE):
        return pixels, 0
    # oiio:BitsPerSample is only set when it differs from the pixel type (e.g. 10-bit DPX).
    bits = buf.spec().get_int_attribute("oiio:BitsPerSample") or buf.spec().format.size() * 8
    return np.round(pixels * ((1 << bits) - 1)) / ((1 << bits) - 1), bits


def ideal_ycbcr(rgb, bits, matrix="bt709", range_="tv"):
    """R'G'B' (0-1, full range) to Y'CbCr code values, as three full resolution planes."""
    kr, kb = MATRICES[matrix]
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = kr * r + (1 - kr - kb) * g + kb * b
    cb, cr = (b - y) / (2 * (1 - kb)), (r - y) / (2 * (1 - kr))
    if RANGES[range_] == "tv":
        s = 1 << (bits - 8)
        planes = [y * 219 * s + 16 * s, cb * 224 * s + 128 * s, cr * 224 * s + 128 * s]
    else:
        m = (1 << bits) - 1
        planes = [y * m, cb * m + (1 << (bits - 1)), cr * m + (1 << (bits - 1))]
    return np.clip(np.round(np.stack(planes)), 0, (1 << bits) - 1).astype(np.int64)


def ideal_rgb(rgb, bits):
    """R'G'B' (0-1) as code values at bits, ordered as gbrp planes (G, B, R)."""
    codes = np.round(np.clip(rgb, 0, 1) * ((1 << bits) - 1)).astype(np.int64)
    return np.stack([codes[..., 1], codes[..., 2], codes[..., 0]])


def interior_mask(planes, bits, margin=8, step=4):
    """True away from edges: more than margin pixels from a step of more than step (8-bit) code values.

    Smooth gradients (e.g. a grey ramp) are not edges, so they are compared in full.
    """
    limit = step << (bits - 8)
    edge = np.zeros(planes.shape[1:], bool)
    for p in planes:
        edge[:, 1:] |= np.abs(np.diff(p, axis=1)) > limit
        edge[1:, :] |= np.abs(np.diff(p, axis=0)) > limit
    near = edge.copy()
    for axis in (0, 1):
        grown = near.copy()
        for shift in range(1, margin + 1):
            grown |= np.roll(near, shift, axis) | np.roll(near, -shift, axis)
        near = grown
    return ~near


def pixels_match(planes, rgb, bits, sxsy, mask):
    """Which matrix and range the decoded Y'CbCr planes match, e.g. "bt709 tv", whatever the tags say.

    Each candidate's ideal conversion of the source is compared away from edges; the best mean error wins. A
    matrix or range that another candidate matches as well (a grey source cannot tell matrices apart) is
    reported as "?", and "none" means nothing came within 8 10-bit code values.
    """
    sx, sy = sxsy
    scores = []
    for matrix in ("bt709", "bt470bg", "bt2020nc"):
        for range_ in ("tv", "pc"):
            ideal = ideal_ycbcr(rgb, bits, matrix, range_)
            errors = []
            for i, plane in enumerate(planes):
                step_y, step_x = (sy, sx) if i else (1, 1)
                m = mask[::step_y, ::step_x][:plane.shape[0], :plane.shape[1]]
                diff = np.abs(plane - ideal[i][::step_y, ::step_x][:plane.shape[0], :plane.shape[1]])
                errors.append(float(diff[m].mean() if m.any() else diff.mean()))
            scores.append((float(np.mean(errors)) * 2.0 ** (10 - bits), matrix, range_))
    scores.sort()
    best, matrix, range_ = scores[0]
    if best > 8:
        return "none"
    close = [s for s in scores[1:] if s[0] <= max(1.2 * best, best + 0.1)]
    if any(s[1] != matrix for s in close):
        matrix = "?"
    if any(s[2] != range_ for s in close):
        range_ = "?"
    return f"{matrix} {range_}"


def _blur(a, sigma, axis):
    """Gaussian blur along one axis, edges extended."""
    r = int(3 * sigma + 1)
    x = np.arange(-r, r + 1)
    k = np.exp(-x * x / (2 * sigma * sigma))
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    a = np.pad(a, pad, mode="edge")
    n = a.shape[axis] - 2 * r
    return sum(w * np.take(a, np.arange(i, i + n), axis) for i, w in enumerate(k))


def _sample(plane, xs, ys):
    """plane at columns xs and rows ys (fractional positions), by linear interpolation."""
    for axis, pos in ((1, xs), (0, ys)):
        i0 = np.clip(np.floor(pos).astype(int), 0, plane.shape[axis] - 2)
        w = (pos - i0).reshape([-1 if a == axis else 1 for a in range(2)])
        plane = np.take(plane, i0, axis) * (1 - w) + np.take(plane, i0 + 1, axis) * w
    return plane


SITING_NAMES = {(0, 0.5): "left", (0.5, 0.5): "center", (0, 0): "topleft", (0.5, 0): "top",
                (0, 1): "bottomleft", (0.5, 1): "bottom"}


def chroma_siting(planes, ideal, bits, sxsy, sigma=2.5, border=24):
    """Where the subsampled chroma samples sit, measured from the pixels: (offset_h, offset_v, name).

    Offsets are in luma samples from the even luma sample: 0 is co-sited (left/top), 0.5 centred. The ideal
    full-resolution chroma and the decoded chroma are both blurred to the same width (sigma luma samples), which
    swamps the converter's own filter, and the decoded samples are matched against the ideal sampled at
    sx * k + offset, allowing for gain and offset. Measured this way the chroma siting chart gives the same as
    tests/chroma_siting.py (zscale co-sited, scale centred). An axis with no chroma detail gives None.
    """
    sx, sy = sxsy
    ch, cw = planes[1].shape
    by, bx = border // sy, border // sx
    ideal_blurred = [_blur(_blur(p.astype(np.float64), sigma, 0), sigma, 1) for p in ideal[1:]]
    decoded = [_blur(_blur(p.astype(np.float64), sigma / sx, 1), sigma / sy, 0)[by:-by, bx:-bx].ravel()
               for p in planes[1:]]

    def detail(axis):
        # Mean chroma gradient along the axis, in 10-bit code values per luma sample.
        return max(float(np.abs(np.diff(g, axis=axis)).mean()) for g in ideal_blurred) * 2.0 ** (10 - bits)

    def cost(dx, dy):
        total = 0.0
        for g, d in zip(ideal_blurred, decoded):
            s = _sample(g, sx * np.arange(cw) + dx, sy * np.arange(ch) + dy)[by:-by, bx:-bx].ravel()
            a = np.stack([s, np.ones_like(s)], 1)
            coef = np.linalg.lstsq(a, d, rcond=None)[0]
            total += float(((a @ coef - d) ** 2).mean())
        return total

    def search(f):
        # Coarse steps, then a parabola through the best point and its neighbours at finer steps.
        coarse = np.arange(-1, 1.5 + 1e-9, 0.25)
        x = coarse[int(np.argmin([f(v) for v in coarse]))]
        for step in (0.1, 0.03):
            a, b, c = f(x - step), f(x), f(x + step)
            den = a - 2 * b + c
            x = x + (step * 0.5 * (a - c) / den if den > 0 else 0)
        return x

    use_h, use_v = sx > 1 and detail(1) > 0.01, sy > 1 and detail(0) > 0.01
    dx, dy = 0.25 * (sx - 1), 0.25 * (sy - 1)
    for _ in range(2):
        if use_h:
            dx = search(lambda v: cost(v, dy))
        if use_v:
            dy = search(lambda v: cost(dx, v))
    offset_h = round(float(dx), 2) if use_h else None
    offset_v = round(float(dy), 2) if use_v else (0.0 if sy == 1 else None)
    if offset_h is None or offset_v is None:
        return offset_h, offset_v, "unmeasured"
    near = lambda v, options: next((o for o in options if abs(v - o) < 0.15), None)
    h, v = near(offset_h, (0, 0.5)), near(offset_v, (0, 0.5, 1))
    if sy == 1:
        name = {0: "left", 0.5: "center"}.get(h)
    else:
        name = SITING_NAMES.get((h, v)) if h is not None and v is not None else None
    return offset_h, (offset_v if sy > 1 else None), name or f"h {offset_h} v {offset_v}"


def probe(ffprobe, path):
    out = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=codec_name,pix_fmt,width,height,color_range,color_space,color_primaries,"
                          "color_transfer,chroma_location", "-of", "json", str(path)],
                         capture_output=True, text=True)
    streams = json.loads(out.stdout or "{}").get("streams", [])
    return streams[0] if streams else None


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


def decode_planes(ffmpeg, path, pix_fmt, width, height):
    """First frame as a list of planes (alpha dropped), the format read, bits and (sx, sy) chroma subsampling."""
    m = YUV_RE.match(pix_fmt)
    g = GBR_RE.match(pix_fmt)
    if m:
        read_fmt, bits, (sx, sy), kind = pix_fmt, int(m.group(2) or 8), SUBSAMPLING[m.group(1)], "ycbcr"
    elif g:
        read_fmt, bits, (sx, sy), kind = pix_fmt, int(g.group(1) or 8), (1, 1), "rgb"
    elif pix_fmt in RGB_PLANAR:
        read_fmt = RGB_PLANAR[pix_fmt]
        bits, (sx, sy), kind = (8 if read_fmt == "gbrp" else 16), (1, 1), "rgb"
    else:
        raise ValueError(f"pixel format {pix_fmt} is not supported by the ycbcr test")
    if read_fmt.endswith("be"):
        read_fmt = read_fmt[:-2] + "le"  # Same values, little-endian; a lossless repack.
    cmd = [ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", read_fmt, "-"]
    out = subprocess.run(cmd, capture_output=True)
    if not out.returncode and not out.stdout:
        # FFmpeg 6.0's HEVC decoder occasionally returns no frame from a valid file; one retry is enough.
        out = subprocess.run(cmd, capture_output=True)
    if out.returncode:
        raise RuntimeError(out.stderr.decode().strip().splitlines()[-1:])
    dtype = "u1" if bits == 8 else "<u2"
    data = np.frombuffer(out.stdout, dtype).astype(np.int64)
    cw, ch = -(-width // sx), -(-height // sy)
    sizes = [width * height, cw * ch, cw * ch]
    shapes = [(height, width), (ch, cw), (ch, cw)]
    if data.size < sum(sizes):
        raise RuntimeError(f"decoded {data.size} samples, expected at least {sum(sizes)}")
    planes, start = [], 0
    for size, shape in zip(sizes, shapes):
        planes.append(data[start:start + size].reshape(shape))
        start += size
    return planes, read_fmt, bits, (sx, sy), kind


def write_images(planes, ideal, mask, bits, kind, matrix, range_, sxsy, image_path, diff_path, scale=20):
    """A viewable RGB image of the decoded frame (converted in numpy) and an error image, x scale."""
    import OpenImageIO as oiio
    sx, sy = sxsy
    full = [planes[0]] + [np.repeat(np.repeat(p, sy, 0), sx, 1)[:planes[0].shape[0], :planes[0].shape[1]]
                          for p in planes[1:]]
    full = np.stack(full).astype(np.float64)
    if kind == "rgb":
        g, b, r = full / ((1 << bits) - 1)
    else:
        kr, kb = MATRICES[matrix]
        if RANGES[range_] == "tv":
            s = 1 << (bits - 8)
            y, cb, cr = (full[0] - 16 * s) / (219 * s), (full[1] - 128 * s) / (224 * s), (full[2] - 128 * s) / (224 * s)
        else:
            m = (1 << bits) - 1
            y, cb, cr = full[0] / m, (full[1] - (1 << (bits - 1))) / m, (full[2] - (1 << (bits - 1))) / m
        r = y + 2 * (1 - kr) * cr
        b = y + 2 * (1 - kb) * cb
        g = (y - kr * r - kb * b) / (1 - kr - kb)
    rgb = np.clip(np.stack([r, g, b], axis=-1), 0, 1)
    spec = oiio.ImageSpec(rgb.shape[1], rgb.shape[0], 3, oiio.UINT16)
    buf = oiio.ImageBuf(spec)
    buf.set_pixels(oiio.ROI(), rgb.astype(np.float32))
    buf.write(str(image_path))
    # Error image: the worst plane at each pixel, in 8-bit code values x scale; areas outside the mask are dimmed.
    err = np.max(np.abs(full - ideal), axis=0) / (1 << (bits - 8)) * scale / 255
    err = np.clip(err, 0, 1)
    out = np.stack([err, err, err], axis=-1)
    out[~mask] = out[~mask] * 0.5 + 0.1
    buf = oiio.ImageBuf(spec)
    buf.set_pixels(oiio.ROI(), out.astype(np.float32))
    buf.write(str(diff_path))


def diverging(err, limit, rounding=1.0):
    """Signed error to RGB: black at 0, orange to yellow when too high, blue to cyan when too low.

    Errors up to rounding are drawn dim; above it the colour brightens, to full at limit.
    """
    mag = np.abs(err)
    above = np.clip((mag - rounding) / max(limit - rounding, 1e-6), 0, 1)
    level = np.where(mag < 1e-6, 0, np.where(mag <= rounding + 1e-6, 0.18, 0.4 + 0.6 * above))
    pos, neg = np.where(err > 0, level, 0), np.where(err < 0, level, 0)
    r = pos + neg * 0.1
    g = pos * (0.35 + 0.65 * pos) + neg * (0.35 + 0.65 * neg) * 0.9
    b = neg + pos * 0.05 * (1 - pos)
    return np.stack([r, g, b], axis=-1)


def write_rgb(rgb, path, fmt=None):
    """Write an (h, w, 3) 0-1 image."""
    import OpenImageIO as oiio
    spec = oiio.ImageSpec(rgb.shape[1], rgb.shape[0], 3, fmt or oiio.UINT8)
    buf = oiio.ImageBuf(spec)
    buf.set_pixels(oiio.ROI(), rgb.astype(np.float32))
    buf.write(str(path))


def write_error_map(errors, masks, path, limit=4.0, rounding=1.0, pool=2, plane_paths=None):
    """The signed error of each plane, side by side, in 10-bit code values (saturating at +-limit).

    errors and masks are full resolution, one per plane. Each panel is reduced by pool, keeping the largest
    error in each block (with its sign), so single-pixel errors still show. Edge areas left out of the
    comparison are dark grey. plane_paths, if given, also gets each panel as its own image (for the viewer,
    which lays them over the decoded frame).
    """
    panels = []
    for i, (err, mask) in enumerate(zip(errors, masks)):
        h, w = (err.shape[0] // pool) * pool, (err.shape[1] // pool) * pool
        blocks = err[:h, :w].reshape(h // pool, pool, w // pool, pool).transpose(0, 2, 1, 3).reshape(h // pool, w // pool, -1)
        pick = np.take_along_axis(blocks, np.abs(blocks).argmax(-1)[..., None], -1)[..., 0]
        inside = mask[:h:pool, :w:pool]
        rgb = diverging(pick, limit, rounding)
        rgb[~inside] = 0.22
        if plane_paths:
            write_rgb(rgb, plane_paths[i])
        panels.append(rgb)
        panels.append(np.full((rgb.shape[0], 8, 3), 1.0))  # A white gap between panels.
    write_rgb(np.concatenate(panels[:-1], axis=1), path)


def error_by_level(ideal_plane, err, mask, bits, bins=32):
    """Mean signed error (10-bit code values) against the ideal level (10-bit), as [[level, error], ...]."""
    to10 = 2.0 ** (10 - bits)
    level, err = ideal_plane[mask] * to10, err[mask] * to10
    if not level.size:
        return []
    index = np.clip((level / 1024 * bins).astype(int), 0, bins - 1)
    count = np.bincount(index, minlength=bins)
    total = np.bincount(index, err, minlength=bins)
    centre = np.bincount(index, level, minlength=bins)
    return [[round(float(centre[i] / count[i]), 1), round(float(total[i] / count[i]), 3)]
            for i in range(bins) if count[i]]


def compare(source_file, movie, ffmpeg="ffmpeg", ffprobe="ffprobe", matrix="bt709", range_="tv",
            margin=8, image_path=None, diff_path=None, error_map_path=None, error_map_limit=4.0, source_image_path=None,
            measure_siting=True, log=None):
    """Compare the first frame of movie with the ideal conversion of source_file. Returns a results dict.

    error_map_path also gets one image per plane, <stem>-<plane>.png (e.g. -errormap-cb.png), and
    source_image_path, if given and not already there, a viewable copy of the source.
    """
    info = probe(ffprobe, movie)
    if not info:
        return {"success": False, "testresult": "Unable to read movie"}
    if "pix_fmt" not in info:
        return {"success": False, "testresult": f"No decoder for {info.get('codec_name')}"}
    width, height = int(info["width"]), int(info["height"])
    planes, read_fmt, bits, (sx, sy), kind = decode_planes(ffmpeg, movie, info["pix_fmt"], width, height)
    if kind == "ycbcr" and matrix == "auto":
        # Check the pixels against the file's own tags.
        matrix = info.get("color_space", "unknown")
        if matrix not in MATRICES:
            return {"success": False, "testresult": f"matrix: auto, but the stream's matrix is {matrix}",
                    "color_space": matrix}
    if kind == "ycbcr" and range_ == "auto":
        range_ = info.get("color_range", "unknown")
        if range_ not in RANGES:
            range_ = "pc" if "yuvj" in info["pix_fmt"] else "tv"
    rgb, source_bits = read_source_rgb(source_file)
    if rgb.shape[:2] != (height, width):
        return {"success": False, "testresult": f"Size {width}x{height} does not match the source "
                                                f"{rgb.shape[1]}x{rgb.shape[0]}"}
    ideal = ideal_rgb(rgb, bits) if kind == "rgb" else ideal_ycbcr(rgb, bits, matrix, range_)
    mask = interior_mask(ideal, bits, margin)
    names = ["g", "b", "r"] if kind == "rgb" else ["y", "cb", "cr"]
    result = {"success": True, "testresult": "ok", "pix_fmt": info["pix_fmt"], "bits": bits,
              "source_bits": source_bits, "compared_as": kind if kind == "rgb" else f"{matrix} {RANGES[range_]}"}
    worst, worst_all, means, p99 = 0, 0, [], 0
    signed_errors, plane_masks, by_level = [], [], {}
    for i, (name, plane, ideal_plane) in enumerate(zip(names, planes, ideal)):
        # Chroma is constant inside the masked area, so subsampling the ideal there is exact.
        step_y, step_x = (sy, sx) if i else (1, 1)
        ideal_plane = ideal_plane[::step_y, ::step_x][:plane.shape[0], :plane.shape[1]]
        m = mask[::step_y, ::step_x][:plane.shape[0], :plane.shape[1]]
        signed = plane - ideal_plane
        signed_errors.append(signed * 2.0 ** (10 - bits))
        plane_masks.append(m)
        by_level[name] = error_by_level(ideal_plane, signed, m, bits)
        diff = np.abs(signed)
        # A source with no flat areas (e.g. fine chroma detail) is compared everywhere; see compared_fraction.
        inside = diff[m] if m.any() else diff.ravel()
        result[f"max_error_{name}"] = int(inside.max())
        result[f"mean_error_{name}"] = round(float(inside.mean()), 4)
        result[f"p99_error_{name}"] = round(float(np.percentile(inside, 99)), 2)
        p99 = max(p99, result[f"p99_error_{name}"])
        worst, worst_all = max(worst, int(inside.max())), max(worst_all, int(diff.max()))
        means.append(float(inside.mean()))
    result["max_error"] = worst
    result["max_error_all"] = worst_all
    result["p99_error"] = p99
    result["mean_error"] = round(sum(means) / len(means), 4)
    result["compared_fraction"] = round(float(mask.mean()), 4)
    # The same errors in 10-bit code values, so one threshold can cover 8, 10 and 12-bit encodes.
    to10 = 2.0 ** (10 - bits)
    for key in ("max_error", "mean_error", "p99_error"):
        result[f"{key}_10bit"] = round(result[key] * to10, 4)
    if kind == "ycbcr" and mask.any():
        # The white level: Y' averaged over the brightest areas, so codec noise averages out. libswscale's
        # error shows here as +3 at 10-bit, even when compression noise hides it in max_error.
        top = ideal[0][mask].max()
        bright = mask & (ideal[0] >= top - (4 << (bits - 8)))
        result["white_y"] = round(float(planes[0][bright].mean()), 2)
        result["white_y_ideal"] = round(float(ideal[0][bright].mean()), 2)
        result["white_error"] = round(result["white_y"] - result["white_y_ideal"], 2)
        result["white_error_10bit"] = round(result["white_error"] * to10, 2)
    if kind == "ycbcr":
        result["pixels_match"] = pixels_match(planes, rgb, bits, (sx, sy), mask)
        if measure_siting and (sx > 1 or sy > 1):
            offset_h, offset_v, name = chroma_siting(planes, ideal, bits, (sx, sy))
            result["chroma_siting_measured"] = name
            if offset_h is not None:
                result["chroma_offset_h"] = offset_h
            if offset_v is not None:
                result["chroma_offset_v"] = offset_v
    for key in ("color_range", "color_space", "color_primaries", "color_transfer", "chroma_location"):
        result[key] = info.get(key, "unknown")
    colr = read_colr(movie)
    if colr is not None:
        result["colr"] = colr
    if log:
        print(json.dumps(result, indent=2), file=log)
    if image_path or diff_path:
        write_images(planes, ideal, mask, bits, kind, matrix, range_, (sx, sy), image_path, diff_path)
    # Kept out of the log, which already has the summary numbers.
    result["error_by_level"] = by_level
    result["plane_names"] = names
    if error_map_path:
        # Chroma panels at full size, so the three line up.
        h, w = planes[0].shape
        full = [signed_errors[0]] + [np.repeat(np.repeat(e, sy, 0), sx, 1)[:h, :w] for e in signed_errors[1:]]
        full_masks = [plane_masks[0]] + [np.repeat(np.repeat(m, sy, 0), sx, 1)[:h, :w] for m in plane_masks[1:]]
        # Dim up to one code value of the encode, or one 10-bit code value for 12-bit and above.
        error_map_path = Path(error_map_path)
        plane_paths = [error_map_path.with_name(f"{error_map_path.stem}-{n}{error_map_path.suffix}") for n in names]
        write_error_map(full, full_masks, error_map_path, error_map_limit, max(1.0, 2.0 ** (10 - bits)),
                        plane_paths=plane_paths)
        result["error_map_limit"] = error_map_limit
    if source_image_path:
        # The same for every wedge of a source, so written once.
        if not Path(source_image_path).exists():
            import OpenImageIO as oiio
            write_rgb(np.clip(rgb, 0, 1), source_image_path, oiio.UINT16)
        result["source_image"] = Path(source_image_path).name
    return result
