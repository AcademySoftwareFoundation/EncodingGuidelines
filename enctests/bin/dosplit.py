# pip install pillow opencv-python

from PIL import Image
import cv2
import numpy as np

import sys
import os


# Load the two TIFF images
files = sys.argv[1:]
# Grab the extension
ext = files[0].split(".")[-1]

for filename in files:
   dir = os.path.dirname(filename)
   if not os.path.exists(dir+"/split"):
       os.makedirs(dir+"/split")
   if filename.endswith(".mov"):
      ofilename = filename.replace(".mov", ".png")
      print(f"ffmpeg -y -i {filename} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt709:out_color_matrix=bt709  -frames:v 1 {ofilename}")
      os.system(f"ffmpeg -y -i {filename} -compression_level 10 -sws_flags lanczos+accurate_rnd+full_chroma_inp+full_chroma_int -pred mixed -pix_fmt rgb48be -vf scale=in_color_matrix=bt709:out_color_matrix=bt709  -frames:v 1 {ofilename}")
   elif filename.endswith(".j2c"):
      ofilename = filename.replace(".j2c", ".tif")
      print("ojph_expand -i %s -o %s" % (filename, ofilename))
      os.system("ojph_expand -i %s -o %s" % (filename, ofilename))
   else:
      ofilename = filename
   print(f"Reading from {ofilename}")
   result = cv2.imread(ofilename, cv2.IMREAD_UNCHANGED)
   lower = result & 255
   lowerbig = lower * 256
   outfilename = dir+"/split/"+os.path.basename(filename).replace(f".{ext}", "-split.png")
   print("Writing to:", outfilename)
   cv2.imwrite(outfilename, lowerbig)


#os.system("iv split.png")
