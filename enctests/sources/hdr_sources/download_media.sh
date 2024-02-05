#!/bin/bash -xv

#downloading sparks

export OCIO=ocio://studio-config-v1.0.0_aces-v1.3_ocio-v2.1

# https://opencontent.netflix.com/
# This first bit of media is really just for sparks, which hopefully should stress encoders.
if [ ! -d sparks ]
then
	echo Downloading netflix sparks pt1.
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/sparks/aces_image_sequence_59_94_fps/ sparks --recursive --exclude "*" --include "SPARKS_ACES_061*.exr"
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/sparks/aces_image_sequence_59_94_fps/ sparks --recursive --exclude "*" --include "SPARKS_ACES_062*.exr"
fi


# https://opencontent.netflix.com/
# This is a second extract from sparks, which is a great HDR test.
if [ ! -d sparks2 ]
then
	echo Downloading netflix sparks pt2.
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/sparks/aces_image_sequence_59_94_fps/ sparks2 --recursive --exclude "*" --include "SPARKS_ACES_067*.exr"
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/sparks/aces_image_sequence_59_94_fps/ sparks2 --recursive --exclude "*" --include "SPARKS_ACES_068*.exr"
fi

if [ ! -f sparks_srgb/sparks_srgb.06100.png ]
then
    mkdir sparks_srgb
	echo Building sparks png
	oiiotool -v --framepadding 5 --frames 6100-6299 sparks/SPARKS_ACES_#.exr --fit 1920x1080 \
       --colorconvert linear srgb -d uint16  -o sparks_srgb/sparks_srgb.#.png

fi

if [ ! -f sparks2_srgb/sparks2_srgb.06700.png ]
then
    mkdir sparks2_srgb
	echo Building sparks2_srgb
	oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --fit 1920x1080 \
        --iscolorspace "ACEScg"  --ociodisplay "sRGB - Display" "ACES 1.0 - SDR Video" -d uint16  -o sparks2_srgb/sparks2_srgb.#.png

fi

if [ ! -f sparks2_hlg/sparks2_hlg.06700.png ]
then
    mkdir sparks2_hlg
	echo Building sparks2_hlg
    oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --iscolorspace "ACEScg"  --fit 1920x1080 --ociodisplay "Rec.2100-HLG - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" -d uint16 -o sparks2_hlg/sparks2_hlg.#.png
fi

if [ ! -f sparks2_pq1000/sparks2_pq1000.06700.png ]
then
    mkdir sparks2_pq1000
	echo Building sparks2_pq1000
    oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr  --iscolorspace "ACEScg" --fit 1920x1080  --ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (1000 nits & Rec.2020 lim)" -d uint16 -o sparks2_pq1000/sparks2_pq1000.#.png
fi

if [ ! -f sparks2_pq2000/sparks2_pq2000.06700.png ]
then
    mkdir sparks2_pq2000
	echo Building sparks2_pq2000
    oiiotool -v --framepadding 5 --frames 6700-6899 sparks2/SPARKS_ACES_#.exr --iscolorspace "ACEScg" --fit 1920x1080  --ociodisplay "Rec.2100-PQ - Display" "ACES 1.1 - HDR Video (2000 nits & Rec.2020 lim)" -d uint16 -o sparks2_pq2000/sparks2_pq2000.#.png
fi

 # Encoding test
# ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   -c:v libx265   -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt yuv444p10le   -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -x265-params ‘colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400’   sparks2_hlg_444.mov

# ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   -c:v libx265   -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt yuv420p10le   -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -x265-params ‘colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400’   sparks2_hlg_420.mov

#ffmpeg -r 30 -start_number 6700 -i sparks2_srgb/sparks2_srgb.%05d.png -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" \
#        -c:v libx264 -preset slower -pix_fmt yuv420p \
#        -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 13 sparks2_srgb_420_v2.mov

# ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -color_range pc   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_hlg/sparks2_hlg.%05d.png   -vf 'scale=in_color_matrix=smpte2084:out_color_matrix=smpte2084' -c:v libx265   -color_range tv   -color_trc arib-std-b67   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt yuv420p10le  -tag:v hvc1  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -x265-params ‘colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400’   sparks2_hlg_420_v2.mov

 # ffmpeg  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -color_range pc   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt rgb48be  -r 30 -start_number 6700 -i sparks2_pq1000/sparks2_pq1000.%05d.png   -vf 'scale=in_color_matrix=smpte2084:out_color_matrix=smpte2084' -c:v libx265   -color_range tv   -color_trc smpte2084   -color_primaries bt2020   -colorspace bt2020nc   -pix_fmt yuv420p10le  -tag:v hvc1  -sws_flags print_info+accurate_rnd+bitexact+full_chroma_int   -x265-params ‘colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:range=limited:master-display=G\(13250,34500\)B\(7500,3000\)R\(34000,16000\)WP\(15635,16450\)L\(10000000,1\):max-cll=1000,400’   sparks2_pq1000_420_v2.mov
