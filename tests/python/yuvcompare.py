"""
Shared code for the A/B comparison pages (tests/chip-color-test.py, tests/icctest-fulltv.py).

A test describes its sources and variants; run_comparison() encodes each source with each variant, decodes the
result to 16-bit RGB (zscale, or a straight copy for RGB files), measures it against the source, and writes:

  <src>-<id>.png         8-bit copy of the decode, for display
  <src>-<id>-err.png     signed error against the source (128 = none, ERR_STEPS steps per code), for Difference
  <src>-<id>.yuv.z       the planes as stored in the file, uint16, zlib-compressed, for the pixel probe
  <src>-<id>.mp4         the encode itself (deleted unless the test keeps it)

write_page() puts the results into tests/python/yuvcompare_template.html.
"""
import json
import os
import struct
import subprocess
import sys
import zlib

import numpy as np
import OpenImageIO as oiio

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yuvcompare_template.html")
ERR_STEPS = 4

# Decode as a player would: BT.709 at the range the file says (or that a player would assume). zscale cannot
# output packed RGB, so it outputs planar 16-bit.
DECODE_YCBCR = "zscale=matrixin=709:rangein={range}:range=full:filter=spline36,format=gbrp16le"
DECODE_RGB = "format=gbrp16le"


def run(cmd):
    print("\n" + cmd)
    r = subprocess.run(cmd, shell=True, capture_output=True)
    if r.returncode:
        sys.exit(r.stderr.decode()[-3000:])
    return r.stdout


def ffmpeg_version():
    v = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    return v.split(" Copyright")[0].replace("ffmpeg version ", "FFmpeg ")


def read_rgb(path):
    return np.array(oiio.ImageBuf(path).get_pixels(oiio.FLOAT))[..., :3].astype(np.float64)


def write_display_png(img, path):
    spec = oiio.ImageSpec(img.shape[1], img.shape[0], 3, oiio.UINT8)
    out = oiio.ImageOutput.create(path)
    out.open(path, spec)
    out.write_image(np.round(np.clip(img, 0, 1) * 255).astype(np.uint8))
    out.close()


def write_raw_png(img, path):
    """8-bit RGB PNG with no colour chunks, so a canvas reads back exactly these values."""
    h, w = img.shape[:2]
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_png16(img, path):
    """Float RGB in 0..1 as a 16-bit RGB PNG with no colour chunks."""
    a = np.round(np.clip(img, 0, 1) * 65535).astype(">u2")
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def srgb_to_linear(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(v):
    v = np.clip(v, 0, None)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def run_images(root, sources, groups, unit_max=255):
    """For tests whose results are RGB images rather than encodes (the resize comparison). Each source has 'path'
    and 'reference' (a float RGB array, the size of the results), and optionally 'exr' (a scene-linear original);
    each variant has 'command', a template with {src}, {exr}, {out} (a 16-bit PNG to write), {w} and {h}, and
    optionally 'only', the source ids it applies to. Results are compared with the reference.

    A source may give 'crop' = (x, y, w, h) in output pixels: the whole image is still resized, but only that part of
    each result (and of the reference) is kept and measured, to keep the page's files small. A resize only looks at
    nearby pixels, so the crop is exactly that part of the full result."""
    os.makedirs(root, exist_ok=True)
    # The probe shows 8-bit RGB values, the same unit as the measurements (and far smaller files than 16-bit).
    rgb8 = {'chroma': '444', 'range': 'full', 'bits': 8, 'rgb': True}

    def planes8(img):
        return [np.round(np.clip(img[..., c], 0, 1) * 255) for c in range(3)]
    out_sources, out_groups, items = [], [], {}
    def cut(img, c):
        return img if c is None else img[c[1]:c[1] + c[3], c[0]:c[0] + c[2]]

    for s in sources:
        full_h, full_w = s['reference'].shape[:2]
        ref = cut(s['reference'], s.get('crop'))
        h, w = ref.shape[:2]
        s = dict(s, reference=ref, out_w=full_w, out_h=full_h, image=f"{s['id']}-reference.png", width=w, height=h,
                 planes=f"{s['id']}-reference.yuv.z", idealLabel="Reference", layout=rgb8)
        write_display_png(ref, os.path.join(root, s['image']))
        write_planes(planes8(ref), os.path.join(root, s['planes']), 8)
        out_sources.append(s)
    for glabel, entries in groups:
        out_groups.append({'label': glabel, 'items': [e['id'] for e in entries]})
        for e in entries:
            it = {'label': e['label'], 'group': glabel, 'description': e['description'], 'flags': e['flags'],
                  'layout': rgb8, 'results': {}}
            for s in out_sources:
                if 'only' in e and s['id'] not in e['only']:
                    continue
                base = f"{s['id']}-{e['id']}"
                tmp = os.path.join(root, base + "-16bit.png")
                cmd = e['command'].format(src=s['path'], exr=s.get('exr', ''), out=tmp, w=s['out_w'], h=s['out_h'])
                run(cmd)
                out = cut(read_rgb(tmp), s.get('crop'))
                os.remove(tmp)
                write_display_png(out, os.path.join(root, base + ".png"))
                write_planes(planes8(out), os.path.join(root, base + ".yuv.z"), 8)
                diff = (out - s['reference']) * unit_max
                err = np.abs(diff)
                it['results'][s['id']] = {
                    'image': base + ".png", 'err': None, 'planes': base + ".yuv.z",
                    'encode': cmd.replace(tmp, base + ".png"), 'decode': "(the result is an RGB image; no decode)",
                    'mean': round(float(err.mean()), 3), 'p99': round(float(np.percentile(err, 99)), 2),
                    'max': round(float(err.max()), 2), 'bias': round(float(diff.mean()), 3)}
            items[e['id']] = it
    return out_sources, out_groups, items


def write_error_png(diff, path):
    """Signed error against the source, in code values: 128 is none, each step is 1/ERR_STEPS of a code."""
    write_raw_png(np.clip(np.round(diff * ERR_STEPS) + 128, 0, 255).astype(np.uint8), path)


def write_planes(planes, path, bits):
    """Planes for the pixel probe, one after the other, zlib-compressed: uint8 for 8-bit values, otherwise uint16
    little-endian. The page reads them with the bit depth from the data."""
    dtype = np.uint8 if bits <= 8 else "<u2"
    with open(path, "wb") as f:
        f.write(zlib.compress(b"".join(p.astype(dtype).tobytes() for p in planes), 9))


def raw_planes(video, layout, w, h):
    """The file's planes as stored, with no conversion. Y', Cb, Cr (or R, G, B), as uint16 arrays."""
    bits, chroma, rgb = layout['bits'], layout['chroma'], layout['rgb']
    if rgb:
        fmt = "gbrp" if bits == 8 else f"gbrp{bits}le"
    else:
        fmt = f"yuv{chroma}p" + ("" if bits == 8 else f"{bits}le")
    # Read at the decoder's own format: some versions decode full-range H.264 as yuvj420p, and asking for yuv420p
    # would then convert it to limited range on the way out.
    native = native_pix_fmt(video)
    if native.replace("yuvj", "yuv") == fmt:
        fmt = native
    raw = run(f"ffmpeg -v error -i {video} -frames:v 1 -f rawvideo -pix_fmt {fmt} -")
    a = np.frombuffer(raw, np.uint8 if bits == 8 else "<u2").astype(np.uint16)
    sx = 1 if chroma == "444" or rgb else 2
    sy = 2 if chroma == "420" and not rgb else 1
    cw, ch = w // sx, h // sy
    p0 = a[:w * h].reshape(h, w)
    p1 = a[w * h:w * h + cw * ch].reshape(ch, cw)
    p2 = a[w * h + cw * ch:w * h + 2 * cw * ch].reshape(ch, cw)
    return [p2, p0, p1] if rgb else [p0, p1, p2]      # gbrp is stored G, B, R


def ideal_ycbcr(rgb, bits=10):
    """BT.709 limited-range Y'CbCr of the source, rounded: what a perfect 4:4:4 conversion stores."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    k = 1 << (bits - 8)
    planes = [16 * k + 219 * k * y, 128 * k + 224 * k * (b - y) / 1.8556, 128 * k + 224 * k * (r - y) / 1.5748]
    return [np.clip(np.round(p), 0, (1 << bits) - 1) for p in planes]


def native_pix_fmt(video):
    return run(f"ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of csv=p=0 {video}").decode().strip()


def cambi(video, workdir, w=None, h=None, rgb=False):
    """Netflix's CAMBI banding score (libvmaf) for the first frame: 0 is no banding, higher is more visible banding.

    CAMBI reads the luma codes. The frame is piped to libvmaf as raw planes at the decoder's own format, relabelled
    from yuvj to yuv where needed, so FFmpeg cannot convert it on the way (some versions turn full-range yuvj420p
    into limited range for libvmaf). RGB files are converted to 10-bit Y'CbCr with zscale first. libvmaf's filter
    takes two inputs, so the frame is passed as both."""
    log = os.path.join(workdir, "cambi.json")
    vmaf = f'-lavfi "[0:v][1:v]libvmaf=feature=name=cambi:log_fmt=json:log_path={log}" -f null -'
    if rgb or w is None:
        conv = "" if w is None else '-vf "zscale=matrix=709:range=limited,format=yuv444p10le"'
        run(f"ffmpeg -v error -i {video} -frames:v 1 {conv} -c:v ffv1 -y {log}.mkv")
        run(f"ffmpeg -v error -i {log}.mkv -i {log}.mkv {vmaf}")
        os.remove(log + ".mkv")
    else:
        fmt = native_pix_fmt(video)
        plain = fmt.replace("yuvj", "yuv")
        raw = f"{log}.raw"
        run(f"ffmpeg -v error -i {video} -frames:v 1 -f rawvideo -pix_fmt {fmt} -y {raw}")
        inp = f"-f rawvideo -pix_fmt {plain} -s {w}x{h} -i {raw}"
        run(f"ffmpeg -v error {inp} {inp} {vmaf}")
        os.remove(raw)
    with open(log) as f:
        score = json.load(f)['frames'][0]['metrics']['cambi']
    os.remove(log)
    return round(float(score), 2)


def cambi_of_source(path, workdir):
    """CAMBI of the source itself, losslessly converted to 10-bit 4:4:4 Y'CbCr (CAMBI reads luma)."""
    tmp = os.path.join(workdir, "cambi-source.mkv")
    run(f'ffmpeg -v error -y -i {path} -frames:v 1 -vf "zscale=matrix=709:range=limited,format=yuv444p10le" '
        f'-c:v ffv1 {tmp}')
    score = cambi(tmp, workdir)
    os.remove(tmp)
    return score


def white_spec(layout):
    top = (1 << layout['bits']) - 1
    if layout['rgb'] or layout['range'] == 'full':
        return top
    return 235 << (layout['bits'] - 8)


def run_comparison(root, sources, groups, unit_max, keep_videos=False, ideal_bits=None, error_maps=True,
                   banding=False):
    """Encode, decode and measure every variant on every source. Returns (sources, groups, items)."""
    os.makedirs(root, exist_ok=True)
    out_sources, out_groups, items = [], [], {}
    for s in sources:
        src = read_rgb(s['path'])
        h, w = src.shape[:2]
        s = dict(s, image=f"{s['id']}-source.png", width=w, height=h, data=src,
                 white=np.all(src >= 1.0 - 1e-6, axis=-1))
        write_display_png(src, os.path.join(root, s['image']))
        if banding:
            s['cambi'] = cambi_of_source(s['path'], root)
        if ideal_bits:
            s['planes'] = f"{s['id']}-source-ideal.yuv.z"
            s['idealBits'] = ideal_bits
            s['idealLabel'] = f"BT.709, limited, {ideal_bits}-bit"
            write_planes(ideal_ycbcr(src, ideal_bits), os.path.join(root, s['planes']), ideal_bits)
        out_sources.append(s)

    for glabel, entries in groups:
        out_groups.append({'label': glabel, 'items': [e['id'] for e in entries]})
        for e in entries:
            lay = e['layout']
            it = {'label': e['label'], 'group': glabel, 'description': e['description'], 'flags': e['flags'],
                  'layout': lay, 'results': {}}
            for s in out_sources:
                video = os.path.join(root, f"{s['id']}-{e['id']}.mp4")
                enc = e['encode'].format(src=s['path'], out=video)
                run(enc)
                decode_vf = DECODE_RGB if lay['rgb'] else DECODE_YCBCR.format(range=e.get('decode_range', lay['range']))
                dec = f'ffmpeg -v error -i {video} -frames:v 1 -vf "{decode_vf}" -f rawvideo -'
                g, b, r = np.frombuffer(run(dec), "<u2").reshape(3, s['height'], s['width']).astype(np.float64) / 65535
                out = np.stack([r, g, b], -1)
                base = f"{s['id']}-{e['id']}"
                write_display_png(out, os.path.join(root, base + ".png"))
                diff = (out - s['data']) * unit_max
                if error_maps:       # finer than the 8-bit display images; not needed when the unit is 8-bit
                    write_error_png(diff, os.path.join(root, base + "-err.png"))
                planes = raw_planes(video, lay, s['width'], s['height'])
                write_planes(planes, os.path.join(root, base + ".yuv.z"), lay['bits'])
                err = np.abs(diff)
                first = planes[1] if lay['rgb'] else planes[0]          # Y', or G for RGB
                white = float(first[s['white']].mean()) - white_spec(lay) if s['white'].any() else None
                it['results'][s['id']] = {
                    'image': base + ".png", 'err': base + "-err.png" if error_maps else None,
                    'planes': base + ".yuv.z",
                    'video': os.path.basename(video), 'encode': enc,
                    'decode': dec.replace(" -v error", "").replace("-f rawvideo -", "decoded.png").replace(
                        video, os.path.basename(video)),
                    'mean': round(float(err.mean()), 3), 'p99': round(float(np.percentile(err, 99)), 2),
                    'max': round(float(err.max()), 2), 'white': None if white is None else round(white, 2),
                    'levels': int(len(np.unique(first))),
                    'cambi': cambi(video, root, s['width'], s['height'], lay['rgb']) if banding else None}
                if not keep_videos:
                    os.remove(video)
            items[e['id']] = it
    return out_sources, out_groups, items


def print_table(version, sources, groups, items, stats):
    print("\n" + version)
    print("| Group | Variant | " + " | ".join(f"{s['label']} {st['short']}" for s in sources for st in stats) + " |")
    print("| :--- | :--- |" + " ---: |" * (len(sources) * len(stats)))
    for g in groups:
        for id_ in g['items']:
            cells = []
            for s in sources:
                r = items[id_]['results'].get(s['id'])
                if r is None:
                    cells += ["n/a"] * len(stats)
                    continue
                for st in stats:
                    v = r[st['key']]
                    cells.append("–" if v is None else (f"{v:+.{st.get('digits', 1)}f}" if st.get('signed')
                                                        else f"{v:.{st.get('digits', 1)}f}"))
            print(f"| {g['label']} | {items[id_]['label']} | " + " | ".join(cells) + " |")


def write_page(root, data, sources):
    data = dict(data, errSteps=ERR_STEPS,
                sources=[{k: s[k] for k in ('id', 'label', 'description', 'image', 'width', 'height', 'planes',
                                            'idealBits', 'idealLabel', 'cambi', 'layout') if k in s} for s in sources])
    with open(TEMPLATE) as f:
        html = f.read().replace("/*DATA*/null", json.dumps(data, indent=1))
    path = os.path.join(root, "compare.html")
    with open(path, "w") as f:
        f.write(html)
    print("Written", path)
