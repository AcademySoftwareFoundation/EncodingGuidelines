# ASWF Encoding Test Framework
-*WORK IN PROGRESS*-

## Goals
Create a framework for easy testing and comparing of FFmpeg versions, video 
codecs and encoding parameters commonly used in the animation and VFX industry. </br>
Through the tests, find the settings best suited for preserving color and quality 
in media for review and deliverables.

## How
Run a set of tests on a selection of test media based on configuration file(s). </br> 
Each test produces new media files compared against source using VMAF and/or idiff.
The resulting media and statistics are stored as media references with metadata 
under clips gathered in an OTIO SerializableCollection.

From the resulting .otio file we can produce HTML reports or playback of media in 
media players either supporting OTIO or a playlist.

## What's been done so far
- [x] Create an initial application framework
- [x] Create SerializableCollection
- [x] Support image sequenced source media
- [x] Support video based source media
- [x] Create a clip per soource
- [x] Create baseline reference media
- [x] Create encoded media based on config file
- [x] Store encoded media as media references under clip
- [x] Compare encoded media with source
- [x] Serialize results in an .otio file
- [x] Create source config file based on video file
- [x] Create source config file based on image sequence
- [x] Choose VMAF model (HD vs 4K) based on res. (width nearest to 1920 or 4096)
- [ ] Create OTIO -> HTML adapter 
- [ ] Option to append new test into existing OTIO file
- [ ] Option to skip previously tested files
- [ ] ..

## Setup Test Environment

In addition to OpenTimelineIO the tests rely on FFmpeg with VMAF support and most
likely OpenImageIO.
The commands below are what's needed to build OTIO for python development. 
As of the time writing this the multi media-reference feature of OTIO is still in
the main branch of the project.
Also, we're relying on FFmpeg and OIIO being installed on the system. (Guides to come)

```
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install cmake pyseq

# Build OTIO
git clone https://github.com/AcademySoftwareFoundation/OpenTimelineIO.git
python -m pip install .

# Run tests (for now)
.venv/bin/python main.py
```

## Example Source config

INI style config describing where to find media and a few crucial bits of info
needed to encode it.
The filename must follow the convention `<source_filename>.source` and reside 
at the same level as the source file. In this case we're looking at an 
image sequence which must be contained in a folder.</br>

Example configuration file `Sintel-trailer-1080p-png.source`:

```
[[SOURCE_INFO]
input_args =
    -r 25
    -start_number 600
path = /home/daniel/Documents/dev/ffmpeg-tests/enctests/sources/Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%%04d.png
width = 1920
heigth = 1080
in = 600
duration = 25
rate = 25.0
```

## Example test config
Same INI style config.

```
[test_colorspace_rgb]

description = colorspace_rgb
suffix = .mov
encoding_args =
    -c:v libx264
    -preset slow
    -crf 18
    -x264-params "keyint=15:no-deblock=1"

```

## Metadata - results 

``` JSON
"metadata": {
    "aswf_enctests": {
        "test_colorspace_rgb": {
            "ffmpeg_version_5.0.1": {
                "encode_arguments": " -c:v libx264 -preset slow -crf 18 -x264-params \"keyint=15:no-deblock=1\"",
                "encode_time": 65.0579,
                "filesize": "28.6MiB",
                "results": {
                    "psnr": {
                        "harmonic_mean": 49.732509,
                        "max": 53.299791,
                        "mean": 49.769349,
                        "min": 47.985198
                    },
                    "vmaf": {
                        "harmonic_mean": 98.237394,
                        "max": 100.0,
                        "mean": 98.245602,
                        "min": 96.345517
                    }
                }
            }
        }
    }
}
``` 
