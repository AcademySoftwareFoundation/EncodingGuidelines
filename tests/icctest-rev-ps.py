import sys
sys.path.append("python")

from PIL import Image
from PIL import ImageCms
import os
from CompareHtml import createCompareHtml
rootpath = "./greyramp-rev-ps"
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
listimages.append({'label': 'raw png', 'image': os.path.basename(source_image)})

#profile = ImageCms.getOpenProfile("/usr/share/color/icc/sRGB.icc")
#img.save(os.path.join(rootpath, "greyscale-srgb.png"), icc_profile=profile.tobytes())
listimages.append({'label': 'srgb png', 'image': "../../sourceimages/greyscale-source-srgb-ps.png"})

#profile = ImageCms.getOpenProfile(r"ICC Profiles - hbrendel.com/Rec709-Rec1886.icc")
#img.save(os.path.join(rootpath, "greyscale-rec1886.png"), icc_profile=profile.tobytes())
#listimages.append({'label': 'rec1886 png', 'image': "greyscale-rec1886.png"})
listimages.append({'label': 'gamma1.95 png', 'image': "../../sourceimages/greyscale-source-gamma195-ps.png"})
listimages.append({'label': 'gamma2.2 png', 'image': "../../sourceimages/greyscale-source-gamma22-ps.png"})
listimages.append({'label': 'gamma2.8 png', 'image': "../../sourceimages/greyscale-source-gamma28-ps.png"})
listimages.append({'label': 'lin png', 'image': "../../sourceimages/greyscale-source-lin-ps.png"})

#imgtst = Image.open(os.path.join(rootpath, "greyscale-sRGB.png"))
#print("ICC - sRGB test:", imgtst.info["icc_profile"])
#imgtst = Image.open(os.path.join(rootpath, "greyscale-rec1886.png"))
#print("ICC - rec1886 test:", imgtst.info["icc_profile"])

# Now lets make the mp4's.
os.system('ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1 ' + rootpath+'/greyscale-raw.mp4')
listimages.append({'label': 'raw', 'video': "greyscale-raw.mp4"})
os.system('ffmpeg -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2 ' + rootpath+'/greyscale-undefined.mp4')
listimages.append({'label': '-color_trc = 2 = undefined', 'video': "greyscale-undefined.mp4"})

trc_types = [{'label': "-color_trc 1 = rec709", 'fileext': "rec709-ps", 'trcnum': 1, 'gamma': 1.95},
			{'label': "-color_trc 13 = sRGB", 'fileext': "srgb-ps", 'trcnum': 13, 'gamma': 2.2},
			{'label': "-color_trc 4 = gamma 2.2", 'fileext': "gamma22-ps", 'trcnum': 4, 'gamma': 2.2},
			{'label': "-color_trc 5 = gamma 2.8", 'fileext': "gamma28-ps", 'trcnum': 5, 'gamma': 2.8},
			{'label': "-color_trc 8 = linear-ps", 'fileext': "lin-ps", 'trcnum': 8, 'gamma': 1},
			]
for trc in trc_types:
	img  = Image.new( mode = "RGB", size = (width, height) )
	for icol in range(0, 256):
		# We are assuming the current monitor gamma ~2.2, so adjust what we think the output should be to match.
		ocol = int(255.0*pow(icol/255.0, 2.2/trc['gamma']))
		imgpaste = Image.new( mode = "RGB", size = (colwidth, height), color=(ocol, ocol, ocol) )
		img.paste(imgpaste, box=(icol*colwidth, 0))

	source_image = os.path.join('..', 'sourceimages', "greyscale-source-{fileext}.png".format(**trc))
	#img.save(source_image)
	# TODO Confirm we have the right one.
	trc['source_image'] = source_image
	trc['rootpath'] = rootpath

	cmd = 'ffmpeg -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc {trcnum} {rootpath}/greyscale-{fileext}.mp4'.format(**trc)
	print(cmd)
	os.system(cmd)
	listimages.append({'label': trc['label'], 'video': "greyscale-{fileext}.mp4".format(**trc), 'cmd': cmd})


createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Color_trc comparison</H1><p> This is trying to reverse out what we think is the gamma for each TRC file, with the hope that if the browser is correctly obeying the flag, that all the ramps would approximately match. The code to generate these files is <a href='../%s'>here</a>. However, the source images were generated in photoshop, by taking the raw.png file, assigning a sRGB profile to it, and then converting to a custom profile, adjusting the gamma but sticking with D65 and HDTV primaries..</p>" % os.path.basename(__file__),
					videohtml = '  ')

