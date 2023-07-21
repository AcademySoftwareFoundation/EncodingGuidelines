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

from pathlib import Path

from .encoders import encoder_factory

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper

except ImportError:
    from yaml import SafeLoader, SafeDumper

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

from .utils.outputTemplate import processTemplate

ENCODE_TEST_SUFFIX = '.yml'
SOURCE_SUFFIX = '.yml'

# We assume macos and linux both have the same binary name
FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    sys.platform == 'win' and 'ffmpeg.exe' or 'ffmpeg'
)


VMAF_LIB_DIR = os.getenv(
    'VMAF_LIB_DIR',
    f'{os.path.dirname(__file__)}/../.venv/usr/local/lib/x86_64-linux-gnu'
)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--sources',
        action='store',
        nargs='+',
        default=[],
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
        default='./encoded',
        help='Where to store the encoded files'
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
        default='encoding-test-results.otio',
        help='Path to results file including ".otio" extenstion '
             '(default: ./encoding-test-results.otio)'
    )

    args = parser.parse_args()

    if not args.output.endswith('.otio'):
        args.output += '.otio'

    return args


def parse_config_file(path):
    config_file = path.absolute().as_posix()
    with open(config_file, 'rt') as f:
        config = list(yaml.load_all(f, SafeLoader))
        config[0]['config_path'] = config_file # Stash where the config file is, useful for reporting and relative paths.

    test_configs = []
    for test_config in config:
        # Store path to config file for future reference.
        test_name = next(iter(test_config))
        if test_name.startswith('test_'):
            # Only store config path for tests
            test_config[test_name]['test_config_path'] = config_file

        test_configs.append(test_config)

    return test_configs


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


def get_configs(args, root_path, config_type):
    configs = []
    for item in scantree(args, root_path, suffix=config_type):
        path = Path(item.path)
        if path.suffix == config_type:
            configs.extend(parse_config_file(path))

    return configs


def tests_only(test_configs):
    """
    Scan the test-configs for just the test configurations (since it can be co-mingled with output and source info).
    Each test must start with the label test" to not confuse it with other configs.
    """
    configs = []
    for config in test_configs:
        for section in config:
            if section.lower().startswith('test'):
                configs.append(config[section])

    return configs


def vmaf_compare(source_clip, test_ref, testname, comparisontestinfo):
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
    # Get settings from metadata used as basis for encoded media
    source_meta = get_source_metadata_dict(source_clip)
    input_args = ''
    if source_meta.get('images'):
        input_args = f"-start_number {source_meta.get('in')}"

    source_path, _ = get_source_path(source_clip)
    reference = f'{input_args} -i "{source_path}" '

    # Assuming all encoded files are video files for now
    distorted = test_ref.target_url

    cmd = vmaf_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        reference=reference,
        distorted=distorted,
        duration=source_meta.get('duration'),
        vmaf_model=get_nearest_model(int(source_meta.get('width', 1920)))
    )
    print(f'VMAF command: {cmd}")

    env = os.environ
    if 'LD_LIBRARY_PATH' in env:
        env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

    else:
        env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

    subprocess.call(shlex.split(cmd), env=env)
    with open(f'compare_log.json', 'rb') as f:
        raw_results = json.load(f)

    results = {
        'vmaf': raw_results['pooled_metrics'].get('vmaf'),
        'psnr': raw_results['pooled_metrics'].get('psnr'),   # FFmpeg < 5.1
        'result': "Completed"
    }

    # FFmpeg >= 5.1 have split psnr results
    if not results['psnr']:
        for key in ['psnr_y', 'psnr_cb', 'psnr_cr']:
            results[key] = raw_results['pooled_metrics'].get(key)

    enc_meta = get_test_metadata_dict(test_ref)
    enc_meta['results'].update(results)

def idiff_compare(source_clip, test_ref, testname, comparisontestinfo):
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

    default_extract_template = "ffmpeg -y -i {newfile} -compression_level 10 -pred mixed -pix_fmt rgb48be  -frames:v 1 -sws_flags spline+accurate_rnd+full_chroma_int {newpngfile}"
    extract_template = comparisontestinfo.get("extracttemplate", default_extract_template)

    # Allow a different image to be compared with, useful for 422 or 420 encoding.
    sourcepng = comparisontestinfo.get("compare_image", source_path.as_posix())

    distortedbase, distortedext = os.path.splitext(distorted)
    distortedpng = os.path.join(os.path.dirname(distorted), distortedbase + ".png")

    extractcmd = extract_template.format(newfile=distorted, newpngfile=distortedpng)
    print(f"About to extract with cmd: {extractcmd}")
    result = {'success': False,
              'result': "undefined"
    }
    cmdresult = subprocess.call(shlex.split(extractcmd))
    if cmdresult != 0:
        result['result'] = "Unable to extract file for test"
    else:
        cmd = apptemplate.format(originalfile=source_path, newfile=distortedpng)
        print(f"Idiff command: {cmd}")
        
        output = subprocess.run(shlex.split(cmd), check=False, stdout=subprocess.PIPE).stdout
        lines = output.decode("utf-8").splitlines()
        if len(lines) < 2:
            result['result'] = "Unable to run idiff"
            result['success'] = False
        else:
            result = {'success': lines[-1] == "PASS", 'result': lines[-1]}
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

def assertresults_compare(source_clip, test_ref, testname, comparisontestinfo):
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
        if testname == "greater":
            if "greater" not in test:
                print(f"WARNING: Skipping test since there is no greater values, in : {test}")
            value = test.get("greater")
            resultstatus = result[testvalue] > value
        if testname == "less":
            if "less" not in test:
                print(f"WARNING: Skipping test since there is no greater values, in :{test}")
            value = test.get("less")
            resultstatus = result[testvalue] < value
 
        if testname == "stringmatch":
            if "string" not in test:
                print(f"WARNING: Skipping test since there is no string to match in : {test}")
            value = test.get("string")

            resultstatus = result[testvalue] == value
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
    if args.sources:
        for path in args.sources:
            source_configs.extend(parse_config_file(Path(path)))

    elif test_sources:
        source_configs.extend(test_sources)

    else:
        source_configs = get_configs(args, args.source_folder, SOURCE_SUFFIX)

    for config in source_configs:
        test_name = None
        # A tuple indicates the source is from a test_config
        if isinstance(config, tuple):
            # We need to split source and test name
            config, test_name = config

        # Create an OTIO clip
        source_clip = create_clip(config)

        # Add breadcrumb indicating this source came from a test config.
        if test_name:
            source_clip.metadata['source_test_name'] = test_name

        # Add to bin
        bin.append(source_clip)

    return bin


def check_for_sources(test_configs):
    """Grab the image source paths from the test_configs file (which are optional)"""
    sources = []
    for test_config in test_configs:
        # Check if config contains sources to test against
        for source in test_config.get('sources', []):
            for source_config in parse_config_file(Path(source)):
                sources.append(
                    (source_config, test_config.get('name'))
                )

    return sources


def run_tests(args, test_configs, timeline):
    track_map = {}

    # Gather test configs
    test_configs = tests_only(test_configs)

    # Check for sources in test configs
    test_sources = check_for_sources(test_configs)

    # Prepare sources for tests
    source_bin = prep_sources(args, test_sources)

    for source_clip in source_bin:
        references = source_clip.media_references()

        for test_config in test_configs:
            # Check if source is defined in test config
            source_test_name = source_clip.metadata.get('source_test_name')
            if source_test_name and source_test_name != test_config.get('name'):
                # We don't want to process sources not mentioned in the test
                continue

            # Create an encoder instance
            encoder = encoder_factory(
                source_clip,
                test_config,
                Path(args.encoded_folder)
            )

            # Run tests and get a dict of resulting media references
            results = encoder.run_wedges()

            comparisontests = [{'testtype': 'vmaf'}]
            if "comparisontest" in test_config:
                comparisontests = test_config.get("comparisontest")

            # Compare results against source
            for test_name, test_ref in results.items():
                for test in comparisontests:
                    testtype = test.get("testtype", "vmaf")
                    if testtype == "vmaf":
                        vmaf_compare(source_clip, test_ref, test_name, test)
                    if testtype == "idiff":
                        idiff_compare(source_clip, test_ref, test_name, test)
                    if testtype == "assertresults":
                        assertresults_compare(source_clip, test_ref, test_name, test)

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

    # Make sure we have a destination folder
    Path(args.encoded_folder).mkdir(parents=True, exist_ok=True)

    # Load test config file(s)
    test_configs = []
    if args.test_config_file:
        test_configs.extend(parse_config_file(Path(args.test_config_file)))

    else:
        test_configs.extend(
            get_configs(args, args.test_config_dir, ENCODE_TEST_SUFFIX)
        )

    # Store results in a timeline, so we can view the results in otioview
    timeline = otio.schema.Timeline(name='aswf-encoding-tests')

    # Run tests
    run_tests(args, test_configs, timeline)

    # Serialize to *.otio
    otio.adapters.write_to_file(timeline, args.output)

    # Generate any reports (if specified in file)
    if not args.skip_reports:
        processTemplate(test_configs, timeline)


if __name__== '__main__':
    main()
