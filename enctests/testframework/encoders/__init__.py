import pathlib
import opentimelineio as otio

from .base import ABCTestEncoder
from .ffmpeg_encoder import FFmpegEncoder


def encoder_factory(
        source_clip: otio.schema.Clip,
        test_config: dict,
        destination: pathlib.Path
) -> ABCTestEncoder:

    encoder_map = {
        'ffmpeg': FFmpegEncoder
    }

    encoder = encoder_map.get(test_config.get('app'))

    return encoder(source_clip, test_config, destination)
