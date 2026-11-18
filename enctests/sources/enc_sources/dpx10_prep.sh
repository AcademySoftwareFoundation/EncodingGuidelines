#!/bin/bash
# Make the 10-bit DPX sources used by test_wedge_configs/intraframeonly*_tests.yml
# (sources/enc_sources/chimera_*_srgb_dpx_10). Run from sources/enc_sources.
set -e
make() {  # name padding first last
  name=$1; pad=$2; first=$3; last=$4
  pat=$(printf '%%0%dd' $pad)
  out=${name}_dpx_10
  mkdir -p $out
  sed "s/\.png/.dpx/" < ${name}/${name}.${pat}.png.yml > ${out}/${name}.${pat}.dpx.yml
  oiiotool -v --framepadding $pad --parallel-frames --frames ${first}-${last} \
    -i ${name}/${name}.#.png -d uint10 -o ${out}/${name}.#.dpx
}
make chimera_cars_srgb 5 2500 2699
make chimera_coaster_srgb 6 44200 44399
make chimera_fountains_srgb 5 5400 5599
make chimera_wind_srgb 6 66600 66799
