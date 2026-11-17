"""
Time the HDR resize variants of tests/resize-test.py on the Sparks EXR sequence, end to end: from the ACES2065-1
EXR frames to a ProRes 422 HQ QuickTime at a quarter of the size, viewed through OCIO's ACES 2.0 SDR view.

The variants (and their filters and oiiotool options) are read from resize-test.py, so the two stay in step:
- FFmpeg variants run as one ffmpeg command: EXR sequence -> resize and view transform -> ProRes.
- oiiotool variants write 16-bit uncompressed TIFFs (oiiotool --frames), then ffmpeg encodes those to ProRes with
  the same settings. Both steps are timed, and their sum is the total.

Everything is written to a temporary folder, which is deleted after each run; only the times are kept. Each output
is checked to have every frame. Before timing, the EXRs are read once so that they come from the file cache, not the
disk, for every variant (10 GB for all 200 frames: with less free memory than that, use fewer frames).

Run from anywhere, with ffmpeg (8.1 or later, with zscale and the ocio filter) and oiiotool on the PATH:
    python tests/resize-timing.py [--frames 6100-6299] [--repeat 3] [--only hc] [--parallel-frames] [--output FILE]
It prints a Markdown table (and writes it to --output if given), and updates resize-timing-results.json, which
resize-test.py reads for the timing table of compare.html: run it once as it is and once with --parallel-frames. Wall time is what matters; CPU time (user + system,
all threads) shows how much of the machine each variant uses.
"""
import argparse
import datetime
import importlib.util
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPARKS_DIR = os.path.join(HERE, "../enctests/sources/hdr_sources/sparks")
SPARKS = "SPARKS_ACES_%05d.exr"
RATE = "60000/1001"   # Sparks is 59.94 fps
W, H = 1024, 540      # a quarter of 4096x2160, as in resize-test.py
# The display image is sRGB-encoded BT.709 (ACES 2.0 SDR view for the sRGB display). zscale converts it to
# Y'CbCr; setparams writes the primaries and transfer (see AGENTS.md / EncodeZscale.md).
YUV = ("zscale=matrix=709:range=limited:filter=lanczos,format=yuv422p10le,"
       "setparams=color_primaries=bt709:color_trc=iec61966-2-1:colorspace=bt709")
PRORES = "-c:v prores_ks -profile:v 3 -vendor apl0"
# The results, read by resize-test.py for the timing table of compare.html. Each run updates its own mode
# ("default" or "parallel-frames") and keeps the other.
RESULTS = os.path.join(HERE, "resize-timing-results.json")


def load_resize_test():
    spec = importlib.util.spec_from_file_location("resize_test", os.path.join(HERE, "resize-test.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def variants(rt):
    """The HDR variants of resize-test.py, as ('ffmpeg', vf) or ('oiiotool', options)."""
    out = []
    for glabel, entries in rt.GROUPS:
        if not glabel.startswith("HDR sources"):
            continue
        for e in entries:
            cmd = e['command']
            m = re.search(r'-vf "(.*)" \{out\}$', cmd)
            if m:
                out.append(dict(id=e['id'], label=e['label'], tool='ffmpeg', vf=m.group(1).format(w=W, h=H, **rt.size_params(4096, W))))
                continue
            m = re.match(r'oiiotool \{exr\} (.*) -d uint16 -o \{out\}$', cmd)
            if m:
                out.append(dict(id=e['id'], label=e['label'], tool='oiiotool', ops=m.group(1).format(w=W, h=H)))
                continue
            print(f"Skipping {e['id']}: cannot turn its command into a sequence", file=sys.stderr)
    return out


def run(cmd, env=None):
    """Run a shell command; return (wall seconds, CPU seconds of the child processes)."""
    c0, t0 = os.times(), time.perf_counter()
    r = subprocess.run(cmd, shell=True, cwd=HERE, env=env, capture_output=True, text=True)
    t1, c1 = time.perf_counter(), os.times()
    if r.returncode:
        sys.exit(f"Failed ({r.returncode}): {cmd}\n{r.stderr}")
    cpu = (c1.children_user - c0.children_user) + (c1.children_system - c0.children_system)
    return t1 - t0, cpu


def frame_count(mov):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", mov],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def time_variant(v, first, last, tmp, env, parallel):
    """One run of a variant; returns a dict of times. Its files are deleted afterwards."""
    n = last - first + 1
    mov = os.path.join(tmp, "out.mov")
    src = os.path.join(SPARKS_DIR, SPARKS)
    t = {}
    if v['tool'] == 'ffmpeg':
        t['total'] = run(f'ffmpeg -v error -y -framerate {RATE} -start_number {first} -i {src} -frames:v {n} '
                         f'-vf "{v["vf"]},{YUV}" {PRORES} {mov}', env)
    else:
        tif = os.path.join(tmp, "frame.#.tif")
        par = "--parallel-frames " if parallel else ""
        t['oiiotool'] = run(f'oiiotool {par}--frames {first}-{last} --framepadding 5 '
                            f'{src.replace("%05d", "#")} {v["ops"]} -d uint16 --compression none -o {tif}', env)
        t['encode'] = run(f'ffmpeg -v error -y -framerate {RATE} -start_number {first} '
                          f'-i {tif.replace("#", "%05d")} -frames:v {n} -vf "{YUV}" {PRORES} {mov}', env)
        t['total'] = tuple(a + b for a, b in zip(t['oiiotool'], t['encode']))
    got = frame_count(mov)
    if got != n:
        sys.exit(f"{v['id']}: {got} frames in the QuickTime, expected {n}")
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    return t


def version(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout or r.stderr).splitlines()[0].strip()


def machine():
    try:
        cpu = subprocess.run(["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    except OSError:
        cpu = ""
    return f"{cpu or platform.processor()} ({os.cpu_count()} cores), {platform.system()} {platform.release()}"


def write_json(path, rows, first, last, args, ff_version, oiio_version):
    """Merge this run into the results file. A different frame range starts a new file."""
    data = {}
    if os.path.exists(path):
        with open(path) as fh:
            data = json.load(fh)
    if data.get('frames') != [first, last]:
        data = {'frames': [first, last]}
    mode = data.setdefault('modes', {}).setdefault("parallel-frames" if args.parallel_frames else "default",
                                                   {'results': {}})
    mode.update(ffmpeg=ff_version, oiiotool=oiio_version, machine=machine(), repeat=args.repeat,
                date=datetime.date.today().isoformat())
    for v, m in rows:
        mode['results'][v['id']] = dict({k: round(t[0], 2) for k, t in m.items()}, tool=v['tool'],
                                        cpu=round(m['total'][1], 1))
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    print("Written", path, file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", default="6100-6299", help="frame range (default: all 200 frames)")
    p.add_argument("--repeat", type=int, default=1, help="runs per variant; the median is reported")
    p.add_argument("--only", help="only variants whose id contains this text")
    p.add_argument("--parallel-frames", action="store_true",
                   help="run oiiotool with --parallel-frames (several frames at once); FFmpeg variants are skipped")
    p.add_argument("--output", help="also write the Markdown table to this file")
    p.add_argument("--json", default=RESULTS, help=f"results file to update (default {os.path.relpath(RESULTS)}); "
                   "'' to not write one")
    args = p.parse_args()
    first, last = (int(x) for x in args.frames.split("-"))
    n = last - first + 1
    files = [os.path.join(SPARKS_DIR, SPARKS % f) for f in range(first, last + 1)]
    missing = [f for f in files if not os.path.exists(f)]
    if missing:
        sys.exit(f"{len(missing)} frames missing, e.g. {missing[0]}: run enctests/sources/hdr_sources/download_media.sh")

    rt = load_resize_test()
    vs = [v for v in variants(rt) if (not args.only or args.only in v['id'])
          and not (args.parallel_frames and v['tool'] == 'ffmpeg')]
    env = dict(os.environ, OCIO="ocio://default")   # as resize-test.py: OCIO 2.5's built-in config

    print(f"Reading {n} EXRs once, so that every variant reads them from the file cache ...", file=sys.stderr)
    for f in files:
        with open(f, "rb") as fh:
            while fh.read(1 << 24):
                pass

    rows = []
    tmp = tempfile.mkdtemp(prefix="resize-timing-")
    try:
        for v in vs:
            runs = []
            for i in range(args.repeat):
                print(f"{v['id']} ({i + 1}/{args.repeat}) ...", file=sys.stderr, flush=True)
                runs.append(time_variant(v, first, last, tmp, env, args.parallel_frames))
            med = {k: (statistics.median(r[k][0] for r in runs), statistics.median(r[k][1] for r in runs))
                   for k in runs[0]}
            rows.append((v, med))
            print(f"  {med['total'][0]:.1f} s, {n / med['total'][0]:.2f} fps", file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    ff_version = version('ffmpeg -version').split(' Copyright')[0]
    oiio_version = version('oiiotool --version')
    if args.json:
        write_json(args.json, rows, first, last, args, ff_version, oiio_version)
    rows.sort(key=lambda r: r[1]['total'][0])
    lines = [
        f"Sparks frames {first}-{last} ({n} frames, 4096x2160 half-float EXR) to {W}x{H} ProRes 422 HQ, "
        f"median of {args.repeat} run(s).",
        "",
        f"{ff_version}; oiiotool {oiio_version}"
        f"{' (--parallel-frames)' if args.parallel_frames else ''}; {machine()}.",
        "",
        "| Variant | Tool | Total (s) | fps | oiiotool (s) | ProRes encode (s) | CPU (s) |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for v, m in rows:
        oi = f"{m['oiiotool'][0]:.1f}" if 'oiiotool' in m else ""
        enc = f"{m['encode'][0]:.1f}" if 'encode' in m else ""
        lines.append(f"| {v['label']} (`{v['id']}`) | {v['tool']} | {m['total'][0]:.1f} | {n / m['total'][0]:.2f} | "
                     f"{oi} | {enc} | {m['total'][1]:.0f} |")
    table = "\n".join(lines)
    print(table)
    if args.output:
        with open(args.output, "w") as fh:
            fh.write(table + "\n")


if __name__ == "__main__":
    main()
