# Test configs
import os
import sys
import time
import shlex
import subprocess

from config import testconfigs, testfiles

# Were to store all rendered files
TEST_DIR = 'results'

# OpenImageIO
OIIOTOOL_BIN = os.getenv(
    "OIIOTOOL_BIN",
    "oiiotool"
)

IDIFF_BIN = os.getenv(
    "IDIFF_BIN",
    "idiff"
)

# We assume macos and linux both have the same binary name
FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    'win' in sys.platform and 'ffmpeg.exe' or 'ffmpeg'
)

# Which vmaf model to use
VMAF_MODEL = os.getenv(
    'VMAF_MODEL',
    "vmaf_v0.6.1.json"
)


def write_html(test_results):
    fields = [
        'testname',
        'testfile',
        'testoutput',
        'vmaf_output',
        'filesize',
        'ffmpeg_duration'
    ]

    head = """\
<html lang="en" xml:lang="en" xmlns= "http://www.w3.org/1999/xhtml">
<meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="en">
<head>
    <style type='text/css'>
        img {
            filter: brightness(10);
        }
    </style>
</head>
<body>
"""
    with open("results/results.html", "w") as results:
        results.write(head)
        results.write("<TABLE border=1>\n")

        # Create header
        results.write("<TR>")
        for field in fields:
            results.write("<TH>{field}</TH>".format(field=field))
        results.write("<TH>Image Diff x 10</TH>")
        results.write("</TR>\n")

        # Write rows with results
        for test_result in test_results:
            results.write("<TR>")
            for field in fields:
                if field == "testoutput":
                    results.write(
                        "<TD><PRE>{data}</PRE></TD>".format(
                            data=str(test_result[field])
                        )
                    )
                    continue
                if type(test_result[field]) is str:
                    results.write(
                        "<TD>{data}</TD>".format(data=str(test_result[field]))
                    )

                else:
                    results.write(
                        "<TD align='right'>{data}</TD>".format(
                            data=str(test_result[field])
                        )
                    )
            results.write("<TD>{diff}</TD></TR>".format(
                diff=test_result['diff_html'])
            )
            results.write(
                "<TR><TD COLSPAN={col_span}>{ffmpeg_cmd}</TD>".format(
                    col_span=len(fields) + 1,
                    ffmpeg_cmd=test_result['ffmpeg_encode_cmd']   # cmd
                )
            )
            results.write("</TR>\n")
        results.write("</TABLE>\n</BODY>\n</HTML>")


def ffmpeg_convert(source_config, test_config, outfile):
    ffmpeg_cmd = "\
{ffmpeg_bin} \
{input_args} \
-i {source} \
{duration} \
{compression_args} \
-y {outfile}\
"
    source = source_config.get('source_file')
    input_args = ' '.join(source_config.get('input_args', []))
    duration = source_config.get('duration', '')
    cmd = ffmpeg_cmd.format(
                ffmpeg_bin=FFMPEG_BIN,
                input_args=input_args,
                source=source,
                duration=duration,
                compression_args=' '.join(test_config.get('ffmpeg_args')),
                outfile=outfile
            )

    print('ffmpeg command:', cmd)
    rc = subprocess.call(shlex.split(cmd))

    return cmd, rc


def ffmpeg_diff(outfile, test_config):
    compare_cmd = "\
{ffmpeg_bin} \
{input_args} \
-i {reference} \
-i {source} \
{duration} \
-filter_complex \
[1:v]format=yuva444p,lut=c3=128,negate[video2withAlpha],\
[0:v][video2withAlpha]overlay[out] -map [out] \
-y {diff}\
"
    duration = test_config.get('duration', '')

    # Movie compare from http://dericed.com/2012/display-video-difference-with-ffmpegs-overlay-filter/
    base, ext = os.path.splitext(outfile)

    # Do the diff movies in mp4 so that they can load in a browser.
    diff_file = f"{base}-diff{ext}"

    cmd = compare_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        input_args=' '.join(test_config.get('input_args', [])),
        reference=test_config['source_file'],
        source=outfile,
        duration=duration,
        diff=diff_file
    )
    print("FFmpeg Compare command:", cmd)
    subprocess.call(shlex.split(cmd))

    diff_html = "<video width='200' height='112' controls>" \
                "<source src='{diff}' type='video/mp4'>" \
                "Your browser does not support the video tag." \
                "</video>".format(diff=os.path.basename(diff_file))

    return diff_html


def extract_png(outfile, source_config):
    extract_cmd = "\
{ffmpeg_bin} \
-i {source} \
{extract_args} \
-y {extract_file}\
"
    _, source_ext = os.path.splitext(outfile)
    extract_file = outfile.replace(source_ext, '.png')

    if os.path.exists(extract_file):
        os.remove(extract_file)

    cmd = extract_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        source=outfile,
        extract_args=' '.join(source_config.get('ffmpeg_extract')),
        extract_file=extract_file
    )
    print("Extract command:", cmd)
    subprocess.call(cmd, shell=True)

    return extract_file


def vmaf_compare(reference, outfile):
    vmaf_cmd = '\
{ffmpeg_bin} \
-i {reference} \
-i {outfile} \
-lavfi \
\"[0:v]setpts=PTS-STARTPTS[reference]; \
[1:v]setpts=PTS-STARTPTS[distorted]; \
[distorted][reference]\
libvmaf=log_fmt=xml:log_path=foo:\
model_path={vmaf_model}\" \
-f null -\
'
    cmd = vmaf_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        reference=reference,
        outfile=outfile,
        vmaf_model=VMAF_MODEL
    )
    print('VMAF command:', cmd)

    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            check=True,
            text=True
        )

        # ffmpeg sends output to stderr
        result = float(proc.stderr.split('VMAF score: ')[1])

    except subprocess.CalledProcessError as err:
        print(
            "VMAF compare failed! {msg}".format(msg=err.stderr)
        )
        result = '{msg} ERROR!'.format(msg=err.stderr)

    return result


def create_mask(outfile, extract_file, source_config, test_config):
    # We have a mask that we need to use before comparing.
    base, _ = os.path.splitext(outfile)
    out_source_mask = f'{base}-sourcemask.png'

    oiio_cmd = "\
{oiio_bin} \
{source} \
{testmask} \
--mul \
-o {out_source_mask}\
"
    cmd = oiio_cmd.format(
        oiio_bin=OIIOTOOL_BIN,
        source=source_config.get('source_file'),
        testmask=test_config.get('testmask'),
        out_source_mask=out_source_mask
    )

    print("oiiotool command:", cmd)
    subprocess.call(shlex.split(cmd))

    # The mask is used to help with comparisons of 444 vs. 422,
    # perhaps a better approach is to compare it to a "raw" 422p/420p image.
    outmask = f"{base}-mask.png"

    oiio_cmd1 = '\
{oiio_bin} \
{source} \
{testmask} \
--mul \
-o {outmask}\
'
    cmd1 = oiio_cmd1.format(
        oiio_bin=OIIOTOOL_BIN,
        source=extract_file,
        testmask=test_config.get('testmask'),
        outmask=outmask
    )

    print("oiiotool command1:", cmd1)
    subprocess.call(shlex.split(cmd1))

    return outmask, out_source_mask


def idiff_compare(outfile, sourceimage, extractfile):
    # Pulled from OpenImageIO's documentation
    error_map = {
        0: "OK: the images match within the warning and error thresholds.",
        1: "WARNING: the errors differ a little, but within error thresholds.",
        2: "FAILURE: the errors differ a lot, outside error thresholds.",
        3: "FAILURE: The images weren’t the same size and couldn’t be compared.",
        4: "FAILURE: Could not find or open input files, etc."
    }

    base, _ = os.path.splitext(outfile)
    diff_file = f"{base}-idiff.png"

    idiff_cmd = "\
{idiff_bin} \
-o {diff_file} \
{source} \
{extract_file}\
"
    cmd = idiff_cmd.format(
        idiff_bin=IDIFF_BIN,
        diff_file=diff_file,
        source=sourceimage,
        extract_file=extractfile
    )
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            capture_output=True,
            check=True,
            text=True
        )
        output = f'{cmd}\n{proc.stdout}'

    except subprocess.CalledProcessError as err:
        output = error_map[err.returncode]

    return output, diff_file


def oiio_compare(outfile, sourceimage, extractfile):
    pass


def is_video_output(testfile):
    _, ext = os.path.splitext(testfile['output_file'])
    return ext in ['.mov', '.mp4']


def main():
    # Make sure we have a place to render files
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)

    test_results = []
    reference = None

    for testfile in testfiles[1:]:
        for testconfig in testconfigs:
            # Used for creating results.html page later
            test_result = {
                'testfile': testfile['source_file'],
                'testname': testconfig['testname']
            }

            # Outfile
            base, source_ext = os.path.splitext(
                testfile.get('output_file')
            )
            outfile = os.path.join(
                TEST_DIR,
                f'{base}-{testconfig["testname"]}{source_ext}'
            )

            # Setup timer
            t_start = time.perf_counter()

            # Convert file
            ffmpeg_cmd, rc = ffmpeg_convert(testfile, testconfig, outfile)
            t_end = time.perf_counter()

            # Update test_result
            test_result['ffmpeg_encode_cmd'] = ffmpeg_cmd
            test_result['ffmpeg_duration'] = t_end - t_start

            if rc != 0:
                print(
                    "ffmpeg FAILED!, return code: {rc}. Skipping the rest"
                    .format(rc=rc)
                )
                continue

            # Update test_result
            test_result['filesize'] = os.path.getsize(outfile)

            # This uses the lossless compressed file as vmaf reference
            if testfile['vmaf_reference'] == testconfig['testname']:
                reference = outfile

            # The VMAF testing. NOTE, you will need to get vmaf compiled into ffmpeg for this.
            # see: https://jina-liu.medium.com/a-practical-guide-for-vmaf-481b4d420d9c
            vmaf_output = ''
            if testfile['vmaf_reference'] != testconfig['testname']:
                vmaf_output = vmaf_compare(reference, outfile)
                print("VMAF Output:", vmaf_output)

            test_result['vmaf_output'] = vmaf_output

            # Try to do a idiff on the result.
            # Currently this only works on a still frame,
            # ideally we modify this to work on an image sequence.
            diffhtml = "Undefined"
            if testfile['stillframe']:
                # Now we extract a file for comparison
                extractfile = extract_png(outfile, testfile)

                # Fetch original for comparison
                sourceimage = testfile['source_file']

                # If the conversion isn't 444, we make a mask of the overlap,
                # so the chroma don't affect the image comparison.
                # However, for movies we don't do that (for now).
                if 'testmask' in testconfig and is_video_output(testfile):
                    # We have a mask that we need to use before comparing.
                    extractfile, sourceimage = create_mask(
                        outfile,
                        extractfile,
                        testfile,
                        testconfig
                    )

                output, diff_file = idiff_compare(
                    outfile,
                    sourceimage,
                    extractfile
                )
                diffhtml = "<img width='200px' src='{base}'/>".format(
                    base=os.path.basename(diff_file)
                )

            else:
                # Movie compare from http://dericed.com/2012/display-video-difference-with-ffmpegs-overlay-filter/
                diffhtml = ffmpeg_diff(outfile, testfile)
                output = ""

            test_result['testoutput'] = output
            test_result['diff_html'] = diffhtml

            # Add test_result to result collection
            test_results.append(test_result)

    # Create a web page with results
    write_html(test_results)


if __name__ == '__main__':
    main()
