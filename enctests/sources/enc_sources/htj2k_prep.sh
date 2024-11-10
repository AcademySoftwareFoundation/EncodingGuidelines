ext=ppm
bitdepth=12
ops=--nativeformat -d uint${bitdepth}
#ops=-pix_fmt rgb30 -compression_level 0
mkdir  chimera_coaster_srgb_${ext}_${bitdepth}
sed "s/.png/.$ext/" < chimera_coaster_srgb/chimera_coaster_srgb.%06d.png.yml > chimera_coaster_srgb_${ext}_${bitdepth}/chimera_coaster_srgb.%06d.$ext.yml
mogrify -path chimera_coaster_srgb_${ext}_${bitdepth} -format $ext -depth $bitdepth chimera_coaster_srgb/*.png
exit
#ffmpeg -f image2 -framerate 1 -start_number 44200 -i chimera_coaster_srgb/chimera_coaster_srgb.%06d.png ${ops} chimera_coaster_srgb_${ext}_${bitdepth}/chimera_coaster_srgb.%06d.$ext
#oiiotool -v -framepadding 6 --parallel-frames --frames 44200-44399 -i chimera_coaster_srgb/chimera_coaster_srgb.#.png ${ops} -o chimera_coaster_srgb_${ext}_${bitdepth}/chimera_coaster_srgb.#.$ext

mkdir  chimera_fountains_srgb_${ext}_${bitdepth}
sed "s/.png/.$ext/" < chimera_fountains_srgb/chimera_fountains_srgb.%05d.png.yml > chimera_fountains_srgb_${ext}_${bitdepth}/chimera_fountains_srgb.%05d.$ext.yml
mogrify -path chimera_fountains_srgb_${ext}_${bitdepth} -format $ext -depth $bitdepth chimera_fountains_srgb/*.png
#oiiotool -v --framepadding 5 --parallel-frames --frames 5400-5599 -i chimera_fountains_srgb/chimera_fountains_srgb.#.png ${ops} -o chimera_fountains_srgb_${ext}_${bitdepth}/chimera_fountains.#.$ext

mkdir  chimera_wind_srgb_${ext}_${bitdepth}
sed "s/.png/.$ext/" < chimera_wind_srgb/chimera_wind_srgb.%06d.png.yml > chimera_wind_srgb_${ext}_${bitdepth}/chimera_wind_srgb.%06d.$ext.yml
mogrify -path chimera_wind_srgb_${ext}_${bitdepth} -format $ext -depth $bitdepth chimera_wind_srgb/*.png
#oiiotool -v --framepadding 6 --parallel-frames --frames 66600-667199 -i chimera_wind_srgb/chimera_wind_srgb.#.png ${ops} -o  chimera_wind_srgb_${ext}_${bitdepth}/chimera_wind_srgb.#.$ext

mkdir  chimera_cars_srgb_${ext}_${bitdepth}
sed "s/.png/.$ext/" < chimera_cars_srgb/chimera_cars_srgb.%05d.png.yml > chimera_cars_srgb_${ext}_${bitdepth}/chimera_cars_srgb.%05d.$ext.yml
mogrify -path chimera_cars_srgb_${ext}_${bitdepth} -format $ext -depth $bitdepth chimera_cars_srgb/*.png
#oiiotool -v --framepadding 5 --parallel-frames --frames 2500-2699 -i chimera_cars_srgb/chimera_cars_srgb.#.png ${ops} -o chimera_cars_srgb_${ext}_${bitdepth}/chimera_cars_srgb.#.$ext
