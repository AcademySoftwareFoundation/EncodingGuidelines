import os
import sys
import yaml
import time
import json
import pyseq
import shlex
import argparse
import subprocess

from pathlib import Path
from copy import deepcopy

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper

except ImportError:
    from yaml import SafeLoader, SafeDumper

import opentimelineio as otio


# Test config files
from utils import sizeof_fmt, get_media_info, get_nearest_model

ENCODE_TEST_SUFFIX = '.yml'
SOURCE_SUFFIX = '.yml'

# We assume macos and linux both have the same binary name
FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    'win' in sys.platform and 'ffmpeg.exe' or 'ffmpeg'
)


VMAF_LIB_DIR = os.getenv(
    'VMAF_LIB_DIR',
    f'{os.path.dirname(__file__)}/.venv/usr/local/lib/x86_64-linux-gnu'
)


def parse_args():
    parser = argparse.ArgumentParser()
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
        help='Where to look for *.enctest files'
    )

    parser.add_argument(
        '--prep-sources',
        action='store_true',
        default=False,
        help='Create *.source files for media in --source-folder'
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
        help='Encode all tests. Default to only encoding new tests'
    )

    parser.add_argument(
        '--output',
        action='store',
        default='encoding-test-results.otio',
        help='Full path to results file (.otio)'
    )

    args = parser.parse_args()

    if not args.output.endswith('.otio'):
        args.output += '.otio'

    return args


def parse_config_file(path):
    config_file = path.as_posix()
    with open(config_file, 'rt') as f:
        config = yaml.load(f, SafeLoader)

    return config


def create_media_reference(path, source_clip):
    config = get_source_metadata_dict(source_clip)
    rate = float(config.get('rate'))
    duration = float(config.get('duration'))

    if path.is_dir():
        # Create ImageSequenceReference
        seq = pyseq.get_sequences(path.as_posix())[0]
        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                seq.start(), rate
            ),
            duration=otio.opentime.RationalTime(
                seq.length(), rate
            )
        )
        mr = otio.schema.ImageSequenceReference(
            target_url_base=Path(seq.directory()).as_posix(),
            name_prefix=seq.head(),
            name_suffix=seq.tail(),
            start_frame=seq.start(),
            frame_step=1,
            frame_zero_padding=len(max(seq.digits, key=len)),
            rate=rate,
            available_range=available_range
        )

    else:
        # Create ExternalReference
        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                0, rate
            ),
            duration=otio.opentime.RationalTime(
                duration, rate
            )
        )
        mr = otio.schema.ExternalReference(
            target_url=path.resolve().as_posix(),
            available_range=available_range,
        )
        mr.name = path.name

    return mr


def create_clip(config):
    path = Path(config.get('path'))

    clip = otio.schema.Clip(name=path.stem)
    clip.metadata.update({'aswf_enctests': {'source_info': deepcopy(config)}})

    # Source range
    clip.source_range = get_source_range(config)
    clip.start_frame = config.get('in')

    # The initial MediaReference is stored as default
    mr = create_media_reference(path, clip)
    clip.media_reference = mr

    return clip


def get_source_range(config):
    source_range = otio.opentime.TimeRange(
        start_time=otio.opentime.RationalTime(
            config.get('in'),
            config.get('rate')
        ),
        duration=otio.opentime.RationalTime.from_seconds(
            config.get('duration') /
            config.get('rate'),
            config.get('rate')
        )
    )

    return source_range


def create_config_from_source(path, startframe=None):
    config_data = {'source_info': {'input_args': {}}}

    media_info = get_media_info(path, startframe)
    if not media_info:
        return

    config_data.update(media_info)

    if startframe:
        config_data['source_info']['input_args'].update(
            {'-start_number': startframe}
        )

    config_path = path.with_suffix(path.suffix + SOURCE_SUFFIX)
    with open(config_path, 'wt') as f:
        yaml.dump(config_data, f, SafeDumper, indent=4)


def scantree(args, path, suffix=None):
    """Recursively yield DirEntry objects for given directory."""
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            sequences = pyseq.get_sequences(entry.path)
            if args.prep_sources and sequences:
                for sequence in sequences:
                    if sequence.name.endswith(".source"):
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


def get_configs(args, root_dir, config_type):
    configs = []
    for item in scantree(args, root_dir, suffix=config_type):
        path = Path(item.path)
        if path.suffix == config_type:
            config = parse_config_file(path)
            configs.append(config)

    return configs


def tests_only(test_configs):
    for config in test_configs:
        for section in config:
            if section.lower().startswith('test'):
                yield config[section]


def get_source_path(source_clip):
    source_mr = source_clip.media_reference
    symbol = ''
    path = Path()
    if isinstance(source_mr, otio.schema.ExternalReference):
        path = Path(source_mr.target_url)

    elif isinstance(source_mr, otio.schema.ImageSequenceReference):
        symbol = f'%0{source_mr.frame_zero_padding}d'
        path = Path(source_mr.abstract_target_url(symbol=symbol))

    return path, symbol


def get_source_metadata_dict(source_clip):
    return source_clip.metadata['aswf_enctests']['source_info']


def get_test_metadata_dict(otio_item, testname):
    ffmpeg_version = get_ffmpeg_version()
    aswf_meta = otio_item.metadata.setdefault('aswf_enctests', {})
    enc_meta = aswf_meta.setdefault(testname, {})

    return enc_meta.setdefault(ffmpeg_version, {})


def get_ffmpeg_version():
    cmd = f'{FFMPEG_BIN} -version -v quiet -hide_banner'
    _raw = subprocess.check_output(shlex.split(cmd))
    version = b'_'.join(_raw.split(b' ')[:3])

    return version


def ffmpeg_convert(args, source_clip, test_config, wedge, testname):
    ffmpeg_cmd = test_config.get('encoding_template')

    source_path, symbol = get_source_path(source_clip)

    # Append test name to source filename
    stem = source_path.stem.replace(symbol, '')
    out_file = Path(args.encoded_folder).absolute().joinpath(
        f"{stem}-{testname}{test_config.get('suffix')}"
    )
    source_meta = get_source_metadata_dict(source_clip)
    input_args = ' '.join(
        [f'{key} {value}' for key, value in
         source_meta.get('input_args', {}).items()]
    )

    encoding_args = ' '.join(
        [f'{key} {value}' for key, value in
         test_config['wedges'][wedge].items()]
    )

    duration = source_clip.source_range.duration.to_frames()

    cmd = ffmpeg_cmd.format(
        input_args=input_args,
        source=source_path,
        duration=duration,
        encoding_args=encoding_args,
        outfile=out_file
    )

    print('ffmpeg command:', cmd)
    # Time encoding process
    t1 = time.perf_counter()

    # Do encoding
    env = os.environ
    if 'LD_LIBRARY_PATH' in env:
        env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

    else:
        env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

    subprocess.call(shlex.split(cmd), env=env)

    # Store encoding time
    enctime = time.perf_counter() - t1

    # Create a media reference of output file
    mr = create_media_reference(out_file, source_clip)

    # Update metadata
    enc_meta = get_test_metadata_dict(mr, testname)
    enc_meta['encode_time'] = round(enctime, 4)
    enc_meta['encode_arguments'] = encoding_args
    enc_meta['filesize'] = sizeof_fmt(out_file)

    return mr


def vmaf_compare(source_clip, test_ref, testname):
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
psnr=1:\
model_path={vmaf_model}\" \
-f null -\
'
    # Get settings from metadata used as basis for encoded media
    source_meta = get_source_metadata_dict(source_clip)
    input_args = ' '.join(
        [f'{key} {value}' for key, value in
         source_meta.get('input_args', {}).items()]
    )

    source_path, _ = get_source_path(source_clip)
    reference = f'{input_args} -i "{source_path}" '

    # Assuming all encoded files are video files for now
    distorted = test_ref.target_url
    start_frame = source_clip.start_frame

    cmd = vmaf_cmd.format(
        ffmpeg_bin=FFMPEG_BIN,
        reference=reference,
        distorted=distorted,
        duration=source_meta.get('duration'),
        vmaf_model=get_nearest_model(int(source_meta.get('width', 1920)))
    )
    print('VMAF command:', cmd)

    env = os.environ
    if 'LD_LIBRARY_PATH' in env:
        env.update({'LD_LIBRARY_PATH': env['LD_LIBRARY_PATH'] + ":" + VMAF_LIB_DIR})
    else:
        env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

    subprocess.call(shlex.split(cmd), env=env)
    with open('compare_log.json', 'rb') as f:
        raw_results = json.load(f)

    results = {
        'vmaf': raw_results['pooled_metrics'].get('vmaf'),
        'psnr': raw_results['pooled_metrics'].get('psnr')
    }
    enc_meta = get_test_metadata_dict(test_ref, testname)
    enc_meta['results'] = results


def prep_sources(args, collection):
    source_configs = get_configs(args, args.source_folder, SOURCE_SUFFIX)
    for config in source_configs:
        source_clip = create_clip(config)
        collection.append(source_clip)


def run_tests(args, test_configs, collection):
    for source_clip in collection:
        references = source_clip.media_references()

        # # Create lossless reference for comparisons
        # lossless_ref = ffmpeg_convert(args, config, 'BASELINE_SETTINGS')
        # references.update({'baseline': lossless_ref})

        for test_config in tests_only(test_configs):
            # perform enctest
            for wedge in test_config['wedges']:
                testname = f"{test_config.get('name')}-{wedge}"
                print(f'Running "{testname}"')
                test_ref = ffmpeg_convert(
                    args, source_clip, test_config, wedge, testname
                )
                references.update({testname: test_ref})
                vmaf_compare(source_clip, test_ref, testname)

        # Add media references to clip
        source_clip.set_media_references(
            references, source_clip.DEFAULT_MEDIA_KEY
        )


def main():
    args = parse_args()

    if args.prep_sources:
        create_source_config_files(args)

        return

    # Make sure we have a folder for test configs
    Path(args.test_config_dir).mkdir(exist_ok=True)

    # Make sure we have a destination folder
    Path(args.encoded_folder).mkdir(exist_ok=True)

    # Load test config files
    test_configs = get_configs(args, args.test_config_dir, ENCODE_TEST_SUFFIX)

    # Create a collection object to hold clips
    collection = otio.schema.SerializableCollection(name='aswf_enctests')

    # Prep source files
    prep_sources(args, collection)

    # Run tests
    run_tests(args, test_configs, collection)

    # Store results in an *.otio file
    otio.adapters.write_to_file(collection, args.output)


if __name__== '__main__':
    main()
