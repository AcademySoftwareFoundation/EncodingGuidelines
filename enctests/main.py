import os
import sys
import time
import timeit
from copy import deepcopy

import pyseq
import shlex
import argparse
import subprocess
import configparser

from pathlib import Path
import opentimelineio as otio

# Test config files
from enctests.utils import sizeof_fmt

ENCODE_SETTINGS_SUFFIX = '.enctest'

# OpenImageIO
OIIOTOOL_BIN = os.getenv(
    "OIIOTOOL_BIN",
    "oiiotool"
)

IDIFF_BIN = os.getenv(
    "IDIFF_BIN",
    "idiff"
)

# We assume macos and linux both have the same binary name
FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    'win' in sys.platform and 'ffmpeg.exe' or 'ffmpeg'
)

# Which vmaf model to use
VMAF_MODEL = os.getenv(
    'VMAF_MODEL',
    "vmaf_v0.6.1.json"
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
        '--test-config-folder',
        action='store',
        default='./sources',
        help='Where to look for *.enctest files'
    )

    parser.add_argument(
        '--prep-tests',
        action='store_true',
        default=False,
        help='Create *.enctest files from media in --source-folder'
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
    encfile = path.as_posix()
    config = configparser.ConfigParser()
    config.read(encfile)

    return config


def create_media_reference(path, config):
    file_desc = config['SOURCE_INFO']

    if path.is_dir():
        # Create ImageSequenceReference
        seq = pyseq.get_sequences(path.as_posix())[0]
        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                seq.start(), file_desc.getfloat('rate')
            ),
            duration=otio.opentime.RationalTime(
                seq.length(), file_desc.getfloat('rate')
            )
        )
        mr = otio.schema.ImageSequenceReference(
            target_url_base=Path(seq.directory()).as_uri(),
            name_prefix=seq.head(),
            name_suffix=seq.tail(),
            start_frame=seq.start(),
            frame_step=1,
            frame_zero_padding=len(max(seq.digits, key=len)),
            rate=file_desc.getfloat('rate'),
            available_range=available_range
        )

    else:
        # Create ExternalReference
        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                0, file_desc.getfloat('rate')
            ),
            duration=otio.opentime.RationalTime(
                file_desc.getint('duration'), file_desc.getfloat('rate')
            )
        )
        mr = otio.schema.ExternalReference(
            target_url=path.resolve().as_uri(),
            available_range=available_range
        )

    return mr


def create_clip(args, config):
    path = Path(args.source_folder).joinpath(
        Path(config.get('SOURCE_INFO', 'path'))
    )
    clip = otio.schema.Clip(name=path.stem)

    # Source range
    clip.source_range = get_source_range(config, 'SOURCE_INFO')
    # The initial MediaReference is stored as default
    mr = create_media_reference(path, config)
    clip.media_reference = mr

    return clip


def get_source_range(config, test_name):
    source_range = otio.opentime.TimeRange(
        start_time=otio.opentime.RationalTime(
            config.getint(test_name, 'in'),
            config.getfloat('SOURCE_INFO', 'rate')
        ),
        duration=otio.opentime.RationalTime.from_seconds(
            config.getint(test_name, 'duration') /
            config.getint(test_name, 'rate'),
            config.getfloat('SOURCE_INFO', 'rate')
        )
    )

    return source_range


def create_enctest_files(args):
    with os.scandir(args.source_folder) as it:
        for item in it:
            path = Path(item.path)
            if path.suffix == ENCODE_SETTINGS_SUFFIX:
                # We only register new media
                continue

            if path.is_dir():
                seq = pyseq.get_sequences(path.as_posix())[0]


def get_test_configs(args):
    configs = []
    with os.scandir(args.source_folder) as it:
        for item in it:
            path = Path(item.path)
            if path.suffix != ENCODE_SETTINGS_SUFFIX:
                continue

            config = parse_config_file(path)
            configs.append(config)

    return configs


def get_ffmpeg_version():
    cmd = f'{FFMPEG_BIN} -version -v quiet -hide_banner'
    _raw = subprocess.check_output(shlex.split(cmd))
    version = b'_'.join(_raw.split(b' ')[:3])

    return version


def tests_only(config):
    for section in config.sections():
        if section.lower().startswith('test'):
            yield section


def get_source_path(args, config):
    path = Path(args.source_folder).joinpath(
        Path(config.get('path'))
    )
    if path.is_dir():
        return pyseq.get_sequences(path.as_posix())[0]

    return path


def get_test_metadata(otio_item, testname):
    ffmpeg_version = get_ffmpeg_version()
    aswf_meta = otio_item.metadata.setdefault('aswf', {})
    enc_meta = aswf_meta.setdefault(ffmpeg_version, {})

    return enc_meta.setdefault(testname, {})


def ffmpeg_convert(args, config, testname):
    ffmpeg_cmd = "\
{ffmpeg_bin} \
{input_args} \
-i {source} \
-vframes {duration}\
{compression_args} \
-y {outfile}\
"
    source_config = config['SOURCE_INFO']
    test_config = dict(config['BASELINE_SETTINGS'])
    test_config.update(config[testname])
    print(test_config)

    source_path = get_source_path(args, source_config)

    symbol = ''
    if source_path.length():
        symbol = f'%0{len(max(source_path.digits, key=len))}d'
        source_file = Path(
            source_path.path().replace(source_path.format('%r'), symbol)
        )

    else:
        source_file = Path(source_path)
    
    # Append test name to source filename
    stem = source_file.stem.replace(symbol, '')
    out_file = Path(args.encoded_folder).absolute().joinpath(
        f"{stem}-{testname}{test_config.get('suffix')}"
    )
    
    input_args = ' '.join(
        test_config.get('input_args').split('\n')
    )
    encoding_args = ' '.join(
        test_config.get('encoding_args').split('\n')
    )

    cmd = ffmpeg_cmd.format(
                ffmpeg_bin=FFMPEG_BIN,
                input_args=input_args,
                source=source_file,
                duration=source_config.getint('duration'),
                compression_args=encoding_args,
                outfile=out_file
            )

    print('ffmpeg command:', cmd)
    # Time encoding process
    t1 = time.perf_counter()

    # Do encoding
    subprocess.call(shlex.split(cmd))

    # Store encoding time
    enctime = time.perf_counter() - t1

    # Create a media reference of output file
    mr = create_media_reference(out_file, config)

    # Update metadata
    enc_meta = get_test_metadata(mr, testname)
    enc_meta['encode_time'] = round(enctime, 4)
    enc_meta['encode_arguments'] = encoding_args
    enc_meta['filesize'] = sizeof_fmt(out_file)

    return mr


def run_tests(args, configs):
    results = otio.schema.SerializableCollection(name='enctests')

    for config in configs:
        # Create an OTIO clip to hold encoded variations and results metadata
        source_clip = create_clip(args, config)
        references = source_clip.media_references()

        # Create lossless reference for comparisons
        lossless_ref = ffmpeg_convert(args, config, 'BASELINE_SETTINGS')
        references.update({'baseline': lossless_ref})

        for testname in tests_only(config):
            # perform enctest
            print(f'Running "{testname}"')
            test_ref = ffmpeg_convert(args, config, testname)
            references.update({testname: test_ref})

        # Add media references to clip
        source_clip.set_media_references(
            references, source_clip.DEFAULT_MEDIA_KEY
        )
        results.append(source_clip)

    return results


def main():
    args = parse_args()

    if args.prep_tests:
        create_enctest_files(args)

        return

    # Load test config files
    test_configs = get_test_configs(args)

    # Make sure we have a destination folder
    Path(args.encoded_folder).mkdir(exist_ok=True)

    # Run tests
    results = run_tests(args, test_configs)
    print(f'Results: {results}')
    print(f'Results: {results[0].media_references()}')

    # Store results in an *.otio file
    otio.adapters.write_to_file(results, args.output)


if __name__== '__main__':
    main()
