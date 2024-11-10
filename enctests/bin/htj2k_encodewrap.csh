#!/usr/bin/env python3


import os
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from functools import partial
import subprocess

def process_file(args, tmpoutputdir, file_path):
    input_path = Path(file_path)
    output_path = Path(os.path.join(tmpoutputdir, os.path.basename(str(input_path)))).with_suffix('.j2c')
    if os.path.exists(str(output_path)):
        print("Removing file:", output_path)
        os.remove(str(output_path))
    try:
        # Your processing here
        # Example: copy file with new extension
        cmd = [f.replace("--reversible", "-reversible") for f in args[:]]
        cmd.extend(['-i', file_path, "-o", str(output_path)])
        print("Running:", " ".join(cmd))
        subprocess.run(cmd)
        return True, input_path, output_path
    except Exception as e:
        print("ERROR:", e)
        return False, input_path, str(e)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-i', '--input',
        dest="input",
        action='store',
        default=[""],
        help='Provide an input file.'
    )
    parser.add_argument(
        '-start_number',
        dest="start_frame",
        default="0",
        help='Start frame for input file.'
    )   
    parser.add_argument(
        '-r',
        dest="framerate",
        default="25",
        help='Frame rate'
    )

    args, otherargs = parser.parse_known_args()
    outputfile = otherargs[-1]
    otherargs = otherargs[:-1] #Strip of the last argument.

    # Configure number of workers
    max_workers = 4

    outputdir = os.path.dirname(outputfile)
    tmpoutputdir = os.path.join(outputdir, "tmpj2kfiles")
    if not os.path.exists(tmpoutputdir):
        os.makedirs(tmpoutputdir)
    
    # Get list of files
    inputfile = args.input
    print("Processing input file spec:", inputfile)
    files = []
    if "%" in inputfile:
        startframe = int(args.start_frame)
        infile = inputfile % startframe
        while os.path.exists(infile):
            files.append(infile)
            startframe = startframe + 1
            infile = inputfile % startframe
            print("Checking:", infile)
    else:
        files.append(inputfile)
    # files = list(Path('directory').glob('*.txt'))
    
    # Process files with progress bar
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(partial(process_file, otherargs, str(tmpoutputdir)), files)
    
    # Report results
    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]
    
    print(f"\nProcessed {len(successes)} files successfully")
    if failures:
        print(f"Failed to process {len(failures)} files:")
        for _, input_path, error in failures:
            print(f"  {input_path}: {error}")
    else:
        intputfilej2k = str(Path(os.path.join(tmpoutputdir, os.path.basename(inputfile))).with_suffix('.j2c'))
        cmd = ['ffmpeg', '-f', 'image2', '-r', args.framerate, 
                '-start_number', args.start_frame, '-i', intputfilej2k, '-vcodec', 'copy', 
                '-color_range',  '1', '-colorspace', '1', '-color_primaries', '1', 
                '-color_trc', '2', '-y', outputfile]
        subprocess.run(cmd)
        # Now we remove the intermediate files.




if __name__ == '__main__':
    main()

