# A script for generating some of the test patterns.

# We need to convert a number of images to 4:2:2 and 4:2:0 
# so that when we do the image check, we are comparing against the ideal version.



ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p10le.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv422p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv422p10le-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv422p10le.png
rm chip-chart-1080-16bit-noicc-yuv422p10le-a.png chip-chart-1080-noicc-yuv422p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p10le.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv420p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv420p10le-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv420p10le.png
rm chip-chart-1080-16bit-noicc-yuv420p10le-a.png chip-chart-1080-noicc-yuv420p10le.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv420p.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv420p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv420p-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv420p.png
rm chip-chart-1080-16bit-noicc-yuv420p-a.png chip-chart-1080-noicc-yuv420p.yuv

ffmpeg  -y -i chip-chart-1080-16bit-noicc.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "chip-chart-1080-noicc-yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i chip-chart-1080-noicc-yuv422p.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    chip-chart-1080-16bit-noicc-yuv422p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i chip-chart-1080-16bit-noicc-yuv422p-a.png --ch r,g,b -o chip-chart-1080-16bit-noicc-yuv422p.png
rm chip-chart-1080-16bit-noicc-yuv422p-a.png chip-chart-1080-noicc-yuv422p.yuv

#smptehdbars_16.png
ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv422p10le.yuv"
ffmpeg  -y -f rawvideo -pixel_format yuv422p10le -video_size 1920x1080 -i smptehdbars_16-yuv422p10le.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16-yuv422p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16-yuv422p10le-a.png --ch r,g,b -o smptehdbars_16-yuv422p10le.png
rm smptehdbars_16-yuv422p10le-a.png smptehdbars_16-yuv422p10le.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p10le \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv420p10le.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p10le -video_size 1920x1080 -i smptehdbars_16-yuv420p10le.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16-yuv420p10le-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16-yuv420p10le-a.png --ch r,g,b -o smptehdbars_16-yuv420p10le.png
rm smptehdbars_16-yuv420p10le-a.png smptehdbars_16-yuv420p10le.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv420p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv420p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv420p -video_size 1920x1080 -i smptehdbars_16-yuv420p.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16-yuv420p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16-yuv420p-a.png --ch r,g,b -o smptehdbars_16-yuv420p.png
rm smptehdbars_16-yuv420p-a.png smptehdbars_16-yuv420p.yuv

ffmpeg  -y -i smptehdbars_16.png -vframes 1 -c:v rawvideo -pix_fmt yuv422p \
      -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 -y "smptehdbars_16-yuv422p.yuv"
ffmpeg -y -f rawvideo -pixel_format yuv422p -video_size 1920x1080 -i smptehdbars_16-yuv422p.yuv -pix_fmt rgba64be \
   -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 \
    -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 \
    smptehdbars_16-yuv422p-a.png
# Strip off the alpha, idiff will otherwise complain.
oiiotool -i smptehdbars_16-yuv422p-a.png --ch r,g,b -o smptehdbars_16-yuv422p.png
rm smptehdbars_16-yuv422p-a.png smptehdbars_16-yuv422p.yuv
