import os
import time
import shlex
import pathlib
import subprocess
from typing import Tuple

import opentimelineio as otio

from .base import ABCTestEncoder
from ..utils import (
    create_media_reference,
    get_test_metadata_dict,
    sizeof_fmt
)


VMAF_LIB_DIR = os.getenv(
    'VMAF_LIB_DIR',
    f'{os.path.dirname(__file__)}/.venv/usr/local/lib/x86_64-linux-gnu'
)


class FFmpegEncoder(ABCTestEncoder):
    def __init__(
            self,
            source_clip: otio.schema.Clip,
            test_config: dict,
            destination: pathlib.Path
    ):
        self.source_clip = source_clip
        self.test_config = test_config
        self.destination = destination

    def run_wedges(self) -> dict:
        results = {}
        for wedge_name, wedge in self.test_config.get('wedges', {}).items():
            test_name = f"{self.test_config.get('name')}-{wedge_name}"
            out_file = self.get_output_filename(test_name)

            cmd = self.prep_encoding_command(wedge, out_file)

            print('ffmpeg command:', cmd)

            # Ensure proper environment
            env = os.environ
            if 'LD_LIBRARY_PATH' in env:
                env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

            else:
                env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

            # Time encoding process
            t1 = time.perf_counter()
            # Do the encoding
            subprocess.call(shlex.split(cmd), env=env)
            # Store timing
            enctime = time.perf_counter() - t1

            # Create a media reference of output file
            mr = create_media_reference(out_file, self.source_clip)

            # Update metadata
            ffmpeg_version = self.get_application_version()
            enc_meta = get_test_metadata_dict(mr, test_name)
            test_meta = enc_meta.setdefault(ffmpeg_version, {})
            test_meta['encode_time'] = round(enctime, 4)
            test_meta['encode_arguments'] = cmd
            test_meta['filesize'] = sizeof_fmt(out_file)

            # Add media reference to result list
            results.update({test_name: mr})

        return results

    def get_application_version(self) -> str:
        cmd = f'ffmpeg -version -v quiet -hide_banner'
        _raw = subprocess.check_output(shlex.split(cmd))
        version = b'_'.join(_raw.split(b' ')[:3])

        return str(version, 'utf-8')

    def prep_encoding_command(self, wedge: dict, out_file: pathlib.Path) -> str:
        template = self.test_config.get('encoding_template')

        source_path, _ = self.get_source_path()
        source_meta = self.source_clip.metadata['aswf_enctests']['source_info']
        input_args = ' '.join(
            [f'{key} {value}' for key, value in
             source_meta.get('input_args', {}).items()]
        )

        encoding_args = ' '.join(
            [f'{key} {value}' for key, value in wedge.items()]
        )

        duration = self.source_clip.source_range.duration.to_frames()

        cmd = template.format(
            input_args=input_args,
            source=source_path,
            duration=duration,
            encoding_args=encoding_args,
            outfile=out_file
        )

        return cmd

    def get_source_path(self) -> Tuple[pathlib.Path, str]:
        source_mr = self.source_clip.media_reference
        symbol = ''
        path = pathlib.Path()
        if isinstance(source_mr, otio.schema.ExternalReference):
            path = pathlib.Path(source_mr.target_url)

        elif isinstance(source_mr, otio.schema.ImageSequenceReference):
            symbol = f'%0{source_mr.frame_zero_padding}d'
            path = pathlib.Path(source_mr.abstract_target_url(symbol=symbol))

        return path, symbol

    def get_output_filename(self, test_name: str) -> pathlib.Path:
        source_path, symbol = self.get_source_path()
        stem = source_path.stem.replace(symbol, '')

        out_file = self.destination.absolute().joinpath(
            f"{stem}-{test_name}{self.test_config.get('suffix')}"
        )

        return out_file

