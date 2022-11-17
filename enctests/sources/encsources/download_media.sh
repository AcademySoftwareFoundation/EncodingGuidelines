#!/usr/bin/bash -xv

#downloading chimera

# https://opencontent.netflix.com/
# This first bit of media is really just for sparks, which hopefully should stress encoders.
if [ ! -d chimera_wind_srgb ]
then
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_wind --recursive --exclude "*" --include "*_790*.tif"
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_wind --recursive --exclude "*" --include "*_791*.tif"
fi

if [[ ! -d chimera_coaster_srgb && ! -d chimera_coaster ]]
then
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_coaster --recursive --exclude "*" --include "*_0442*.tif"
	aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k5994p/ chimera_coaster --recursive --exclude "*" --include "*_0443*.tif"
fi


if [ ! -d chimera_cars_srgb ]
then
        echo Downloading netflix cars.
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_cars --recursive --exclude "*" --include "*_025*.tif"
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_cars --recursive --exclude "*" --include "*_026*.tif"
fi

if [ ! -d chimera_fountains_srgb ]
then
        echo Downloading netflix fountains
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_fountains --recursive --exclude "*" --include "*_054*.tif"
        aws s3 cp --no-sign-request s3://download.opencontent.netflix.com/Chimera/tif_DCI4k2398p/ chimera_fountains --recursive --exclude "*" --include "*_055*.tif"
fi

# I think the file labeling is actually incorrect, this media is actually pretty close to gamma2.2 or 2.4 its not HDR at all. 
# The associated mov file has no HDR metadata associated with it. So I'm going to assume no color space conversion is necessary.

if [ ! -d chimera_wind_srgb ]
then
    mkdir chimera_wind_srgb
	echo Building chimera_wind png
	oiiotool -v --framepadding 6 --frames 79000-79199 -i chimera_wind/Chimera_DCI4k5994p_HDR_P3PQ_@@@@@@.tif --resize 2048x1080 -dither -o chimera_wind_srgb/chimera_wind_srgb.#.png
	rm -rf chimera_wind
fi

if [ ! -d chimera_coaster_srgb ]
then
    mkdir chimera_coaster_srgb
	echo Building chimera_coaster_srgb png
	oiiotool -v --framepadding 6 --frames 44200-44399 -i chimera_coaster/Chimera_DCI4k5994p_HDR_P3PQ_@@@@@@.tif --resize 2048x1080 -dither -o chimera_coaster_srgb/chimera_coaster_srgb.#.png
	#rm -rf chimera_coaster
fi


if [ ! -d chimera_cars_srgb ]
then
    mkdir chimera_cars_srgb
	echo Building chimera_cars png
	oiiotool -v --framepadding 5 --frames 2500-2699 -i chimera_cars/Chimera_DCI4k2398p_HDR_P3PQ_@@@@@.tif --resize 2048x1080 -dither -o chimera_cars_srgb/chimera_cars_srgb.#.png
	rm -rf chimera_cars
fi


if [ ! -d chimera_fountains_srgb ]
then
    mkdir chimera_fountains_srgb
	echo Building chimera_fountains png
	oiiotool -v --framepadding 5 --frames 5400-5599 -i chimera_fountains/Chimera_DCI4k2398p_HDR_P3PQ_@@@@@.tif --resize 2048x1080 -dither -o chimera_fountains_srgb/chimera_fountains_srgb.#.png
	rm -rf chimera_fountains
fi
