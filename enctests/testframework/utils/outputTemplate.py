
# This has the following requirements.
# pip install kaleido plotly pandas jinja2

import os
import plotly.express as px
import opentimelineio as otio
import pandas as pd
import jinja2



def processTemplate(test_configs, otio_info):
  tracks = otio_info.tracks[0]
  
  tests = {}
  alltests = []
  reportconfig = None
  for config in test_configs:
    print("KEYS:", config.keys())
    if "reports" in config:
      reportconfig = config['reports']
    
  if reportconfig is None:
    print("Failed to find report config. Skipping html export.")
    exit(0)

  testinfo = {'ffmpeg_version': tracks.name.replace("ffmpeg_version_", "")}


  for track in tracks:
      results = []
      for ref_name, test_info in track.media_references().items():
          #merge_test_info = {'name': ref_name}
          #print(ref_name, test_info.metadata)
          if ref_name == "DEFAULT_MEDIA":
              #print("Track:", track)
              continue
          #if tracks.name not in test_info.metadata[tracks.name][ref_name]:
          #    print("Not finding:", test_info.metadata[tracks.name][ref_name])
          #    continue
          #enc_info = test_info.metadata[tracks.name][ref_name]# [tracks.name]
          # for key, enc_data in enc_info.items():
          #     if key == 'results':
          #         for arg, value in enc_data.items():
          #             merge_test_info[arg] = value
          #     else:
          #         #print("Something ese:", value)
          #         merge_test_info['encoder_version'] = key
          #         for arg, value in enc_data.items():
          #             merge_test_info[arg] = value
          print("ref_name:", ref_name)
          #print("testInfo:", test_info.metadata)
          merge_test_info = test_info.metadata['aswf_enctests']['results']
          merge_test_info['name'] = ref_name
          results.append(merge_test_info)
          merge_test_info['media'] = track.name
          merge_test_info['vmaf_min'] = float(merge_test_info['vmaf']['min'])
          merge_test_info['vmaf_mean'] = float(merge_test_info['vmaf']['mean'])
          merge_test_info['vmaf_harmonic_mean'] = float(merge_test_info['vmaf']['harmonic_mean'])
          merge_test_info['filesize'] = merge_test_info['filesize']
          if "_" in ref_name:
            #This is a hack that we need to get rid of.
            try:
              merge_test_info['quality'] = int(ref_name.split("_")[-1])
            except Exception as e:
              print("Exception:", e, " for getting quality from ", ref_name)
          # We merge the arguments into the dictionary too, as well as merge it into a single string, to make the graphing simpler.
          args=[]
          for k,v in test_info.metadata['aswf_enctests']['encode_arguments'].items():
            args.extend([k,str(v)])
            merge_test_info[k] = v 
          merge_test_info['encode_arguments'] = " ".join(args)
          alltests.append(merge_test_info)
      tests[track.name] = {'results': results, 'source_info': track.metadata['aswf_enctests']['source_info']}

  for graph in reportconfig.get("graphs", []):
      df = pd.DataFrame(alltests)
      df = df.sort_values(by=graph.get("sortby", "name"))
      #print(df)
      fig = px.line(df, **graph.get("args")) #"x='quality', y='min', color='media', markers=True, text="min")
      filename = reportconfig['name']+"-"+graph.get("name")
      if "directory" in reportconfig:
        filename = os.path.join(reportconfig['directory'], filename)
      if os.path.exists(filename):
        # Running inside docker sometimes doesnt let you write over files. 
        os.remove(filename)
      print("Writing out:", filename)
      fig.write_image(filename)
      print("Written out:", filename)

  environment = jinja2.Environment(loader=jinja2.FileSystemLoader("testframework/templates/"))

  template = environment.get_template(reportconfig['templatefile'])
  htmlreport = reportconfig['name']+".html"
  if "directory" in reportconfig:
    htmlreport = os.path.join(reportconfig['directory'], htmlreport)
  if os.path.exists(htmlreport):
    # Running inside docker sometimes doesnt let you write over files.
    os.remove(htmlreport)
  f = open(htmlreport, "w")
  f.write(template.render(tests=tests, testinfo=testinfo, config=reportconfig))
  f.close()
  print("Written out:", htmlreport)

