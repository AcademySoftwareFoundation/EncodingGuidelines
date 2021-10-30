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
source_image = "radialgrad.png"
listimages = []
listimages.append({'id': 'greypng', 'label': 'raw png', 'image': os.path.join("..", source_image)})
listimages.append({'id': 'greymp4', 'label': 'raw mp4 Media encoder', 'video': os.path.join("..", "radialgrad.mp4")})
# Now lets make the mp4's.

cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/greyscale-{fileext}.mp4'.format(outrange="tv", source_image=source_image, fileext="tv", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greytv', 'label': 'out_range=tv -pix_fmt yuv420p 16-235 range', 'video': "greyscale-tv.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/greyscale-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="fullj", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greyfullj', 'label': 'out_range=full yuvj420p 0-255 range', 'video': "greyscale-fullj.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/greyscale-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greyfull', 'label': 'out_range=full -pix_fmt yuv420p color_range=2', 'video': "greyscale-full.mp4", 'cmd': cmd})


cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 0 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/greyscale0-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greyfull0', 'label': 'out_range=full -pix_fmt yuv420p color_range=0', 'video': "greyscale0-full.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i {source_image}  -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" {rootpath}/greyscale-raw-10bit.mp4'.format(source_image=source_image, rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greytv10', 'label': 'yuv444p10le 10-bit mp4', 'video': "greyscale-raw-10bit.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i {source_image}  -c:v libx264rgb -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" {rootpath}/greyscale-raw-rgb.mp4'.format(source_image=source_image, rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'greyrgb', 'label': 'libx264rgb 8-bit mp4', 'video': "greyscale-raw-rgb.mp4", 'cmd': cmd})


source_image = "Digital_LAD_sRGB.png"
cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/marcie-{fileext}.mp4'.format(outrange="tv", source_image=source_image, fileext="tv", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'marcietv', 'label': 'marcie out_range=tv -pix_fmt yuv420p 16-235 range', 'video': "marcie-tv.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -color_range 0 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/marcie-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="fullj", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'marciefullj', 'label': 'marcie out_range=full yuvj420p 0-255 range', 'video': "marcie-fullj.mp4", 'cmd': cmd})

cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range={outrange}:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 1 {rootpath}/marcie-{fileext}.mp4'.format(outrange="full", source_image=source_image, fileext="full", rootpath=rootpath)
os.system(cmd)
listimages.append({'id': 'marciefull', 'label': 'marcie out_range=full -pix_fmt yuv420p -color_range 2', 'video': "marcie-full.mp4", 'cmd': cmd})

createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Full range vs TV Range</H1><p> Comparing full range encoding vs. tv range, but also yuv420p vs. yuvj420p. The code to generate these files is <a href='../%s'>here</a>. </p>" % os.path.basename(__file__),
					videohtml = ' width=920 ')

