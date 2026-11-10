import sys
sys.path.append("python")
from PIL import Image
from PIL import ImageCms
import subprocess
import shutil
import os
from CompareOverHtml import createCompareHtml
rootpath = "./chip-chart-yuvconvert"
if not os.path.exists(rootpath):
	os.makedirs(rootpath)

source_image = os.path.join("..", "sourceimages", "chip-chart-1080-noicc.png")
shutil.copyfile(source_image, os.path.join(rootpath, os.path.basename(source_image)))


listimages = []
listimages.append({'id': 'none', 'label': ''})

listimages.append({'id': 'chipchartpng', 'label': 'Reference PNG', 'image': os.path.basename(source_image), 'cmd': "Source PNG file"})
print(listimages)

# Colour tagging arguments for the encode. Entries can override this with a 'color' key, e.g. '' to show
# what happens with a minimal command line. Since FFmpeg 7.1 -colorspace and -color_range also drive the
# RGB to YCbCr matrix of the auto-inserted scaler, but -color_primaries and -color_trc are overwritten by
# the (unspecified) frame values, so we set those with the h264_metadata bitstream filter instead.
default_color = '-color_range {color_range} -colorspace bt709 -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=13'

processes = [
        {'labelonly': 'yuv422p10le encodes'},
        {'id': 'basic', 'label': 'Default Encode (terrible)', 'conv': '', 'color': '', 'pix_fmt': 'yuv422p10le', 'description': 'Basic ffmpeg conversion with no colour arguments. ffmpeg converts using bt601 and leaves the file untagged, but players will typically assume bt709 for HD, giving significant color changes from the PNG file.', 'qp': "1"},
        {'id': 'basictagged', 'label': 'Default Encode + colour tags', 'conv': '', 'pix_fmt': 'yuv422p10le', 'description': 'No filter, but with the colour tagging arguments. Since FFmpeg 7.1 -colorspace bt709 also sets the matrix used by the auto-inserted libswscale conversion, so this is now correct. Before FFmpeg 7.1 it only tagged the file, and the pixels were still converted with bt601, giving the same result as the default encode.', 'qp': "1"},
        {'id': 'colormatrix', 'label': 'Colormatrix filter (close)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv422p10le', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. Visually its getting pretty close. ', 'qp': "1"},
        {'id': 'colorspace', 'label': 'Colorspace filter', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv422p10le', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too. Visually pretty close to colormatrix, but slight improvement based on colormatrix values.', 'qp': "1"},
        # {'id': 'nospline', 'label': 'libswscale filter', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"  ', 'pix_fmt': 'yuv422p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.', 'qp': "1"},
        {'id': 'splinecolormatrix', 'label': 'libswscale filter + flags (best)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" ', 'pix_fmt': 'yuv422p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Visually this is close to the above two, but slight improvement based on colormatrix results.', 'qp': "1"},
        {'id': 'zscale', 'label': 'zscale filter', 'conv': '-vf "zscale=matrixin=709:matrix=709:rangein=full:range=limited:filter=spline36" ', 'pix_fmt': 'yuv422p10le', 'description': 'Using the zscale (zimg) filter for the matrix and range conversion. zscale does not have the libswscale bias when converting to limited range, so white lands on the specification value. The decode back to RGB also uses zscale. Needs an ffmpeg built with --enable-libzimg.', 'qp': "1", 'extract_vf': 'zscale=matrixin=709:matrix=709:rangein=limited:range=full:filter=spline36'},
        {'labelonly': 'yuv444p10le encodes (Chrome Only)', 'description': 'Encodes are more accurate.'},

             {'id': 'basic444', 'label': 'Default Encode (terrible)', 'conv': '', 'color': '', 'pix_fmt': 'yuv444p10le', 'description': 'Basic ffmpeg conversion with no colour arguments, now at 444. ffmpeg converts using bt601 and leaves the file untagged. Results look terrible.', 'qp': "0"},
             {'id': 'basic444tagged', 'label': 'Default Encode + colour tags', 'conv': '', 'pix_fmt': 'yuv444p10le', 'description': 'No filter, but with the colour tagging arguments. Since FFmpeg 7.1 -colorspace bt709 also sets the matrix used by the auto-inserted libswscale conversion, so this is now correct. Before FFmpeg 7.1 the pixels were still converted with bt601.', 'qp': "0"},
             {'id': 'spline444colormatrix2', 'label': 'Colormatrix filter (close)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colormatrix filter. colormatrix only supports 8-bit per component images. Visually pretty close, but still off.', 'qp': "0"},
             {'id': 'spline444colorspace', 'label': 'Colorspace filter', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too. Visually slight differences, but getting closer.', 'qp': "0"},
             #{'id': '444out_color_matrix', 'label': 'yuv444p10le no sws_flags out_color_matrix=bt709 (chrome only)', 'conv': ' -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. ', 'qp': "0"},
             #{'id': '444out_color_matrix2', 'label': 'yuv444p10le no sws_flags no range out_color_matrix=bt709 (chrome only)', 'conv': ' -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing. ', 'qp': "0"},
             {'id': 'spline444out_color_matrix', 'label': 'libswscale filter + flags (Match)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Looking at the oiio difference, this is the first one that has an identical result to the input image.', 'qp': "0", 'color_range': "1"},
             {'id': 'spline444out_color_matrixfull', 'label': 'libswscale filter + flags full-range (Match)', 'conv': '-sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in. This also has a number of libswscale parameters. Looking at the oiio difference, this is the first one that has an identical result to the input image.', 'qp': "0", 'color_range': "2"},
             {'id': 'zscale444', 'label': 'zscale filter', 'conv': '-vf "zscale=matrixin=709:matrix=709:rangein=full:range=limited" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the zscale (zimg) filter for the matrix and range conversion. zscale does not have the libswscale bias when converting to limited range, so white lands on the specification value. The decode back to RGB also uses zscale. Needs an ffmpeg built with --enable-libzimg.', 'qp': "0", 'color_range': "1", 'extract_vf': 'zscale=matrixin=709:matrix=709:rangein=limited:range=full'},
             {'id': 'zscale444full', 'label': 'zscale filter full-range', 'conv': '-vf "zscale=matrixin=709:matrix=709:rangein=full:range=full" ', 'pix_fmt': 'yuv444p10le', 'description': 'Using the zscale (zimg) filter for the matrix and range conversion. zscale does not have the libswscale bias when converting to limited range, so white lands on the specification value. The decode back to RGB also uses zscale. Needs an ffmpeg built with --enable-libzimg.', 'qp': "0", 'color_range': "2", 'extract_vf': 'zscale=matrixin=709:matrix=709:rangein=full:range=full'},
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
    proc['color_range'] = proc.get('color_range', '1')
    proc['out_range'] = "tv"
    if proc['color_range'] == "2":
        proc['out_range'] = "full"
    if 'ffmpeg_extract' not in proc:
        proc['ffmpeg_extract'] = ' -compression_level 10 -pred mixed -pix_fmt rgba64be -sws_flags spline+accurate_rnd+full_chroma_int'
    if 'extract_vf' not in proc:
        proc['extract_vf'] = 'scale=in_range='+proc['out_range']+':in_color_matrix=bt709:out_color_matrix=bt709:out_range=full'
    proc['video'] = '{id}.mp4'.format(**proc)
    proc['color'] = proc.get('color', default_color).format(**proc)
    cmd = 'ffmpeg -y -r 1 -i {source_image} {conv} -c:v libx264  -preset placebo -qp {qp} -x264-params "keyint=15:no-deblock=1"  -pix_fmt {pix_fmt} -qscale:v 1 {color} {rootpath}/{id}.mp4'.format(**proc)
    # cmd = 'ffmpeg -y -r 1 -i {source_image} -c:v prores_ks -profile:v 3 -qscale:v 1  {conv}  -pix_fmt {pix_fmt} {rootpath}/{id}.mov'.format(**proc)
    #1w_GAL_5000_vfx_cmp_colorSpaceTestsam_colorTestAceshprores_p003.3_sRGB.mov']
    # ('Running:', 'ffmpeg -threads auto -y -r 60 -start_number 89900 -framerate 60 -i {source_image} -frames:v 1 -c:v prores_ks -profile:v 3 -qscale:v 1 -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -pix_fmt yuv422p10le -metadata title=saus01w_GAL_5000_vfx_cmp_colorSpaceTestsam_colorTestAceshprores_p003.3_sRGB.mov I:/jobs/W/EC/FW/ENER/saus01w/shots/GAL_5000/vfx/_pub/cmp/_enc/saus01w_GAL_5000_vfx_cmp_colorSpaceTestsam_colorTestAceshprores_p003.3_sRGB.mov'
    
    os.system(cmd)
    proc['cmd'] = cmd
    listimages.append(proc)
    encodeimage = os.path.join(rootpath, proc['video'])
    extractfile = os.path.join(rootpath, os.path.basename(source_image[:-4])+"-"+proc['id']+".png")
    if os.path.exists(extractfile):
        os.remove(extractfile)
    extractcmd = ffmpeg_cmd + " -i " + encodeimage + " " + proc['ffmpeg_extract'] + " -sws_flags spline+accurate_rnd+full_chroma_int -frames:v 1 -vf " + proc['extract_vf'] + " " + extractfile
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
    proc['cmd'] = "<h3>ffmpeg flags to add: %s</H3><p>Full creation commandline:<BR/>%s</p><H3>OIIO idiff output</H3><PRE>%s</PRE>" % (proc['conv'] + proc['color'], proc['cmd'], output)


createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Comparing YUV conversion approaches.</H1><p> This is comparing different ways to do the YUV conversion. We are doing it in both 420p and 444p since 444p is a fairer binary image comparison. The takeaway should be to use the zscale filter. The code to generate these files is <a href='../%s'>here</a>. </p>" % os.path.basename(__file__),
					videohtml = ' width=960 ')

