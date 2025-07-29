import subprocess
import os
# This script generates a 2x2 mosaic of 8K images from various source media files.
# We are going for the 8k-UHD resolution rather than true 8K DCI resolution.

source_media=[{'path': "chimera_cars/Chimera_DCI4k2398p_HDR_P3PQ_%05d.tif", "start": 2500},
              {'path': "chimera_coaster/Chimera_DCI4k5994p_HDR_P3PQ_%06d.tif", "start": 44200},
              {'path': "chimera_fountains/Chimera_DCI4k2398p_HDR_P3PQ_%05d.tif", "start": 5400},
              {'path': "chimera_wind/Chimera_DCI4k5994p_HDR_P3PQ_%06d.tif", "start": 66600}
              ]

outputdir = "mosaic_8k"
if not os.path.exists(outputdir):
    os.makedirs(outputdir)

with open("mosaic_8k/mosaic.%05d.tif.yml", "w") as f:
    f.write("images: true\n")
    f.write("path: mosaic.%05d.tif\n")
    f.write("width: 8192\n")
    f.write("height: 4320\n")
    f.write("in: 1\n")
    f.write("duration: 200\n")
    f.write("rate: 25\n")

for frame in range(1, 201):
    cmd = ["oiiotool"]
    for media in source_media:
        cmd.append("-i")
        cmd.append(media['path'] % (media['start'] + frame - 1))
    cmd.extend(["-mosaic:fit=3840x2160", "2x2", "-o", "mosaic_8k/mosaic.%05d.tif" % frame, "--compression", "zip"])
    print("Running command:", " ".join(cmd))
    subprocess.run(cmd, check=True)
