import sys
sys.path.append("python")

from PIL import Image
from PIL import ImageCms
import os
from CompareHtml import createCompareHtml
rootpath = "./greyramp-osx"
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

profile = ImageCms.getOpenProfile("/usr/share/color/icc/sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-srgb.png"), icc_profile=profile.tobytes())
listimages.append({'label': 'srgb png', 'image': "greyscale-srgb.png"})

profile = ImageCms.getOpenProfile(r"../ICC/Rec709-Rec1886.icc")
img.save(os.path.join(rootpath, "greyscale-rec1886.png"), icc_profile=profile.tobytes())
listimages.append({'label': 'rec1886 png', 'image': "greyscale-rec1886.png"})

# Now lets make the mp4's.
os.system('ffmpeg -r 1 -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1 ' + rootpath+'/greyscale-raw.mp4')
listimages.append({'label': 'raw', 'video': "greyscale-raw.mp4"})

trc_types = [{'label': "-color_trc 1 = rec709", 'fileext': "rec709", 'trcnum': 1},
                        {'label': "-color_trc 2 = gamma 1.95", 'fileext': "gamma195", 'trcnum': 2, 'gamma': 1.95},
			{'label': "-color_trc 2 = unknown", 'fileext': "unknown", 'trcnum': 2},
			{'label': "-color_trc 13 = sRGB", 'fileext': "srgb", 'trcnum': 13},
			#{'label': "-color_trc 14 = rec2020", 'fileext': "rec2020", 'trcnum': 14},
			#{'label': "-color_trc 15 = rec2020", 'fileext': "rec2020b", 'trcnum': 15},
			{'label': "-color_trc 4 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 4},
                        {'label': "-color_trc 2 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 2, 'gamma': 2.2},
                        #{'label': "-color_trc 2 = gamma 2.4", 'fileext': "gamma24", 'trcnum': 2, 'gamma': 2.4},
			{'label': "-color_trc 5 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 5},
                        {'label': "-color_trc 2 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 2, 'gamma': 2.8},
			{'label': "-color_trc 8 = linear", 'fileext': "lin", 'trcnum': 8},
                        {'label': "-color_trc 2 = gamma 1", 'fileext': "gamma1", 'trcnum': 2, 'gamma': 1},
			]
for trc in trc_types:
	# TODO Confirm we have the right one.
	trc['source_image'] = source_image
	trc['rootpath'] = rootpath

	cmd = 'ffmpeg -r 1 -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc {trcnum} {rootpath}/greyscale-{fileext}.mp4'.format(**trc); ext="mp4"
	if "gamma" in trc:
	   cmd = 'ffmpeg -r 1 -y -i  {source_image} -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries 1 -color_trc {trcnum} -movflags write_colr+write_gama -mov_gamma {gamma} {rootpath}/greyscale-{fileext}.mov'.format(**trc); ext="mov"

	os.system(cmd)
	trc['ext'] = ext
	listimages.append({'label': trc['label'], 'video': "greyscale-{fileext}.{ext}".format(**trc), 'cmd': cmd})



createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Color_trc comparison for OSX</H1><p> This is comparing a png file written with different ICC profiles (i.e. the underlying data is identical in all png files), and comparing it to mp4's where the only change is the -color_trc flag setting, along with mov files with different gamma values. The code to generate these files is <a href='../%s'>here</a>. You can reorder the wedges to help with comparison by drag and drop.</p>" % os.path.basename(__file__),
                                    videohtml = '  '
                                        )
