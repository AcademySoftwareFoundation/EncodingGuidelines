# This is for generating tests from the markdown code.
import os
import argparse
import yaml

try:
    from yaml import CSafeLoader as SafeLoader
    from yaml import CSafeDumper as SafeDumper

except ImportError:
    from yaml import SafeLoader, SafeDumper

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--root',
        action='store',
        default='..',
        help='Where to look for *.md files to generate the config file.'
    )

    parser.add_argument(
        '--output-config',
        action='store',
        dest='output_config_file',
        default="test_configs/documentation_tests.yml",
        help='Specify output file to write test wrappers to.'
    )

    args = parser.parse_args()

    return args

def main():
    args = parse_args()
    rootdir = os.path.abspath(args.root)

    markdownfiles = []
    for root, dirs, files in os.walk(rootdir):
        for name in files:
            if name.endswith(".md"):
                markdownfiles.append(os.path.join(root, name))

    for markdownfile in markdownfiles:
        print("------\n", markdownfile)
        f = open(markdownfile, "r")
        incomment = False
        incommand = False
        command = ""
        info = ""
        allinfo = []
        for line in f:
            if "<!---" in line:
                incomment = True
                continue
            if "-->" in line:
                incomment = False
                print("Got comment:", info)
                continue
            if "```" in line:
                if incommand:
                    incommand = False
                    if "ffmpeg" in command and info != "":
                        try:
                            infostruct = yaml.load(info, SafeLoader)
                            print("Command:", infostruct, command)
                            allinfo.append({'config': infostruct, 'command': command})
                        except:
                            pass
                    command = ""
                    info = ""
                else:
                    incommand = True
                continue
            if incomment:
                info = info + line
            if incommand:
                command = command + line            


if __name__== '__main__':
    main()
