# Test configs

import os
import subprocess

testdir = "results"

testconfigs = [
    {'test': 'scale_yuv444p10le',
     'description': 'scale (yuv444p10le)',
     'ffmpeg_args': '-c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2',
    },
    {'test': 'colormatrix_yuv444p10le',
     'description': 'colormatrix (yuv444p10le) from https://trac.ffmpeg.org/wiki/colorspace',
     'ffmpeg_args': '-c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1',
    },
    {'test': 'colorspace_yuv444p10le',
     'description': 'colorspace (yuv444p10le) from https://trac.ffmpeg.org/wiki/colorspace',
     'ffmpeg_args': '-c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1',
    },
    {'test': 'colorspace_yuv444p10le_nomd',
     'description': 'colorspace (yuv444p10le) from https://trac.ffmpeg.org/wiki/colorspace without the metadata',
     'ffmpeg_args': '-c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ',
    },
    {'test': 'yuv444p',
     'description': ' yuv444p from https://trac.ffmpeg.org/wiki/colorspace',
     'ffmpeg_args': ' -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p -sws_flags spline+accurate_rnd+full_chroma_int -color_range 1 -colorspace 5 -color_primaries 5 -color_trc 6 ',
    },
    {'test': 'colorspace_yuv444p',
     'description': ' yuv444p from https://trac.ffmpeg.org/wiki/colorspace',
     'ffmpeg_args': ' -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p -sws_flags spline+accurate_rnd+full_chroma_int  -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 ',
    },
    {'test': 'colorspace_yuv420p10le',
     'description': 'colorspace_yuv420p10le from https://trac.ffmpeg.org/wiki/colorspace',
     'ffmpeg_args': '-c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv420p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'colorspace_yuv420p',
     'description': 'colorspace_yuv420p',
     'ffmpeg_args': '-c:v libx264 -preset slow -crf 18 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv420p -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'colorspace_rgb',
     'description': 'colorspace_rgb',
     'ffmpeg_args': '-c:v libx264 -preset slow -crf 18 -x264-params "keyint=15:no-deblock=1" ',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'colorspace_yuv420pfull',
     'description': 'colorspace_yuv420p',
     'ffmpeg_args': '-c:v libx264 -preset slow -crf 18 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv420p -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 1',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'shotgun_diy_encode',
    'description': 'From https://support.shotgunsoftware.com/hc/en-us/articles/219030418-Do-it-yourself-DIY-transcoding',
    'ffmpeg_args': ' -vcodec libx264 -pix_fmt yuv420p -g 30 -vprofile high -bf 0 -crf 2',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'wdi-mpeg2',
    'ffmpeg_args': ' -vcodec mpeg2video -profile:v 4 -level:v 4 -b:v 38M -bt 38M -q:v 1 -maxrate 38M -pix_fmt yuv420p -vf colormatrix=bt601:bt709',
    'testmask': 'sources/1920px-SMPTE_Color_Bars_16x9-edges.png',
    },
    {'test': 'wdi-prores_colormatrix',
    'ffmpeg_args': ' -c:v prores_ks -profile:v 4444 -qscale:v 1 -vendor ap10 -pix_fmt yuv444p10le -vf colormatrix=bt601:bt709', # 
    },
    {'test': 'wdi-prores2',
    'ffmpeg_args': ' -c:v prores_ks -profile:v 4444 -qscale:v 1 -vendor ap10 -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1', # 
    },
    {'test': 'wdi-prores444_scale',
    'ffmpeg_args': ' -c:v prores_ks -profile:v 4444 -qscale:v 1 -vendor ap10 -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2', # 
    },
]

ffmpeg_cmd = "ffmpeg"
oiiotool_cmd = "oiiotool"
idiff_cmd = "idiff"

if not os.path.exists(testdir):
    os.makedirs(testdir)

testfiles = [
    {'file': 'sources/SMPTE_Color_Bars.png',
     'testfilename': 'colorbars.mov',
     'stillframe': True,
     'vmaf_compare': 'scale_yuv444p10le',
     #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
     'ffmpeg_extract': ' -compression_level 10 -pred mixed -pix_fmt rgb24 -sws_flags +accurate_rnd+full_chroma_int'
    },
    {#'file': 'Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%%04d.png',
    'file': 'sources/1080p/sintel_trailer_2k_%04d.png',
    'ffmpeg_startup': ' -r 24 -start_number 600 ', #-vframes 25 ',
    'vframes': 25,
     'vmaf_compare': 'scale_yuv444p10le',
     'testfilename': 'trailer.mov',
     'stillframe': False,
     'vmaf_compare': 'scale_yuv444p10le',
     #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
     'ffmpeg_extract': ' -compression_level 10 -pred mixed -pix_fmt rgb24 -sws_flags +accurate_rnd+full_chroma_int'
    },
    {#'file': 'Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%%04d.png',
    'file': 'sources/1080p/sintel_trailer_2k_0620.png',
     'testfilename': 'trailerstill.mov',
     'stillframe': True,
     'vmaf_compare': 'scale_yuv444p10le',
     #'testmask': '1920px-SMPTE_Color_Bars_16x9-edges.png',
     'ffmpeg_extract': ' -compression_level 10 -pred mixed -pix_fmt rgb24 -sws_flags +accurate_rnd+full_chroma_int'
    },
]


#testconfigs = testconfigs[:2] # For testing.
testfiles = testfiles[1:2]

results = open("results/results.html", "w")
results.write("""<<html lang="en" xml:lang="en" xmlns= "http://www.w3.org/1999/xhtml">
<meta charset="UTF-8">
<meta name="google" content="notranslate">
<meta http-equiv="Content-Language" content="en"><head>
<style type='text/css'>
img {
    filter: brightness(10);
}
</style>
</head>
<body>""")
results.write("<TABLE border=1>")

fields = ['test', 'testfile', 'testoutput', 'vmafoutput', 'filesize']
results.write("<TR>")
for field in fields:
    results.write("<TH>"+field+"</TH>")
results.write("<TH>Image Diff x 10</TH>")
results.write("</TR>")

for testfile in testfiles:
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

        cmd = ffmpeg_cmd + " " + ffmpeg_startup +" -i " + testfile['file'] + duration + " " + testconfig['ffmpeg_args'] + " " + outfile
        print("ffmpeg cmd:", cmd)
        os.system(cmd)
        if not os.path.exists(outfile):
            print("Warning file: %s is missing, skipping test." % outfile)
            continue
        
        vmafoutput = ""
        vmafscore = ""
        if testfile['vmaf_compare'] != testconfig['test']:
            comparefile = outputfiles[testfile['vmaf_compare']]
            # We assume that the testconfig.
            vmafcmd = ffmpeg_cmd + " -i " + comparefile + " -i "+outfile+' -lavfi "[0:v]setpts=PTS-STARTPTS[reference];[1:v]setpts=PTS-STARTPTS[distorted];[distorted][reference]libvmaf=log_fmt=xml:log_path=foo:model_path=/usr/local/share/model/vmaf_v0.6.1.json" -f null -'
            try:
                vmafoutput = subprocess.check_output(vmafcmd, stderr=subprocess.STDOUT, shell=True)
                vmafoutput = str(vmafoutput).split("VMAF score: ")[1][:-2]
            except Exception as e:
                vmafoutput = str(e.output) + "ERROR!"
            print("VMAF Output:", vmafoutput)
        
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
        testresult = {'testfile': testfile['file'], 'test': testconfig['test'], 'testoutput': output, 'filesize':encodesize, 'vmafoutput': vmafoutput}
        results.write("<TR>")
        for field in fields:
            if field == "testoutput":
                results.write("<TD><PRE>"+str(testresult[field])+"</PRE></TD>")
                continue
            if type(testresult[field]) is str:
                results.write("<TD>"+str(testresult[field])+"</TD>")
            else:
                results.write("<TD align='right'>"+str(testresult[field])+"</TD>")
        results.write("<TD>%s</TD></TR>" % diffhtml)
        results.write("<TR><TD COLSPAN=%d>%s</TD>" % (len(fields)+1, cmd))
        results.write("</TR>")
results.write("</TABLE></BODY></HTML>")
results.close()
