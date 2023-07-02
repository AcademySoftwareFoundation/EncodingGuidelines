---
layout: default
nav_order: 4.5
title: HEVC/H265 Encoding
parent: Encoding Overview
---

HEVC

See (ffmpeg h265 docs)[https://trac.ffmpeg.org/wiki/Encode/H.265] 
HDR Support, 

libx265

yuv420p
yuvj420p ?
yuv422p
yuv422p10
yuv444p10le
gbrp10le
gbrp12le
gbrp

-crf
-qp
-preset
-tune
-profile


hevc_videotoolbox

bgra
p010le
nv12

-profile main main10
| -- | -- |
| -preset medium | Can be one of ultrafast, superfast, verfast, faster, fast, medium, slow, slower, and placebo |
| -crf 18 | Similar to h264, default is 28, but should be similar to crf 23 |
| -x265-params lossless=1 | Does lossless encoding, -crf 0 is not required |
| -tag:v hvc1 | To make it "Apple "Industry standard" compliant |




TODO Test h265 CRF values 


mp4 container (mov?)

Not supported by firefox
