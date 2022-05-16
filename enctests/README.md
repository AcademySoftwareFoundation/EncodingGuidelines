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

## Setup Test Environment

In addition to OpenTimelineIO the tests rely on FFmpeg with VMAF support and most
likely OpenImageIO.
The commands below are what's needed to build OTIO for python development. 
As of the time writing this the multi media-reference feature of OTIO is still in
the main branch of the project.
Also we're relying on FFmpeg and OIIO being installed on the system. (Guides to come)

```
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install cmake pyseq

# Build OTIO
git clone git@github.com:PixarAnimationStudios/OpenTimelineIO.git
python -m pip install OpenTimelineIO
```

## What's been done so far
- [x] Create an initial application framework
- [x] Create SerializableCollection
- [x] Support image sequenced source media
- [ ] Support video based source media
- [x] Create a clip per soource
- [x] Create baseline reference media
- [x] Create encoded media based on config file
- [x] Store encoded media as media references under clip
- [ ] Compare encoded media with source
- [x] Serialize results in an .otio file


## Ideas

* Store sample files as OTIO `Clip`
  * Raw source as DEFAULT `MediaReference`
  * Wedges stored as alternative `MediaReferences`
    * All media refs contain metadata with:
      ``` JSON
      {
          "aswf": {
              "FFMpeg4.4.1": {
                  "encoding_parameters": {},
                  "encoding_time": 114.4,
                  "filesize": 1234,
                  "VMAF_score" 99.1,
                  "idiff_score": 1.
              }
          }
      }
      ``` 
* Store Clips in a `SerializableCollection`

