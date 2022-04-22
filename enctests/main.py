import os
import pathlib
import argparse
import opentimelineio as otio
import pyseq

ENCODE_SETTINGS_SUFFIX = 'aswfenc'


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


def create_media_reference(path):
    # TODO parse enc settings file in a function
    encsettings = {"rate": 24}
    # Create ImageSequenceReference
    if path.is_dir():
        seq = pyseq.get_sequences(path.as_posix())[0]
        # TODO create range
        available_range = otio.opentime.TimeRange(
            otio.opentime.RationalTime()
        )
        mr = otio.schema.ImageSequenceReference(
            target_url_base=seq.directory(),
            name_prefix=seq.head(),
            name_suffix=seq.tail(),
            start_frame=seq.start(),
            frame_step=1,
            frame_zero_padding=len(max(seq.digits, key=len)),
            rate=encsettings.get('rate'),
            available_range=available_range
        )

    else:
        # Create ExternalReference
        mr = otio.schema.ExternalReference(
            target_url=path.as_uri()
        )

    return mr


def create_clip(path):
    encfile = path.with_suffix(ENCODE_SETTINGS_SUFFIX)
    clip = otio.schema.Clip(name=path.stem)
    mr = create_media_reference(path)

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
            if path.with_suffix(ENCODE_SETTINGS_SUFFIX).exists():
                clip = create_clip(pathlib.Path(item.path))
                sources.append(clip)

    return sources


def main():
    args = parse_args()

    # Gather sources
    sources = get_source_clips(args)


if __name__== '__main__':
    main()
