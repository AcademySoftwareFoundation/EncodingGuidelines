# A script for generating some of the test patterns.

# We need to convert a number of images to 4:2:2 and 4:2:0 
# so that when we do the image check, we are comparing against the ideal version.

python3 generate_chroma.py

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 chip-chart-1080-16bit-noicc-yuv422p10le.png
# Strip off the alpha, idiff will otherwise complain.
rm  chip-chart-1080-noicc-yuv422p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chip-chart-1080-16bit-noicc-yuv420p10le.png
# Strip off the alpha, idiff will otherwise complain.
rm chip-chart-1080-noicc-yuv420p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p.yuv -pix_fmt rgb48be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chip-chart-1080-16bit-noicc-yuv420p.png
# Strip off the alpha, idiff will otherwise complain.
rm chip-chart-1080-noicc-yuv420p.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p.yuv -pix_fmt rgb48be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chip-chart-1080-16bit-noicc-yuv422p.png
# Strip off the alpha, idiff will otherwise complain.
rm chip-chart-1080-noicc-yuv422p.yuv

#smptehdbars_16.png
ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i smptehdbars_16-yuv422p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv422p10le.png

# Strip off the alpha, idiff will otherwise complain.
rm smptehdbars_16-yuv422p10le.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i smptehdbars_16-yuv420p10le.yuv -pix_fmt rgb48be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv420p10le.png
# Strip off the alpha, idiff will otherwise complain.
rm smptehdbars_16-yuv420p10le.yuv


ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v h264 -pix_fmt yuv420p10le \
     -sws_flags spline+accurate_rnd+full_chroma_int -preset placebo -qp 0 -qscale:v 1  -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv420p10le.mov"
ffmpeg -i smptehdbars_16-yuv420p10le.mov -pix_fmt rgb48be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv420p10le-alt.png

ffmpeg -i smptehdbars_16-yuv420p10le.mov -pix_fmt rgb48be \
   -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv420p10le-alt2.png
# Strip off the alpha, idiff will otherwise complain.

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i smptehdbars_16-yuv420p.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv420p.png
# Strip off the alpha, idiff will otherwise complain.
rm smptehdbars_16-yuv420p.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i smptehdbars_16-yuv422p.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y smptehdbars_16-yuv422p.png
# Strip off the alpha, idiff will otherwise complain.
#rm  smptehdbars_16-yuv422p.yuv


ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-yuv420p10le.yuv"

ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v h264 -g 0 -preset placebo -pix_fmt yuv420p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-yuv420p10le.mov"

ffmpeg   -colorspace bt709 -color_primaries bt709 -color_trc 2 -y -i chromatest_1080.png -vframes 1 -c:v h264 -g 0 -preset placebo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-spline2-yuv420p10le.mov"


#ffmpeg  -i chromatest_1080.png -frames:v 200 -g 0 -c:v libx264 -color_primaries 1 -color_range 1 -color_trc 2 -colorspace 1 -pix_fmt yuv420p10le -preset slow -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -y "chromatest_1080-spline3-yuv420p10le.mp4"

#ffmpeg  -i chromatest_1080.png -frames:v 200 -crf 5 -c:v libx264 -color_primaries 1 -color_range 1 -color_trc 2 -colorspace 1 -pix_fmt yuv420p10le -preset slow -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -y "chromatest_1080-spline4-yuv420p10le.mp4"

#ffmpeg  -i "/Users/sam/git/EncodingGuidelines/sourceimages/chromatest_1080.png" -frames:v 200         -crf 18                         -y -c:v libx264 -color_primaries 1 -color_range 1 -color_trc 2 -colorspace 1 -pix_fmt yuv420p10le -preset slow -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -y "chromatest_1080-spline5-yuv420p10le.mp4"

fmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chromatest_1080-yuv420p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest_1080-yuv420p10le.png
# Strip off the alpha, idiff will otherwise complain.
#rm chromatest_1080-yuv420p.yuv


ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i chromatest_1080-yuv420p.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest_1080-yuv420p.png
# Strip off the alpha, idiff will otherwise complain.
#rm chromatest_1080-yuv420p.yuv


ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
      -y "chromatest_1080-yuv422p.yuv"

ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i chromatest_1080-yuv422p.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest_1080-yuv422p.png
# Strip off the alpha, idiff will otherwise complain.
#rm  chromatest_1080-yuv422p.yuv

ffmpeg  -y -i chromatest4_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest4_1080-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i chromatest4_1080-yuv422p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest4_1080-yuv422p10le.png
# Strip off the alpha, idiff will otherwise complain.
rm  chip-chart-1080-noicc-yuv422p10le.yuv

ffmpeg  -y -i chromatest4_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest4_1080-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chromatest4_1080-yuv420p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest4_1080yuv420p10le.png


ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i chromatest_1080-yuv422p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest_1080-yuv422p10le.png
# Strip off the alpha, idiff will otherwise complain.
rm  chip-chart-1080-noicc-yuv422p10le.yuv

ffmpeg  -y -i chromatest_1080.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -sws_flags spline+accurate_rnd+full_chroma_int -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chromatest_1080-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chromatest_1080-yuv420p10le.yuv -pix_fmt rgb48be \
    -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    -colorspace bt709 -color_primaries bt709 -color_trc 2 -y chromatest_1080-yuv420p10le.png


# Strip off the alpha, idiff will otherwise complain.