This contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.

This is being done as part of the [ASWF Media Review working-group](https://wiki.aswf.io/display/PRWG/Playback+And+Review+Working+Group).

The main page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

## Encoding Cheat sheet

If you are encoding from an image sequence (e.g. imagefile.0000.png imagefile.0001.png ...) to h264 using ffmpeg, we recommend:
```
ffmpeg -r 24 -i inputfile.%04d.png -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264 -preset slower  -pix_fmt yuv420p -qscale:v 1 -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 2 outputfile.mp4
```

Where:
   * **-r 24** means 24 fps
   * **-i inputfile.%04d.png means**  will be padded to 4 digits, i.e. 0000, 0001, 0002, etc.
   *  **-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"** means use the sw-scale filter, setting:
      * **in_range=full** means Full range 0-255 video coming in.
      * **out_range=tv** means tv-range (35-235) video going out.
      * **in_color_matrix=rec709** means color space bt709 video coming in (normal for TV/Desktop video).
      * **out_color_matrix=rec709** means color space bt709 video going out. The combination of this and in_color_matrix will mean the color encoding will match the source media. If you are only adding one set of flags, this is the one, otherwise it will default to an output colorspace of bt601, which is a standard definition spec from the last century, and not suitable for sRGB or HD displays.
   * **-c:v libx264** means use the h264 encoding library (libx264)
   * **-preset slower** a reasonably high quality preset, which will run slow, but not terribly slow.
   * **-pix_fmt yuv420p** use yuv420 video format, which is typical for web playback. If you want a better quality for RV or other desktop tools use -pix_fmt yuv444p10le 
   * **-qscale:v 1** TODO NOT SURE WHAT THIS IS DOING.
   * **-color_range 1** - mp4 metadata - specifying color range as 16-235 (which is default for web playback).
   * **-colorspace 1** - mp4 metadata - specifying rec709 yuv color pixel format 
   * **-color_primaries 1** - mp4 metadata - rec709 color gamut primaries
   * **-color_trc 2** -- mp4 metadata color transfer = unknown - See tests below.

The crutial part is:
'''
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" 
'''
Which is specifying the input and output colorspaces to be bt709.

Separately, if you are converting from exr's in other colorspaces, please use [OCIO](https://opencolorio.org/) to do the color space conversions. [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) is an excellent open-source tool for this.

Links:
   * [Comparing approaches to do the YUV conversion correctly](https://richardssam.github.io/ffmpeg-tests/tests/chip-chart-yuvconvert/compare.html) this shows the right way to do the yuv conversion, comparing the three different ways you can do it in ffmpeg.
   * [Comparing full-range vs. tv range](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-fulltv/compare.html) - reviews how you can get an extended range in your yuv conversion, including on web browsers.
   * [Comparing different outputs for -color_trc](https://richardssam.github.io/ffmpeg-tests/tests/greyramp/compare.html) - Showing what the -color_trc flag is doing.
   * [Comparing different outputs for -color trc part2](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-rev2/compare.html) - Showing how messed up web browers are.


