#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys

DESC = """epp script to replace output folder path in the AUTOMATED - NovaSeq Run step.

The default path is:     \\<some novaseq windows network path>\clinicaldata\Runs\<run folder>
Should be replaced with: \\130.237.80.51\Runs\<run folder>

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class ReplacePath():

    def __init__(self, process):
        self.process = process
        self.fail = ''

    def replace(self):
        current_path = self.process.udf.get('Output Folder')
        if current_path:
            replace_path = '\\\\130.237.80.51\\Runs' + current_path.split('Runs')[1]
            self.process.udf['Output Folder'] = replace_path
            self.process.put()
        else:
            self.fail = 'Output Folder udf not set. Could not replace it.'

def main(lims, args):
    process = Process(lims, id = args.pid)
    RP = ReplacePath(process)
    RP.replace()

    if RP.fail:
        sys.exit(RP.fail)
    else:
        print('Replaced path', file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
