import os
import sys
from copy import deepcopy
import time
import yaml
import json
import pyseq
import shlex
import argparse
import subprocess
import platform
from pathlib import Path
import jinja2

base_ffmpeg_path = "/Users/sam/roots/ffapv/bin"

extensions = ['mxf', 'mp4', 'mov']

decompress = {'h264': [{'name': 'h264_software',
                       'flags': ' '},
                       {'name': 'h264_videotoolbox',
                        'platform': ['darwin'],
                       'flags': '-hwaccel videotoolbox '},
                       ],
              'av1': [{'name': 'av1_software',
                       'flags': ' '},
                       {'name': 'av1_libdav1d',
                       'flags': '-c:v libdav1d '},
                       {'name': 'av1_libaom-av1',
                       'flags': '-c:v libaom-av1 '},
                       ],
              'hevc': [{'name': 'hevc_software',
                       'flags': ' '},
                       {'name': 'hevc_videotoolbox',
                        'platform': ['darwin'],
                       'flags': '-hwaccel videotoolbox '},
                       ],
             'prores': [{'name': 'prores_software',
                       'flags': ' '},
                       {'name': 'prores_videotoolbox',
                        'platform': ['darwin'],
                       'flags': '-hwaccel videotoolbox '},
                       ],
}

def scanFiles(location):
    allfiles = []
    for root, dirs, files in os.walk(location):
        allfiles.extend([os.path.join(root, file) for file in files if file[-3:] in extensions and file[0] != "."])
    data = []
    for file in allfiles:
        filep = Path(file)
        #if "sparks" not in str(filep):
        #    continue
        if filep.stat().st_size == 0:
            print(f"Skipping {file}, since its empty.")
            continue
        cmd = f"{base_ffmpeg_path}/ffprobe -v quiet -print_format json -show_format -show_streams {file}"
        _raw = subprocess.check_output(shlex.split(cmd))
        jsondata = json.loads(_raw)
        print(f"{file} {jsondata['streams'][0]['codec_name']}")
        data.append({'file': filep, 'codec': jsondata['streams'][0]['codec_name']})
        #benchmark([data[-1]])
    return data

def benchmark(allfileinfo):
    results = []
    for fileinfo in allfileinfo:
        if fileinfo['codec'] not in decompress:
            decompress[fileinfo['codec']] = [{'name': f"{fileinfo['codec']}_default", 'flags': ''}]
            print(f"Adding codec: {fileinfo['codec']}")
        for decode in decompress[fileinfo['codec']]:
            cmd = f"{base_ffmpeg_path}/ffmpeg {decode['flags']} -i {fileinfo['file']}  -benchmark -f null -"
            print(cmd)
            try:
                t1 = time.perf_counter()
                _raw = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT, universal_newlines=True)
                duration = time.perf_counter() - t1
            except:
                print(f"Failed to run: {cmd}")
                continue
            bench = str(_raw).split("bench:")[1]
            utime = bench.split("utime=")[1].split("s")[0]
            stime = bench.split("stime=")[1].split("s")[0]
            rtime = bench.split("rtime=")[1].split("s")[0]

            maxrss = str(_raw).split("bench: maxrss=")[1]
            results.append({"fileinfo": fileinfo, 
                           'duration': duration,
                           'utime': utime,
                           'stime': stime,
                           'rtime': rtime,
                           'maxrss': maxrss,
                           'cmd': cmd,
                           'decode': decode,
                           "raw": str(_raw)})
    return results
            #print(f"{fileinfo['file']} {fileinfo['codec']} {decode['flags']} utime:{utime} stime:{stime} rtime:{rtime} maxess:{maxrss}")
#allfiles = scanFiles('../codec-encode')

#allfiles = scanFiles("../wedge_results/ffmpeg_version_7.1/darwin-arm64/htj2k4koiio_options_tests-encode/")
allfiles = scanFiles("../wedge_results/ffmpeg_version_git-2025-05-09-0a1b790f29/darwin-arm64/osx_apv444_tests-encode/")
results = benchmark(allfiles)

resultsbyname = {}
for result in results:
    path = str(result['fileinfo']['file']).split(".-")[0]
    if path not in resultsbyname:
        resultsbyname[path] = [result]
    else:
        resultsbyname[path].append(result)

htmltemplate = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{config.title}}</title>
  <link rel="stylesheet" href="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/css/just-the-docs-default.css"> 
  <script type="text/javascript" src="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/js/vendor/lunr.min.js"></script> 
  <script type="text/javascript" src="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/js/just-the-docs.js"></script>
</head>

<body>
{% for media, results in resultsbyname.items() %}
<H1>{{ media }}</H1>
<table>
<TR>
<TH>Name</TH>
<TH>Duration</TH>
<TH>Utime</TH>
<TH>Stime</TH>
<TH>Rtime</TH>
<TH>Max-RSS</TH>
<TH>Cmd</TH>
</TR>
{% for result in results %}
<TR>
<TD>{{result.decode.name}}</TD>
<TD ALIGN=right>{{"%.3f"|format(result.duration)}}</TD>
<TD ALIGN=right>{{result.utime}}</TD>
<TD ALIGN=right>{{result.stime}}</TD>
<TD ALIGN=right>{{result.rtime}}</TD>
<TD ALIGN=right>{{result.maxrss}}</TD>
<TD ALIGN=right>{{result.cmd}}</TD>
</TR>
{% endfor %}
</TABLE>
{% endfor %}
</body>
</html>
"""

template = jinja2.Template(htmltemplate)
f = open("results.html", "w")
f.write(template.render(resultsbyname=resultsbyname, config={'title': "Codecs"}))
f.close()

