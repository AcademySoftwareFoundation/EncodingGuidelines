#!/usr/bin/env python3


import os
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from functools import partial
import subprocess



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
    file_path = args.input
    outputfile = otherargs[-1]
    otherargs = otherargs[:-1] #Strip of the last argument.

    input_path = Path(file_path)

    outputdir = os.path.dirname(outputfile)
    tmpoutputdir = os.path.join(outputdir, "tmpj2kfiles", os.path.basename(outputfile))
)
    output_path = Path(os.path.join(tmpoutputdir, os.path.basename(str(input_path)))).with_suffix('.j2c')

    if not os.path.exists(tmpoutputdir):
        os.makedirs(tmpoutputdir)
    
    # Get list of files
    inputfile = args.input

    oiio_args = []
    launch_arg = otherargs.pop(0) # Get rid of the app to run.
    arg = otherargs.pop(0)
    while otherargs:
        if arg.startswith("-jph:"):
            oiio_args.append("--attrib")
            oiio_args.append(arg.replace("-jph:", "jph:"))
            arg = otherargs.pop(0)
            oiio_args.append(arg)
        else:
            print("Misc arg:", arg)
            oiio_args.append(arg)
        if not otherargs:
            break
        arg = otherargs.pop(0)
    
    endframe = int(args.start_frame)
    file = str(input_path) % endframe
    print("FILE:", file, " from :", input_path)
    while(os.path.exists(str(input_path) % endframe)):
        endframe += 1
    endframe -= 1

    oiio_args = [launch_arg, '-v', '-i', str(input_path), "--parallel-frames", "--frames", "%s-%d" % (args.start_frame, endframe)]+oiio_args+['-o', str(output_path)]
    print(" ".join(oiio_args))
    subprocess.run(oiio_args)
        

    intputfilej2k = str(Path(os.path.join(tmpoutputdir, os.path.basename(inputfile))).with_suffix('.j2c'))
    cmd = ['ffmpeg', '-f', 'image2', '-r', args.framerate, 
            '-start_number', args.start_frame, '-i', intputfilej2k, '-vcodec', 'copy', 
            '-color_range',  '1', '-colorspace', '1', '-color_primaries', '1', 
            '-color_trc', '2', '-y', outputfile]
    subprocess.run(cmd)
    # Now we remove the intermediate files.




if __name__ == '__main__':
    main()

