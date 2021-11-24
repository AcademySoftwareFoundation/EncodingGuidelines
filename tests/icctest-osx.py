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
listimages.append({'id': 'raw', 'label': 'raw png', 'image': os.path.basename(source_image)})

profile = ImageCms.getOpenProfile("/usr/share/color/icc/sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-srgb.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'srgbpng', 'label': 'srgb png', 'image': "greyscale-srgb.png", 'group': 'srgb'})

profile = ImageCms.getOpenProfile(r"../ICC/Simplified-sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-g22.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'g22png', 'label': 'gamma2.2 png', 'image': "greyscale-g22.png", 'group': 'gamma22'})

profile = ImageCms.getOpenProfile(r"../ICC/Rec709-Rec1886.icc")
img.save(os.path.join(rootpath, "greyscale-rec1886.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'rec1886png', 'label': 'rec1886 png', 'image': "greyscale-rec1886.png", 'group': 'bt1886'})

# Now lets make the mp4's.
os.system('ffmpeg -r 1 -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1 ' + rootpath+'/greyscale-raw.mp4')
listimages.append({'id': 'raw', 'label': 'raw', 'video': "greyscale-raw.mp4"})

trc_types = [{'id': 'rec709', 'label': "-color_trc 1 = rec709", 'fileext': "rec709", 'trcnum': 1, 'group': 'rec709'},
            {'id': 'gamma195', 'label': "-color_trc 2 = gamma 1.95", 'fileext': "gamma195", 'trcnum': 2, 'gamma': 1.95, 'group': 'rec709'},
			{'id': 'unknown', 'label': "-color_trc 2 = unknown", 'fileext': "unknown", 'trcnum': 2},
			{'id': 'srgb', 'label': "-color_trc 13 = sRGB", 'fileext': "srgb", 'trcnum': 13, 'group': 'srgb'},
			#{'label': "-color_trc 14 = rec2020", 'fileext': "rec2020", 'trcnum': 14},
			#{'label': "-color_trc 15 = rec2020", 'fileext': "rec2020b", 'trcnum': 15},
			{'id': 'gamma22mp4', 'label': "-color_trc 4 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 4, 'group': 'gamma22'},
            {'id': 'gamma22mov', 'label': "-color_trc 2 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 2, 'gamma': 2.2, 'group': 'gamma22'},
            {'id': 'gamma24mov', 'label': "-color_trc 2 = gamma 2.4", 'fileext': "gamma24", 'trcnum': 2, 'gamma': 2.4, 'group': 'bt1886'},
			{'id': 'gamma28mp4', 'label': "-color_trc 5 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 5, 'group': 'gamma28'},
            {'id': 'gamma28mov', 'label': "-color_trc 2 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 2, 'gamma': 2.8, 'group': 'gamma28'},
			{'id': 'gammalinmp4', 'label': "-color_trc 8 = linear", 'fileext': "lin", 'trcnum': 8, 'group': 'lin'},
            {'id': 'gammalinmov', 'label': "-color_trc 2 = gamma 1", 'fileext': "gamma1", 'trcnum': 2, 'gamma': 1, 'group': 'lin'},
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
	listimages.append({'id': trc['id'], 'group': trc.get('group', 'unknown'), 'label': trc['label'], 'video': "greyscale-{fileext}.{ext}".format(**trc), 'cmd': cmd})



createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction="<H1>Color_trc comparison for OSX</H1><p> This is comparing a png file written with different ICC profiles (i.e. the underlying data is identical in all png files), and comparing it to mp4's where the only change is the -color_trc flag setting, along with mov files with different gamma values. The code to generate these files is <a href='../%s'>here</a>. You can reorder the wedges to help with comparison by drag and drop.</p>" % os.path.basename(__file__),
                                    videohtml = '  '
                                        )
