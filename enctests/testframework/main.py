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
from .test_suite import TestSuite, SourceConfig
from .encoders import encoder_factory, destination_from_config

import opentimelineio as otio

# Test config files
from .utils import (
    create_clip,
    get_media_info,
    get_source_path,
    get_nearest_model,
    get_test_metadata_dict,
    get_source_metadata_dict
)

from .utils.outputTemplate import processTemplate, outputSummaryIndex

ENCODE_TEST_SUFFIX = '.yml'
SOURCE_SUFFIX = '.yml'

# We assume macos and linux both have the same binary name
FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    sys.platform == 'win' and 'ffmpeg.exe' or 'ffmpeg'
)

IDIFF_BIN = os.getenv(
    'IDIFF_BIN',
    sys.platform == 'win' and 'idiff.exe' or 'idiff'
)


VMAF_LIB_DIR = os.getenv(
    'VMAF_LIB_DIR',
    f'{os.path.dirname(__file__)}/../.venv/usr/local/lib/x86_64-linux-gnu'
)

if not Path(VMAF_LIB_DIR, "model", "vmaf_v0.6.1.json").exists():
    print(f"WARNING: Cannot find VMAF configuration files at path {VMAF_LIB_DIR}")

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--sources',
        action='store',
        nargs='+',
        default=[""],
        help='Provide a list of paths to sources in stead of running all '
             'from source folder. '
             'Please note this overrides the --source-folder argument.'
    )

    parser.add_argument(
        '--source-folder',
        action='store',
        default='./sources',
        help='Where to look for source media files'
    )

    parser.add_argument(
        '--test-config-dir',
        action='store',
        default='./test_configs',
        help='Where to look for *.yml files containing test descriptions'
    )

    parser.add_argument(
        '--test-config',
        action='store',
        dest='test_config_file',
        default=None,
        help='Specify a single test config file to run'
    )

    parser.add_argument(
        '--prep-sources',
        action='store_true',
        default=False,
        help='Create *.yml files from media in --source-folder used as sources '
             'in encoding tests'
    )

    parser.add_argument(
        '--encoded-folder',
        action='store',
        default='', # If its '', we determine the path procedurally.
        help='Where to store the encoded files'
    )


    parser.add_argument(
        '--results-folder',
        action='store',
        default='./results',
        help='Basepath for all the results, not used if --encoded-folder is defined.'
    )

    parser.add_argument(
        '--encode-all',
        action='store_true',
        default=False,
        help=argparse.SUPPRESS
        # help='Encode all tests. Default to only encoding new tests'
    )

    parser.add_argument(
        '--skip-reports',
        action='store_true',
        default=False,
        help='Skip any report generation (default: False).'
    )

    parser.add_argument(
        '--output',
        action='store',
        default='',
        help='Path to results file including ".otio" extenstion '
             '(default: ./encoding-test-results.otio)'
    )

    args = parser.parse_args()

    if args.output != '' and not args.output.endswith('.otio'):
        args.output += '.otio'

    return args


def create_config_from_source(path, startframe=None):
    config_data = {'images': False}

    media_info = get_media_info(path, startframe)
    if not media_info:
        return

    config_data.update(media_info)

    if startframe:
        config_data['images'] = True

    config_path = path.with_suffix(path.suffix + SOURCE_SUFFIX)
    with open(config_path, 'wt') as f:
        yaml.dump(config_data, f, SafeDumper, indent=4, sort_keys=False)
        print(f'Successfully wrote source file: "{config_path}"')


def scantree(args, path, suffix=None):
    """Recursively yield DirEntry objects for given directory."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            sequences = pyseq.get_sequences(entry.path)
            if args.prep_sources and sequences:
                for sequence in sequences:
                    if sequence.name.endswith(SOURCE_SUFFIX):
                        # Can ignore any .source files.
                        continue
                    if sequence.length() < 2:
                        yield from scantree(args, entry.path, suffix)
                    else:
                        yield sequence
            else:
                yield from scantree(args, entry.path, suffix)

        else:
            if suffix and not entry.path.endswith(suffix):
                continue

            yield entry


def create_source_config_files(args):
    """ Create source config files based on ffprobe results. """

    # for item in os.scandir(root):
    for item in scantree(args, args.source_folder):
        startframe = None
        if isinstance(item, pyseq.Sequence):
            startframe = item.start()
            pad = f'%0{len(max(item.digits, key=len))}d'
            path = Path(item.format('%D%h') + pad + item.format('%t'))

        else:
            path = Path(str(item.path))

        if path.suffix == SOURCE_SUFFIX:
            # We only register new media
            continue

        create_config_from_source(path, startframe=startframe)

    print(
        f'Done creating source files. '
        f'Make sure to do adjustments of in point, duration and so on.'
    )

def get_source_configs(args, root_path, config_type):
    sourceconfigs = []
    for item in scantree(args, root_path, suffix=config_type):
        path = Path(item.path)
        if path.suffix == config_type:
            try:
                sourceconfigs.append(SourceConfig(path))
            except Exception as e:
                print(f"ERROR: Failed to load {path} error is: {e}")

    return sourceconfigs


def get_configs(args, root_path, config_type):
    configs = []
    for item in scantree(args, root_path, suffix=config_type):
        path = Path(item.path)
        if path.suffix == config_type:
            try:
                configs.append(TestSuite(path))
            except Exception as e:
                print(f"ERROR: Failed to load {path} error is: {e}")

    return configs


def vmaf_compare(source_clip, test_ref, testname, comparisontestinfo, source_path, distorted, log_file_object):
    """
    Compare the sourceclip to the test_ref using vmaf.
    source_clip -- The original clip that the new media is based on.
    test_ref    -- The generated movie we are testing.
    testname    -- The testname we are running.
    comparisontestinfo -- other parameters that can be used to configure the test.

    This creates a results dictionary with the following parameters:
    vmaf - the vmaf comparison metric.
    psnr - the PSNR dictionary.
    psnr_y - The PSNR lumanance value.
    psnr_cb, psnr_cr - the PNSR chrominance.
    result - Was the test able to run (Completed = Yes)
    success - Boolean, was the test a success. 
    """
    vmaf_cmd = '\
{ffmpeg_bin} \
{reference} \
-i "{distorted}" \
-vframes {duration} \
-lavfi \
\"[0:v]setpts=PTS-STARTPTS[reference]; \
[1:v]setpts=PTS-STARTPTS[distorted]; \
[distorted][reference]\
libvmaf=log_fmt=json:\
log_path=compare_log.json:\
feature="name=psnr":\
model=path={vmaf_model}\" \
-f null -\
'

    if not distorted.exists():
        results = {'success': False,
            'testresult': "No movie generated."
        }
    
        enc_meta = get_test_metadata_dict(test_ref)
        enc_meta['results'].update(results)
        return

    # Get settings from metadata used as basis for encoded media
    source_meta = get_source_metadata_dict(source_clip)
    input_args = ''
    if source_meta.get('images'):
        input_args = f"-start_number {source_meta.get('in')}"

    reference = f'{input_args} -i "{source_path}" '

    # Assuming all encoded files are video files for now

    cmd = vmaf_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        reference=reference,
        distorted=distorted.as_posix(),
        duration=source_meta.get('duration'),
        vmaf_model=get_nearest_model(int(source_meta.get('width', 1920)))
    )
    print(f'VMAF command: {cmd}', file=log_file_object)
    log_file_object.flush() # Need to flush it to make sure its before the subprocess logging.

    env = os.environ
    if 'LD_LIBRARY_PATH' in env:
        env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

    else:
        env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

    compare_log = Path("compare_log.json")
    if compare_log.exists():
        # Make sure we remove the old one, so that we know one is generated.
        compare_log.unlink()
    process = subprocess.Popen(
            shlex.split(cmd),
            stdout=log_file_object,
            stderr=log_file_object,
            universal_newlines=True,
            env=env
        )
    process.wait()
    if not compare_log.exists():
        results = {'result': 'Failed to run'}
        enc_meta = get_test_metadata_dict(test_ref)
        enc_meta['results'].update(results)
        print(f"\tFailed to generate {compare_log.name}")
        print(f"Failed to generate {compare_log.name}", file=log_file_object)
        return
    
    with compare_log.open(mode='rb') as f:
        raw_results = json.load(f)

    results = {
        'vmaf': raw_results['pooled_metrics'].get('vmaf'),
        'psnr': raw_results['pooled_metrics'].get('psnr'),   # FFmpeg < 5.1
        'testresult': "Completed"
    }

    # TODO Do this as a pretty print.
    print(f"--- VMAF output\n {raw_results['pooled_metrics']}", file=log_file_object)

    # FFmpeg >= 5.1 have split psnr results
    if not results['psnr']:
        for key in ['psnr_y', 'psnr_cb', 'psnr_cr']:
            results[key] = raw_results['pooled_metrics'].get(key)

    enc_meta = get_test_metadata_dict(test_ref)
    enc_meta['results'].update(results)

def identity_compare(source_dict, source_clip, test_ref, testname, comparisontestinfo, source_path, distorted, log_file_object):
    """
    Compare the sourceclip to the test_ref using ffmpeg identity.
    We allow it to compare one wedge to another.

    compare_movie -- The image we are comparing to, which by default we assume is the output of the first test.
    test_ref    -- The generated movie we are testing.
    testname    -- The testname we are running.
    comparisontestinfo -- other parameters that can be used to configure the test.

    This creates a results dictionary with the following parameters:
    mean_error 
    rms_error
    peak_snr
    max_error
    result - Was the test able to run (Completed = Yes)
    success - Boolean, was the test a success. 
    """
    if source_clip not in source_dict:
        source_dict[source_clip] = distorted
        enc_meta = get_test_metadata_dict(test_ref)
        result = {'success': True, 'result': "Using image as reference"}

        enc_meta['results'].update(result)
        return
    compare_movie = source_dict[source_clip]


    default_app_template = "{ffmpeg_bin} -nostats -hide_banner -i {originalfile} -i {newfile} -lavfi identity -f null -"
    apptemplate = comparisontestinfo.get("testtemplate", default_app_template)

    if "compare_image" in comparisontestinfo:
        compare_movie = comparisontestinfo.get("compare_image")

    if not distorted.exists():
        result = {'success': False,
            'testresult': "No movie generated."
        }
    else:
        cmd = apptemplate.format(originalfile=compare_movie, newfile=distorted, ffmpeg_bin=FFMPEG_BIN)
        print(f"\n\identity command: {cmd}", file=log_file_object)
        
        result = subprocess.run(shlex.split(cmd), 
                                check=False, 
                                capture_output=True, text=True
                                )
        lines = result.stderr.splitlines()
        print("\n".join(lines), file=log_file_object)
        if len(lines) < 2:
            result['result'] = "Unable to run ffmpeg"
            result['success'] = False
        else:
            result = {'success': True, 'result': lines[-1]}
            for line in lines[-2:]:
                if "identity " not in line:
                    continue
                line = line.split(" identity ")[1]
                kv_pairs = line.split(" ")
    
                # Create a dictionary from the list
                for pair in kv_pairs:
                    key, value = pair.split(":")
                    result[key] = float(value)

    enc_meta = get_test_metadata_dict(test_ref)
    enc_meta['results'].update(result)

def idiff_compare(source_clip, test_ref, testname, comparisontestinfo, source_path, distorted, log_file_object):
    """
    Compare the sourceclip to the test_ref using OIIO idiff.
    This requires that we extract the movie into an image to do the comparison. We really only want to do this for single frames. This is a good test for checking the color is good.

    source_clip -- The original clip that the new media is based on.
    test_ref    -- The generated movie we are testing.
    testname    -- The testname we are running.
    comparisontestinfo -- other parameters that can be used to configure the test.

    This creates a results dictionary with the following parameters:
    mean_error 
    rms_error
    peak_snr
    max_error
    result - Was the test able to run (Completed = Yes)
    success - Boolean, was the test a success. 
    """
    default_app_template = "{idiff_bin} {originalfile} {newfile} -abs -scale 20 -o {newfilediff}"
    apptemplate = comparisontestinfo.get("testtemplate", default_app_template)

    default_extract_template = "ffmpeg -y -i {newfile} -compression_level 10 -pred mixed -pix_fmt rgb48be  -frames:v 1 {newpngfile}"
    extract_template = comparisontestinfo.get("extracttemplate", default_extract_template)

    # Allow a different image to be compared with, useful for 422 or 420 encoding.
    sourcepng = comparisontestinfo.get("compare_image", source_path.as_posix())

    distortedpng = Path(distorted.parent, distorted.stem).with_suffix(".png")
    diffpng = Path(distorted.parent, distorted.stem + "-x20diff").with_suffix(".png")

    if not distorted.exists():
            result = {'success': False,
              'testresult': "No movie generated."
            }
            cmdresult = 1
    else:
        extractcmd = extract_template.format(ffmpeg_bin=FFMPEG_BIN, 
                                             newfile=distorted.as_posix(), 
                                             newpngfile=distortedpng.as_posix()
                                             )
        print(f"\n------------\nAbout to extract with cmd:{extractcmd}", file=log_file_object)
        log_file_object.flush()
        result = {'success': False,
                'testresult': "undefined"
        }
        process = subprocess.Popen(
                    shlex.split(extractcmd),
                    stdout=log_file_object,
                    stderr=log_file_object,
                    universal_newlines=True
                )

        process.wait()

        cmdresult = process.returncode
        
    if cmdresult != 0:
        result['result'] = "Unable to extract file for test"
    else:
        cmd = apptemplate.format(originalfile=sourcepng, 
                                 newfile=distortedpng.as_posix(),
                                idiff_bin=IDIFF_BIN, 
                                newfilediff=diffpng.as_posix())
        print(f"\n\nIdiff command: {cmd}", file=log_file_object)
        
        output = subprocess.run(shlex.split(cmd), check=False, stdout=subprocess.PIPE).stdout
        lines = output.decode("utf-8").splitlines()
        print("\n".join(lines), file=log_file_object)
        if len(lines) < 2:
            result['result'] = "Unable to run idiff"
            result['success'] = False
        else:
            result = {'success': True, 'result': lines[-1]}
            for line in lines[:-1]:
                if " = " not in line:
                    continue
                key, value = line.split(" = ")
                key = key.strip().replace(" ", "_").lower()
                if key == "max_error":
                    value, location = value.split(" @ ")
                    result['max_location'] = location
                else:
                    value = value.strip()
                result[key] = float(value)
    enc_meta = get_test_metadata_dict(test_ref)
    enc_meta['results'].update(result)

def assertresults_compare(source_clip, test_ref, testname, comparisontestinfo, source_path, distorted, log_file_object):
    """
    Check the results of the tests against known values (or value ranges).
    We assume that we have already run some tests, and just want to check that the values are good.
    
    source_clip -- The original clip that the new media is based on. (not used)
    test_ref    -- The generated movie we are testing.(not used)
    testname    -- The testname we are running.
    comparisontestinfo -- other parameters that can be used to configure the test.

    testresult - Was the test able to run (Completed = Yes)
    success - Boolean, was the test a success. 
    """
    tests = comparisontestinfo.get("tests", [])
    enc_meta = get_test_metadata_dict(test_ref)
    result = enc_meta['results']
    resultstatus = True
    if not result['success']:
        # If the processing wasnt a success, we fail.
        return
    for test in tests:
        if "assert" not in test:
            print(f"WARNING: no test to run in test:{test} expecting a field called assert with the test type.")
            continue
        testname = test.get("assert")
        testvalue = test.get("value") # which field to test.
        if testvalue not in result:
            print(f"Skipping test {test} since value {testvalue} is not in results: {result}")
            continue

        if testname == "between":
            if "between" not in test:
                print(f"WARNING: Skipping test since there is no between values, in: {test}")
            values = test.get("between")
            resultstatus = result[testvalue] > values[0] and result[testvalue] < values[1]
            print(f"{'Pass' if resultstatus else 'Fail'} Parameter:{testvalue} > {values[0]} and {testvalue} < {values[1]} ", file=log_file_object)
        if testname == "greater":
            if "greater" not in test:
                print(f"WARNING: Skipping test since there is no greater values, in : {test}")
                continue
            value = test.get("greater")
            resultstatus = result[testvalue] > value
            print(f"{'Pass' if resultstatus else 'Fail'} Parameter:{testvalue} > {value}", file=log_file_object)
        if testname == "less":
            if "less" not in test:
                print(f"WARNING: Skipping test since there is no greater values, in :{test}")
                continue
            value = test.get("less")
            resultstatus = result[testvalue] < value

            print(f"{'Pass' if resultstatus else 'Fail'} Parameter:{testvalue} < {value}", file=log_file_object)
        if testname == "stringmatch":
            if "string" not in test:
                print(f"WARNING: Skipping test since there is no string to match in : {test}")
                continue
            value = test.get("string")
            resultstatus = result[testvalue] == value
            print(f"{'Pass' if resultstatus else 'Fail'} Parameter:{testvalue} == {value}", file=log_file_object)

        if not resultstatus:
            break
    if resultstatus:
        result['success'] = True
        result['testresult'] = "Test Passed"
    else:
        result['success'] = False
        result['testresult'] = "Test Failed"

def prep_sources(args, test_sources=None):
    bin = otio.schema.SerializableCollection()

    # Priority of sources
    # args.source | test_configs | source_folder

    source_configs = []
    #if args.sources:
    #    for path in args.sources:
    #        source_configs.extend(parse_config_file(Path(path)))

    if test_sources:
        source_configs.extend(test_sources)
    else:
        source_configs = get_source_configs(args, args.source_folder, SOURCE_SUFFIX)

    for clipconfig in source_configs:
        test_name = None
        # A tuple indicates the source is from a test_config
        if isinstance(clipconfig, tuple):
            # We need to split source and test name
            clipconfig, test_name = clipconfig

        # Create an OTIO clip
        source_clip = create_clip(clipconfig)

        # Add breadcrumb indicating this source came from a test config.
        if test_name:
            source_clip.metadata['source_test_name'] = test_name

        # Add to bin
        bin.append(source_clip)

    return bin



def run_tests(args, config_data, timeline):
    track_map = {}

    print(f"\n\nRunning test suite {config_data.config_file()}\n")

    # Gather test configs
    tests = config_data.tests()

    for test_config in tests:
        # Check for sources in test configs
        test_sources = test_config.sources()

        identity_distort_clips = {}

        # Prepare sources for tests
        source_bin = prep_sources(args, test_sources)
        for source_clip in source_bin:
            references = source_clip.media_references()
            # Check if source is defined in test config
            source_test_name = source_clip.metadata.get('source_test_name')
            if source_test_name and source_test_name != test_config.get('name'):
                # We don't want to process sources not mentioned in the test
                continue

            # Create an encoder instance
            encoder = encoder_factory(
                source_clip,
                test_config,
                config_data.get("destination")
            )

            # Run tests and get a dict of resulting media references
            results = encoder.run_wedges()

            comparisontests = test_config.get("comparisontest", [{'testtype': 'vmaf'}])

            # Compare results against source
            source_path, _ = get_source_path(source_clip)
            for test_name, test_ref in results.items():
                # Lets add some machine stats.
                enc_meta = get_test_metadata_dict(test_ref)
                enc_meta['host_config'] = {
                    'os': platform.system(),
                    'os_version': platform.release(),
                    'arch': platform.architecture(),
                    'processor': platform.processor(),
                    'hostname': platform.node(),
                }
                distorted = Path(test_ref.target_url)

                print(f"Testing: {distorted.name}")
                # Send all the log output of the tests to a separate log file.
                log_file = Path(distorted.parent, distorted.stem + "_tests.log")
                with open(log_file, "w") as log_file_object:
                    for test in comparisontests:
                        t1 = time.perf_counter()

                        testtype = test.get("testtype", "vmaf")
                        print(f"\t {testtype}")
                        print("######################", file=log_file_object)
                        print(f"Test: {testtype}", file=log_file_object)

                        if testtype == 'identity':
                            identity_compare(identity_distort_clips, source_clip, test_ref, test_name, test, source_path, distorted, log_file_object)
                        if testtype == "vmaf":
                            vmaf_compare(source_clip, test_ref, test_name, test, source_path, distorted, log_file_object)
                        if testtype == "idiff":
                            idiff_compare(source_clip, test_ref, test_name, test, source_path, distorted, log_file_object)
                        if testtype == "assertresults":
                            assertresults_compare(source_clip, test_ref, test_name, test, source_path, distorted, log_file_object)
                        enctime = time.perf_counter() - t1
                        print(f"\t\t took: {enctime:.2f} seconds. ")

            # Update dict of references
            references.update(results)

            # Add media references to clip
            source_clip.set_media_references(
                references, source_clip.DEFAULT_MEDIA_KEY
            )

            # Get or create a track to hold test results
            encoder_version = encoder.get_application_version()
            track = track_map.setdefault(
                encoder_version,
                otio.schema.Track(name=encoder_version)
            )

            # We need to copy the clip since there can only be one instance
            # pr/timeline
            # Add clip to track
            if source_clip not in track:
                track.append(deepcopy(source_clip))

    timeline.tracks.extend(track_map.values())


def main():
    args = parse_args()

    # Make sure we have a folder for test configs
    Path(args.test_config_dir).mkdir(parents=True, exist_ok=True)

    if args.prep_sources:
        create_source_config_files(args)
        return

    # Load test config file(s)
    test_configs = []
    if args.test_config_file:
        test_configs.append(TestSuite(Path(args.test_config_file)))

    else:
        test_configs.extend(
            get_configs(args, args.test_config_dir, ENCODE_TEST_SUFFIX)
        )

    for test_config in test_configs:
        # Figure out where we are writing the otio file to
        # Which if args.output is not defined it will goto the encode
        # folder based on the first test in the config file.
        destination_folder = destination_from_config(
            test_config,
            args.output,
            Path(args.results_folder)
        )
        output_file = args.output
        if output_file == '':
            # We base it on the test filename
            output_file = destination_folder / f"{Path(test_config.config_file()).stem}.otio"
            print("Outputfile:", output_file)
        
        if output_file.exists() and output_file.stat().st_mtime > test_config.config_file().stat().st_mtime:
            print(f"Skipping test {test_config.config_file()}")
            continue

        # Want to get the encoder version, we make a dummy encoder-factory.

        # Store results in a timeline, so we can view the results in otioview
        timeline = otio.schema.Timeline(name='aswf-encoding-tests')
        timeline.metadata['config_file'] = test_config.config_file().as_posix()
        timeline.metadata['test_start'] = time.strftime("%Y-%m-%d %I:%M:%S")
        t = time.time()
        # Run tests
        run_tests(args, test_config, timeline)

        timeline.metadata["test_duration"] = time.time() - t
        timeline.metadata['test_end'] = time.strftime("%Y-%m-%d %I:%M:%S")

        # Serialize to *.otio
        otio.adapters.write_to_file(timeline, str(output_file))

        # Generate any reports (if specified in file)
        if not args.skip_reports:
            processTemplate(test_config, timeline)
    
    # Output the index of all the reports in the specified folder.
    outputSummaryIndex(args.results_folder)


if __name__== '__main__':
    main()
