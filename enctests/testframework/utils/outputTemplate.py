
# This has the following requirements.
# pip install kaleido plotly pandas jinja2

import os
import plotly.express as px
import opentimelineio as otio
import pandas as pd
import jinja2
from pathlib import Path
from ..test_suite import TestSuite, SourceConfig

def _exportGraph(config, reportconfig, graph, alltests):
  """
  Export a graph using all the test data.
  :param reportconfig: The report configuration to output. 
  :param graph: The specific graph to output.
  :param alltest: The raw test data to use.
  """
  graphargs = graph.get("args")

  sortvalues = True
  if "colororder" in graphargs:
    colororder = graphargs.pop("colororder")
    for test in alltests:
      test['colororder'] = colororder.index(test[graphargs['color']])
    df = pd.DataFrame(alltests)
    df = df.sort_values(by='colororder')
    sortvalues = False
  else:
    df = pd.DataFrame(alltests)
    # This sorts the filenames.
  if graph.get("type", "line") == "bar":
    if sortvalues:
      df = df.sort_values(by=graph.get("sortby", "name"))
    fig = px.bar(df, **graphargs) 
  else:
    # If we have a a line graph, we need to make sure the data values are sorted by x.
    # but we still want to sort the categories, so we explicitly pull out the possible categories
    # to make sure they are sorted.
    if sortvalues:
      df = df.sort_values(by=graphargs.get("x"))
    labels = {}
    for test in alltests:
       labels[test[graphargs['color']]] = test[graphargs['color']]
    category_orders = {graphargs['color']: labels.keys()}
    graphargs['category_orders'] = category_orders
    fig = px.line(df, **graphargs) 

  filename = Path(reportconfig['name']+"-"+graph.get("name"))
  if "directory" in reportconfig:
    filename = config.get('destination') / filename
  if filename.exists():
    # Running inside docker sometimes doesnt let you write over files. 
    filename.unlink()
  print("Writing out:", filename)
  fig.write_image(filename)
  print("Written out:", filename)



def processTemplate(config, timeline):
  """
  Look for any report configs in the test_configurations and apply them to the specified otio file.
  :param test_configs: a list of test configurations.
  :param otio_info: A otio object containing the test results.
  """

  reportconfig = config.report()
  if reportconfig is None:
    print("Failed to find report config. Skipping html export.")
    return

  tracks = timeline.tracks[0]
  testinfo = {'ffmpeg_version': tracks.name.replace("ffmpeg_version_", "")}

  tests = {}
  alltests = []
  for track in tracks:
      results = []
      default_media = None
      for ref_name, test_info in track.media_references().items():
          if ref_name == "DEFAULT_MEDIA":
              default_media = {'name': track.name, 'basename': track.name, 'test_info': test_info}
              continue
          merge_test_info = test_info.metadata['aswf_enctests']['results']
          merge_test_info['name'] = ref_name
          merge_test_info['testbasename'] = test_info.metadata['aswf_enctests']['testbasename']
          merge_test_info['wedge'] = test_info.metadata['aswf_enctests']['wedge_name']
          print("Wedge:", merge_test_info['wedge'], ref_name)
          if 'description' in test_info.metadata['aswf_enctests']:
            merge_test_info['test_description'] = test_info.metadata['aswf_enctests']['description']
          results.append(merge_test_info)
          merge_test_info['media'] = track.name
          merge_test_info['output_media'] = test_info.name
          if "vmaf" in merge_test_info:
            merge_test_info['vmaf_min'] = float(merge_test_info['vmaf']['min'])
            merge_test_info['vmaf_mean'] = float(merge_test_info['vmaf']['mean'])
            merge_test_info['vmaf_harmonic_mean'] = float(merge_test_info['vmaf']['harmonic_mean'])
            merge_test_info['psnr_y_harmonic_mean'] = float(merge_test_info['psnr_y']['harmonic_mean'])
            if "cambi" in merge_test_info:
              merge_test_info['cambi_harmonic_mean'] = float(merge_test_info['cambi']['harmonic_mean'])
              merge_test_info['float_ms_ssim_harmonic_mean'] = float(merge_test_info['float_ms_ssim']['harmonic_mean'])
          else:
            merge_test_info['psnr_y'] = {}
            merge_test_info['psnr_cr'] = {}
            merge_test_info['psnr_cb'] = {}
            merge_test_info['vmaf_harmonic_mean'] = -1
            merge_test_info['psnr_y_harmonic_mean'] = -1
            merge_test_info['cambi_harmonic_mean'] = -1
            merge_test_info['float_ms_ssim_harmonic_mean'] = -1

          merge_test_info['filesize'] = merge_test_info['filesize']
          if 'host_config' in test_info.metadata['aswf_enctests']:
             #  We assume all the tests have the same values.
             testinfo['host_config'] = test_info.metadata['aswf_enctests']['host_config']

          # We merge the arguments into the dictionary too, as well as merge it into a single string, to make the graphing simpler.
          args=[]
          for k,v in test_info.metadata['aswf_enctests']['encode_arguments'].items():
            args.extend([k,str(v)])
            merge_test_info[k] = v 
          merge_test_info['encode_arguments'] = " ".join(args)
          merge_test_info["command"] = test_info.metadata['aswf_enctests']['command']
          alltests.append(merge_test_info)
      if track.name in tests:
        tests[track.name]['results'].extend(results)
      else:
        tests[track.name] = {'results': results, 'source_info': track.metadata['aswf_enctests']['source_info'], 'default_media': default_media}

  for graph in reportconfig.get("graphs", []):
    _exportGraph(config, reportconfig, graph, alltests)

  environment = jinja2.Environment(loader=jinja2.FileSystemLoader("testframework/templates/"))

  template = environment.get_template(reportconfig['templatefile'])
  htmlreport = reportconfig['name']+".html"
  #if "directory" in reportconfig:
  htmlreport = config.get('destination') / htmlreport
  if htmlreport.exists():
    # Running inside docker sometimes doesnt let you write over files.
    htmlreport.unlink()
  with htmlreport.open("w") as f:
      f.write(template.render(tests=tests, testinfo=testinfo, config=reportconfig))
  print("Written out:", htmlreport)
  return {'reporturl': htmlreport, 'tests': tests, 'testinfo': testinfo, 'config': reportconfig}

def outputSummaryIndex(output_dir):
    """
    Create a summary index of all the test results in the specified folder.
    :param output folder.
    """

    test_results = []
    for root, dirs, files in os.walk(output_dir):
        for filename in files:
            if filename.endswith(".otio"):
                path = Path(root) / filename
                timeline = otio.adapters.read_from_file(path.as_posix())
                # Now we need to figure out the config file.
                track = timeline.tracks[0]

                configfile = timeline.metadata['config_file']

                #Load the test 
                try:
                  testsuite = TestSuite(Path(configfile))
                except FileNotFoundError:
                   print(f"Warning: config file {configfile} is missing, skipping report.")
                   continue
                reportconfig = testsuite.report()
                if reportconfig is None:
                   continue
                htmlreport = path.parent / (reportconfig['name']+".html")
                results = {'title': reportconfig["title"],
                           'description': reportconfig['description'],
                           'relativeurl': htmlreport.relative_to(output_dir),
                           'error_tests': 0,
                           'success_tests': 0,
                           'test_start': timeline.metadata.get("test_start", "unknown"),
                           'platform': timeline.metadata.get("platform", path.parent.parent.parent.name),
                           'applicationVersion': timeline.metadata.get("applicationVersion", path.parent.parent.name),
                           'test_duration': timeline.metadata.get("test_duration", "unknown")
                           }
                for trackitem in track:
                  for ref_name, test_info in trackitem.media_references().items():
                    if ref_name == "DEFAULT_MEDIA":
                       continue
                    merge_test_info = test_info.metadata['aswf_enctests']['results']
                    if merge_test_info.get('success', True):
                       results['success_tests'] += 1
                    else:
                       results['error_tests'] += 1
                test_results.append(results)

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("testframework/templates/"))

    template = environment.get_template('index.html.jinja')
    htmlreport = Path(output_dir) / "index.html"
    with htmlreport.open("w") as f:
      f.write(template.render(results=test_results))
