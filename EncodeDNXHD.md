---
layout: default
nav_order: 4.3
title: DNxHD Encoding
parent: Encoding
---

https://en.wikipedia.org/wiki/Avid_DNxHD

https://avid.secure.force.com/pkb/articles/en_US/White_Paper/DNxHR-Codec-Bandwidth-Specifications

++ Profiles
| Profile name | Profile description |
| dnxhd | | 0 | 
| dnxhr_lb | Low Bandwidth | 1 | YUV 4:2:2 (8-bit) |
| dnxhr_sq | Standard Quality | 2 | YUV 4:2:2 (8-bit) |
| dnxhr_hq | High Quality | 3 | YUV 4:2:2 (8-bit) |
| dnxhr_hqx | High Quality (12 bit) | 4 | YUV 4:2:2 (10-bit) |
| dnxhr_444 | DNxHR 4:4:4 12-bit | 5 | YUV 4:4:4 or RGB (10-bit) |

ffmpeg -i "$in" -vf scale=1920:1080:lanczos \
 -an -metadata project="MY PROJECT" -metadata material_package_name="MY CLIP" \
 -b:v 36M -f mxf_opatom "$out-V1.mxf" \
 -vn -metadata project="MY PROJECT" -metadata material_package_name="MY CLIP" \
 -ac 1 -ar 48000 -f mxf_opatom "$out-A01.mxf"
 https://johnwarburton.net/blog/?p=50731

