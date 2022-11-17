import argparse
from pathlib import Path

from testframework.main import *
from testframework.utils.outputTemplate import processTemplate
# This code ideally ends up in main.py but may also make sense as a standalone.

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--test-config-dir',
        action='store',
        default='./test_configs',
        help='Where to look for *.yml files containing test descriptions'
    )

    parser.add_argument(
        '--test-config',
        action='store',
        dest='test_config_file',
        default=None,
        help='Specify a single test config file to run'
    )


    parser.add_argument(
        '--results',
        action='store',
        default='encoding-test-results.otio',
        help='Path to results file including ".otio" extenstion '
             '(default: ./encoding-test-results.otio)'
    )


    args = parser.parse_args()

    return args

def otio2htmlmain():
    args = parse_args()

    # Make sure we have a folder for test configs
    Path(args.test_config_dir).mkdir(parents=True, exist_ok=True)

    test_configs = []
    if args.test_config_file:
        test_configs.extend(parse_config_file(Path(args.test_config_file)))
    else:
        test_configs.extend(
            get_configs(args, args.test_config_dir, ENCODE_TEST_SUFFIX)
        )
    
    timeline = otio.adapters.read_from_file(args.results)

    processTemplate(test_configs, timeline)

if __name__== '__main__':
    otio2htmlmain()
