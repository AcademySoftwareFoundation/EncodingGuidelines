import argparse
from pathlib import Path
import jinja2
from testframework.main import *
from .test_suite import TestSuite, SourceConfig
from testframework.utils.outputTemplate import processTemplate, outputSummaryIndex
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
        default='',
        help='Path to results file including ".otio" extenstion '
             '(default: ./encoding-test-results.otio)'
    )

    parser.add_argument(
        '--encoded-folder',
        action='store',
        default='', # If its '', we determine the path procedurally.
        help='Where to store the encoded files'
    )

    parser.add_argument(
        '--results-folder',
        action='store',
        default='./results',
        help='Basepath for all the results, not used if --encoded-folder is defined.'
    )

    args = parser.parse_args()

    return args

def otio2htmlmain():
    args = parse_args()

    # Make sure we have a folder for test configs
    Path(args.test_config_dir).mkdir(parents=True, exist_ok=True)

    test_configs = []
    if args.test_config_file:
        test_configs.append(TestSuite(Path(args.test_config_file)))
    else:
        test_configs.extend(
            get_test_configs(args, args.test_config_dir, ENCODE_TEST_SUFFIX)
        )

    results = []

    for test_config in test_configs:
        destination_folder = destination_from_config(
            test_config,
            args.results,
            Path(args.results_folder)
        )
        output_file = args.results
        if output_file == '':
            # We base it on the test filename
            output_file = destination_folder / f"{test_config.config_file().stem}.otio"
        else:
            output_file = Path(output_file)
        if not output_file.exists():
            continue
        
        print("Outputfile:", output_file)
        print("destination_folder:", destination_folder)

        timeline = otio.adapters.read_from_file(str(output_file))
        # Create an encoder instance, since this will configure the destination folder.
        
        first_test = test_config.tests()[0]
        
        result = processTemplate(test_config, timeline)
        if result is not None:
            result["relativeurl"] = Path(result['reporturl']).relative_to(args.results_folder)
            results.append(result)
        
    outputSummaryIndex(args.results_folder)

if __name__== '__main__':
    otio2htmlmain()
