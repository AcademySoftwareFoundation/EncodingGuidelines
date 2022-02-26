This contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.

This is being done as part of the [ASWF Media Review working-group](https://wiki.aswf.io/display/PRWG/Playback+And+Review+Working+Group).

The main page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

## Encoding Cheat sheet

If you are encoding from an image sequence (e.g. imagefile.0000.png imagefile.0001.png ...) to h264 using ffmpeg, we recommend:
```
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" -vframes 100 -c:v libx264 -preset slower  -pix_fmt yuv420p -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 13 outputfile.mp4
```

Where:
   * **-r 24** means 24 fps
   * **-start_number* means the frame sequence starts from frame 1 (defaults to 0)
   * **-i inputfile.%04d.png means**  will be padded to 4 digits, i.e. 0000, 0001, 0002, etc.
   * **-vframes 100* This is optional, but allows you to specify how many frames to encode, otherwise it will encode the entire frame range.
   *  **-vf "scale=in_color_matrix=bt709:out_color_matrix=bt709"** means use the sw-scale filter, setting:
      * **in_color_matrix=rec709** means color space bt709 video coming in (normal for TV/Desktop video).
      * **out_color_matrix=rec709** means color space bt709 video going out. The combination of this and in_color_matrix will mean the color encoding will match the source media. If you are only adding one set of flags, this is the one, otherwise it will default to an output colorspace of bt601, which is a standard definition spec from the last century, and not suitable for sRGB or HD displays.
   * **-c:v libx264** means use the h264 encoding library (libx264)
   * **-preset slower** a reasonably high quality preset, which will run slow, but not terribly slow.
   * **-pix_fmt yuv420p** use yuv420 video format, which is typical for web playback. If you want a better quality for RV or other desktop tools use -pix_fmt yuv444p10le 
   * **-color_range 1** - mp4 metadata - specifying color range as 16-235 (which is default for web playback).
   * **-colorspace 1** - mp4 metadata - specifying rec709 yuv color pixel format 
   * **-color_primaries 1** - mp4 metadata - rec709 color gamut primaries
   * **-color_trc 13** -- mp4 metadata color transfer = sRGB - See tests below.

The crutial part is:
'''
-vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" 
'''
Which is specifying the input and output colorspaces to be bt709.

Separately, if you are converting from exr's in other colorspaces, please use [OCIO](https://opencolorio.org/) to do the color space conversions. [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) is an excellent open-source tool for this.

## Encoding Overview

Creating movies for review, should be a simple process where the movie file accurately represents the source media content, so that you can feel confident that issues with the content are not as a result of creating the movie. Sadly, this is not the case, there are many steps that can create an incorrect result, either through a color shift, or encoding artifacts. This frequently means there isnt a single right answer for all cases, so we will attempt to document the different senarios where you could get tripped up. 

We will mostly be focusing on encoding with ffmpeg, however there will be some cases where we will recommend other tools. Splitting the process into two steps:
   1 Convert the source media to the target color space.
   2 Encode the target intermediate frames into the resulting movie.


## Acknoledgements 

This document is a result of feedback from many people, in particular I would like to thank Kevin Wheatley, Gates Roberg Clark, Rick Sayre, Wendy Heffner and J Schulte for their time and patence.

### Color space conversion.

The color space conversion we are assuming is being done using tools such as [Nuke][https://www.foundry.com/products/nuke-family/nuke] or [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) using [OCIO](https://opencolorio.org/). We strongly recommend using the ACES configuration whever possible, since it provides a good baseline for colorspace conversion. Note, we may mention the use of Nuke a number of times, there are now a large number of 3rd party tools that will also do great at this color space conversion.

Typically, we would assume that an intermediate file would get written out, such as PNG, TIF or DPX for processing in ffmpeg. NOTE, by default the nuke PNG writer will have the slow compression enabled, this does add a little time that is un-necessary for the sort of intermediate file we are using. In the nuke SDK they do provide the source for the PNG writer, so it is possible to get this disabled. However, you may find that switching to Tif will have the same result.




Links:
   * [NCLC Testing Overview](https://richardssam.github.io/ffmpeg-tests/compare.html) This is an overview of the NCLC Tag tests for web review.
   * [Comparing approaches to do the YUV conversion correctly](https://richardssam.github.io/ffmpeg-tests/tests/chip-chart-yuvconvert/compare.html) this shows the right way to do the yuv conversion, comparing the three different ways you can do it in ffmpeg.
   * [Comparing full-range vs. tv range](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-fulltv/compare.html) - reviews how you can get an extended range in your yuv conversion, including on web browsers.
   * [Comparing different outputs for -color_trc](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-osx/compare.html) - Showing what the -color_trc flag is doing, compared to embedding in mov and png.
   * [Comparing different outputs for the -colorprimaries](https://richardssam.github.io/ffmpeg-tests/gamuttests/iccgamut/compare.html) 


