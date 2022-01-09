import sys
sys.path.append("../tests/python")

from PIL import Image
from PIL import ImageCms
import shutil
import os
from CompareHtml import createCompareHtml
rootpath = "./iccgamut"
if not os.path.exists(rootpath):
	os.makedirs(rootpath)
 
source_image = "ps-combined-rec2020-g2.2.png"
listimages = []

with Image.open(source_image) as im:
    profile = ImageCms.getOpenProfile("../ICC/rec2020.icc")
    im.save(os.path.join(rootpath, "combined-iccrec2020.png"), icc_profile=profile.tobytes())
listimages.append({'label': 'rec2020 gamma 2.2', 'image': os.path.basename(source_image), 'group': 'rec2020 png'})
shutil.copyfile(source_image, os.path.join(rootpath, source_image))
#listimages.append({'label': 'rec2020', 'image': "combined-iccrec2020.png", 'group': 'rec2020 png'})

source_image_p3 = "ps-combined-displayp3-g2.2.png"
shutil.copyfile(source_image_p3, os.path.join(rootpath, source_image_p3))
listimages.append({'label': 'display-p3 gamma2.2 png', 'image': os.path.basename(source_image_p3), 'group': 'displayp3 png'})

with Image.open(source_image) as im:
    profile = ImageCms.getOpenProfile("../ICC/P3D65.icc")
    im.save(os.path.join(rootpath, "combined-iccdisplayp3.png"), icc_profile=profile.tobytes())
#listimages.append({'label': 'displayp3 png', 'image': "combined-iccdisplayp3.png", 'group': 'png'})

#source_image = "combined-srgb.png"
#with Image.open(source_image) as im:
#    profile = ImageCms.getOpenProfile("../ICC/Simplified-sRGB.icc")
#    im.save(os.path.join(rootpath, "combined-iccsRGB.png"), icc_profile=profile.tobytes())
#listimages.append({'label': 'sRGB png', 'image': "combined-iccsRGB.png", 'group': 'png'})


trc_types = [#{'id': 'rec709', 'label': "-color_primaries 1 = rec709", 'fileext': "rec709", 'primnum': 1,   'group': 'rec709 colortrc', 'source': 'combined-srgb.png'},
             {'id': 'diosplayp3', 'label': "-color_primaries 12 = display p3", 'fileext': "displayp3", 'primnum': 12, 'group': 'displayp3 mp4', 'source': source_image_p3},
             #{'id': 'dcip3', 'label': "-color_primaries 11 = DCI p3", 'fileext': "dcip3", 'primnum': 11, #'group': 'rec709 colortrc', 'source': 'combined-dcip3.png'},
             {'id': 'rec2020', 'label': "-color_primaries 9 = rec2020", 'fileext': "rec2020", 'primnum': 9, 'group': 'rec2020 mp4', 'source': source_image},
     ]
for trc in trc_types:
	# TODO Confirm we have the right one.
	trc['rootpath'] = rootpath

	cmd = 'ffmpeg -loop 1 -y -i  {source}  -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264 -t 10 -pix_fmt yuv420p -qscale:v 1  -color_range 1 -colorspace 1 -color_primaries {primnum} -color_trc 13 {rootpath}/greyscale-{fileext}.mp4'.format(**trc); ext="mp4"

	os.system(cmd)
	trc['ext'] = ext
	listimages.append({'id': trc['id'], 'group': trc.get('group', 'unknown'), 'label': trc['label'], 'video': "greyscale-{fileext}.{ext}".format(**trc), 'cmd': cmd})

# Sort images by group.
listimages = sorted(listimages, key=lambda k:k['group'])

introduction = """
<H1>Primary comparisons</H1>
<p> This is comparing two PNG files to ffmpeg converted versions of those files. Ideally you should be able to see rec2020 if your monitor is rec2020, and P3-D65 if you have a P3 display or will not see any text if nothing is displayed. Since most people do not have rec2020 displays, you shouldnt see the rec2020 text at all. The code to generate these files is <a href='../%s'>here</a>. You can reorder the images to help with comparison by drag and drop.</p>
Filtered views:
<p>
<bl>
<li><A href="compare.html">See all</a></li>
<li><A href="compare.html?.groupdisplayp3">display p3</a></li>
<li><A href="compare.html?.grouprec2020">rec2020</a></li>
<li><A href="compare.html?.png">png files</a></li>
<li><A href="compare.html?.mp4">Mp4 files</a></li>
</bl>
</p>
""" % os.path.basename(__file__)

createCompareHtml(outputpath=rootpath+"/compare.html", 
					listimages=listimages,
					introduction=introduction,
                                    videohtml = '  '
                                        )
