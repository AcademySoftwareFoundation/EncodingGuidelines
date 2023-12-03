import pathlib
import opentimelineio as otio
import platform

from .base import ABCTestEncoder
from .ffmpeg_encoder import FFmpegEncoder



encoder_map = {
    'ffmpeg': FFmpegEncoder
}

def destination_from_config(
        test_config: dict,
        destination: pathlib.Path,
        results_folder: pathlib.Path
        ):
    encoder_cls = encoder_map.get(test_config.get('app'))
    
    encoder = encoder_cls(None, test_config, destination)

    if destination == '':
        # This happens if its not defined, then we change it to be
        # results/<ENCODERVER>/<APPLICATIONVERSION>/<TEST>-encode
        app_version = encoder.get_application_version()
        config_file_base = pathlib.Path(test_config.config_file()).stem
        destination = results_folder / app_version / f"{platform.system().lower()}-{platform.machine().lower()}" / f"{config_file_base}-encode"
    test_config.set_destination(destination)
    return destination

def encoder_factory(
        source_clip: otio.schema.Clip,
        test_config: dict,
        destination: pathlib.Path
) -> ABCTestEncoder:


    encoder_cls = encoder_map.get(test_config.get('app'))
    
    encoder = encoder_cls(source_clip, test_config, destination)

    encoder.destination = pathlib.Path(destination)
    print(f"Output directory: {destination}")
    # Make sure we have a destination folder
    pathlib.Path(destination).mkdir(parents=True, exist_ok=True)

    return encoder