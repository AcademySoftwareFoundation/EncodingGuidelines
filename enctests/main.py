import configparser
import os
import pathlib
import argparse
import opentimelineio as otio
import pyseq

ENCODE_SETTINGS_SUFFIX = '.aswfenctest'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--source-folder',
        action='store',
        default='./sources',
        help='Where to look for source media files'
    )

    parser.add_argument(
        '--encoded-folder',
        action='store',
        default='./encoded',
        help='Where to store the encoded files'
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
    encfile = path.with_suffix(path.suffix + ENCODE_SETTINGS_SUFFIX)
    config = configparser.ConfigParser()
    config.read(encfile)

    return config


def create_media_reference(path):
    config = parse_config_file(path)
    file_desc = config['GENERAL']

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
            target_url_base=pathlib.Path(seq.directory()).as_uri(),
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


def create_clip(path):
    clip = otio.schema.Clip(name=path.stem)
    mr = create_media_reference(path)

    # The initial MediaReference is stored as default
    clip.media_reference = mr

    # Set source_range
    # clip.source_range =

    return clip


def get_source_clips(args):
    sources = otio.schema.SerializableCollection(name='enctests')
    with os.scandir(args.source_folder) as it:
        for item in it:
            path = pathlib.Path(item.path)
            # We don't use these as sources
            if path.suffix == ENCODE_SETTINGS_SUFFIX:
                continue

            # But we need to make sure they exist as they describe the tests
            if path.with_suffix(path.suffix + ENCODE_SETTINGS_SUFFIX).exists():
                clip = create_clip(pathlib.Path(item.path))
                sources.append(clip)

    return sources


def main():
    args = parse_args()

    # Gather sources
    sources = get_source_clips(args)
    otio.adapters.write_to_file(sources, args.output)


if __name__== '__main__':
    main()
