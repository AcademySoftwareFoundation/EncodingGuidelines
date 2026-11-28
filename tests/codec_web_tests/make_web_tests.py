#!/usr/bin/env python3
"""Encode the movies for web_compatibility.html from enctests/test_wedge_configs/codec_web_tests.yml.

Each wedge is written next to this script as <source>-<test>-<wedge>.mp4, the names the page uses.
Run with the FFmpeg you want to test on the PATH, e.g.
    rez-env encodingguidelines_env ffmpeg-9.0.2 -- python tests/codec_web_tests/make_web_tests.py
"""
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
CONFIG = HERE.parent.parent / "enctests" / "test_wedge_configs" / "codec_web_tests.yml"


def main():
    config = yaml.safe_load(CONFIG.read_text())
    failed = []
    for test_name, test in config.items():
        template = test["encoding_template"]
        for source in test["sources"]:
            # Sources are relative to enctests/, as for the test framework.
            source_path = (CONFIG.parent.parent / source).resolve()
            for wedge_name, args in test["wedges"].items():
                encoding_args = " ".join(f"{k} {v}" for k, v in args.items())
                outfile = HERE / f"{source_path.stem}-{test_name}-{wedge_name}{test['suffix']}"
                cmd = template.format(input_args="-v error", source=source_path, duration=1,
                                      encoding_args=encoding_args, outfile=outfile)
                print(outfile.name, flush=True)
                if subprocess.run(shlex.split(cmd)).returncode != 0:
                    failed.append(outfile.name)
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
