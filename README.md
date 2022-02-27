This contains a variety of test suites to help pick encoding profiles suitable for VFX/Animation media reviews.

This is being done as part of the [ASWF Media Review working-group](https://wiki.aswf.io/display/PRWG/Playback+And+Review+Working+Group).

The main page for this for now is [here](https://wiki.aswf.io/pages/viewpage.action?pageId=16031068)

1. [Encoding Cheat Sheet](#Encoding-Cheat-sheet)
2. [Encoding Overview](#Encoding-Overview)
3. [Acknowledgements](#Acknowledgements)
4. [Color space conversion](#Color-space-conversion)

## Encoding Cheat sheet

If you are encoding from an image sequence (e.g. imagefile.0000.png imagefile.0001.png ...) to h264 using ffmpeg, we recommend:
```
ffmpeg -r 24 -start_number 1 -i inputfile.%04d.png -vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" -vframes 100 -c:v libx264 -preset slower -pix_fmt yuv420p -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 13 outputfile.mp4
```

Where:
* **-r 24** means 24 fps
* **-start_number** means the frame sequence starts from frame 1 (defaults to 0)
* **-i inputfile.%04d.png** means the file sequence will be padded to 4 digits, i.e. 0000, 0001, 0002, etc.
* **-vframes 100** This is optional, but allows you to specify how many frames to encode, otherwise it will encode the entire frame range.
 *   **-vf "scale=in_color_matrix=bt709:out_color_matrix=bt709"** means use the sw-scale filter, setting:
    * **in_color_matrix=rec709** means color space bt709 video coming in (normal for TV/Desktop video).
    * **out_color_matrix=rec709** means color space bt709 video going out. The combination of this and in_color_matrix will mean the color encoding will match the source media. If you are only adding one set of flags, this is the one, otherwise it will default to an output colorspace of bt601, which is a standard definition spec from the last century, and not suitable for sRGB or HD displays.
* **-c:v libx264** means use the h264 encoding library (libx264)
* **-preset slower** a reasonably high quality preset, which will run slow, but not terribly slow.
* **-pix_fmt yuv420p** use yuv420 video format, which is typical for web playback. If you want a better quality for RV or other desktop tools use -pix_fmt yuv444p10le 
 * **-color_range 1** - mp4 metadata - specifying color range as 16-235 (which is default for web playback).
 * **-colorspace 1** - mp4 metadata - specifying rec709 yuv color pixel format 
 * **-color_primaries 1** - mp4 metadata - rec709 color gamut primaries
 * **-color_trc 13** -- mp4 metadata color transfer = sRGB - See tests below.

The crucial part is:
```
-vf "scale=in_color_matrix=bt709:out_color_matrix=bt709" 
```
Which is specifying the input and output colorspaces to be bt709.

Separately, if you are converting from exr's in other colorspaces, please use [OCIO](https://opencolorio.org/) to do the color space conversions. [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) is an excellent open-source tool for this.

## Encoding Overview <a name="Encoding-Overview"></a>

Creating movies for review should be a simple process where the movie file accurately represents the source media content, so that you can feel confident that issues with the content are not as a result of creating the movie. Sadly, this is not the case, there are many steps that can create an incorrect result, either through a color shift, or encoding artifacts. This frequently means there isn't a single right answer for all cases, so we will attempt to document the different scenarios where you could get tripped up. 

We will mostly be focusing on encoding with ffmpeg, however there will be some cases where we will recommend other tools. Splitting the process into two steps:
1. Convert the source media to the target color space.
2. Encode the target intermediate frames into the resulting movie.


## Acknowledgements  <a name="Acknowledgements"></a>

This document is a result of feedback from many people, in particular I would like to thank Kevin Wheatley, Gates Roberg Clark, Rick Sayre, Wendy Heffner and J Schulte for their time and patience.  

### Color space conversion.  <a name="Color-space-conversion"></a>

The color space conversion we are assuming is being done using tools such as [Nuke](https://www.foundry.com/products/nuke-family/nuke) or [oiiotool](https://openimageio.readthedocs.io/en/latest/oiiotool.html) using [OCIO](https://opencolorio.org/). We strongly recommend using the ACES configuration whenever possible, since it provides a good baseline for colorspace conversion. Note, we may mention the use of Nuke a number of times, there are now a large number of 3rd party tools that will also do great at this color space conversion using OCIO.

Typically, we would assume that an intermediate file would get written out, such as PNG, TIF or DPX for processing in ffmpeg. NOTE, by default the nuke PNG writer will have the slow compression enabled, this does add a little time that is unnecessary for the sort of intermediate file we are using. In the nuke SDK they do provide the source for the PNG writer, so it is possible to get this disabled. However, you may find that switching to Tif will have the same result.


### Media Encoding with ffmpeg

We will break the encoding process into three parts:
1. The RGB to YCrCb conversion.
2. The encoding process itself.
3. Metadata tagging.

#### RGB to YCrCb Conversion
This is the area you are most likely to get wrong. By default 
As a rule of thumb, we would like ffmpeg to do as little as possible in terms of color space conversion. i.e. what comes in goes out. The problem is that most of the codecs are doing some sort of RGB to YUV conversion (technically YCrCb). The notable exception is x264rgb (see below). 

The main problem is that ffmpeg by default assumes that any unknown still image format has a color space of[rec601](https://en.wikipedia.org/wiki/Rec._601) which is very unlikely to be the color space your source media was generate in. So unless you tell it otherwise it will attempt to convert from that colorspace producing a color shift.

Separately, all the video formats typically do not use the full numeric range but instead the R', B', G' and Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantisation artifacts for 8-bit encoding (the standard for web playback). This fortunately is something you can change, see TV vs. Full range. below. The other option is to use higher bit depth, e.g. 10-bit or 12 bit for formats such as ProRes (see later).

For more information, see: https://trac.ffmpeg.org/wiki/colorspace 

TODO -- Review the SWS_Flags.


For examples comparing these see: [here](https://richardssam.github.io/ffmpeg-tests/tests/chip-chart-yuvconvert/compare.html)

##### colormatrix filter
```
-vf "colormatrix=bt470bg:bt709"
```
This is the most basic colorspace filtering. bt470bg is essentially part of the bt601 spec.  See: https://www.ffmpeg.org/ffmpeg-filters.html#colormatrix
e.g.
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png -sws_flags spline+accurate_rnd+full_chroma_int -vf "colormatrix=bt470bg:bt709" -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 ./chip-chart-yuvconvert/spline444colormatrix2.mp4
```
##### colorspace filter
```
 -vf "colorspace=bt709:iall=bt601-6-625:fast=1"
 ```
Using colorspace filter, better quality filter, SIMD so faster too, can support 10-bit too.  The second part -vf "colorspace=bt709:iall=bt601-6-625:fast=1" encodes for the output being bt709, rather than the default bt601 matrix. iall=bt601-6-625 says to treat all the input (colorspace, primaries and transfer function) with the bt601-6-625 label). fast=1 skips gamma/primary conversion in a mathematically correct way.  See:  https://ffmpeg.org/ffmpeg-filters.html#colorspace
e.g.
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png -sws_flags spline+accurate_rnd+full_chroma_int -vf "colorspace=bt709:iall=bt601-6-625:fast=1" -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 ./chip-chart-yuvconvert/spline444colorspace.mp4
```
##### libswscale filter
```
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"
```
Using the libswscale library. Seems similar to colorspace, but with image resizing, and levels built in.  https://www.ffmpeg.org/ffmpeg-filters.html#scale-1

This is the recommended filter.
e.g.
```
ffmpeg -y -i ../sourceimages/chip-chart-1080-noicc.png -sws_flags spline+accurate_rnd+full_chroma_int+full_chroma_inp -vf "scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709" -c:v libx264 -preset placebo -qp 0 -x264-params "keyint=15:no-deblock=1" -pix_fmt yuv444p10le -qscale:v 1 -color_range 1 -colorspace 1 -color_primaries 1 -color_trc 1 ./chip-chart-yuvconvert/spline444out_color_matrix.mp4
```

#### TV vs. Full range.
All the video formats typically do not use the full numeric range but instead the R', B', G' and Y' (luminance) channel have a nominal range of [16..235]  and the CB and CR channels have a nominal range of [16..240] with 128 as the neutral value. This frequently results in quantisation artifacts for 8-bit encoding (the standard for web playback).

TODO Get Quantization examples.

You can force the encoding to be full range using the libswscale library by using 
```
-vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709"
```
Specifying "out_range=full" forces the output range, but you also need to set the NCLX tag:
```
-color_range 2
```
A full example encode would look like:
```
ffmpeg -y -loop 1 -i ../sourceimages/radialgrad.png -sws_flags spline+accurate_rnd+full_chroma_int -vf "scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709" -c:v libx264 -t 5 -pix_fmt yuv420p -qscale:v 1 -color_range 2 -colorspace 1 -color_primaries 1 -color_trc 13 ./greyramp-fulltv/radialgrad-full.mp4
```
We have seen the full range encoding work across all browsers, and a number of players including RV.
TODO: Do additional testing across all players.

For a detailed breakdown of options see:[Comparing full-range vs. tv range](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-fulltv/compare.html) 

#### Encoding as RGB.
You do not *have* to encode into YCrCb, h264 does support RGB encoding, which may be preferable in some situations.

Using the encoder:
```
-c:v libx264rgb 
```
Will skip the conversion completely. Sadly this has no support in web browsers, but is supported by some players (e.g. RV). It is also limited to 8-bit.
TODO Check about 10-bit encoding.

### Encoding
We are mainly going to focus on h264 for now, however we hope to expand this in the future.
NOTE, We do not have any test suites for encoding a this time. This is an area for future development.

A good starting point for encoding options is here: https://trac.ffmpeg.org/wiki/Encode/VFX
#### H264
Key flags (see https://trac.ffmpeg.org/wiki/Encode/H.264 ) 

* **-crf 23** - This is the constant rate factor, controlling the default quality (see: https://slhck.info/video/2017/02/24/crf-guide.html ) where -crf 0 is uncompressed. By default this is set to 23, which is a little on the low side, using values closer to 11 is recommended, but this does come at the expense of file-size..
* **-qp 23** - Quantization Parameter - it is recommended that you do not use this, in preference to -crf above (see: https://slhck.info/video/2017/03/01/rate-control.html )
* **-preset slower** - https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ
* **-tune film** - Optionally use the tune option to change settings based on specific inputs - https://trac.ffmpeg.org/wiki/Encode/H.264#FAQ - see also: https://superuser.com/questions/564402/explanation-of-x264-tune I suspect that we would want to use one of:
    * **-tune film**    good for live action content.
    * **-tune animation** good for animated content with areas of flat colors.
    * **-tune grain**   good for live action content where you want to preserve the grain as much as possible.
* **-qscale:v 9** - Generic quality scale flag: https://www.ffmpeg.org/ffmpeg.html#toc-Main-options - TODO experiment with this.

An example would be: 
```
-preset slower -crf 11  -profile:v high -tune film
```
#### ProRes
There are four Prores encoders, Prores, Prores_ks, Prores_aw and now with ffmpeg 5 VideoToolBox Prores, which is a hardware based OSX M1 encoder/decoder. 

From https://trac.ffmpeg.org/wiki/Encode/VFX the recommendation is to use Prores_ks with -profile:v 3 and the qscale of 11

Options that can be used include:

-profile:v values can be one of.
* proxy (0)
* lt (1)
* standard (2)
* hq (3)
* 4444 (4)
* 4444xq (5)

-qscale:v between values of 9 - 13 give a good result, 0 being best.
-vendor apl0 - tricks the codec into believing its from an Apple codec.

Using this with the usual color space flags, seems to work well with the exception of ffmpeg itself, which needs the flags:-vf scale=in_color_matrix=bt709:out_color_matrix=bt709 added to the command to ensure the right input colorspace is recognised, e.g.:

ffmpeg.exe -i INPUTFILE.mov -compression_level 10 -pred mixed -pix_fmt rgba64be -sws_flags spline+accurate_rnd+full_chroma_int -vframes 1 -vf scale=in_color_matrix=bt709:out_color_matrix=bt709 OUTPUTFILE.png


However, other encoders seem to be recognised correctly, so there is clearly some metadata missing. I did try using the prores_metadata filter to try adding some additional parameters, but it didnt seem to help.
```
ffmpeg.exe -i ./chip-chart-yuvconvert\basicnclc.mov -c copy -bsf:v prores_metadata=color_primaries=bt709:color_trc=bt709:colorspace=bt709 chip-chart-yuvconvert\basicnclcmetadata.mov
```

TODO:
* Figure out the missing metadata.
* Wedge qscale values
* Do some colorspace tests with different qscale values to see where color breaks down.
* VMAF

### Metadata NCLC/NCLX
There are a number of metadata flags designed to help the player know what colorspace the media is in, so it can correctly interpret it for playback. We do recommend adding the metadata tags to media, particularly if you are reviewing it on a web browser, however there are a lot of gotchas here, please see the section on [Web Review](#review).

The NCLC/NCLX is defined as a ISO spec here (see https://www.iso.org/standard/73412.html). The numbers below are part of the definition. NCLC stands for Non-Consistent Luminance Coding, a brief overview of its history is here. For MP4 files, its also known as NCLX. Additionally this metadata can also be represented in the h264 metadata stream in the video usability Information (VUI) block. 

You can read the metadata using mp4box.js which is a visual browser of the mp4 metadata, and look at moov/trak/mdia/minf/stbl/stsd/avc1/colr

NOTE: None of the flags below affect the encoding of the source imagery, they are meant to be used to guide how the mp4 file is decoded.

The docs are pretty sparse for this, some of the better info is [FFmpeg/pixfmt.h at master](https://github.com/FFmpeg/FFmpeg/blob/master/libavutil/pixfmt.h)

#### Color Range

### Web Review
See:
     * [NCLC Testing Overview](https://richardssam.github.io/ffmpeg-tests/compare.html) This is an overview of the NCLC Tag tests for web review.
     * [Comparing different outputs for -color_trc](https://richardssam.github.io/ffmpeg-tests/tests/greyramp-osx/compare.html) - Showing what the -color_trc flag is doing, compared to embedding in mov and png.
     * [Comparing different outputs for the -colorprimaries](https://richardssam.github.io/ffmpeg-tests/gamuttests/iccgamut/compare.html) 

