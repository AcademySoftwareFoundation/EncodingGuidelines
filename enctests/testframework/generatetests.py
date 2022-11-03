# This is for generating tests from the markdown code.
import os
import argparse
import yaml
import re
from pathlib import Path

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
    rootdir = Path(args.root).absolute()

    markdownfiles = []
    for root, dirs, files in os.walk(rootdir):
        for name in files:
            if name.endswith(".md"):
                markdownfiles.append(os.path.join(root, name))

    allinfo = []

    for markdownfile in markdownfiles:
        with open(markdownfile, "r") as f:
            incomment = False
            incommand = False
            command = ""
            info = ""
            lastcommandstart = -1
            for linenumber, line in enumerate(f):
                if "<!---" in line:
                    incomment = True
                    continue
                if "-->" in line:
                    incomment = False
                    continue
                if "```" in line:
                    if incommand:
                        incommand = False
                        if "ffmpeg" in command and info != "":
                            try:
                                infostruct = yaml.load(info, SafeLoader)
                                command = command.replace("\\\n", "").replace("\n", "")
                                allinfo.append({'config': infostruct, 'command': command, 'file': markdownfile, 'line': lastcommandstart})
                            except:
                                pass
                        command = ""
                        info = ""
                    else:
                        incommand = True
                        lastcommandstart = linenumber
                    continue
                if incomment:
                    info = info + line
                if incommand:
                    command = command + line

    # Now we process the scanned data to create the config file.
    tests = []

    for testcount, test in enumerate(allinfo):
        testconfigs = {}

        testname = test['config'].get("name", "test-%d" % (testcount + 1))
        outputfile = test['command'].split(" ")[-1]
        outputfileext = outputfile.split(".")[-1]
        #print("START:", test['command'])
        template = re.sub("\s\S+$", ' {encoding_args} -y "{outfile}"', test['command'])
        template = re.sub("\s-i\s\S+\s", ' {input_args} -i "{source}" ', template)
        #print("Pre vframes:", template)
        template = re.sub("\s-vframes\s\S+\s", ' -vframes {duration} ', template)
        #print("Post vframes:", template)

        # input arg flags.
        for arg in ['-r', '-start_number']:
            template = re.sub("\s%s\s\S+\s" % arg, ' ', template) 
        
        wedge = {}

        # Main args.
        for arg in ["-vf", '-color_range', '-colorspace', '-color_primaries', '-profile:v', '-compression_level', '-pred', '-color_trc', '-pix_fmt', '-preset', '-c:v', '-sws_flags']:
            match = re.search("\s%s\s(\S+)\s" % arg, template)
            if match:
                wedge[arg] = match.group(1)
                template = template.replace(match.group(0), ' ')
        
        #print("Wedge:", wedge)


        print("Name:", testname)
        print("Template:", template)
        if "sources" in test['config']:
            for i in range(0, len(test['config']['sources'])):
                test['config']['sources'][i] = os.path.abspath(os.path.join(args.root, test['config']['sources'][i]))
        testconfigs[testname] = test['config']
        testconfigs[testname]['encoding_template'] = template
        testconfigs[testname]['suffix'] = "." + outputfileext
        testconfigs[testname]['description'] = "Test from %s line %d" % (test['file'], test['line'])
        testconfigs[testname]['name'] = testname
        testconfigs[testname]['app'] = 'ffmpeg'
        if 'wedges' in testconfigs[testname]:
            # We allow additional wedges to be added in the docs config file.
            print("Already got wedge:", testconfigs[testname]['wedges'])
            testconfigs[testname]['wedges']['wedge0'] = wedge
        else:
            testconfigs[testname]['wedges'] = {'wedge0': wedge}
        tests.append(testconfigs)

    reports = {'reports': {'name': 'doc-tests',
                            'directory': 'docs-encode',
                            'templatefile': 'doctests.html.jinja'}}
    tests.append(reports)

    with open(args.output_config_file, "w") as f:
        yaml.dump_all(tests, f)


if __name__== '__main__':
    main()
