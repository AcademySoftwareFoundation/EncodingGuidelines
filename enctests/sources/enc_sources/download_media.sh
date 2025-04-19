#!/bin/bash -xv


#if [ ! -d Sintel-trailer-1080p-png ]
#then
#	echo Downloading Sintel-trailer-1080p-png
#	curl https://s3.amazonaws.com/senkorasic.com/test-media/video/sintel/source/Sintel-trailer-1080p-png.zip -o Sintel-trailer-1080p-png.zip
#	unzip Sintel-trailer-1080p-png.zip -d Sintel-trailer-1080p-png
#	rm -rf Sintel-trailer-1080p-png.zip
#fi

#downloading chimera

# https://opencontent.netflix.com/
# This first bit of media is really just for sparks, which hopefully should stress encoders.
if [[ ! -d chimera_wind && ! -f chimera_wind_srgb/chimera_wind_srgb.66600.png ]]
then
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_wind --recursive --exclude '*' --include '*_0666*.tif'
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_wind --recursive --exclude "*" --include "*_0667*.tif"
fi

if [[ ! -f chimera_coaster_srgb/chimera_coaster_srgb.44200.png && ! -d chimera_coaster ]]
then
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_coaster --recursive --exclude "*" --include "*_0442*.tif"
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_coaster --recursive --exclude "*" --include "*_0443*.tif"
fi


if [[ ! -f chimera_cars_srgb/chimera_cars_srgb.02500.png && ! -d chimera_cars ]]
then
        echo Downloading netflix cars.
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_cars --recursive --exclude "*" --include "*_025*.tif"
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_cars --recursive --exclude "*" --include "*_026*.tif"
fi

if [[ ! -f chimera_fountains_srgb/chimera_fountains_srgb.05400.png && ! -d chimera_fountains ]]
then
        echo Downloading netflix fountains
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_fountains --recursive --exclude "*" --include "*_054*.tif"
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_fountains --recursive --exclude "*" --include "*_055*.tif"
fi

# I think the file labeling is actually incorrect, this media is actually pretty close to gamma2.2 or 2.4 its not HDR at all. 
# The associated mov file has no HDR metadata associated with it. So I'm going to assume no color space conversion is necessary.

if [ ! -f chimera_wind_srgb/chimera_wind_srgb.66600.png ]
then
    mkdir chimera_wind_srgb
	echo Building chimera_wind png
	oiiotool -v --framepadding 6 --parallel-frames --frames 66600-66799 -i chimera_wind/Chimera_DCI4k5994p_HDR_P3PQ_@@@@@@.tif --resize 1920x1080  --powc 2 -d uint16 -o chimera_wind_srgb/chimera_wind_srgb.#.png
	# rm -rf chimera_wind
fi

if [ ! -f chimera_coaster_srgb/chimera_coaster_srgb.44200.png ]
then
    mkdir chimera_coaster_srgb
	echo Building chimera_coaster_srgb png
	oiiotool -v --framepadding 6 --parallel-frames --frames 44200-44399 -i chimera_coaster/Chimera_DCI4k5994p_HDR_P3PQ_@@@@@@.tif --resize 1920x1080  --powc 2 -d uint16 -o chimera_coaster_srgb/chimera_coaster_srgb.#.png
	#rm -rf chimera_coaster
fi


if [ ! -f chimera_cars_srgb/chimera_cars_srgb.02500.png ]
then
    mkdir chimera_cars_srgb
	echo Building chimera_cars png
	oiiotool -v --framepadding 5 --parallel-frames --frames 2500-2699 -i chimera_cars/Chimera_DCI4k2398p_HDR_P3PQ_@@@@@.tif --resize 1920x1080  --powc 2 -d uint16 -o chimera_cars_srgb/chimera_cars_srgb.#.png
	#rm -rf chimera_cars
fi


if [ ! -f chimera_fountains_srgb/chimera_fountains_srgb.05400.png ]
then
    mkdir chimera_fountains_srgb
	echo Building chimera_fountains png
	oiiotool -v --framepadding 5 --parallel-frames --frames 5400-5599 -i chimera_fountains/Chimera_DCI4k2398p_HDR_P3PQ_@@@@@.tif --resize 1920x1080  --powc 2  -d uint16 -o chimera_fountains_srgb/chimera_fountains_srgb.#.png
	#rm -rf chimera_fountains
fi

#oiiotool -v --frames 2500-2699 --parallel-frames -i chimera_cars/Chimera_DCI4k2398p_HDR_P3PQ_%05d.tif --ociodisplay:from=ACEScg:inverse=1 'ST2084-P3-D65 - Display' 'ACES 1.1 - HDR Video (1000 nits & P3 lim)' --mulc 0.15 -o chimera_cars_ACEScg_exr/chimera_cars_ACEScg_exr.%05d.exr
#oiiotool -v --frames 044200-44399 --parallel-frames -i chimera_coaster/Chimera_DCI4k5994p_HDR_P3PQ_%06d.tif --ociodisplay:from=ACEScg:inverse=1 'ST2084-P3-D65 - Display' 'ACES 1.1 - HDR Video (1000 nits & P3 lim)' -o exr/coaster.%06d.exr
#oiiotool -v --framepadding 5 --parallel-frames --frames 5400-5599 -i chimera_fountains/Chimera_DCI4k2398p_HDR_P3PQ_@@@@@.tif --ociodisplay:from=ACEScg:inverse=1 'ST2084-P3-D65 - Display' 'ACES 1.1 - HDR Video (1000 nits & P3 lim)'  -o chimera_fountains/chimera_fountains.%06d.exr
