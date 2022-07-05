import sys
sys.path.append("python")
from PIL import Image
from PIL import ImageCms
import subprocess
import os
from CompareOverHtml import createCompareHtml
rootpath = "./chip-chart-yuvconvert"
if not os.path.exists(rootpath):
	os.makedirs(rootpath)

source_image = os.path.join("..", "sourceimages", "chip-chart-1080-noicc.png")

listimages = []
listimages.append({'id': 'none', 'label': ''})

listimages.append({'id': 'chipchartpng', 'label': 'Reference PNG', 'image': os.path.join("..", "..", 'sourceimages', os.path.basename(source_image)), 'cmd': "Source PNG file"})
print(listimages)

processes = [
        {'labelonly': 'YUV420p encodes'},
        {'id': 'basic', 'label': 'Default Encode (terrible)', 'conv': '', 'pix_fmt': 'yuv420p', 'description': 'Basic ffmpeg conversion, no colorspace specified, ffmpeg assumes bt601 colorspace. This is a terrible filter, significant color changes from PNG file.', 'qp': "1"},
        {'id': 'colormatrix', 'label': 'Colormatrix filter (close)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv420p', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. Visually its getting pretty close. ', 'qp': "1"},
        {'id': 'colorspace', 'label': 'Colorspace filter', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv420p', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too. Visually pretty close to colormatrix, but slight improvement based on colormatrix values.', 'qp': "1"},
        # {'id': 'nospline', 'label': 'libswscale filter', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"  ', 'pix_fmt': 'yuv420p', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.', 'qp': "1"},
        {'id': 'splinecolormatrix', 'label': 'libswscale filter + flags (best)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv420p', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Visually this is close to the above two, but slight improvement based on colormatrix results.', 'qp': "1"},
        {'labelonly': 'YUV444p encodes (Chrome Only)', 'description': 'Encodes are more accurate.'},

             {'id': 'basic444', 'label': 'Default Encode (terrible)', 'conv': '', 'pix_fmt': 'yuv444p10le', 'description': 'Basic ffmpeg conversion, ffmpeg assumes bt601 colorspace, now at 444. Results look terrible.', 'qp': "0"},
             {'id': 'spline444colormatrix2', 'label': 'Colormatrix filter (close)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. Visually pretty close, but still off.', 'qp': "0"},
             {'id': 'spline444colorspace', 'label': 'Colorspace filter', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too. Visually slight differences, but getting closer.', 'qp': "0"},
             #{'id': '444out_color_matrix', 'label': 'yuv444p10le no sws_flags out_color_matrix=bt709 (chrome only)', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. ', 'qp': "0"},
             #{'id': '444out_color_matrix2', 'label': 'yuv444p10le no sws_flags no range out_color_matrix=bt709 (chrome only)', 'conv': ' -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing. ', 'qp': "0"},
             {'id': 'spline444out_color_matrix', 'label': 'libswscale filter + flags (Match)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Looking at the oiio difference, this is the first one that has an identical result to the input image.', 'qp': "0", 'color_range': "1"},
             {'id': 'spline444out_color_matrixfull', 'label': 'libswscale filter + flags full-range (Match)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Looking at the oiio difference, this is the first one that has an identical result to the input image.', 'qp': "0", 'color_range': "2"},
             ]

ffmpeg_cmd = "ffmpeg"
oiiotool_cmd = "oiiotool"
idiff_cmd = "idiff"

for proc in processes:
    if "labelonly" in proc:
            listimages.append({'id': 'none', 'label': proc['labelonly']})
            continue
    proc['source_image'] = source_image
    proc['rootpath'] = rootpath
    if 'ffmpeg_extract' not in proc:
        proc['ffmpeg_extract'] = ' -compression_level 10 -pred mixed -pix_fmt rgb24 -sws_flags spline+accurate_rnd+full_chroma_int'
    proc['video'] = '{id}.mp4'.format(**proc)
    cmd = 'ffmpeg -y -i  {source_image} {conv} -c:v libx264  -preset placebo -qp {qp} -x264-params "keyint=15:no-deblock=1"  -pix_fmt {pix_fmt} -qscale:v 1  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/{id}.mp4'.format(**proc)
    os.system(cmd)
    proc['cmd'] = cmd
    listimages.append(proc)
    encodeimage = os.path.join(rootpath, proc['video'])
    extractfile = os.path.join(rootpath, os.path.basename(source_image[:-4])+"-"+proc['id']+".png")
    if os.path.exists(extractfile):
        os.remove(extractfile)
    extractcmd = ffmpeg_cmd + " -i " + encodeimage + " " + proc['ffmpeg_extract'] + " -vframes 1 " + extractfile
    print("\nExtractcmd:", extractcmd)
    os.system(extractcmd)
    del proc['video']
    proc['image'] = os.path.basename(extractfile)
    print("IMAGE = ", proc['image'])
    difffile = os.path.join(rootpath, os.path.basename(source_image[:-4])+"diff.png")
    oiiocmd = idiff_cmd + " -o " + difffile + " "+source_image + " " + extractfile 
    print("\nOIIO CHECK:", oiiocmd)
    try:
        output = subprocess.check_output(oiiocmd, shell=True)
    except Exception as e:
        output = str(e.output) + "ERROR!"
    output = str(oiiocmd)+"\n"+str(output).replace("\\n", "<BR/>")
    proc['cmd'] = "<h3>ffmpeg flags to add: %s</H3><p>Full creation commandline:<BR/>%s</p><H3>OIIO idiff output</H3>%s" % (proc['conv'], proc['cmd'], output)


createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Comparing YUV conversion approaches.</H1><p> This is comparing different ways to do the YUV conversion. We are doing it in both 420p and 444p since 444p is a fairer binary image comparison. The takeaway should be to use the libswscale filter. The code to generate these files is <a href='../%s'>here</a>. </p>" % os.path.basename(__file__),
					videohtml = ' width=960 ')

