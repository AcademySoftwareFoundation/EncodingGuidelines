import os
import pathlib
import json
import shlex
from subprocess import run, PIPE, CalledProcessError

VMAF_LIB_DIR = os.getenv(
    'VMAF_LIB_DIR',
    f'{os.path.dirname(__file__)}/.venv/usr/local/lib/x86_64-linux-gnu'
)


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


def get_media_info(path):
    cmd = f'ffprobe ' \
          f'-v quiet ' \
          f'-hide_banner ' \
          f'-print_format json ' \
          f'-show_streams ' \
          f'-i "{path.as_posix()}"'

    env = os.environ
    env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})
    print(cmd)
    try:
        proc = run(shlex.split(cmd), capture_output=True, env=env, check=True)
        raw_json = json.loads(proc.stdout)

    except CalledProcessError as err:
        print(f'Unable to probe "{path.name}, {err}"')
        return None

    stream = None
    for raw_stream in raw_json.get('streams'):
        if raw_stream.get('codec_type') == 'video':
            stream = raw_stream
            break

    if not stream:
        print(f'Unable to locate video stream in "{path.name}"')
        return None

    info = {
        'path': path.as_posix(),
        'width': stream.get('width'),
        'heigth': stream.get('height'),
        'in': 0,
        'duration': stream.get('nb_frames', stream.get('duration_ts', 1)),
        'rate': calculate_rate(stream.get('r_frame_rate'))
    }

    return info


if __name__ == '__main__':
    path = pathlib.Path(
        '/home/daniel/Desktop/encoding_test_files/'
        'face_HEVC 100mbps VBR High - Good.mp4'
    )
    info = get_media_info(path=path)
    print(info)
