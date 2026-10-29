import os
import sys
import time
import shlex
import pathlib
import subprocess
from typing import Tuple
from datetime import datetime, timezone
from pathlib import Path
import fileseq

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

# A single still image is encoded as this many frames (the tests compare the first). x265 sometimes gives a
# one-frame encode with B-frames a garbage dts, which the MOV muxer rejects ("Not yet implemented") or writes as
# a file that decodes to nothing; with more frames it does not happen.
STILL_IMAGE_FRAMES = 5
STILL_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.dpx', '.exr'}

# Seconds before an encode is killed. A looped image that fails to decode makes ffmpeg spin forever.
ENCODE_TIMEOUT = float(os.getenv('ENCODE_TIMEOUT', 1800))

FFMPEG_BIN = os.getenv(
    'FFMPEG_BIN',
    sys.platform  in ['win', 'win32'] and 'ffmpeg.exe' or 'ffmpeg'
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

    def run_wedges(self, verbose: bool) -> dict:
        # The results dictionary is passed to source clip's list of available
        # media references. Key is test name and value is media reference
        results = {}
        for wedge_name, wedge in self.test_config.get('wedges', {}).items():
            # Test name is based on main test name and wedge name
            test_name = f"{self.test_config.get('name')}-{wedge_name}"
            out_file, testbasename = self.get_output_filename(test_name)

            # Remove it, so if the new run fails to create anything 
            # we are not accidentally using the old one.
            if out_file.exists():
                out_file.unlink()

            cmd = self.prep_encoding_command(wedge, out_file)

            print(f"Creating Wedge: {test_name} from {self.get_source_path()[0].name}")

            fss = fileseq.findSequencesOnDisk(str(self.get_source_path()[0]))
            if not fss:
                print(f"ERROR: Could not find source file {self.get_source_path()[0]}")
                exit(1)
            fs = fss[0]
            for f in fs:
                with open(f, 'rb') as file:
                    file.read()

            # Ensure proper environment
            env = os.environ
            if 'LD_LIBRARY_PATH' in env:
                env['LD_LIBRARY_PATH'] += f'{os.pathsep}{VMAF_LIB_DIR}'

            else:
                env.update({'LD_LIBRARY_PATH': VMAF_LIB_DIR})

            # Time encoding process
            t1 = time.perf_counter()
            # Do the encoding
            log_file = Path(out_file.parent, out_file.stem + ".log")
            with open(log_file, "w") as log_file_object:
                if verbose:
                    print(f'ffmpeg command: {cmd}')
                print(f'ffmpeg command: {cmd}', file=log_file_object)
                log_file_object.flush()
                process = subprocess.Popen(
                    shlex.split(cmd),
                    stdout=log_file_object,
                    stderr=log_file_object,
                    universal_newlines=True,
                    env=env
                )

                try:
                    process.wait(timeout=ENCODE_TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    print(f"ERROR: {test_name} killed after {ENCODE_TIMEOUT:g} seconds")
                    print(f"ERROR: killed after {ENCODE_TIMEOUT:g} seconds", file=log_file_object)

            # Store timing
            enctime = time.perf_counter() - t1
            print(f"\t took: {enctime:.2f} seconds. ")
            # !! Use this function from utils to create a media reference
            # of output the file.
            mr = create_media_reference(out_file, self.source_clip)

            # Update metadata for use later
            # !! Use this function from utils to make sure we find the metadata
            # later on
            test_meta = get_test_metadata_dict(mr)
            test_meta['test_config_path'] = str(self.test_config.get(
                'test_config_path'
            ))
            test_meta['command'] = cmd
            test_meta['wedge_name'] = wedge_name
            test_meta['test_prefix'] = self.test_config.get('name')
            test_meta['encode_arguments'] = wedge
            test_meta['description'] = self.test_config.get('description')
            test_meta['outputfile'] = str(out_file)
            test_meta['testbasename'] = testbasename
            result_meta = test_meta.setdefault('results', {})
            result_meta['completed_utc'] = \
                datetime.now(timezone.utc).isoformat()
            result_meta['encode_time'] = round(enctime, 4)
            if os.path.exists(out_file) and out_file.stat().st_size > 0:
                result_meta['filesize'] = out_file.stat().st_size
            else:
                print(f"ERROR: {test_name} failed to create a file {out_file}")
                print(f"\tERROR: {test_name} failed to create a file ")
                log_file_object.close()
                with open(log_file, "r") as log_file_object:
                    print("Output from file generation:\n", log_file_object.read())
                result_meta['filesize'] = -1
                

            # Add media reference to result list
            results.update({test_name: mr})

        return results

    def get_application_version(self) -> str:
        if not self._application_version:
            cmd = f'{FFMPEG_BIN} -version -v quiet -hide_banner'
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

        encoding_args_v = []
        for key, value in wedge.items():
            if value == '':
                encoding_args_v.append(key)
            else:
                encoding_args_v.append(f'{key} {value}')
        encoding_args = ' '.join(encoding_args_v)

        duration = self.source_clip.source_range.duration.to_frames()
        if (not source_meta.get('images') and duration == 1
                and source_path.suffix.lower() in STILL_IMAGE_SUFFIXES):
            # Loop the image; -t limits the input, since not every template has -frames:v {duration}.
            rate = float(source_meta.get('rate') or 25)
            input_args = f"-loop 1 -framerate {rate:g} -t {STILL_IMAGE_FRAMES / rate:g}"
            duration = STILL_IMAGE_FRAMES

        cmd = template.format(
            ffmpeg_bin = FFMPEG_BIN,
            input_args=input_args,
            source=source_path.as_posix(),
            duration=duration,
            encoding_args=encoding_args,
            outfile=out_file.as_posix()
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

    def get_output_filename(self, test_name: str) -> Tuple[pathlib.Path, str]:
        source_path, symbol = self.get_source_path()
        stem = source_path.stem.replace(symbol, '')
        if stem[-1] == ".":
            stem = stem[:-1]
    
        testbasename = f"{stem}-{test_name}"

        out_file = self.destination.absolute().joinpath(
            f"{testbasename}{self.test_config.get('suffix')}"
        )

        return out_file, testbasename

