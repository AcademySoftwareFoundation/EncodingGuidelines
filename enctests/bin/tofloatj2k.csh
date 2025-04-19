#!/usr/bin/env python3


import os
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

    args, otherargs = parser.parse_known_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    intermediate_path = output_path.with_suffix(".exr")
    # Initial conversion to exr, to ensure the ojph_compress is using exr and its half float.
    cmd = ['oiiotool', '-i', str(input_path), "-o", str(intermediate_path) ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)
    # Now we do the j2c compression
    j2k_intermediate_path = output_path.with_suffix(".j2c")
    cmd = ["/Users/sam/git/OpenJphExr/build/src/apps/ojph_compress/ojph_compress", "-i", str(intermediate_path)]
    cmd.extend(otherargs)
    cmd.extend(["-o", str(j2k_intermediate_path)])
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)

    # Now we do the decompression using the same decompression code
    exr_intermediate_path2 = str(output_path).replace(".png", "2.exr")
    cmd = ["/Users/sam/git/OpenJphExr/build/src/apps/ojph_expand/ojph_expand", "-i", str(j2k_intermediate_path), "-o", str(exr_intermediate_path2)]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)

    # Finally we convert the result back to png
    cmd = ['oiiotool', '-i', str(exr_intermediate_path2), "-o", str(output_path) ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd)

if __name__ == '__main__':
    main()