import os
import json
import shlex
import fileseq
from pathlib import Path
from subprocess import run, CalledProcessError

import opentimelineio as otio

VMAF_MODEL_DIR = os.getenv(
    'VMAF_MODEL_DIR',
    '/usr/share/vmaf'
)

# Which vmaf model to use
VMAF_HD_MODEL = Path(VMAF_MODEL_DIR, "vmaf_v0.6.1.json")


VMAF_4K_MODEL = Path(VMAF_MODEL_DIR, "vmaf_4k_v0.6.1.json")


# Based on accepted answer here:
# https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
def sizeof_fmt(path, suffix="B"):
    num = os.path.getsize(path)
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0

    return f"{num:.1f}Yi{suffix}"


def calculate_rate(rate_str):
    numerator, denominator = rate_str.split('/')
    return float(numerator) / float(denominator)


def get_nearest_model(width):
    models = {
        1920: VMAF_HD_MODEL,
        4096: VMAF_4K_MODEL
    }
    diff = lambda list_value: abs(list_value - width)

    return models[min(models, key=diff)].as_posix()


def get_media_info(path, startframe=None):
    input_args = ''
    if startframe:
        input_args = f'-start_number {startframe} '

    cmd = f'ffprobe ' \
          f'-v quiet ' \
          f'-hide_banner ' \
          f'-print_format json ' \
          f'-show_streams ' \
          f'{input_args}' \
          f'-i "{path.as_posix()}"'

    print(f'Probe command: {cmd}')
    env = os.environ
    if 'LD_LIBRARY_PATH' in env:
        env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

    else:
        env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

    try:
        proc = run(shlex.split(cmd), capture_output=True, env=env, check=True)
        raw_json = json.loads(proc.stdout)

    except CalledProcessError as err:
        print(f'Unable to probe "{path.name}, {err}"')
        return None

    stream = None
    for raw_stream in raw_json.get('streams', []):
        if raw_stream.get('codec_type') == 'video':
            stream = raw_stream
            break

    if not stream:
        print(f'Unable to locate video stream in "{path.name}"')
        return None

    info = {
        'path': path.as_posix(),
        'width': stream.get('width'),
        'height': stream.get('height'),
        'pix_fmt': stream.get('pix_fmt'),
        'in': startframe or 0,
        'duration': int(stream.get('nb_frames', stream.get('duration_ts', 1))),
        'rate': calculate_rate(stream.get('r_frame_rate'))
    }

    return info


def create_media_reference(path, source_clip, is_sequence=False):
    config = get_source_metadata_dict(source_clip)
    rate = float(config.get('rate'))
    duration = float(config.get('duration'))

    if is_sequence:
        # Create ImageSequenceReference
        # TODO find a less error prone way to find correct sequence
        parentdir = path.parent.as_posix()
        if not os.path.exists(parentdir):
            print("Warning: ", path, " doesnt exist")
            return
        seq = max(
            fileseq.findSequencesOnDisk(parentdir),
           key=lambda s: len(s)
        )
        available_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                seq.start(), rate
            ),
            duration=otio.opentime.RationalTime(
                len(seq), rate
            )
        )

        mr = otio.schema.ImageSequenceReference(
            target_url_base=Path(seq.dirname()).as_posix(),
            name_prefix=seq.basename(),
            name_suffix=seq.extension(),
            start_frame=seq.start(),
            frame_step=1,
            frame_zero_padding=seq.zfill(),
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


def get_test_metadata_dict(otio_clip):
    aswf_meta = otio_clip.metadata.setdefault('aswf_enctests', {})

    return aswf_meta


def get_source_metadata_dict(source_clip):
    return source_clip.metadata['aswf_enctests']['source_info']


def create_clip(config):
    path = config.path()

    clip = otio.schema.Clip(name=path.stem)
    clip.metadata.update({'aswf_enctests': {'source_info': config.dictcopy()}})

    # Source range
    clip.source_range = get_source_range(config)
    clip.start_frame = config.get('in')

    # Check if we have an image sequence source
    is_sequence = config.get('images', False)

    # The initial MediaReference is stored as default
    mr = create_media_reference(path, clip, is_sequence)
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
