This contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.

This is being done as part of the [ASWF Media Review working-group](https://wiki.aswf.io/display/PRWG/Playback+And+Review+Working+Group).

The main page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

## Encoding Cheat sheet

If you are encoding from an image sequence to h264 using ffmpeg, if you are doing one thing, please use the yuv conversion correctly:
```
ffmpeg -y -r 24 -i inputfile.%04d.png -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264 -preset slow  -pix_fmt yuv420p -qscale:v 1 -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2 outputfile.mp4
```

The crutial part is:
'''
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" 
'''
Which is specifying the input and output colorspaces to be bt709.

Separately, if you are converting from exr's in other colorspaces, please use OCIO to do the color space conversions. oiiotool is an excellent open-source tool for this.

Links:
   * [Comparing approaches to do the YUV conversion correctly](https://richardssam.github.io/ffmpeg-tests/tests/chip-chart-yuvconvert/compare.html)
   * [Comparing full-range vs. tv range](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-fulltv/compare.html)
   * [Comparing different outputs for -color_trc](https://richardssam.github.io/ffmpeg-tests/tests/greyramp/compare.html)
   * [Comparing different outputs for -color trc part2](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-rev2/compare.html)


