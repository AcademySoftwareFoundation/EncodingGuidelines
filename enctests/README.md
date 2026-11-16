---
layout: default
title: ORI Encoding Test Framework
nav_order: 7
has_children: true
---

# ORI Encoding Test Framework

<details open markdown="block">
  <summary>
    Table of contents
  </summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

## Goals

Create a framework for testing and comparing encoded media through various encoders
making sure color and quality is preserved.

## Requirements

* Python 3.10 or later, with the packages in the repository's `requirements.txt` (OpenTimelineIO, OpenImageIO,
  pandas, plotly, ...); see [Setup Test Environment](#setup-test-environment).
* An FFmpeg build with `libvmaf` (and the VMAF model files) and `zscale` (zimg). To decode AV1 it also needs
  `libdav1d` or `libaom-av1`. Tests whose encoder is not in the build are skipped, not failed; see
  [Requirements: skipping tests](#requirements-skipping-tests-the-build-or-machine-cannot-run).
* Google Chrome, which `kaleido` uses to write the report graphs (or run `kaleido_get_chrome`).

## Description

The test suite takes advantage of the excellent [VMAF](https://github.com/Netflix/vmaf) perceptual video quality assessment algorithm developed by Netflix. We use a FFmpeg plugin version of this library to compare the original media to the encoded media. This algorithm combines human vision modeling with machine learning to give you a encoding quality metric. At the same time it also generates [PSNR](https://en.wikipedia.org/wiki/Peak_signal-to-noise_ratio) and [SSIM](https://en.wikipedia.org/wiki/Structural_similarity) comparison results, so depending on the test you are doing you may end up wanting to look at the other factors.

You can use your own test data, but we also provide scripts for downloading some [reference media](sources/enc_sources/README.html).

## Usage

```console
usage: main.py [-h] [--sources SOURCES [SOURCES ...]]
               [--source-folder SOURCE_FOLDER]
               [--test-config-dir TEST_CONFIG_DIR]
               [--test-config TEST_CONFIG_FILE] [--prep-sources] [--verbose]
               [--force] [--encoded-folder ENCODED_FOLDER]
               [--results-folder RESULTS_FOLDER] [--skip-reports]
               [--output OUTPUT]

options:
  -h, --help            show this help message and exit
  --sources SOURCES [SOURCES ...]
                        Provide a list of paths to sources in stead of running
                        all from source folder. Please note this overrides the
                        --source-folder argument.
  --source-folder SOURCE_FOLDER
                        Where to look for source media files
  --test-config-dir TEST_CONFIG_DIR
                        Where to look for *.yml files containing test
                        descriptions
  --test-config TEST_CONFIG_FILE
                        Specify a single test config file to run
  --prep-sources        Create *.yml files from media in --source-folder used
                        as sources in encoding tests
  --verbose             Be verbose in the progress.
  --force               Force generation of results.
  --encoded-folder ENCODED_FOLDER
                        Where to store the encoded files
  --results-folder RESULTS_FOLDER
                        Basepath for all the results, not used if --encoded-
                        folder is defined.
  --skip-reports        Skip any report generation (default: False).
  --output OUTPUT       Path to results file including ".otio" extension
                        (default: ./encoding-test-results.otio)
```

The defaults are `--source-folder ./sources`, `--test-config-dir ./test_configs` and `--results-folder ./results`,
so run it from the `enctests` folder. When `--output` is not given, each config writes its own `.otio` file in the
results folder (see [Results](#results)).

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
    encoding_template: 'ffmpeg {input_args} -i "{source}" -frames:v {duration} {encoding_args} -y "{outfile}"'
    wedges:
        slow_crf_23: &base_args
            -c:v: libx264
            -preset: slow
            -crf: 23
            -x264-params: '"keyint=15:no-deblock=1"'
            -pix_fmt: yuv420p
            -sws_flags: spline+accurate_rnd+full_chroma_int
            -vf: '"scale=out_color_matrix=bt709:out_range=tv"'
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
            -vf: '"scale=out_color_matrix=bt709:out_range=full"'
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
    encoding_template: 'ffmpeg {input_args} -i "{source}" -frames:v {duration} {encoding_args} -y "{outfile}"'
    sources:
      - sources/Sintel-trailer-1080p-png/1080p/sintel_trailer_2k_%04d.png.yml
    wedges:
        slow_crf_23: &base_args
            -c:v: libx264
            -preset: slow
            -crf: 23
```

#### Comparison tests

`comparisontest` lists the checks run on each encode, in order. If it is left out, `vmaf` is used. The other
types are `vmaf3`, `ffmpeg_psnr`, `identity`, `ycbcr`, `idiff`, `yuvdiff`, `frame_extract` and `assertresults`.

For color accuracy, use `ycbcr`. It decodes the first frame of the encode at the stream's own pixel format, so
FFmpeg does no color conversion, and compares it with the ideal conversion of the source RGB, worked out in
numpy (see `testframework/ycbcr_compare.py`). RGB encodes are compared with the source RGB directly. Unlike
`idiff`, it does not extract the encode to a PNG with `scale`, which added a second libswscale conversion, so it
can see libswscale's errors.

```yaml
comparisontest:
- testtype: ycbcr
  matrix: bt709   # bt709 (default), bt2020nc, bt470bg, smpte170m, or auto to use the stream's tag
  range: tv       # tv (default), pc, or auto to use the stream's tag
  chroma_siting: true  # false skips measuring 4:2:2/4:2:0 chroma siting (about a second per encode)
- testtype: assertresults
  tests:
  - assert: between
    value: white_error
    between: [-1.5, 1.5]
  - assert: less
    value: max_error
    less: 4
  - assert: stringmatch
    value: color_primaries
    string: bt709
```

A source that is not RGB (a JPEG, or a video file) cannot be the reference itself, so its `.yml` names the RGB
image it should decode to, relative to the `.yml`:

```yaml
path: chip-chart-1080-420.jpg
reference: chip-chart-1080-420-libjpeg.png
```

Its results are in code values at the encode's bit depth:

| Result | Meaning |
| :--- | :--- |
| `max_error`, `mean_error` (and `_y`, `_cb`, `_cr`, or `_g`, `_b`, `_r` per plane) | Worst and mean error more than 8 pixels (`margin`) from any edge, so 4:2:2/4:2:0 chroma filtering and siting do not count |
| `max_error_all` | Worst error anywhere |
| `p99_error` (and per plane) | 99th percentile error away from edges. For lossy codecs use this rather than `max_error`, which is a single pixel set by compression |
| `white_y`, `white_y_ideal`, `white_error` | Average Y' over the brightest areas, what it should be, and the difference. Compression noise averages out, so this shows a white level error (e.g. libswscale's +3 at 10-bit) that `max_error` cannot |
| `max_error_10bit`, `mean_error_10bit`, `p99_error_10bit`, `white_error_10bit` | The same, in 10-bit code values, so one threshold covers several bit depths |
| `color_range`, `color_space`, `color_primaries`, `color_transfer`, `chroma_location` | The stream's tags, from `ffprobe` |
| `colr` | The MOV/MP4 `colr` atom, e.g. `nclx 1/13/1 tv`, or `none` |
| `pixels_match` | The matrix and range the pixels match, whatever the tags say, e.g. `bt709 tv`. `?` where the source cannot tell (a grey source has no matrix), `none` if nothing is within 8 10-bit code values |
| `chroma_siting_measured`, `chroma_offset_h`, `chroma_offset_v` | For 4:2:2/4:2:0, where the chroma samples sit, measured from the pixels: a name as `ffprobe` uses (`left`, `center`, `topleft`, ...) and the offsets in luma samples, 0 co-sited, 0.5 centred. It fits a sub-sample shift between the decoded chroma and the ideal, both blurred, so it does not depend on the converter's filter. On `sourceimages/chroma_siting_chart.png` it agrees with `tests/chroma_siting.py` |
| `chroma_siting_assumed`, `chroma_shift_h`, `chroma_shift_v` | For an RGB result decoded from a 4:2:2/4:2:0 source whose `.yml` gives `chroma_siting:` (where its chroma really is), the siting the decoder assumed and how far that moved the chroma, in luma samples: 0 when it was right, +0.5 when it took co-sited chroma as centred. `source_chroma_location` is the source's tag. See `decode_siting_tests.yml` |

The encode also gets a viewable PNG (converted in numpy), an `-x20diff.png` error image (unsigned, not
used by the report templates) and an `-errormap.png`: the signed error of each plane side by side, in 10-bit code values,
orange/yellow too high and blue/cyan too low, full color at `error_map_limit` (default 4). Errors within one code
value of the encode (rounding) are dim, and edges left out of the comparison are grey. The results also hold
`error_by_level`, the mean signed error per plane against the ideal level, which shows a gain error as a slope and
an offset as a shift. The `ycbcr.html.jinja` report template shows both, with the white, max, mean and p99 errors
and the range tag for each wedge; see [Reading the Color Test Reports](ReadingColourReports.html). Each plane's
map is also written on its own (`-errormap-y.png`, `-errormap-cb.png`, ...), with a copy of the source
(`<source>-source.png`), for the report's viewer, which lays an error map over the decoded frame.

`assertresults` checks results from the earlier tests with `less`, `greater`, `between` (two values in a list),
`equal` or `stringmatch` (with `string:`).

#### Requirements: skipping tests the build or machine cannot run

A wedge whose `-c:v` encoder is not in the FFmpeg build is skipped, not failed. So is a hardware encoder
(`*_nvenc`, `*_videotoolbox`, `*_qsv`, `*_vaapi`, ...) that is built in but cannot encode one test frame, for
example `hevc_nvenc` without an NVIDIA GPU. A wedge is also skipped when the build cannot decode what its
encoder writes, as every comparison decodes the encode: an AV1 encoder needs `libdav1d` or `libaom-av1` in the
build, because FFmpeg's own `av1` decoder only works with hardware. This is checked by encoding and decoding one
trial frame; if the trial encode fails, the wedge runs, so a broken encoder is still reported as a failure.
Anything else a test needs goes in a `requires:` block, either on the
whole test or on one wedge (a wedge's requirements add to the test's):

```yaml
test_example:
  requires:
    filters: [zscale]
  wedges:
    lanczos+unstable:
      requires:
        ffmpeg: ">=8.1"           # a string, or a list that must all hold
      -vf: '"scale=out_color_matrix=bt709:out_range=tv:flags=unstable+lanczos"'
```

| Key | Needs |
| :--- | :--- |
| `ffmpeg` | A version range: `>=`, `>`, `<=`, `<`, `==`, `!=`, e.g. `[">=7.1", "<9.0"]`. `==9.0` matches any 9.0.x |
| `encoders`, `decoders`, `filters`, `hwaccels` | Names listed by `ffmpeg -encoders`, `-decoders`, `-filters`, `-hwaccels` |
| `hardware` | Encoders that must encode a test frame |
| `platform` | `sys.platform` values, e.g. `darwin`, `linux`, `win32` |

Git builds print no release number (`ffmpeg version N-124257-g73262c9136`). They are placed after the newest
release whose libavutil version they include, shown as e.g. `8.1+dev`: newer than any 8.1.x, older than 9.0.
For a feature that is only in development builds, use e.g. `>=9.0+dev`. The libavutil version of each release
is listed in `testframework/capabilities.py`; add new releases there.

A skipped wedge is not encoded or compared. Its result says what was missing, e.g.
`Skipped: needs encoder liboapv`, and the report index counts it under Skipped.

#### Changes between FFmpeg versions

The asserts check whether a result is right. To see what a new FFmpeg version changed, including what no assert
covers, each run also writes `changes.html` (and `changes.json`) in the results folder, linked from the index. It
lines up every test's results across the FFmpeg versions in the folder: the result (pass, fail, known, unexpected,
skipped), the stream tags (`color_range`, `color_space`, `color_primaries`, `color_transfer`, `chroma_location`,
`colr`), the pixel format, and the measured errors (`white`, `max`, `mean`, `p99`, identity and VMAF/PSNR scores).
A value that differs from the previous release is flagged as better (closer to the ideal), worse, or changed (a
tag or pixel format). Development builds are compared with the newest release.

As well as what the comparison measures, every encode records what FFmpeg wrote and how
(`testframework/stream_metadata.py`), so these changes are flagged too:

| Field | What it is |
| :--- | :--- |
| `pix_fmt`, `profile`, `color_*`, `chroma_location` | ffprobe's view of the stream. Some are decoder defaults when nothing is written. |
| `colr` | The MOV/MP4 `colr` atom, e.g. `nclx 1/1/1 tv`. |
| `bitstream_colour` | The color fields in the bitstream itself, read with `-bsf:v trace_headers` (H.264/HEVC VUI, AV1, VP9, APV, MPEG-2), as `primaries/transfer/matrix range`, e.g. `1/1/1 tv`. |
| `bitstream_chroma_loc` | The chroma location in the bitstream (H.264/HEVC, AV1), or `not written`. |
| `prores_header` | Primaries/transfer/matrix in the ProRes frame header, which the encoder writes separately from `colr`. |
| `container_chroma_siting` | The MKV `ChromaSitingHorz`/`Vert` elements, or the MXF descriptor's siting. |
| `auto_conversions` | Conversions FFmpeg inserted itself that change the color space or range, e.g. `rgb48be gbr pc -> yuv444p10le bt709 tv`, or `none`. |
| `encoder_library` | The encoder library's version as it logs it, e.g. `x265 3.6+1-aa7f602f7`. |
| `decoder` | The decoder FFmpeg picks for the file, with `(fails)` if it cannot decode it. |

`auto_conversions` comes from a verbose copy of the encode log, `<test>.report.log`, which each encode writes by
setting `FFREPORT`; the command and the ordinary `<test>.log` are unchanged. The `.otio` also records the build:
the `ffmpeg -version` line, its configure options and, for a dynamically linked build, the libraries it links.
`changes.html` lists these per version, as a change that comes with a different library (OpenAPV, SVT-AV1, x265
...) or a library missing from one build is not an FFmpeg change.

Only runs of the same config file contents are compared: each run records a hash of its config
(`config_sha256`) and the framework's git commit (`framework_commit`) in the `.otio`, so editing a config or its
asserts is not mistaken for an FFmpeg change. To compare versions, run the same configs on each, e.g.

```bash
for v in 6.1.6 7.1.5 8.0.1 9.0; do
  rez-env encodingguidelines_env ffmpeg-$v -- python -m testframework.main --test-config-dir ./test_configs --source-folder ./sources --force
done
```

To regenerate the page from existing results: `python -m testframework.utils.versionChanges results`.

#### Known issues: tracking problems across FFmpeg versions

A wedge that is known to fail on some versions has a `known_issue:` block, with the same `ffmpeg` and `platform`
keys as `requires:` (default: every version), and a note:

```yaml
    libswscale_12bit:
      -vf: '"scale=out_range=full"'
      known_issue:
        ffmpeg: "<8.0"
        note: "libswscale: white 4 low (10-bit code values), fixed in 8.0 by 384fe39623"
```

On an affected version, a failure is reported as `Known issue: <note>` and counted under Known issue in the
report index, not under Fail. A pass is reported as an unexpected pass, which usually means the issue has been
fixed upstream: check it, then narrow or remove the block. On other versions the wedge is an ordinary test, so
a failure there is a regression. `ycbcr_range_tests.yml` uses this to follow libswscale's range conversion.

A block can also name the sources it covers (`source:`, a glob or a list of them, matched against the source
name, e.g. `chip-chart*`), and `known_issue:` can be a list of blocks, for an issue that differs between versions
or sources. The first block that applies is used:

```yaml
      known_issue:
      - ffmpeg: ">=8.0"
        note: "libswscale RGB to full range: luma gain too high, white +2.8 (10-bit), since 384fe39623"
      - ffmpeg: "<8.0"
        source: "chip-chart*"
        note: "within 1 but biased from the 16-bit chip chart; exact from the 10-bit bars"
```

`color_tests.yml` gives every deliberately wrong method a block like this, so that on any version only a change
shows as a failure.

A wedge that merges another (`<< : *anchor`) also inherits its `known_issue:`; set `known_issue: []` in a wedge
that should not have it (see `cicp_flags_tests.yml`).

### Run the tests

From the `enctests` folder, with the virtual environment active:

```console
cd enctests
python -m testframework.main --test-config-dir ./test_configs --source-folder ./sources
```

This runs every `*.yml` config in `test_configs`. To run one config, use `--test-config`:

```console
python -m testframework.main --test-config test_configs/color_tests.yml
```

A config is skipped when its results `.otio` is newer than the config file, so a second run only re-runs configs
that have changed. After changing anything else (the FFmpeg build, the framework, a source), pass `--force`, or
nothing is re-encoded and only the index and change report are rewritten. `--skip-reports` leaves out the HTML
report for each config, and `--results-folder` writes the results somewhere other than `./results`, for example to
try a build without touching existing results.

With rez, `rez/encodingguidelines_env` provides the Python environment and FFmpeg is picked separately, so the same
tests can run against several FFmpeg versions:

```console
cd enctests
rez-env encodingguidelines_env ffmpeg-8.1 -- python -m testframework.main --test-config-dir ./test_configs --source-folder ./sources
```

#### Environment variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `FFMPEG_BIN` | `ffmpeg` (`ffmpeg.exe` on Windows) | The `ffmpeg` binary to test. |
| `IDIFF_BIN` | `idiff` (`idiff.exe` on Windows) | OpenImageIO's `idiff`, for `idiff` comparison tests. |
| `VMAF_MODEL_DIR` | `/usr/share/vmaf` | Folder with the VMAF model JSON files. With Homebrew on macOS, use `/opt/homebrew/share/libvmaf/model/`. |
| `ENCODE_TIMEOUT` | `1800` | Seconds an encode may run before it is killed. |

An encode that runs past `ENCODE_TIMEOUT` is killed, and "killed after N seconds" goes to the console and the
test's log. The killed encode then fails like any other encode that leaves no usable file, and the run carries on.
The timeout exists because some FFmpeg builds can loop forever on a bad input: a PNG with a broken EXIF chunk once
held up a full run for 9 hours (see
[PNGs with bad EXIF data](../FFmpegChanges.html#png-exif-81)). If a slow encoder on a long source needs more time,
raise the limit, for example `ENCODE_TIMEOUT=7200`.

### Results

Each config's results go in `<results-folder>/ffmpeg_version_<version>/<platform>/<config>-encode/`, for example
`results/ffmpeg_version_9.0.2/darwin-arm64/color_tests-encode/`: the encoded files, a log per test, the
`<config>.otio` file and the config's HTML report. In the `.otio` file each source clip has a media reference for
its source plus one for each encoded test, with the comparison results (VMAF, PSNR, Y'CbCr errors, tags) in the
media reference's metadata.

The results folder also gets an `index.html` linking every report, and `changes.html`/`changes.json`, which compare
the FFmpeg versions in the folder (see [Changes between FFmpeg versions](#changes-between-ffmpeg-versions)).

## Setup Test Environment

### Python packages

From the repository root:

```console
python3 -m venv .venv
source .venv/bin/activate          # on Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
kaleido_get_chrome                 # only if Google Chrome is not installed
```

The `OpenImageIO` package also provides `oiiotool` and `idiff`, which some tests and the source download scripts
use. With rez, install `rez/encodingguidelines_env` instead (`rez-build -i` in that folder); it has the same
packages.

### FFmpeg

Check that your build has what the tests need:

```console
ffmpeg -hide_banner -filters | grep -E "libvmaf|zscale"
ffmpeg -hide_banner -decoders | grep -E "libdav1d|libaom"
```

Package-manager builds vary in what they include. The `conan/` recipes and the `docker/` files in this repository
build FFmpeg from source with everything the tests use. Set `FFMPEG_BIN` to test a build that is not first on the
`PATH`.

The VMAF model files (`vmaf_v0.6.1.json` and `vmaf_4k_v0.6.1.json`) come with libvmaf. Point `VMAF_MODEL_DIR` at
their folder if it is not `/usr/share/vmaf`: with Homebrew on macOS that is `/opt/homebrew/share/libvmaf/model/`. The
models can also be downloaded from the [VMAF repository](https://github.com/Netflix/vmaf/tree/master/model). The
framework prints a warning at start-up if it cannot find them.

On Windows, [vcpkg](https://github.com/microsoft/vcpkg) can install FFmpeg and OpenImageIO
(`vcpkg install openimageio[tools]:x64-windows ffmpeg[ffmpeg]:x64-windows`); add their `tools` folders to the
`PATH`, for example in `.venv\Scripts\activate.bat`. This route has not been retested with the current
`requirements.txt`.

### Test sources

Most configs use images from `../sourceimages`, which are in the repository. The rest use media from
`enctests/sources`, which is downloaded:

```console
cd enctests/sources
./download_media.sh
```

This runs `enc_sources/download_media.sh` and `hdr_sources/download_media.sh`, which need the AWS command-line tool
(`pip install awscli`; no account is needed) and `oiiotool`; see [Reference Source Test Media](sources/enc_sources/README.html).
`sws_tests`, `swsscale_tests`, `swsyuv420_tests` and `order_tests` also need
`sourceimages/SonyF35.StillLife_srgb.png`, which is not committed: `sourceimages/generate.sh` makes it.

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

The main templates are:

* basic.html.jinja - which assumes you want three graphs representing encode_time, file-size and encode-quality, along with showing the VMAF parameters from the OTIO file.
* ycbcr.html.jinja - for the `ycbcr` comparison: the white, max, mean and p99 errors, error maps and level plots. Also
  used for the documentation tests (see later), where it adds a Source column linking to the page and line each
  command came from (on GitHub; set `source_url` in the report config to point elsewhere).
* identity.html.jinja - for the `identity` comparison: the percentage of each plane identical to the reference wedge,
  graphs if the config has any, and a thumbnail of each output that is a PNG. With no comparison it just shows the
  outputs side by side (e.g. `swsscale_tests.yml`).
* compare.html.jinja - an interactive viewer for comparing encodes side by side, listed after basicvmafimagecompare.html.jinja.
* index.html.jinja - the index of every report in a results folder, grouped by FFmpeg version and platform.

`ycbcr.html.jinja`, `identity.html.jinja` and `index.html.jinja` share their styles and macros (`_style.css.jinja`,
`_macros.html.jinja`), and the site links and Google Analytics tag (`_nav.html.jinja`, `_analytics.html.jinja`).

### Graphing strings

The example above compares strings (the `-preset` values), so it uses bar graphs (`type: bar`), grouped by the `-preset` flag. Where the wedges vary a number, such as `-crf`, a line graph (`type: line`) of that value against file size, encode time and quality is usually clearer.
