import sys
sys.path.append("python")

from PIL import Image
from PIL import ImageCms
import os
from CompareOverHtml import createCompareHtml
rootpath = "./greyramp-fulltv"
if not os.path.exists(rootpath):
	os.makedirs(rootpath)

colwidth = 4
height = 150
width = 256*colwidth

img  = Image.new( mode = "RGB", size = (width, height) )
for icol in range(0, 256):
	imgpaste = Image.new( mode = "RGB", size = (colwidth, height), color=(icol, icol, icol) )
	img.paste(imgpaste, box=(icol*colwidth, 0))

source_image = os.path.join(rootpath, "greyscale-raw.png")
img.save(source_image)
#source_image = os.path.join(rootpath, "greyscale-srgb-photoshop.png")
listimages = []
# Now lets make the mp4's.
listimages.append({'id': 'none', 'label': 'Test-1: Greyramp'})
listimages.append({'id': 'greyramppng', 'label': 'Source png file', 'description': '', 'image': os.path.join("..", source_image)})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/greyscale-{fileext}.mp4'.format(outrange="tv", source_image=source_image, fileext="tv", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greytv', 'label': 'Normal encode', 'video': "greyscale-tv.mp4", 'description': 'Using the PNG greyramp, with the normal "TV" out range of 16-235, and using yuv420p encoding. ', 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/greyscale-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greyfull', 'label': 'Full range encoding.', 'description': 'Greyramp encoded using out_range=full yuv420p encoding, here we also set color_range=2 to let the decoder know to process it correctly.', 'video': "greyscale-full.mp4", 'cmd': cmd})

source_image = "../sourceimages/radialgrad.png"
listimages.append({'id': 'none', 'label': 'Test-2: Radial gradent'})
listimages.append({'id': 'radialgradpng', 'label': 'Source png file', 'description': 'This is a less forgiving test image', 'image': os.path.join("..", source_image)})


cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="tv", source_image=source_image, fileext="tv", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradtv', 'label': 'Normal encode', 'description': 'Using the radial gradent with normal yuv420p encoding and yuv420p.', 'video': "radialgrad-tv.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradfull', 'label': 'Full range encoding.', 'description': 'Using the full range yuv420p encoding with color_range=2', 'video': "radialgrad-full.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuvj420p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="fullj", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradfullj', 'label': 'Alternate full range encoding', 'description': 'This is an older alternative to full-range encoding, that ffmpeg is currently deprecating. ', 'video': "radialgrad-fullj.mp4", 'cmd': cmd})


cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range unknown -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full0", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradfull0', 'label': 'Using full range without color_range flag', 'description': 'This is what happens if you specify full range without the color_range flag (color_range=0). DONT DO THIS!', 'video': "radialgrad-full0.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv444p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full444", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradfull444', 'label': 'Full range with yuv444 (chrome only)', 'description': 'This is testing yuv444p but still 8-bit, this will only work on chrome.', 'video': "radialgrad-full444.mp4", 'cmd': cmd})

#cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx265  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/radialgrad-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="h265", rootpath=rootpath)
#os.system(cmd)
#listimages.append({'id': 'radialgradh265', 'label': 'Full range with yuv420 h265', 'description': 'This is testing yuv444p but still 8-bit, this will only work on chrome.', 'video': "radialgrad-h265.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i {source_image}  -c:v libx264 -t 5 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" {rootpath}/radialgrad-raw-10bit.mp4'.format(source_image=source_image, rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradtv10', 'label': '10-bit encoding, tv-range (chrome only)', 'description': 'This is testing 10-bit encoding, yuv444p10le', 'video': "radialgrad-raw-10bit.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i {source_image}  -c:v libx264rgb -t 5 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" {rootpath}/radialgrad-raw-rgb.mp4'.format(source_image=source_image, rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'radialgradrgb', 'label': 'This is using RGB encoding', 'description': 'libx264rgb 8-bit mp4 (not supported)', 'video': "radialgrad-raw-rgb.mp4", 'cmd': cmd})


source_image = "../sourceimages/Digital_LAD_raw.png"
listimages.append({'id': 'none', 'label': 'Test-3: Marcie'})

listimages.append({'id': 'marcieraw', 'label': 'Source png file', 'image': os.path.join("..", source_image), 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/marcie-{fileext}.mp4'.format(outrange="tv", source_image=source_image, fileext="tv", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'marcietv', 'label': 'Normal encoding', 'description': 'marcie out_range=tv -pix_fmt yuv420p 16-235 range', 'video': "marcie-tv.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -loop 1 -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 {rootpath}/marcie-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'marciefull', 'label': 'Full Range', 'video': "marcie-full.mp4", 'cmd': cmd})

createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Full range vs TV Range</H1><p> Comparing full range encoding vs. tv range, but also yuv420p vs. yuvj420p. We believe that this is well supported on web browsers, and dont see a downside to it. There may be cases where other applications do not read it. The code to generate these files is <a href='../%s'>here</a>. Full screen view is <a href='/ffmpeg-tests/tests/greyramp-fulltv/compare.html'>here</a></p>" % os.path.basename(__file__),
					videohtml = ' width=920 ')

