import os
import time
import shlex
import pathlib
import subprocess
from typing import Tuple
from datetime import datetime, timezone

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
        super(FFmpegEncoder, self).__init__(
            source_clip,
            test_config,
            destination
        )

    def run_wedges(self) -> dict:
        # The results dictionary is passed to source clip's list of available
        # media references. Key is test name and value is media reference
        results = {}
        for wedge_name, wedge in self.test_config.get('wedges', {}).items():
            # Test name is based on main test name and wedge name
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

            # !! Use this function from utils to create a media reference
            # of output the file.
            mr = create_media_reference(out_file, self.source_clip)

            # Update metadata for use later
            # !! Use this function from utils to make sure we find the metadata
            # later on
            test_meta = get_test_metadata_dict(mr)
            test_meta['test_config_path'] = self.test_config.get(
                'test_config_path'
            )
            test_meta['encode_arguments'] = wedge
            test_meta['description'] = self.test_config.get('description')

            result_meta = test_meta.setdefault('results', {})
            result_meta['completed_utc'] = \
                datetime.now(timezone.utc).isoformat()
            result_meta['encode_time'] = round(enctime, 4)
            result_meta['filesize'] = out_file.stat().st_size

            # Add media reference to result list
            results.update({test_name: mr})

        return results

    def get_application_version(self) -> str:
        if not self._application_version:
            cmd = f'ffmpeg -version -v quiet -hide_banner'
            _raw = subprocess.check_output(shlex.split(cmd))
            version = b'_'.join(_raw.split(b' ')[:3])

            self._application_version = str(version, 'utf-8')

        return self._application_version

    def prep_encoding_command(self, wedge: dict, out_file: pathlib.Path) -> str:
        template = self.test_config.get('encoding_template')

        source_path, _ = self.get_source_path()
        source_meta = self.source_clip.metadata['aswf_enctests']['source_info']

        input_args = ''
        if source_meta.get('images'):
            input_args = f"-start_number {source_meta.get('in')}"

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

