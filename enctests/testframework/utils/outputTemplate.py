
# This has the following requirements.
# pip install kaleido plotly pandas jinja2

import os
import plotly.express as px
import opentimelineio as otio
import pandas as pd
import jinja2

def _exportGraph(reportconfig, graph, alltests):
  """
  Export a graph using all the test data.
  :param reportconfig: The report configuration to output. 
  :param graph: The specific graph to output.
  :param alltest: The raw test data to use.
  """
  df = pd.DataFrame(alltests)
  df = df.sort_values(by=graph.get("sortby", "name"))
  if graph.get("type", "line") == "bar":
    fig = px.bar(df, **graph.get("args")) 
  else:
    fig = px.line(df, **graph.get("args")) 

  filename = reportconfig['name']+"-"+graph.get("name")
  if "directory" in reportconfig:
    filename = os.path.join(reportconfig['directory'], filename)
  if os.path.exists(filename):
    # Running inside docker sometimes doesnt let you write over files. 
    os.remove(filename)
  print("Writing out:", filename)
  fig.write_image(filename)
  print("Written out:", filename)



def processTemplate(test_configs, otio_info):
  """
  Look for any report configs in the test_configurations and apply them to the specified otio file.
  :param test_configs: a list of test configurations.
  :param otio_info: A otio object containing the test results.
  """

  reportconfig = None
  for config in test_configs:
    if "reports" in config:
      reportconfig = config['reports']
    
  if reportconfig is None:
    print("Failed to find report config. Skipping html export.")
    exit(0)

  tracks = otio_info.tracks[0]
  testinfo = {'ffmpeg_version': tracks.name.replace("ffmpeg_version_", "")}

  tests = {}
  alltests = []
  for track in tracks:
      results = []
      for ref_name, test_info in track.media_references().items():
          if ref_name == "DEFAULT_MEDIA":
              default_media = {'name': test_info.name, 'target_url_base': test_info.target_url_base}
              continue
          merge_test_info = test_info.metadata['aswf_enctests']['results']
          merge_test_info['name'] = ref_name
          if 'description' in test_info.metadata['aswf_enctests']:
            merge_test_info['test_description'] = test_info.metadata['aswf_enctests']['description']
          results.append(merge_test_info)
          merge_test_info['media'] = track.name
          if "vmaf" in merge_test_info:
            merge_test_info['vmaf_min'] = float(merge_test_info['vmaf']['min'])
            merge_test_info['vmaf_mean'] = float(merge_test_info['vmaf']['mean'])
            merge_test_info['vmaf_harmonic_mean'] = float(merge_test_info['vmaf']['harmonic_mean'])
          else:
            merge_test_info['psnr_y'] = {}
            merge_test_info['psnr_cr'] = {}
            merge_test_info['psnr_cb'] = {}

          merge_test_info['filesize'] = merge_test_info['filesize']

          # We merge the arguments into the dictionary too, as well as merge it into a single string, to make the graphing simpler.
          args=[]
          for k,v in test_info.metadata['aswf_enctests']['encode_arguments'].items():
            args.extend([k,str(v)])
            merge_test_info[k] = v 
          merge_test_info['encode_arguments'] = " ".join(args)
          alltests.append(merge_test_info)
      if track.name in tests:
        tests[track.name]['results'].extend(results)
      else:
        tests[track.name] = {'results': results, 'source_info': track.metadata['aswf_enctests']['source_info']}

  for graph in reportconfig.get("graphs", []):
    _exportGraph(reportconfig, graph, alltests)

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

