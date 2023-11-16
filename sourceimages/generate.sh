#!/bin/bash -xv

# A script for generating some of the test patterns.

# We need to convert a number of images to 4:2:2 and 4:2:0 
# so that when we do the image check, we are comparing against the ideal version.

set -e
set -o xtrace

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv422p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv422p10le-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv422p10le.png
rm chip-chart-1080-16bit-noicc-yuv422p10le-a.png chip-chart-1080-noicc-yuv422p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv420p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv420p10le-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv420p10le.png
rm chip-chart-1080-16bit-noicc-yuv420p10le-a.png chip-chart-1080-noicc-yuv420p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv420p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv420p-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv420p.png
rm chip-chart-1080-16bit-noicc-yuv420p-a.png chip-chart-1080-noicc-yuv420p.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv422p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv422p-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv422p.png
rm chip-chart-1080-16bit-noicc-yuv422p-a.png chip-chart-1080-noicc-yuv422p.yuv

#smptehdbars_16.png
ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16_yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i smptehdbars_16_yuv422p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16_yuv422p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16_yuv422p10le-a.png --ch r,g,b -o smptehdbars_16_yuv422p10le.png
rm smptehdbars_16_yuv422p10le-a.png smptehdbars_16_yuv422p10le.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16_yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i smptehdbars_16_yuv420p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16_yuv420p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16_yuv420p10le-a.png --ch r,g,b -o smptehdbars_16_yuv420p10le.png
rm smptehdbars_16_yuv420p10le-a.png smptehdbars_16_yuv420p10le.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16_yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i smptehdbars_16_yuv420p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16_yuv420p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16_yuv420p-a.png --ch r,g,b -o smptehdbars_16_yuv420p.png
rm smptehdbars_16_yuv420p-a.png smptehdbars_16_yuv420p.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16_yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i smptehdbars_16_yuv422p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16_yuv422p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16_yuv422p-a.png --ch r,g,b -o smptehdbars_16_yuv422p.png
rm smptehdbars_16_yuv422p-a.png smptehdbars_16_yuv422p.yuv

#ffmpeg -y -i smptehdbars_16.png -pix_fmt yuv422p10le -strict -1 smptehdbars_16_yuv422p10le.y4m
#ffmpeg -y -i smptehdbars_16_yuv422p10le.y4m -pix_fmt rgba64be -sws_flags area+accurate_rnd+full_chroma_int smptehdbars_16_yuv422p10le.png

#ffmpeg -y -i smptehdbars_16.png -pix_fmt yuv420p10le -strict -1 smptehdbars_16_yuv420p10le.y4m
#ffmpeg -y -i smptehdbars_16_yuv420p10le.y4m -pix_fmt rgba64be -sws_flags area+accurate_rnd+full_chroma_int smptehdbars_16_yuv420p10le.png

# Make a 10-bit image as a DPX file.
oiiotool -i smptehdbars_16.png -d uint10 -o smptehdbars_10.dpx
# 420 image
ffmpeg -y -i smptehdbars_10.dpx -vframes 1 -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p10le  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -strict -1 -y smptehdbars_10_yuv420p10le.y4m
ffmpeg -i smptehdbars_10_yuv420p10le.y4m -sws_flags area+accurate_rnd -pix_fmt rgba64be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_10_yuv420p10le_a.png
oiiotool -i smptehdbars_10_yuv420p10le_a.png --ch r,g,b -o smptehdbars_10_yuv420p10le.png
#rm smptehdbars_10_yuv420p10le_a.png smptehdbars_10_yuv420p10le.yuv

# 422 image
ffmpeg -y -i smptehdbars_10.dpx -vframes 1 -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p10le  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -strict -1 -y smptehdbars_10_yuv422p10le.y4m
ffmpeg -y -i smptehdbars_10_yuv422p10le.y4m -sws_flags area+accurate_rnd -pix_fmt rgba64be \
   -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -vframes 1 \
    smptehdbars_10_yuv422p10le_a.png
oiiotool -i smptehdbars_10_yuv422p10le_a.png --ch r,g,b -o smptehdbars_10_yuv422p10le.png
# rm smptehdbars_10_yuv422p10le_a.png smptehdbars_10_yuv422p10le.yuv

#ffmpeg -y -i smpte_dpx/smptehdbars_10_resolve2_00086400.dpx -vframes 1 -sws_flags 'area+accurate_rnd+full_chroma_int' -pix_fmt yuv422p10le  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -strict -1 -y smptehdbars_10_yuv422p10le_resolvedpx_pixfmt_area.y4m
#ffmpeg -y -i smpte_dpx/smptehdbars_10_resolve2_00086400.dpx -vframes 1 -sws_flags 'area+accurate_rnd+full_chroma_int' -vf scale=in_color_matrix=bt709:out_color_matrix=bt709,format=yuv422p10le -strict -1 -y smptehdbars_10_yuv422p10le_resolvedpx_vf2.y4m
#fmpeg -y -i smpte_dpx/smptehdbars_10_resolve2_00086400.dpx -vframes 1 -sws_flags 'area+accurate_rnd+full_chroma_int' -vf scale=in_color_matrix=bt709:out_color_matrix=bt709,format=yuv422p10le -strict -1 -y smptehdbars_10_yuv422p10le_resolvedpx_vf2_noarea.y4m

#ffmpeg -y -i smptehdbars_10.dpx -vframes 1 -pix_fmt yuv422p10le  -c:v v210 -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y smptehdbars_10_yuv422p10le.mov


# ffmpeg -y -i smptehdbars_10.dpx -vframes 1 -pix_fmt yuv422p10le  -sws_flags area+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -strict -1 -y smptehdbars_10_yuv422p10le_accurate.y4m
# ffmpeg -y -i smptehdbars_10_yuv422p10le.y4m -pix_fmt rgba64be \
#    -sws_flags area+area+accurate_rnd+full_chroma_int -vframes 1 \
#     -vf scale=in_h_chr_pos=0:in_v_chr_pos=0:in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_10_yuv422p10le_a_topleft.png
# ffmpeg -y -i smptehdbars_10_yuv422p10le.y4m -pix_fmt rgba64be \
#    -sws_flags area+accurate_rnd+full_chroma_int -vframes 1 \
#     -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_10_yuv422p10le_nospline.png

#oiiotool -i smptehdbars_10_yuv422p10le_a.png --ch r,g,b -o smptehdbars_10_yuv422p10le.png
#rm smptehdbars_10_yuv422p10le_a.png smptehdbars_10_yuv422p10le.yuv



# Make a 12-bit image as a dpx file.
oiiotool -i smptehdbars_16.png -d uint12 -o smptehdbars_12.dpx

# 420 image
ffmpeg -y -i smptehdbars_12.dpx -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p10le  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y smptehdbars_12_yuv420p10le.yuv
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i smptehdbars_12_yuv420p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_12_yuv420p10le_a.png
oiiotool -i smptehdbars_12_yuv420p10le_a.png --ch r,g,b -o smptehdbars_12_yuv420p10le.png
rm smptehdbars_12_yuv420p10le_a.png smptehdbars_12_yuv420p10le.yuv

# 422 image
ffmpeg -y -i smptehdbars_12.dpx -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p10le  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y smptehdbars_12_yuv422p10le.yuv
ffmpeg -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i smptehdbars_12_yuv422p10le.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_12_yuv422p10le_a.png
oiiotool -i smptehdbars_12_yuv422p10le_a.png --ch r,g,b -o smptehdbars_12_yuv422p10le.png
rm smptehdbars_12_yuv422p10le_a.png smptehdbars_12_yuv422p10le.yuv

# 
oiiotool -i smptehdbars_16.png -d uint8 -o smptehdbars_8.png
# 420 image
ffmpeg -y -i smptehdbars_8.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv420p  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y smptehdbars_8_yuv420p.yuv
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i smptehdbars_8_yuv420p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_8_yuv420p_a.png
oiiotool -i smptehdbars_8_yuv420p_a.png --ch r,g,b -o smptehdbars_8_yuv420p.png
rm smptehdbars_8_yuv420p_a.png smptehdbars_8_yuv420p.yuv

# 422 image
ffmpeg -y -i smptehdbars_8.png -vframes 1 -c:v rawvideo -sws_flags area+accurate_rnd+full_chroma_int -pix_fmt yuv422p  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y smptehdbars_8_yuv422p.yuv
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i smptehdbars_8_yuv422p.yuv -pix_fmt rgba64be \
   -sws_flags area+accurate_rnd -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 smptehdbars_8_yuv422p_a.png
oiiotool -i smptehdbars_8_yuv422p_a.png --ch r,g,b -o smptehdbars_8_yuv422p.png
rm smptehdbars_8_yuv422p_a.png smptehdbars_8_yuv422p.yuv

