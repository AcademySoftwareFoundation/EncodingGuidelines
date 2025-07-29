---
layout: default
title: ORI Encoding Test Framework
nav_order: 7
has_children: true
---

# ORI Encoding Test Framework
-*WORK IN PROGRESS*-

## Goals
Create a framework for testing and comparing encoded media through various encoders
making sure color and quality is preserved.

## Requirements
* FFmpeg with VMAF enabled
* OpenTimelineIO (>=0.15)

## Description

The test suite takes advantage of the excellent [VMAF](https://github.com/Netflix/vmaf) perceptual video quality assessment algorithm developed by Netflix. We use a ffmpeg plugin version of this library to compare the original media to the encoded media. This algorithm combines human vision modeling with machine learning to give you a encoding quality metric. At the same time it also generates [PSNR](https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio) and [SSIM](https://en.wikipedia.org/wiki/Structural_similarity) comparison results, so depending on the test you are doing you may end up wanting to look at the other factors.

You can use your own test data, but we also provide scripts for downloading some [reference media](sources/enc_sources/README.html).

## Usage

```
usage: main.py [-h] [--source-folder SOURCE_FOLDER] [--test-config-dir TEST_CONFIG_DIR] [--prep-sources] [--encoded-folder ENCODED_FOLDER] [--output OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  --sources SOURCES [SOURCES ...]
                        Provide a list of paths to sources instead of running all from source folder. Please note this overrides the --source-folder argument.
  --source-folder SOURCE_FOLDER
                        Where to look for source media files
  --test-config-dir TEST_CONFIG_DIR
                        Where to look for *.yml files containing test descriptions
  --test-config TEST_CONFIG_FILE
                        Specify a single test config file to run
  --prep-sources        Create *.yml files from media in --source-folder used as sources in encoding tests
  --encoded-folder ENCODED_FOLDER
                        Where to store the encoded files
  --output OUTPUT       Path to results file including ".otio" extension (default: ./encoding-test-results.otio)
```

### Prepare your sources
Start by prepping your source files. This is done with the `--prep-sources` flag.
A set of "sourcefile.ext.yml" files get created alongside the source media.
This is done, so you can adjust the desired in point and duration of the media
before running your tests. In-point and duration are set in frames.

```
# Prep sources 
python -m testframework.main --prep-sources --source-folder /path/to/source_media/
```

#### Example source file
sintel_trailer_2k_%04d.png.yml
```yaml
images: true
path: sintel_trailer_2k_%04d.png
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

```console
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
# Note pyseq now needs rust (so for msys2 you need pacman -S )
pip install pyseq OpenTimelineIO PyYAML meson kaleido plotly pandas jinja2 yuvio

# Run tests (for now)
.venv/bin/python main.py
```

## Native Windows Configuration

Have tried using MSYS2 - [msys2](https://www.msys2.org/) once that is installed you can install ffmpeg and openimageio with:
```
pacman -S mingw-w64-x86_64-openimageio 
pacman -S mingw-w64-x86_64-ffmpeg 
```
But had problems getting OTIO working. The build environment doesnt like the windows/ming64x environment.

So have instead used [VCPKG](https://github.com/microsoft/vcpkg):
```
vcpkg install openimageio[tools]:x64-windows ffmpeg[ffmpeg]:x64-windows
```
And then used the above virtual environment.
You will need to add the paths to the above tools to your path, which would be:
%VCPKGHOME%\installed\x64-windows\tools\ffmpeg;%VCPKGHOME%\installed\x64-windows\tools\openimageio;
which you can do in the .venv/Scripts/activate.bat file.

This does not get you the vmaf model though which can be downloaded 
https://raw.githubusercontent.com/Netflix/vmaf/master/model/vmaf_v0.6.1.json
Also you need to install an earlier version of kaleido since the current one will hang when generating an image.
```
pip install kaleido==0.1.0post1 
```

## OSX Configuration

```console
brew install openimageio ffmpeg

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip3 install --upgrade pip
pip3 install six testresources recommonmark sphinx-press-theme sphinx-tabs breathe pyseq 
pip3 install awscli pillow PyYAML meson kaleido plotly pandas jinja2 OpenTimelineIO

mkdir aces
cd aces
curl -sLO https://github.com/colour-science/OpenColorIO-Configs/archive/refs/tags/v1.2.tar.gz && \
tar zxvf v1.2.tar.gz OpenColorIO-Configs-1.2/aces_1.2 && \
rm v1.2.tar.gz
export OCIO=$PWD/OpenColorIO-Configs-1.2/aces_1.2/config.ocio
        
# Set VMAF_Models NOTE, should probably change this.
export VMAF_MODEL_DIR=/opt/homebrew/Cellar/libvmaf/3.0.0/share/libvmaf/model/

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


## Report Generation

Reports can be generated by adding a report section to the .yml file, e.g.:

```yaml
---

reports:
    graphs:
    - args:
        color: -preset
        height: 400
        barmode: group
        x: media
        y: vmaf_harmonic_mean
        range_y:  
            - 90
            - 100
      name: vmaf_harmonic_mean.png
      type: bar
    - args:
        color: -preset
        height: 400
        x: media
        barmode: group
        y: encode_time
      name: encode_time.png
      type: bar
    - args:
        color: -preset
        height: 400
        x: media
        barmode: group
        y: filesize
      name: filesize.png
      type: bar
    name: h264-test
    title: H264 Preset Comparison
    description: This is a comparison of different Preset values for h264 encoding, with CRF = 18.
    directory: h264-encode
    templatefile: basic.html.jinja
```

The configuration uses html [jinja](https://palletsprojects.com/p/jinja/) templates defined in the templates folder. The template combines the parameters from each wedge test with the results of the test, grouped by image name.

The graphs are generated using the [plotly.express](https://plotly.com/python-api-reference/generated/plotly.express.html#module-plotly.express) library. The parameters in the yaml file are fed directly into the constructor for the graph creation. Currently we are only supporting line graphs and bar graphs, but other graph types should be easy to add.

Currently there are two templates:
   * basic.html.jinja - which assumes you want three graphs representing encode_time, file-size and encode-quality, along with showing the VMAF parameters from the OTIO file.
   * doctests.html.jinja - which assumes no graphs are needed. This is primarily using the output of the test suite for the docs (see later).

### Graphing strings
The above example is a fairly straightforward line graph, suitable where you are comparing numeric values to file-size, encode-time and encode-quality. To compare strings we recommend using bar-graphs, e.g.:
```yaml
reports:
    graphs:
    - args:
        color: -preset
        height: 400
        barmode: group
        x: media
        y: vmaf_harmonic_mean
        range_y:  
            - 90
            - 100
      name: vmaf_harmonic_mean.png
      type: bar
    - args:
        color: -preset
        height: 400
        x: media
        barmode: group
        y: encode_time
      name: encode_time.png
      type: bar
    - args:
        color: -preset
        height: 400
        x: media
        barmode: group
        y: filesize
      name: filesize.png
      type: bar
    name: h264-test
    title: H264 Preset Comparison
    description: This is a comparison of different Preset values for h264 encoding, with CRF = 18.
    directory: h264-encode
    templatefile: basic.html.jinja
```

This example creates bar-graphs based on the `-preset` flag.
