import yuvio
import subprocess
import shlex
import os
import numpy
import pyseq


def seqToStr(array):
    if array:
        return pyseq.Sequence(array).format("%R")
    return ""

tests = [
          {'testname': 'prores_ks_10_4444xq',
          'pix_fmt': 'yuv444p10le',
          'codec': 'prores_ks',
          'otherargs': ' -profile:v 4444xq', # 4444xq
          'bits': 10
          }, 
          {'testname': 'prores_ks_10_proxy',
          'pix_fmt': 'yuv422p10le',
          'codec': 'prores_ks',
          'otherargs': ' -profile:v proxy', # 4444
          'bits': 10
          }, 
          {'testname': 'prores_ks_10_hq',
          'pix_fmt': 'yuv444p10le',
          'codec': 'prores_ks',
          'otherargs': ' -profile:v hq', # hq
          'bits': 10
          }, 
          {'testname': 'prores_vt_12_xq',
          'pix_fmt': 'yuv444p12le',
          'codec': 'prores_videotoolbox',
          'otherargs': ' -profile:v xq', # 4444
          'bits': 12
          },
          {'testname': 'prores_vt_10_xq',
          'pix_fmt': 'yuv444p10le',
          'codec': 'prores_videotoolbox',
          'otherargs': ' -profile:v xq', # 4444
          'bits': 10
          },
          {'testname': 'prores_vt_12_proxy',
          'pix_fmt': 'yuv444p12le',
          'codec': 'prores_videotoolbox',
          'otherargs': ' -profile:v proxy', # 4444
          'bits': 12
          },
          {'testname': 'prores_vt_10_hq',
          'pix_fmt': 'yuv444p10le',
          'codec': 'prores_videotoolbox',
          'otherargs': ' -profile:v hq', # hq
          'bits': 10
          },
           {'testname': 'dnxhd_10_dnxhr_444',
          'pix_fmt': 'yuv444p10le',
          'codec': 'dnxhd',
          'otherargs': ' -profile:v dnxhr_444', # 4444
          'bits': 10
          },
           {'testname': 'dnxhd_10_dnxhqx_422',
          'pix_fmt': 'yuv422p10le',
          'codec': 'dnxhd',
          'otherargs': ' -profile:v dnxhr_hqx ', # 4444
          'bits': 10
          },
          {'testname': 'h264-placebo',
          'pix_fmt': 'yuv444p10le',
          'codec': 'h264',
          'otherargs': ' -preset placebo -qp 0 ', # 4444
          'bits': 10
          },
          {'testname': 'h264-slower',
          'pix_fmt': 'yuv444p10le',
          'codec': 'h264',
          'otherargs': ' -preset slower -crf 15 ', # 4444
          'bits': 10
          },
           {'testname': 'hevc-slower-444-10',
          'pix_fmt': 'yuv444p10le',
          'codec': 'hevc',
          'otherargs': ' -profile:v main444-10 -preset slower -crf 10 ', # 444
          'bits': 10
          },
           {'testname': 'hevc-slower-444-12',
          'pix_fmt': 'yuv444p12le',
          'codec': 'hevc',
          'otherargs': ' -profile:v main444-12 -preset slower -crf 2 ', # 444
          'bits': 12
          } ,
           {'testname': 'vp9-slower-444-10',
          'pix_fmt': 'yuv444p10le',
          'codec': 'libvpx-vp9',
          'ext': 'mp4',
          'otherargs': ' -quality good -crf 5 -b:v 0 ', # 444
          'bits': 10
          },
           {'testname': 'vp9-slower-444-12',
          'pix_fmt': 'yuv444p12le',
          'codec': 'libvpx-vp9',
          'ext': 'mp4',
          'otherargs': ' -quality good -crf 5  -b:v 0 ', # 444
          'bits': 12
          } ,
           {'testname': 'libsvtav1-420-10',
          'pix_fmt': 'yuv444p10le',
          'codec': 'libsvtav1',
          'ext': 'mp4',
          'otherargs': '-preset 9 -crf 3 ', # 444
          'bits': 10
          }  ,
         {'testname': 'hevc_vt_8_main',
          'pix_fmt': 'yuv420p',
          'out_pix_fmt': 'yuv444p',
          'codec': 'hevc_videotoolbox',
          'otherargs': ' -profile:v main -q:v 100 ', # 8-bit hevc
          'bits': 8
          },
         {'testname': 'hevc_vt_10_main10',
          'pix_fmt': 'p010le',
          'out_pix_fmt': 'yuv444p10le',
          'codec': 'hevc_videotoolbox',
          'otherargs': ' -profile:v main10 -q:v 100 ', # 10-bit hevc
          'bits': 10
         }
       ]

resultfile = open("bitDepthResults.html", "w")
print("<TABLE BORDER=1><TR><TH>Test Name</TH><th>Bit Depth</th><TH>Unique Values</TH><TH>Range of Valid Values</TH><TH>STDDEV < 0.1</TH><TH>Off by 1</TH><TH>Other Invalid</TH></TR>", file=resultfile)
generatedfiles = {}

for test in tests:
    test['frames'] = test.get('frames', int(pow(2, test['bits']))) # Make sure we have a frame for each possible value
    test['halfvalue'] = test.get('half', int(test['frames'] / 2)) # Half is used for the Croma values, to get mid-grey.
    test['ext'] = test.get("ext", "mov") # default to quicktime, but it could be other formats.
    test['basepath'] = "."
    if not "out_pix_fmt" in test:
        # Default to pix_fmt
        test['out_pix_fmt'] = test['pix_fmt']

    outencode = "{basepath}/colors-{testname}.{ext}".format(**test)
    if outencode in generatedfiles:
        print("ERROR: the file ", outencode, " was used first in the test, ", generatedfiles[outencode], " and is being used again in the test:", test)
        exit(1)
        # We need to make sure that each output from the test is unique.
    
    cmd = "ffmpeg -y -r 24 -f lavfi -i nullsrc=s=720x480,format={pix_fmt} -frames:v {frames} -vf geq=N:{halfvalue}:{halfvalue} -c:v {codec} {otherargs} {basepath}/colors-{testname}.{ext} ".format(**test)

    if not os.path.exists(outencode) or os.path.getsize(outencode) == 0:
        print(cmd)
        subprocess.check_output(shlex.split(cmd))

    if not os.path.exists(outencode) or os.path.getsize(outencode) == 0:
        print("ERROR: file ", outencode, " not created")
        exit(1)

    yuvfile = "{basepath}/colors-{testname}.yuv".format(**test)
    if not os.path.exists(yuvfile) or os.path.getsize(yuvfile) == 0:
        extracttoyuv = "ffmpeg -y -i colors-{testname}.{ext} -pix_fmt {out_pix_fmt} -c:v rawvideo {basepath}/colors-{testname}.yuv".format(**test)
        print(extracttoyuv)
        subprocess.check_output(shlex.split(extracttoyuv))

    if not os.path.exists(yuvfile) or os.path.getsize(yuvfile) == 0:
        print("ERROR: file ", yuvfile, " not converted to yuv.")
        exit(1)
    
    count = 0
    last = -1
    yuvreader = yuvio.get_reader(yuvfile, 720, 480, test['out_pix_fmt'])
    framecount = len(yuvreader)
    nearlymissing = []
    nearlymissing1 = []
    missing = []
    validvalues = []
    for f in range(0, framecount):
        i = yuvreader.read(f, 1)[0].y[0][0]
        if i != last:
            #print(count, " match")
            last = i
            count = count + 1
        # if i != f:
        #     #print("Missing:", f, " got value:", i)
        #     missing.append(str(f))
        #     a = yuvreader.read(f, 1)[0].y
        #     #if a.std() > 0.0001:
        #     print("WARNING:", yuvfile, " doesnt have consistent values, frame ", f, " mean:", a.mean(), " std:", a.std())
        #     continue
        # else:
        #     validvalues.append(f)
        a = yuvreader.read(f, 1)[0].y
        if not numpy.all(a == f):
            #if a.std() > 0.0001:
            std = a.std()
            m = a.mean()
            if a.std() < 0.0001: # Nearly 0
                if int(m - f) == 1:
                    nearlymissing1.append(str(f))
                    print("WARNING:", yuvfile, " doesnt have consistent values, frame ", f, " mean:", a.mean(), " std:", a.std(), " off by 1")

                else:
                    missing.append(str(f))
                    print("WARNING:", yuvfile, " doesnt have consistent values, frame ", f, " mean:", a.mean(), " std:", a.std(), " bad.")
                    continue
            else:
                nearlymissing.append(str(f))
                print("WARNING:", yuvfile, " doesnt have consistent values, frame ", f, " mean:", a.mean(), " std:", a.std(), " nearly.")

            missing.append(str(f))
            continue
        else:
            validvalues.append(str(f))
        a = yuvreader.read(f, 1)[0].u
        if not numpy.all(a == test['halfvalue']):
            print("ERROR:", yuvfile, " does not have a uniform u for frame ", f, " expecting", test['halfvalue'], " mean:", a.mean(), " std:", a.std())
        a = yuvreader.read(f, 1)[0].v
        if not numpy.all(a == test['halfvalue']):
            print("ERROR:", yuvfile, " does not have a uniform v for frame ", f, " expecting", test['halfvalue'], " mean:", a.mean(), " std:", a.std())
        #else:
            #print(f, i)
    #if len(missing) > 16:
    #    print(test['testname'], count, " unique values, missing values:", missing[:8], "...", missing[-8:])
    #else:
    print(test['testname'], count, " unique values, valid values:", seqToStr(validvalues), " invalid values < 1:", seqToStr(nearlymissing), " missing by 1:", seqToStr(nearlymissing1), "other", seqToStr(missing))
    print("<TR><TD>", test['testname'], "</TD><TD>", test['bits'],"</TD><TD>", count, "/", test['frames'], "</TD><TD>", seqToStr(validvalues), "</TD><TD>", seqToStr(nearlymissing), "</TD><TD>", seqToStr(nearlymissing1), "</TD><TD>", seqToStr(missing), "</TD><TD>",cmd,"</TD><TR>", file=resultfile)
print("</TABLE>", file=resultfile)