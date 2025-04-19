import os
import subprocess
import sys
import json
import yaml

testdirs = ["../wedge_results/ffmpeg_version_7.0/darwin-arm64/codec_tests-encode"]
testdirs = ["../wedge_results/ffmpeg_version_7.0.1/darwin-arm64/intraframe_tests-encode"]

testdirs = ["../wedge_results/ffmpeg_version_7.0.1/darwin-arm64/intraframe_tests-encode", 
            "../wedge_results/ffmpeg_version_7.0/darwin-arm64/codec_tests-encode"]
testdirs = [#"../wedge_results/ffmpeg_version_7.1/linux-x86_64/intraframe_tests-encode", 
            #"../wedge_results/ffmpeg_version_7.1/linux-x86_64/codec_tests-encode", 
            #"../wedge_results/ffmpeg_version_7.1/linux-x86_64/htj2k_options_tests-encode", 
            #"../wedge_results/ffmpeg_version_7.1/darwin-arm64/htj2k_options_tests-encode"]
            "../wedge_results/ffmpeg_version_7.1/darwin-arm64/htj2k4koiio_options_tests-encode/",
]


def get_video_codec(filename):
  """
  Extracts the video codec from a QuickTime file using ffprobe and Python.

  Args:
      filename (str): Path to the QuickTime file.

  Returns:
      str: The video codec of the file, or None if an error occurs.
  """
  command = ['ffprobe', '-v', 'quiet', '-show_format', '-show_streams', '-print_format', 'json', filename]
  try:
    # Run ffprobe with capture output
    output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    # Parse the JSON output
    data = json.loads(output)
    # Get the video stream
    streams = data.get('streams', [])
    for stream in streams:
      if stream.get('codec_type') == 'video':
        return stream.get('codec_name')
    return None
  except subprocess.CalledProcessError as e:
    print(f"Error running ffprobe for {filename} error: {e}")
    return None

def estimate_gop_size(filename):
  """
  Estimates the GOP size of a QuickTime file by analyzing frame types using ffprobe.

  Args:
      filename (str): Path to the QuickTime file.

  Returns:
      int: Estimated GOP size (distance between I-frames), or None if an error occurs.
  """
  command = ['ffprobe', '-v', 'quiet', '-show_entries', 'frame=pict_type', filename]
  try:
    output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
    # Look for lines with pict_type=I
    i_frame_count = 0
    previous_i_frame = False
    for line in output.splitlines():
      if "pict_type" not in line:
        continue
      if "pict_type=I" in line:
        if previous_i_frame:
          return i_frame_count
        else:
          previous_i_frame = True
          i_frame_count = 1
      else:
        i_frame_count += 1
    if previous_i_frame:
      return i_frame_count
    return None  # No I-frames found
  except subprocess.CalledProcessError as e:
    print(f"Error running ffprobe for {filename}, error {e}")
    return None


files = []
for testdir in testdirs:
    files.extend([os.path.join(testdir, f) for f in os.listdir(testdir) if f.endswith(".mp4") or f.endswith(".mov")])


f = open("playback_results3.html", "w")

print("""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Codecs</title>
  <link rel="stylesheet" href="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/css/just-the-docs-default.css"> 
  <script type="text/javascript" src="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/js/vendor/lunr.min.js"></script> 
  <script type="text/javascript" src="https://academysoftwarefoundation.github.io/EncodingGuidelines/assets/js/just-the-docs.js"></script>
</head>

<body>
""", file=f)

codecmap = {
  'dnxhd': ['dnxhd'],
  'vp9': ['libvpx-vp9'],
  'av1': ['libdav1d', 'libaom-av1'],
  'h264': ['h264'],
  'hevc': ['hevc'],
  'cfhd': ['cfhd'],
  'prores': ['prores'],
  'mjpeg': ['mjpeg'],
  'jpeg2000': ['jpeg2000'],
}

fields=['basename', 'Decoder', 'filesize', 'gopsize', 'FirstFrame', 'FirstFrame%30', 'FirstFrame%60', 'Average','Max FPS', 'Average%30', 'Average%60']

files = sorted(files, key=lambda f:os.path.basename(f).split("-")[0])
print(files)
lastfile = None

for file in files:
    print(file)
    info={}
    info['basename'] = os.path.basename(file)
    basefile = info['basename'].split("-")[0]
    if basefile  != lastfile:
        if lastfile is not None:
            print("</TABLE>", file=f)
        lastfile = basefile
        print(f"<h2>{basefile}</H2>", file=f)
        print("<TABLE BORDER=1><TR>", file=f)
        for field in fields:
            print(f"<TH ALIGN=RIGHT>{field}</TH>", file=f)
    print("</TR>", file=f)
    codec = get_video_codec(file)
    gopsize = estimate_gop_size(file)
    info['codec'] = codec
    info['gopsize'] = gopsize
    info['filesize'] = os.path.getsize(file)
    #print(file, codec, gopsize)
    if codec not in codecmap:
      codecmap['codec'] = [codec]
      print(f"WARNING: codec {codec} not defined, assuming default.")
    
    for codeclib in codecmap[codec]:
          command = ['./codec_test', file, codeclib, '80']
          print("Running:", " ".join(command))
          output = subprocess.run(command, capture_output=True, text=True, check=True).stdout
          # Parse the JSON output
          print("Got output:", output, " from ", codeclib)

          data = yaml.safe_load(output)
          if data is None:
            print(f"ERROR, Failed to run {' '.join(command)}")
            continue
          print(output, data)
          info['FirstFrame'] = data['FirstFrame']
          info['Average'] = data['Average']
          info['Max FPS'] = data['FPS']
          info['Decoder'] = codeclib
          print("info:", info['Decoder'])
          info['FirstFrame%30'] = 100.0 * data['FirstFrame'] / (1/30.0)

          info['FirstFrame%60'] = 100.0 * data['FirstFrame'] / (1/60.0)
          info['Average%30'] = 100.0 * data['Average'] / (1/30.0)

          info['Average%60'] = 100.0 * data['Average'] / (1/60.0)
          print("<TR>", file=f)
          for field in fields:
            if "%" in field:
               print(f"<TD ALIGN=RIGHT>{info.get(field, 'Undef'):.2f}</TD>", file=f)
            else:
               print(f"<TD ALIGN=RIGHT>{info.get(field, 'Undef')}</TD>", file=f)
          print("</TR>", file=f)
print("</TABLE></BODY>", file=f)        
f.close()
