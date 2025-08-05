---
layout: default
title: Adding Metadata
nav_order: 7
parent: Encoding Overview
---

# Adding Metadata

The more metadata we can store with the movie files, the better, there is nothing worse than losing a sidecar file that contains critical information. If the reviewer is loading the original file, then it should be easy with OpenRV to view the associated metadata.

OpenRV was modified to show any arbitrary metadata in movie files see PR - https://github.com/AcademySoftwareFoundation/OpenRV/pull/504

We cover how to add metadata to
   * [MXF](#mxf)
   * [MKV](#mkv)
   * [MP4/MOV](#mp4mov)

We also suggest a list of [common metadata attributes](#common-metadata-values-for-vfx) that would be useful in VFX movie containers.

Its also worth looking at [Editorial Workflow](EditorialWorkflow.html) for information about adding timecode, which can help with frame numbers.


## Querying metadata with ffprobe

```
ffprobe -v quiet -print_format json -show_format -show_streams \
        chimera_cars_srgb-test_mov-mjpeg_metadata.mxf
```

## Adding Metadata to movie files

Depending on the movie file, there are a variety of mechanisms for embedding key-value metadata into movie files. 

### MKV

Mkv is the most flexible for adding arbitrary key-value strings to the file, all values are preserved and viewable by openrv.

```
ffmpeg -i input.mp4 -metadata my_custom_key="my value" -c copy output.mkv
```

### MXF

ffmpeg can add some custom metadata to MXF files, but with important limitations:

* Standard metadata fields (like material_package_name) can be set and will persist in the output MXF file.  
* Arbitrary custom metadata fields (such as project, artist, etc.) specified with -metadata key=value will not generally be written into the MXF file in a way that survives a subsequent ffprobe or ffmpeg read—except for a specific workaround.  
* Workaround: If you use the comment_ prefix for your custom metadata keys (e.g., -metadata comment_project="TEST PROJECT"), ffmpeg will write these as user comments in the MXF file. This method requires at least ffmpeg 4.2 and works for the mxf and mxf_opatom formats, but not for mxf_d10[1](https://stackoverflow.com/questions/69185798/how-can-i-add-custom-metadata-to-an-mxf-using-ffmpeg)10\.

Other metadata strings used include:

* company_name  
* product_name  
* product_version

Example Command

```
ffmpeg -i input.mp4 -metadata comment_project\="Test Project" -metadata comment_artist\="Artist" 
            -metadata material_package_name\="Test Clip" -f mxf output.mxf
```

### MP4/mov

By default, MP4 and MOV only support a limited set of standard metadata fields:

* title  
* artist  
* album  
* genre  
* year  
* comment  
* copyright  
* encoder  
* track  
* album_artist  
* composer  
* description  
* creation_time  
* publisher

To add arbitrary/custom metadata keys, use the -movflags use_metadata_tags option. This writes your custom fields into the mdta atom, which ffmpeg and ffprobe and openrv can read, but most standard players (like QuickTime) will ignore these fields.

```
ffmpeg -i input.mp4 -movflags use_metadata_tags \
    -metadata my_custom_key="my value" -c copy output.mp4
```

You can also use this flag to transcode media and keep the metadata:
```
ffmpeg -i input.mp4 -movflags use_metadata_tags -crf 22 output.mp4
```

## Common metadata values for VFX

Below are suggestions for common metadata fields:


| first_frame, last_frame | int | Encoding to movie files typically loses the start frame, making it a pain to identify which frame you are looking at. We could look at doing this with timecode, but sometimes you want both timecode and a frame number. |  |
| :---- | :---- | :---- | :---- |
| source_filename | string | Something to track where the encoded media came from. |  |
| source_id | string | Unique ID from vendor creating content. - This could be using: [https://proto.school/content-addressing/04](https://proto.school/content-addressing/04) |  |
| source_frame_rate | float | If you are reviewing a proxy, but still want to remap back to the source frame, knowing the source frame rate is required (DO WE NEED THIS AND LAST FRAME?) – useful for high-frame rate media, e.g. 120 fps - (MIGHT MAKE SENSE AS A STRING TO HANDLE 59.94 better?) |  |
| image_active_area | xMin, yMin, xMax, yMax | The bounding box of the picture location within the image. This is used in cases where the image is a re-processed version of the source frame, e..g. where a 2.35 aspect ratio picture has been padded to HD (perhaps time-code is burnt in, etc), this would allow any annotations to be always defined relative to the source frames, so would be able to be correctly overlayed on top. |  |
| watermarking | String | Document what sort of watermarking has been applied? - invisible, burnin? |  |
| slate_length | Int | Duration of slate length (0 if no slate). |  |
| display_type | Enum | Stereo left/right Stereo top/bottom  Long/Lat VR mono Long/Lat VR Stereo top/bottom NOTE: This should be based on existing standards, e.g. [https://github.com/google/spatial-media/tree/master/spatialmedia](https://github.com/google/spatial-media/tree/master/spatialmedia) |  |
| task | string | Taskname if known. |  |
| date_authored | string | The latest date of the original authored content. This would be carried through any transcoding, so we dont end up with the transcoded timestamps. |  |
| aswf_color_space | string | Many file-formats do already have options for color spaces, but certainly for internal reviews facilities may decide to encode to a non-standard color space. For media that is crossing facilities we should stick to known embedded colorspaces, and allow existing tools to remap where necessary. - TBD - Color interop. |  |

THis was originally defined [here](https://lf-aswf.atlassian.net/wiki/spaces/PRWG/pages/11274595/Playback+and+Review+Standards)