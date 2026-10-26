# Chroma siting in codecs and containers (9.0)

FFmpeg build: `n9.0.1-6-g9d4ca21220b`.

## Where chroma siting is recorded

Frames carry the chroma location in the first column (set with `zscale ... chromal=`).

| Codec | Chroma | Container | Frames say | Codec field | Container field | ffprobe |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| h264 | 4:2:0 | mp4 | left | not written | no field | left |
| h264 | 4:2:0 | mkv | left | not written | H left/top, V half | left |
| h264 | 4:2:0 | mov | left | not written | no field | left |
| h264 | 4:2:0 | mp4 | center | center | no field | center |
| h264 | 4:2:0 | mkv | center | center | H half, V half | center |
| h264 | 4:2:0 | mov | center | center | no field | center |
| h264 | 4:2:0 | mp4 | topleft | topleft | no field | topleft |
| h264 | 4:2:0 | mkv | topleft | topleft | H left/top, V left/top | topleft |
| h264 | 4:2:0 | mov | topleft | topleft | no field | topleft |
| h264 | 4:2:2 | mp4 | left | not written | no field | left |
| h264 | 4:2:2 | mkv | left | not written | H left/top, V half | left |
| h264 | 4:2:2 | mov | left | not written | no field | left |
| h264 | 4:2:2 | mp4 | center | not written | no field | left |
| h264 | 4:2:2 | mkv | center | not written | H half, V half | center |
| h264 | 4:2:2 | mov | center | not written | no field | left |
| hevc | 4:2:0 | mp4 | left | left | no field | left |
| hevc | 4:2:0 | mkv | left | left | H left/top, V half | left |
| hevc | 4:2:0 | mov | left | left | no field | left |
| hevc | 4:2:0 | mp4 | center | center | no field | center |
| hevc | 4:2:0 | mkv | center | center | H half, V half | center |
| hevc | 4:2:0 | mov | center | center | no field | center |
| hevc | 4:2:0 | mp4 | topleft | topleft | no field | topleft |
| hevc | 4:2:0 | mkv | topleft | topleft | H left/top, V left/top | topleft |
| hevc | 4:2:0 | mov | topleft | topleft | no field | topleft |
| hevc | 4:2:2 | mp4 | left | not written | no field | unspecified |
| hevc | 4:2:2 | mkv | left | not written | H left/top, V half | left |
| hevc | 4:2:2 | mov | left | not written | no field | unspecified |
| hevc | 4:2:2 | mp4 | center | not written | no field | unspecified |
| hevc | 4:2:2 | mkv | center | not written | H half, V half | center |
| hevc | 4:2:2 | mov | center | not written | no field | unspecified |
| av1-svt | 4:2:0 | mp4 | left | vertical (= left) | no field | unspecified |
| av1-svt | 4:2:0 | mkv | left | vertical (= left) | H left/top, V half | left |
| av1-svt | 4:2:0 | mp4 | center | unknown | no field | unspecified |
| av1-svt | 4:2:0 | mkv | center | unknown | H half, V half | center |
| av1-svt | 4:2:0 | mp4 | topleft | colocated (= topleft) | no field | unspecified |
| av1-svt | 4:2:0 | mkv | topleft | colocated (= topleft) | H left/top, V left/top | topleft |
| av1-aom | 4:2:0 | mp4 | left | unknown | no field | unspecified |
| av1-aom | 4:2:0 | mkv | left | unknown | H left/top, V half | left |
| av1-aom | 4:2:0 | mp4 | center | unknown | no field | unspecified |
| av1-aom | 4:2:0 | mkv | center | unknown | H half, V half | center |
| av1-aom | 4:2:0 | mp4 | topleft | unknown | no field | unspecified |
| av1-aom | 4:2:0 | mkv | topleft | unknown | H left/top, V left/top | topleft |
| av1-aom | 4:2:2 | mp4 | left | no field (not 4:2:0) | no field | unspecified |
| av1-aom | 4:2:2 | mkv | left | no field (not 4:2:0) | H left/top, V half | left |
| av1-aom | 4:2:2 | mp4 | center | no field (not 4:2:0) | no field | unspecified |
| av1-aom | 4:2:2 | mkv | center | no field (not 4:2:0) | H half, V half | center |
| prores | 4:2:2 | mov | left | no field | no field | unspecified |
| prores | 4:2:2 | mkv | left | no field | H left/top, V half | left |
| prores | 4:2:2 | mxf | left | no field | 6 vertical midpoint | unspecified |
| prores | 4:2:2 | mov | center | no field | no field | unspecified |
| prores | 4:2:2 | mkv | center | no field | H half, V half | center |
| prores | 4:2:2 | mxf | center | no field | 3 quincunx | unspecified |
| dnxhr | 4:2:2 | mov | left | no field | no field | unspecified |
| dnxhr | 4:2:2 | mkv | left | no field | H left/top, V half | left |
| dnxhr | 4:2:2 | mxf | left | no field | 6 vertical midpoint | unspecified |
| dnxhr | 4:2:2 | mov | center | no field | no field | unspecified |
| dnxhr | 4:2:2 | mkv | center | no field | H half, V half | center |
| dnxhr | 4:2:2 | mxf | center | no field | 3 quincunx | unspecified |

## DNxHR HQX 4:2:2 in MXF

Label is the MXF `ColorSiting`; position is where the chroma actually is in the decoded DNxHR (0 = co-sited, as the label 0 says; 0.5 = centred), from the chart's single-pixel lines (the mean of the even- and odd-column results). At 10-bit the tent measurement is only good to about +/-0.05 and DNxHR compression noise adds to that, so the lines are used here.

| Wrapper | Command | MXF ColorSiting | Chroma position | Lines |
| :--- | :--- | :--- | :--- | :--- |
| mxf | `scale (EncodeDNXHD.md before Oct 2026)` | 0 co-sited | centre | **pair-averaged** (0 / 1) |
| mxf | `scale + out_chroma_loc=left + full_chroma_inp` | 6 vertical midpoint | co-sited | consistent (0 / 0) |
| mxf | `zscale` | 0 co-sited | co-sited | consistent (0 / 0) |
| mxf | `zscale chromal=left` | 6 vertical midpoint | co-sited | consistent (0 / 0) |
| mxf | `zscale chromal=topleft` | 0 co-sited | co-sited | consistent (0 / 0) |
| mxf_opatom | `scale (EncodeDNXHD.md before Oct 2026)` | 0 co-sited | centre | **pair-averaged** (0 / 1) |
| mxf_opatom | `scale + out_chroma_loc=left + full_chroma_inp` | 6 vertical midpoint | co-sited | consistent (0 / 0) |
| mxf_opatom | `zscale` | 0 co-sited | co-sited | consistent (0 / 0) |
| mxf_opatom | `zscale chromal=left` | 6 vertical midpoint | co-sited | consistent (0 / 0) |
| mxf_opatom | `zscale chromal=topleft` | 0 co-sited | co-sited | consistent (0 / 0) |
