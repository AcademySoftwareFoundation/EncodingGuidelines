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
listimages.append({'id': 'chipchartpng', 'label': 'orig png', 'image': os.path.join("..", "..", 'sourceimages', os.path.basename(source_image)), 'cmd': "Source PNG file"})
print(listimages)

processes = [{'id': 'basic', 'label': 'yuv420p default ffmpeg', 'conv': '', 'pix_fmt': 'yuv420p', 'description': 'Basic ffmpeg conversion, no colorspace specified, ffmpeg assumes bt601 colorspace', 'qp': "1"},
        {'id': 'colormatrix', 'label': 'yuv420p colormatrix=bt709', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv420p', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. ', 'qp': "1"},
        {'id': 'colorspace', 'label': 'yuv420p colorspace=bt709', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv420p', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too.', 'qp': "1"},
        {'id': 'nospline', 'label': 'yuv420p bt709 no sws_flags out_color_matrix=bt709', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"  ', 'pix_fmt': 'yuv420p', 'description': 'Using the libavscale library. Seems similar to colorspace, but with image resizing, and levels built in.', 'qp': "1"},
        {'id': 'splinecolormatrix', 'label': 'yuv420p sws_flags out_color_matrix=bg709', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv420p', 'description': 'Using the libavscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libwscale parameters.', 'qp': "1"},

             {'id': 'basic444', 'label': 'yuv444p10le default ffmpeg (chrome only)', 'conv': '', 'pix_fmt': 'yuv444p10le', 'description': 'Basic ffmpeg conversion, ffmpeg assumes bt601 colorspace, now at 444', 'qp': "0"},
             {'id': 'spline444colormatrix2', 'label': 'yuv444p10le colormatrix=bt709 (chrome only)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. ', 'qp': "0"},
             {'id': 'spline444colorspace', 'label': 'yuv444p10le colorspace=bt709 (chrome only)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too.', 'qp': "0"},
             {'id': '444out_color_matrix', 'label': 'yuv444p10le no sws_flags out_color_matrix=bt709 (chrome only)', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libavscale library. Seems similar to colorspace, but with image resizing, and levels built in. ', 'qp': "0"},
             {'id': 'spline444out_color_matrix', 'label': 'yuv444p10le out_color_matrix=bt709 (chrome only)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libavscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libwscale parameters.', 'qp': "0"},
             ]

ffmpeg_cmd = "ffmpeg"
oiiotool_cmd = "oiiotool"
idiff_cmd = "idiff"

for proc in processes:
    proc['source_image'] = source_image
    proc['rootpath'] = rootpath
    if 'ffmpeg_extract' not in proc:
        proc['ffmpeg_extract'] = ' -compression_level 10 -pred mixed -pix_fmt rgb24 -sws_flags spline+accurate_rnd+full_chroma_int'
    proc['video'] = '{id}.mp4'.format(**proc)
    cmd = 'ffmpeg -y -i  {source_image} {conv} -c:v libx264  -preset placebo -qp {qp} -x264-params "keyint=15:no-deblock=1"  -pix_fmt {pix_fmt} -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/{id}.mp4'.format(**proc)
    os.system(cmd)
    proc['cmd'] = cmd
    listimages.append(proc)
    encodeimage = os.path.join(rootpath, proc['video'])
    extractfile = os.path.join(rootpath, os.path.basename(source_image[:-3])+"png")
    if os.path.exists(extractfile):
        os.remove(extractfile)
    extractcmd = ffmpeg_cmd + " -i " + encodeimage + " " + proc['ffmpeg_extract'] + " " + extractfile
    print(extractcmd)
    os.system(extractcmd)
    difffile = os.path.join(rootpath, os.path.basename(source_image[:-4])+"diff.png")
    oiiocmd = idiff_cmd + " -o " + difffile + " "+source_image + " " + extractfile 
    try:
        output = subprocess.check_output(oiiocmd, shell=True)
    except Exception as e:
        output = str(e.output) + "ERROR!"
    output = str(oiiocmd)+"\n"+str(output).replace("\\n", "<BR/>")
    proc['cmd'] = "<h3>%s</H3><p>%s</p>%s<H3>OIIO idiff output</H3>%s" % (proc['conv'], proc['description'], proc['cmd'], output)


createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Comparing YUV conversion approaches.</H1><p> Recommended to use firefox, otherwise png is wrong. The code to generate these files is <a href='../%s'>here</a>. </p>" % os.path.basename(__file__),
					videohtml = ' width=960 ')

