#!/usr/bin/env python3
"""
Check and update the graphs the documentation uses (enctests/reference-results/), using graphs.yml.

  python reference-results/update_doc_graphs.py --check
      For every graph group: the config exists, its report name matches, the OTIO exists (and which FFmpeg version
      and date it is from), whether the config has changed since that run, and that every image the pages use is
      here. Also lists images the pages use that graphs.yml doesn't know about. Exits 1 if anything is missing.

  python reference-results/update_doc_graphs.py --update intra-test422 --version 9.0.2
      Copies the graphs and OTIO of a run (wedge_results/ffmpeg_version_<version>/<platform>/<config>-encode/)
      into this folder, renamed to the group's prefix.

  python reference-results/update_doc_graphs.py --redraw intra-test422
      Redraws the group's graphs from the OTIO in this folder (no encoding), e.g. to add the version stamp.
      Uses the current config's graph settings.

Run from enctests/ (paths in graphs.yml are relative to it).
"""
import argparse
import hashlib
import pathlib
import re
import shutil
import sys
import tempfile

import yaml

HERE = pathlib.Path(__file__).resolve().parent
ENCTESTS = HERE.parent
DOCS = ENCTESTS.parent
# Pages that are not part of the site.
SKIP_PAGES = {"TODO.md", "DONE.md", "SAMTODO.md", "AGENTS.md", "README.md"}


def load_manifest():
    with open(HERE / "graphs.yml") as f:
        return yaml.safe_load(f)


def config_report(config_path):
    """Return (report dict, sha256) for a config file."""
    data = config_path.read_bytes()
    report = None
    for doc in yaml.safe_load_all(data):
        if doc and "reports" in doc:
            report = doc["reports"]
    return report, hashlib.sha256(data).hexdigest()


def otio_info(otio_path):
    """Return a dict of what the run's OTIO says about itself, read without loading the whole timeline."""
    import opentimelineio as otio
    timeline = otio.adapters.read_from_file(str(otio_path))
    meta = timeline.metadata
    return {
        "ffmpeg": timeline.tracks[0].name.replace("ffmpeg_version_", ""),
        "date": str(meta.get("test_start", "")).split(" ")[0],
        "config_sha256": meta.get("config_sha256"),
    }


def page_references():
    """Map each file in reference-results that a page uses to the pages using it."""
    refs = {}
    for page in sorted(DOCS.glob("*.md")):
        if page.name in SKIP_PAGES:
            continue
        for name in re.findall(r"reference-results/([A-Za-z0-9_.%-]+)", page.read_text(errors="replace")):
            refs.setdefault(name, set()).add(page.name)
    return refs


def check(manifest):
    refs = page_references()
    errors = 0
    known = set(manifest.get("other", {}))
    rows = []
    for prefix, entry in sorted(manifest["graphs"].items()):
        problems = []
        config = ENCTESTS / entry["config"]
        version = date = "-"
        changed = ""
        report, sha = (None, None)
        if not config.exists():
            problems.append(f"config {entry['config']} missing")
        else:
            report, sha = config_report(config)
            want = entry.get("report", prefix)
            if not report or report.get("name") != want:
                problems.append(f"config report name is {report and report.get('name')!r}, expected {want!r}")
        otio_path = HERE / entry["otio"]
        if not otio_path.exists():
            problems.append(f"{entry['otio']} missing")
        else:
            info = otio_info(otio_path)
            version, date = info["ffmpeg"], info["date"] or "?"
            if info["config_sha256"] and sha and info["config_sha256"] != sha:
                changed = "config changed since run"
        used = sorted(n for n in refs if n.startswith(prefix + "-") and n.endswith(".png")
                      and not any(n.startswith(p + "-") for p in manifest["graphs"]
                                  if len(p) > len(prefix) and p.startswith(prefix)))
        known.update(used)
        for name in used:
            if not (HERE / name).exists():
                problems.append(f"{name} (used by {', '.join(sorted(refs[name]))}) missing")
        pages = sorted({p for n in used for p in refs[n]})
        rows.append((prefix, version, date, ", ".join(pages) or "(not used)", changed))
        if problems:
            errors += len(problems)
            for p in problems:
                print(f"ERROR {prefix}: {p}")
        if entry.get("note") and "--verbose" in sys.argv:
            print(f"note {prefix}: {entry['note']}")

    for name in sorted(set(refs) - known):
        errors += 1
        print(f"ERROR {name} (used by {', '.join(sorted(refs[name]))}) is not in graphs.yml")
    for name in sorted(set(manifest.get("other", {}))):
        if not (HERE / name).exists():
            errors += 1
            print(f"ERROR {name} missing")

    print()
    print(f"| {'Graphs':24} | {'FFmpeg':26} | {'Run':10} | Pages |")
    print(f"| {'-' * 24} | {'-' * 26} | {'-' * 10} | ----- |")
    for prefix, version, date, pages, changed in rows:
        print(f"| {prefix:24} | {version:26} | {date:10} | {pages}{'  (' + changed + ')' if changed else ''} |")
    print()
    print("OK" if not errors else f"{errors} problem(s)")
    return 1 if errors else 0


def report_graph_names(entry):
    report, _ = config_report(ENCTESTS / entry["config"])
    return report, [g["name"] for g in report.get("graphs", [])]


def copy_group(prefix, entry, src_dir, report_name):
    report, names = report_graph_names(entry)
    for name in names:
        src = src_dir / f"{report_name}-{name}"
        if src.exists():
            shutil.copyfile(src, HERE / f"{prefix}-{name}")
            print(f"{src} -> {prefix}-{name}")
        else:
            print(f"(no {src.name} in the run)")


def update(manifest, prefix, version, results_folder, platform):
    entry = manifest["graphs"][prefix]
    config = pathlib.Path(entry["config"])
    run_dir = ENCTESTS / results_folder / f"ffmpeg_version_{version}" / platform / f"{config.stem}-encode"
    otio_src = run_dir / f"{config.stem}.otio"
    if not otio_src.exists():
        sys.exit(f"{otio_src} not found")
    report, _ = config_report(ENCTESTS / config)
    copy_group(prefix, entry, run_dir, report["name"])
    shutil.copyfile(otio_src, HERE / entry["otio"])
    print(f"{otio_src} -> {entry['otio']}")


def redraw(manifest, prefix):
    sys.path.insert(0, str(ENCTESTS))
    import opentimelineio as otio
    from testframework.test_suite import TestSuite
    from testframework.utils.outputTemplate import processTemplate
    entry = manifest["graphs"][prefix]
    suite = TestSuite(pathlib.Path(entry["config"]))
    with tempfile.TemporaryDirectory() as tmp:
        suite.set_destination(pathlib.Path(tmp))
        processTemplate(suite, otio.adapters.read_from_file(str(HERE / entry["otio"])))
        copy_group(prefix, entry, pathlib.Path(tmp), suite.report()["name"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check graphs.yml against the pages, configs and OTIOs.")
    group.add_argument("--update", metavar="PREFIX", help="Copy a run's graphs and OTIO in.")
    group.add_argument("--redraw", metavar="PREFIX", help="Redraw the graphs from the OTIO here.")
    parser.add_argument("--version", help="FFmpeg version folder of the run to copy (with --update).")
    parser.add_argument("--results-folder", default="wedge_results", help="Relative to enctests/.")
    parser.add_argument("--platform", default="darwin-arm64")
    parser.add_argument("--verbose", action="store_true", help="Also print the notes.")
    args = parser.parse_args()

    import os
    os.chdir(ENCTESTS)
    manifest = load_manifest()
    for prefix in (args.update, args.redraw):
        if prefix and prefix not in manifest["graphs"]:
            sys.exit(f"{prefix} is not in graphs.yml")
    if args.check:
        sys.exit(check(manifest))
    if args.update:
        if not args.version:
            sys.exit("--update needs --version")
        update(manifest, args.update, args.version, args.results_folder, args.platform)
    else:
        redraw(manifest, args.redraw)


if __name__ == "__main__":
    main()
