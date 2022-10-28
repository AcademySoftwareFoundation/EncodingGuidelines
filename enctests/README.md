# ASWF Encoding Test Framework
-*WORK IN PROGRESS*-

## Goals
Create a framework for testing and comparing encoded media through various encoders 
making sure color and quality is preserved.

## Requirements
* FFmpeg with VMAF enabled
* OpenTimelineIO (0.15+ currently only in main) 

## Usage

```commandline
usage: main.py [-h] [--source-folder SOURCE_FOLDER] [--test-config-dir TEST_CONFIG_DIR] [--prep-sources] [--encoded-folder ENCODED_FOLDER] [--output OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  --sources SOURCES [SOURCES ...]
                        Provide a list of paths to sources in stead of running all from source folder. Please note this overrides the --source-folder argument.
  --source-folder SOURCE_FOLDER
                        Where to look for source media files
  --test-config-dir TEST_CONFIG_DIR
                        Where to look for *.yml files containing test descriptions
  --test-config TEST_CONFIG_FILE
                        Specify a single test config file to run
  --prep-sources        Create *.yml files from media in --source-folder used as sources in encoding tests
  --encoded-folder ENCODED_FOLDER
                        Where to store the encoded files
  --output OUTPUT       Path to results file including ".otio" extenstion (default: ./encoding-test-results.otio)
```

### Prepare your sources
Start by prepping your source files. This is done with the `--prep-sources` flag. 
</br>A set of "sourcefile.ext.yml" files get created alongside the source media.
This is done, so you can adjust the desired in point and duration of the media
before running your tests. In-point and duration are set in frames.

``` commandline
# Prep sources 
python -m testframework.main --prep-sources --source-folder /path/to/source_media/
```

#### Example source file
sintel_trailer_2k_%04d.png.yml
```yaml
images: true
path: /path/to/sources/Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%04d.png
width: 1920
height: 1080
in: 600
duration: 25
rate: 25.0
```

### Prepare your test files
A set of default tests are provided for you in the "test_configs" folder.
The test files are yaml based and require a couple of keys and values to work. 
By default, the tests are geared towards encoding with FFmpeg, but you may write 
your own encoder classes and test files geared towards that encoder.
You may provide several tests in the same file separated by "---" so yaml reads 
them as separate documents.

#### Example test configuration
```yaml
---
test_colorspace_yuv420p:
    name: test_colorspace_yuv420p
    description: variations of colorspace yuv420p
    app: ffmpeg
    suffix: .mov
    encoding_template: 'ffmpeg {input_args} -i "{source}" -vframes {duration} {encoding_args} -y "{outfile}"'
    wedges:
        slow_crf_23: &base_args
            -c:v: libx264
            -preset: slow
            -crf: 23
            -x264-params: '"keyint=15:no-deblock=1"'
            -pix_fmt: yuv420p
            -sws_flags: spline+accurate_rnd+full_chroma_int
            -vf: '"scale=in_range=full:in_color_matrix=bt709:out_range=tv:out_color_matrix=bt709"'
            -color_range: 1
            -colorspace: 1
            -color_primaries: 1
            -color_trc: 2

        slower_crf_18:
            << : *base_args
            -preset: slower
            -crf: 18

        slower_crf_18_film:
            << : *base_args
            -preset: slower
            -crf: 18
            -tune: film

        slow_full_range:
            << : *base_args
            -crf: 18
            -vf: '"scale=in_range=full:in_color_matrix=bt709:out_range=full:out_color_matrix=bt709"'
            -color_range: 2
            -color_trc: 1
---
```

#### Additional options in the test config
You may provide a list of sources in a test config. Please note that this will 
override the behavior of the `--source-folder` argument. Only the sources 
provided in the test config will be used in the tests.

Example:
```yaml
---
test_colorspace_yuv420p:
    name: test_colorspace_yuv420p
    description: variations of colorspace yuv420p
    app: ffmpeg
    suffix: .mov
    encoding_template: 'ffmpeg {input_args} -i "{source}" -vframes {duration} {encoding_args} -y "{outfile}"'
    sources:
      - sources/Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%04d.png.yml
    wedges:
        slow_crf_23: &base_args
            -c:v: libx264
            -preset: slow
            -crf: 23
```

### Run the tests
To run the default tests, simply run the app like below

```commandline
python -m testframework.main --source-folder /path/to/sources/ --encoded-folder /path/to/save/the/encoded/files/
```

### Results
The results are stored in an "*.otio" file. Each source clip contains a media reference 
for its source plus all additional encoded test files. 
Each test is compared against the source with VMAF and the score is stored in 
the media reference's metadata.

## Setup Test Environment
**Please note! We're working on dockerizing this**

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
pip install cmake pyseq OpenTimelineIO PyYAML meson kaleido plotly pandas jinja2

# Run tests (for now)
.venv/bin/python main.py
```

## How to add an encoder
This is still **work in progress** so for now you'll have to add an encoder class
to a file in the "encoders" folder.
Since every encoder has its own set of arguments, a new encoder also requires 
its own test configs.

* Create a subclass of the `ABCTestEncoder` found in "encoders/base.py".
  * Implement the required methods to make your encoder work.
  * Make sure you add new media references to a dictionary for each wedge
    * Use `create_media_reference(out_file, self.source_clip)` from utils
  * Make sure you store the test parameters in metadata under a test name based on "\<testname\>-\<wedgename\>"
    * Use `get_test_metadata_dict(otio_clip, testname)` from utils 
* Register your new class in the `encoder_factory` function found in "encoders/\_\_init\_\_.py" (for now)
  * The key in the `encoder_map` dictionary needs to match the "app" value in the test configuration file
* Create a test configuration file
  * Required keys: 
    * "name" - name of test
    * "app" - name of application used in mapping mentioned above
    * "wedges" - containing list of wedges (which are named freely)
  * Just make sure you add the key/values you need in your class
