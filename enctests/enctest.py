# Test configs

import os
import time
import subprocess

from config import testconfigs, testfiles


def write_html(test_results):
    fields = [
        'test',
        'testfile',
        'testoutput',
        'vmafoutput',
        'filesize',
        'duration'
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
        results.write("</TR>")

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
            results.write("</TR>")
        results.write("</TABLE></BODY></HTML>")


def main():
    testdir = "results"

    ffmpeg_cmd = "ffmpeg"
    oiiotool_cmd = "oiiotool"
    idiff_cmd = "idiff"

    if not os.path.exists(testdir):
        os.makedirs(testdir)

    test_results = []

    for testfile in testfiles[1:2]:
        outputfiles = {}
        for testconfig in testconfigs:
            outfile = os.path.join(testdir, testfile['testfilename'][:-4]+"-"+testconfig['test']+testfile['testfilename'][-4:])
            outputfiles[testconfig['test']] = outfile
            if os.path.exists(outfile):
                print("REMOVING:", outfile)
                os.remove(outfile)
            ffmpeg_startup = testfile.get("ffmpeg_startup", "")
            duration = ""
            if "vframes" in testfile:
               duration = " -vframes %s " % testfile['vframes']

            # Do the initial media encode - i.e. what we are testing.
            cmd = ffmpeg_cmd + " " + ffmpeg_startup +" -i " + testfile['file'] + duration + " " + testconfig['ffmpeg_args'] + " " + outfile
            print("ffmpeg cmd:", cmd)
            t = time.time()
            os.system(cmd)
            ffmpegduration = time.time() - t
            if not os.path.exists(outfile):
                print("Warning file: %s is missing, skipping test." % outfile)
                continue

            # The VMAF testing. NOTE, you will need to get vmaf compiled into ffmpeg for this.
            # see: https://jina-liu.medium.com/a-practical-guide-for-vmaf-481b4d420d9c
            vmafoutput = ""
            vmafscore = ""
            if testfile['vmaf_compare'] != testconfig['test']:
                comparefile = outputfiles[testfile['vmaf_compare']]
                # We assume that the testconfig.
                vmafcmd = ffmpeg_cmd + " -i " + comparefile + " -i "+outfile+' -lavfi "[0:v]setpts=PTS-STARTPTS[reference];[1:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=log_fmt=xml:log_path=foo:model_path=/usr/local/share/model/vmaf_v0.6.1.json" -f null -'
                try:
                    vmafoutput = subprocess.check_output(vmafcmd, stderr=subprocess.STDOUT, shell=True)
                    vmafoutput = str(vmafoutput).split("VMAF score: ")[1][:-3]
                except Exception as e:
                    vmafoutput = str(e.output) + "ERROR!"
                print("VMAF Output:", vmafoutput)

            # Try to do a idiff on the result. Currently this only works on a still frame, ideally we modify this to work on an image sequence.
            diffhtml = "Undefined"
            if testfile['stillframe']:
                # Now we extract the file
                extractfile = outfile[:-3]+"png"
                if os.path.exists(extractfile):
                    os.remove(extractfile)
                extractcmd = ffmpeg_cmd + " -i " + outfile + " " + testfile['ffmpeg_extract'] + " " + extractfile
                print("Extract cmd:", extractcmd)
                os.system(extractcmd)

                sourceimage = testfile['file']

                # If the conversion isnt 444, we make a mask of the overlap, so the chroma dont affect the image comparison.
                # However, for movies we dont do that (for now).
                if 'testmask' in testconfig and ("mov" in testfile['testfilename'] or "mp4" in testfile['testfilename']):
                    # We have a mask that we need to use before doing the compare.
                    outsourcemask = outfile[:-4]+"sourcemask.png"
                    oiiocmd = oiiotool_cmd + " "+testfile['file'] + " " + testconfig['testmask'] + " --mul -o " + outsourcemask
                    print(oiiocmd)
                    os.system(oiiocmd)

                    # The mask is used to help with comparisons of 444 vs. 422, perhaps a better approach is to compare it to a "raw" 422p/420p image.
                    sourceimage = outsourcemask
                    outmask = outfile[:-4]+"mask.png"
                    oiiocmd = oiiotool_cmd + " "+extractfile + " " + testconfig['testmask'] + " --mul -o " + outmask
                    print(oiiocmd)
                    os.system(oiiocmd)
                    extractfile = outmask
                difffile = outfile[:-4]+"diff.png"
                oiiocmd = idiff_cmd + " -o " + difffile + " "+sourceimage + " " + extractfile
                try:
                    output = subprocess.check_output(oiiocmd, shell=True)
                except Exception as e:
                    output = str(e.output) + "ERROR!"
                output = str(oiiocmd)+"\n"+str(output).replace("\\n", "\n")
                diffhtml = "<IMG width='200px' SRC='%s' />" % os.path.basename(difffile)
            else:
                # Movie compare from http://dericed.com/2012/display-video-difference-with-ffmpegs-overlay-filter/
                difffile = outfile[:-4]+"diff.mp4" # Do the diff movies in mp4 so that they can load in a browser.

                comparecmd = ffmpeg_cmd + " -y "+ " " + ffmpeg_startup +" -i "+testfile['file']+" -i "+outfile+duration+" -filter_complex [1:v]format=yuva444p,lut=c3=128,negate[video2withAlpha],[0:v][video2withAlpha]overlay[out] -map [out] "+difffile
                #comparecmd = ffmpeg_cmd + " -y "+ " " + ffmpeg_startup +" -i "+testfile['file']+" -i "+outfile+" -filter_complex blend=all_mode=difference,hue=s=0 "+difffile
                print("Comparecmd:", comparecmd)
                os.system(comparecmd)
                diffhtml = "<video width='200' height='112' controls><source src='"+os.path.basename(difffile)+"' type='video/mp4'>Your browser does not support the video tag.</video>"
                output = ""

            encodesize = os.path.getsize(outfile)
            testresult = {
                'testfile': testfile['file'],
                'test': testconfig['test'],
                'testoutput': output,
                'filesize': encodesize,
                'vmafoutput': vmafoutput,
                'duration': ffmpegduration,
                'ffmpeg_encode_cmd': cmd,
                'diff_html': diffhtml
            }
            test_results.append(testresult)

    # Create a web page with results
    write_html(test_results)


if __name__ == '__main__':
    main()
