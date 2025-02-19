#!/usr/bin/env python3


import os, sys
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from functools import partial
import subprocess

# This allows you to compress the file with the compressor of your choice, and then wrap the result in a quicktime file
# So we can do the comparison with vmaf.
# We assume that what ever the intermediate compressor is doing that the resulting intermediate file is a png file.

def process_file(args, tmpoutputdir, ext, file_path):
    input_path = Path(file_path)
    output_path = Path(os.path.join(tmpoutputdir, os.path.basename(str(input_path)))).with_suffix(ext)
    if os.path.exists(str(output_path)):
        print("Removing file:", output_path)
        os.remove(str(output_path))
    try:
        # Your processing here
        # Example: copy file with new extension
        cmd = args[:]
        cmd.extend(['-i', file_path])

        cmd.extend(["-o", str(output_path)])
        print("Running:", " ".join(cmd))
        subprocess.run(cmd)
        return True, input_path, output_path
    except Exception as e:
        print("ERROR:", e)
        return False, input_path, str(e)

def main():
    print("Root:", os.path.dirname(os.path.abspath(__file__)))
    os.environ['PATH'] = os.path.dirname(os.path.abspath(__file__)) + ":" + os.environ['PATH']
    
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
    
    parser.add_argument(
        '--extension',
        dest="extension",
        default="png",
        help='Intermediate extension'
    )

    args, otherargs = parser.parse_known_args()
    ext = args.extension
    print("EXT:", ext)
    outputfile = otherargs[-1]
    otherargs = otherargs[:-1] #Strip of the last argument.

    # Configure number of workers
    max_workers = 4

    outputdir = os.path.dirname(outputfile)
    tmpoutputdir = os.path.join(outputdir, "tmppngfiles", os.path.basename(outputfile))
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
        results = executor.map(partial(process_file, otherargs, str(tmpoutputdir), "." + ext), files)
    
    # Report results
    successes = [r for r in results if r[0]]
    failures = [r for r in results if not r[0]]
    
    print(f"\nProcessed {len(successes)} files successfully")
    if failures:
        print(f"Failed to process {len(failures)} files:")
        for _, input_path, error in failures:
            print(f"  {input_path}: {error}")
    else:
        intputfilej2k = str(Path(os.path.join(tmpoutputdir, os.path.basename(inputfile))).with_suffix("." + ext))
        cmd = ['ffmpeg', '-f', 'image2', '-r', args.framerate, 
                '-start_number', args.start_frame, '-i', intputfilej2k, '-vcodec', 'copy', 
                '-color_range',  '1', '-colorspace', '1', '-color_primaries', '1', 
                '-color_trc', '2', '-y', outputfile]
        print(" ".join(cmd))
        subprocess.run(cmd)
        # Now we remove the intermediate files.




if __name__ == '__main__':
    main()

