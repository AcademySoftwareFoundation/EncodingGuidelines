from PIL import Image
from PIL import ImageCms
import os
from CompareHtml import createCompareHtml
rootpath = "./greyramp-rev2"
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
# listimages.append({'label': 'raw png', 'image': os.path.basename(source_image)})

profile = ImageCms.getOpenProfile("/usr/share/color/icc/sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-srgb.png"), icc_profile=profile.tobytes())
listimages.append({'label': 'srgb png', 'image': "greyscale-srgb.png"})

#profile = ImageCms.getOpenProfile(r"ICC Profiles - hbrendel.com/Rec709-Rec1886.icc")
#img.save(os.path.join(rootpath, "greyscale-rec1886.png"), icc_profile=profile.tobytes())
# listimages.append({'label': 'rec1886 png', 'image': "greyscale-rec1886.png"})

#imgtst = Image.open(os.path.join(rootpath, "greyscale-sRGB.png"))
#print("ICC - sRGB test:", imgtst.info["icc_profile"])
#imgtst = Image.open(os.path.join(rootpath, "greyscale-rec1886.png"))
#print("ICC - rec1886 test:", imgtst.info["icc_profile"])

# Now lets make the mp4's.
os.system('ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1 ' + rootpath+'/greyscale-raw.mp4')
listimages.append({'label': 'raw', 'video': "greyscale-raw.mp4"})

trc_types = [{'label': "-color_trc 1 = rec709", 'fileext': "rec709", 'trcnum': 1, 'gamma': 1.95},
			{'label': "-color_trc 13 = sRGB", 'fileext': "srgb", 'trcnum': 13, 'gamma': 2.2},
			{'label': "-color_trc 4 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 4, 'gamma': 2.2},
			#{'label': "-color_trc 5 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 5, 'gamma': 2.8},
			{'label': "-color_trc 8 = linear", 'fileext': "lin", 'trcnum': 8, 'gamma': 1},
			]
for trc in trc_types:
	img  = Image.new( mode = "RGB", size = (width, height) )
	for icol in range(0, 256):
		# We are assuming the current monitor gamma ~2.2, so adjust what we think the output should be to match.
		ocol = int(255.0*pow(icol/255.0, 2.2/trc['gamma']))
		imgpaste = Image.new( mode = "RGB", size = (colwidth, height), color=(ocol, ocol, ocol) )
		img.paste(imgpaste, box=(icol*colwidth, 0))

	source_image = os.path.join(rootpath, "greyscale-source-{fileext}.png".format(**trc))
	#img.save(source_image)
	# TODO Confirm we have the right one.
	trc['source_image'] = source_image
	trc['rootpath'] = rootpath
	listimages.append({'label': trc['label'], 'video': "greyscale-{fileext}.mp4".format(**trc)})

	cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc {trcnum} {rootpath}/greyscale-{fileext}.mp4'.format(**trc)
	print(cmd)
	os.system(cmd)


createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Color_trc comparison</H1><p> This is trying to reverse out what we think is the gamma for each TRC file, with the hope that if the browser is correctly obaying the flag, that all the ramps would approximately match. The code to generate these files is <a href='../%s'>here</a>. However, the source images were generated in nuke.</p>" % os.path.basename(__file__),
					videohtml = '  ')

#os.system('ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 4 ' + rootpath+'/greyscale-raw.mp4')

#os.system('ffmpeg -y -i  ' + source_image + '  -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" greyscale-raw-10bit.mp4')
#os.system('ffmpeg -y -i  ' + source_image + '  -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 ' + rootpath+'/greyscale-rec709.mp4')
#os.system('ffmpeg -y -i  ' + source_image + '  -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 13 ' + rootpath+'/greyscale-srgb.mp4')
#os.system('ffmpeg -y -i  ' + source_image + '  -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 4 ' + rootpath+'/greyscale-gamma22.mp4')
#os.system('ffmpeg -y -i  ' + source_image + '  -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 4 ' + rootpath+'/greyscale-gamma22b.mp4')
#os.system('ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuvj420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 4 ' + rootpath+'/greyscale-gamma22c.mp4')

#ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -pix_fmt yuv420p -qscale:v 1  -f rawvideo raw_yuv420p.raw
