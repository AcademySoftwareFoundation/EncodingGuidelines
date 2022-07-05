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
listimages.append({'id': 'raw', 'label': 'raw ', 'image': os.path.basename(source_image), 'group': 'raw png'})

profile = ImageCms.getOpenProfile("/usr/share/color/icc/OpenICC/sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-srgb.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'srgbpng', 'label': 'srgb', 'ext': 'png', 'image': "greyscale-srgb.png", 'group': 'srgb png'})

profile = ImageCms.getOpenProfile(r"../ICC/Simplified-sRGB.icc")
img.save(os.path.join(rootpath, "greyscale-g22.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'g22png', 'label': 'gamma2.2', 'ext': 'png', 'image': "greyscale-g22.png", 'group': 'gamma22 png'})

profile = ImageCms.getOpenProfile(r"../ICC/gamma28.icc")
img.save(os.path.join(rootpath, "greyscale-g28.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'g28png', 'label': 'gamma2.8', 'ext': 'png', 'image': "greyscale-g28.png", 'group': 'gamma28 png'})

profile = ImageCms.getOpenProfile(r"../ICC/linear.icc")
img.save(os.path.join(rootpath, "greyscale-lin.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'linpng', 'label': 'Linear', 'ext': 'png', 'image': "greyscale-lin.png", 'group': 'lin png'})

profile = ImageCms.getOpenProfile(r"../ICC/Rec709-Rec1886.icc")
img.save(os.path.join(rootpath, "greyscale-rec1886.png"), icc_profile=profile.tobytes())
listimages.append({'id': 'rec1886png', 'label': 'rec1886', 'ext': 'png', 'image': "greyscale-rec1886.png", 'group': 'bt1886 png'})

# Now lets make the mp4's.
os.system('ffmpeg -r 1 -y -i  ' + source_image + '  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264  -pix_fmt yuv420p -qscale:v 1 ' + rootpath+'/greyscale-raw.mp4')
listimages.append({'id': 'raw', 'label': 'raw', 'ext': 'mp4', 'video': "greyscale-raw.mp4", 'group': 'raw'})

trc_types = [{'id': 'rec709', 'label': "-color_trc 1 = rec709", 'fileext': "rec709", 'trcnum': 'bt709', 'group': 'rec709 colortrc'},
            {'id': 'gamma195', 'label': "(OSX Only) -color_trc 2 = gamma 1.95", 'fileext': "gamma195", 'trcnum': 'unknown', 'gamma': 1.95, 'group': 'rec709'},
			{'id': 'unknown', 'label': "-color_trc 2 = unknown", 'fileext': "unknown", 'trcnum': 'unknown'},
			{'id': 'srgb', 'label': "-color_trc 13 = sRGB", 'fileext': "srgb", 'trcnum': "iec61966-2-1", 'group': 'srgb colortrc'},
			#{'label': "-color_trc 14 = rec2020", 'fileext': "rec2020", 'trcnum': 14},
			#{'label': "-color_trc 15 = rec2020", 'fileext': "rec2020b", 'trcnum': 15},
			{'id': 'gamma22mp4', 'label': "-color_trc 4 = gamma 2.2", 'fileext': "gamma22", 'trcnum': "gamma22", 'group': 'gamma22 colortrc'},
            {'id': 'gamma22mov', 'label': "(OSX Only) -color_trc 2 = gamma 2.2", 'fileext': "gamma22", 'trcnum': 'unknown', 'gamma': 2.2, 'group': 'gamma22'},
            {'id': 'gamma24mov', 'label': "(OSX Only) -color_trc 2 = gamma 2.4 BT1886", 'fileext': "gamma24", 'trcnum': 'unknown', 'gamma': 2.4, 'group': 'bt1886'},
			{'id': 'gamma28mp4', 'label': "-color_trc 5 = gamma 2.8", 'fileext': "gamma28", 'trcnum': "gamma28", 'group': 'gamma28 colortrc'},
            {'id': 'gamma28mov', 'label': "(OSX Only) -color_trc 2 = gamma 2.8", 'fileext': "gamma28", 'trcnum': 'unknown', 'gamma': 2.8, 'group': 'gamma28'},
			{'id': 'gammalinmp4', 'label': "-color_trc 8 = linear", 'fileext': "lin", 'trcnum': 'linear', 'group': 'lin colortrc'},
            {'id': 'gammalinmov', 'label': "(OSX Only) -color_trc 2 = gamma 1", 'fileext': "gamma1", 'trcnum': 'unknown', 'gamma': 1, 'group': 'lin'},
			]
for trc in trc_types:
	# TODO Confirm we have the right one.
	trc['source_image'] = source_image
	trc['rootpath'] = rootpath

	cmd = 'ffmpeg -loop 1 -y -i  {source_image}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -c:v libx264 -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace rec709 -color_primaries rec709 -color_trc {trcnum} {rootpath}/greyscale-{fileext}.mp4'.format(**trc); ext="mp4"
	if "gamma" in trc:
	   cmd = 'ffmpeg -loop 1 -y -i  {source_image} -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -c:v libx264 -t 5 -pix_fmt yuv420p -qscale:v 1  -color_range pc -colorspace rec709 -color_primaries rec709 -color_trc {trcnum} -movflags write_colr+write_gama -mov_gamma {gamma} {rootpath}/greyscale-{fileext}.mov'.format(**trc); ext="mov"

	os.system(cmd)
	trc['ext'] = ext
	outputfile = '{rootpath}/greyscale-{fileext}.{ext}'.format(**trc)
	if not os.path.exists(outputfile):
		print("ERROR: {outputfile} was not created by the command:{cmd}".format(outputfile=outputfile, cmd=cmd))
		exit(1)
	trc['ext'] = ext
	listimages.append({'id': trc['id'], 'group': trc.get('group', 'unknown'), 'label': trc['label'], 'video': "greyscale-{fileext}.{ext}".format(**trc), 'cmd': cmd})

# Sort images by group.
listimages = sorted(listimages, key=lambda k:k['group'])

introduction = """
<H1>Color_trc comparison for OSX</H1>
<p> This is comparing a png file written with different ICC profiles (i.e. the underlying data is identical in all png files), and comparing it to mp4's where the only change is the -color_trc flag setting, along with mov files with different gamma values. The code to generate these files is <a href='../%s'>here</a>. You can reorder the wedges to help with comparison by drag and drop.</p>
Filtered views:
<p>
<bl>
<li><A href="compare.html">See all</a></li>
<li><A href="compare.html?.groupbt1886">bt1886</a></li>
<li><A href="compare.html?.groupsrgb">sRGB</a></li>
<li><A href="compare.html?.groupgamma22">gamma 2.2</a></li>
<li><A href="compare.html?.groupgamma22+.groupsrgb">gamma 2.2 and sRGB</a></li>
<li><A href="compare.html?.groupgamma28">gamma 2.8</a></li>
<li><A href="compare.html?.grouplin">linear</a></li>
<li><A href="compare.html?.colortrc">mp4's only.</a></li>
<li><A href="compare.html?.png">png's only.</a></li>
</bl>
</p>
""" % os.path.basename(__file__)

createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction=introduction,
                                    videohtml = '  '
                                        )
