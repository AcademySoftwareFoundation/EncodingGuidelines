# Encoding Test Framework

Setup encoding tests with wedges for all relevant parameters and store the 
results as clips in a serializable collection. 
The resulting otio file can then easily be distributed as an otioz containing 
the media files if desired.


# Ideas

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
* Media linker to execute the test and store the reference(?)
  * Based on a simple descriptive file (JSON?) perform test matrix

# Setup OTIO

Clone/submodule OpenTmelineIO and then:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install cmake pyseq
git clone git@github.com:PixarAnimationStudios/OpenTimelineIO.git
cd OpenTimelineIO
python -m pip install .
```
