"""
Compare the results of the same tests across FFmpeg versions, and report what changed.

The tests' asserts answer "is this right?". This answers "is this different from the previous version?", so a
change shows up even where no assert covers it (a tag, a pixel format, an error inside the limits). For each
config, source and wedge, the watched fields (FIELDS) are lined up across the release versions found under a
results folder, oldest first, and every value that differs from the previous release is flagged, as better,
worse or changed. Development builds cannot be placed between releases from their folder name, so each is
compared with the newest release instead.

Only results from the same config file contents are compared (config_sha256, recorded by main.py), so a change
in the config or its asserts is not reported as an FFmpeg change; results from before that was recorded are
left out. Within those, a field missing from either side is not a change.

    python -m testframework.utils.versionChanges results [more folders...]

writes changes.html (and changes.json) in each folder. main.py also writes it after each run.
"""
import json
import os
import re
import sys
from pathlib import Path

import jinja2

# field: (tolerance, direction). Direction: "abs" (closer to 0 is better), "up" (higher is better), None (neither).
# A tolerance below 1 is absolute; "1%" style strings are relative.
FIELDS = {
    "status": (None, None),
    "pix_fmt": (None, None),
    "color_range": (None, None),
    "color_space": (None, None),
    "color_primaries": (None, None),
    "color_transfer": (None, None),
    "chroma_location": (None, None),
    "colr": (None, None),
    # stream_metadata.py: what is in the file itself, and how FFmpeg made it.
    "profile": (None, None),
    "bitstream_colour": (None, None),
    "bitstream_chroma_loc": (None, None),
    "prores_header": (None, None),
    "container_chroma_siting": (None, None),
    "auto_conversions": (None, None),
    # ycbcr_compare.py: what the pixels are, whatever the tags say.
    "pixels_match": (None, None),
    "chroma_siting_measured": (None, None),
    "chroma_offset_h": (0.1, None),
    "chroma_offset_v": (0.1, None),
    "chroma_siting_assumed": (None, None),
    "chroma_shift_h": (0.1, None),
    "chroma_shift_v": (0.1, None),
    # The libraries used, so a change that comes with one can be told from a change in FFmpeg.
    "encoder_library": (None, None),
    "decoder": (None, None),
    # Lossy encodes move by a few hundredths between encoder library versions; real changes are much larger.
    "white_error_10bit": (0.1, "abs"),
    "max_error_10bit": (0.01, "abs"),
    "mean_error_10bit": (0.05, "abs"),
    "p99_error_10bit": (0.01, "abs"),
    "Y": (1e-4, "up"), "U": (1e-4, "up"), "V": (1e-4, "up"),
    "R": (1e-4, "up"), "G": (1e-4, "up"), "B": (1e-4, "up"),
    "average": (1e-4, "up"),
    "vmaf_harmonic_mean": (0.1, "up"),
    "psnr_y_harmonic_mean": (0.05, "up"),
}

# Shown beside a change, to explain it, but not a change on their own: the libraries differ between builds of
# the same FFmpeg version.
CONTEXT = {"encoder_library", "decoder"}

RELEASE = re.compile(r"^\d+(\.\d+)*$")


def release_key(version):
    return tuple(int(p) for p in (version.split(".") + ["0", "0"])[:3])


def dev_key(version):
    # N-<commit count>-g<hash> or git-<date>-<hash>: order by the numbers in the name.
    return tuple(int(n) for n in re.findall(r"\d+", version)[:3])


def status_of(result):
    """As shown on the reports: pass, fail, known (a known issue), unexpected (a known issue that passed), skipped."""
    if result.get("skipped"):
        return "skipped"
    if result.get("known_issue"):
        return "known"
    if result.get("unexpected_pass"):
        return "unexpected"
    return "pass" if result.get("success", True) else "fail"


PASSED = {"pass": True, "unexpected": True, "fail": False, "known": False}


def comparison_kind(result):
    """Which comparison made a result, so results from different comparisons are not compared."""
    if "max_error_10bit" in result or result.get("compared_as"):
        return "ycbcr"
    if "average" in result:
        return "identity"
    if "vmaf_harmonic_mean" in result or "vmaf" in result:
        return "vmaf"
    return "other"


def flat(result):
    values = {"status": status_of(result)}
    if "vmaf" in result and isinstance(result["vmaf"], dict):
        values["vmaf_harmonic_mean"] = result["vmaf"].get("harmonic_mean")
    if "psnr_y" in result and isinstance(result["psnr_y"], dict):
        values["psnr_y_harmonic_mean"] = result["psnr_y"].get("harmonic_mean")
    for key in FIELDS:
        if key in result and key not in values:
            values[key] = result[key]
    return values


def classify(field, old, new):
    """None if the same, else "better", "worse" or "changed"."""
    tolerance, direction = FIELDS[field]
    if field == "status":
        if old == new:
            return None
        if "skipped" in (old, new) or PASSED[old] == PASSED[new]:
            return "changed"
        return "better" if PASSED[new] else "worse"
    if isinstance(old, (int, float)) and isinstance(new, (int, float)):
        if isinstance(tolerance, str):
            limit = abs(old) * float(tolerance.rstrip("%")) / 100
        else:
            limit = tolerance or 0
        if abs(new - old) <= limit:
            return None
        if direction == "abs":
            return "better" if abs(new) < abs(old) else "worse"
        if direction == "up":
            return "better" if new > old else "worse"
        return "changed"
    return None if old == new else "changed"


def read_results(root):
    """{(platform, config, config sha): {version: {(source, wedge): (kind, values, testresult)}}}, the framework
    commit of each, the build of each (platform, version), and the results without a config hash (from before it
    was recorded)."""
    found, commits, builds, legacy = {}, {}, {}, []
    for path in sorted(Path(root).rglob("*.otio")):
        if path.name.startswith("."):
            continue
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        version = path.parent.parent.parent.name.replace("ffmpeg_version_", "")
        platform = path.parent.parent.name
        config = path.stem
        sha = (data.get("metadata") or {}).get("config_sha256")
        if not sha:
            legacy.append(path)
            continue
        wedges = {}
        for track in data.get("tracks", {}).get("children", []):
            for clip in track.get("children", []):
                for ref_name, ref in clip.get("media_references", {}).items():
                    meta = (ref.get("metadata") or {}).get("aswf_enctests")
                    if ref_name == "DEFAULT_MEDIA" or not meta:
                        continue
                    result = meta.get("results", {})
                    wedges[(clip.get("name"), ref_name)] = (comparison_kind(result), flat(result),
                                                           result.get("testresult", ""))
        if wedges:
            found.setdefault((platform, config, sha), {})[version] = wedges
            commits.setdefault((platform, config, sha), {})[version] = data["metadata"].get("framework_commit", "")
            if data["metadata"].get("ffmpeg_configuration") is not None:
                builds[(platform, version)] = build_summary(data["metadata"])
    return found, commits, builds, legacy


def build_summary(metadata):
    """The external libraries a build was configured with, and those it links dynamically (with versions)."""
    enabled = sorted(set(re.findall(r"--enable-(lib[\w-]+)", metadata.get("ffmpeg_configuration") or "")))
    linked = [l for l in metadata.get("ffmpeg_libraries") or []
              if not re.match(r"lib(av|sw|postproc)\w*\.", l)]
    return {"enabled": enabled, "linked": linked, "static": not any(
        re.match(r"libav\w*\.", l) for l in metadata.get("ffmpeg_libraries") or [])}


def compare_versions(versions, by_version):
    """Rows for one config: each (source, wedge, field) that changes between neighbouring versions.

    versions is the ordered list of columns; by_version maps version -> wedges. Each release is compared with the
    previous release that has a value; each development build with the newest release.
    """
    releases = [v for v in versions if RELEASE.match(v)]
    newest = releases[-1] if releases else None
    keys = sorted({k for v in versions for k in by_version.get(v, {})})
    rows, pairs = [], {}
    for source, wedge in keys:
        cells = {}
        for field in FIELDS:
            line, changed, previous = {}, False, None
            for version in versions:
                entry = by_version.get(version, {}).get((source, wedge))
                if entry is None or field not in entry[1]:
                    continue
                kind, values, note = entry
                value = values[field]
                if RELEASE.match(version):
                    base = previous
                else:
                    base = cells.get("_newest", {}).get(field) if newest else None
                verdict = None
                # Status is compared whatever the comparison (a skipped result has no other fields).
                if base is not None and (base[0] == kind or field == "status"):
                    verdict = classify(field, base[1], value)
                line[version] = {"value": value, "verdict": verdict, "note": note if field == "status" else "",
                                 "base": base[2] if base else None}
                if verdict:
                    changed = True
                if verdict and field not in CONTEXT:
                    pair = (base[2], version)
                    pairs.setdefault(pair, {"better": 0, "worse": 0, "changed": 0, "configs": set()})
                    pairs[pair][verdict] += 1
                if RELEASE.match(version):
                    previous = (kind, value, version)
                    if version == newest:
                        cells.setdefault("_newest", {})[field] = previous
            if changed:
                cells[field] = line
        cells.pop("_newest", None)
        if any(field not in CONTEXT for field in cells):
            rows.append({"source": source, "wedge": wedge, "fields": cells})
    return rows, pairs


def fmt(value):
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, int) and abs(value) >= 10000:
        return f"{value:,}"
    return str(value)


def outputVersionChanges(output_dir):
    """Write changes.html and changes.json in output_dir, from all the results under it."""
    found, commits, builds, legacy = read_results(output_dir)
    sections, summary = [], {}
    for (platform, config, sha), by_version in sorted(found.items()):
        releases = sorted((v for v in by_version if RELEASE.match(v)), key=release_key)
        devs = sorted((v for v in by_version if not RELEASE.match(v)), key=dev_key)
        versions = releases + devs
        if len(versions) < 2:
            continue
        rows, pairs = compare_versions(versions, by_version)
        for pair, counts in pairs.items():
            entry = summary.setdefault((platform,) + pair, {"better": 0, "worse": 0, "changed": 0, "configs": []})
            for k in ("better", "worse", "changed"):
                entry[k] += counts[k]
            entry["configs"].append({"config": config, "id": f"{platform}-{config}-{sha[:8]}"})
        sections.append({"platform": platform, "config": config, "sha": sha[:8], "versions": versions, "rows": rows,
                         "commits": commits[(platform, config, sha)], "id": f"{platform}-{config}-{sha[:8]}"})

    def pair_key(item):
        (platform, old, new), _ = item
        dev = not RELEASE.match(new)
        return (platform, dev, dev_key(new) if dev else release_key(new))
    pairs = [{"platform": p, "old": o, "new": n, **counts}
             for (p, o, n), counts in sorted(summary.items(), key=pair_key)]

    template_dir = Path(__file__).parent.parent / "templates"
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_dir)))
    environment.filters["fmt"] = fmt
    def build_key(item):
        (platform, version), _ = item
        dev = not RELEASE.match(version)
        return (platform, dev, dev_key(version) if dev else release_key(version))
    builds = [{"platform": p, "version": v, **b} for (p, v), b in sorted(builds.items(), key=build_key)]
    html = environment.get_template("changes.html.jinja").render(sections=sections, pairs=pairs, legacy=len(legacy),
                                                                 builds=builds, release=RELEASE.match)
    Path(output_dir, "changes.html").write_text(html)
    with Path(output_dir, "changes.json").open("w") as f:
        json.dump({"pairs": pairs, "builds": builds, "sections": sections}, f, indent=1, default=str)
    print("Written out:", Path(output_dir, "changes.html"))


if __name__ == "__main__":
    for folder in sys.argv[1:] or ["results"]:
        outputVersionChanges(folder)
