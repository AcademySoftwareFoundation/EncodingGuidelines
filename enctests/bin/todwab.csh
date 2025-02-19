#!/usr/bin/env python3


import os, sys
import argparse
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        dest="input",
        action='store',
        default="",
        help='Provide an input file.'
    )

    parser.add_argument(
        '-o', '--output',
        dest="output",
        action='store',
        default="",
        help='Provide an output file.'
    )

    print("ARGV:", sys.argv)

    args, otherargs = parser.parse_known_args(sys.argv[1:])
    newotherargs = []
    print("Other args:", otherargs)
    print("ARGS:", args)


    input_path = Path(args.input)
    output_path = Path(args.output)
    intermediate_path = output_path.with_suffix(".exr")

    cmd = ["oiiotool", "-i", str(input_path)]
    cmd.extend(otherargs)
    cmd.extend(["-o", str(intermediate_path)])
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)
    cmd = ['oiiotool', '-i', str(intermediate_path), "-o", str(output_path) ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)

if __name__ == '__main__':
    main()