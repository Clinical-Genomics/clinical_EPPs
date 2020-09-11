#!/home/glsai/miniconda2/envs/epp_master/bin/python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys
import numpy as np

DESC = """epp script to calculate Average Size (bp) from a subset of the samples actual Sizes. 

Average Size (bp) is then applyed to all samples

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class AverageSizeBP():

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.size_list = []
        self.average_size = None

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "ResultFile"]

    def make_average_size(self):
        for art in self.artifacts:
            try:
                self.size_list.append(int(art.udf['Size (bp)']))
            except:
                pass
        if self.size_list:  
            self.average_size = np.mean(self.size_list)
        else:
            sys.exit("Set 'Size (bp)' for at least one sample")

    def set_average_size(self):
        if self.average_size:
            for art in self.artifacts:
                art.udf['Average Size (bp)'] = self.average_size
                art.put()

    
def main(lims, args):
    process = Process(lims, id = args.pid)
    ASBP = AverageSizeBP(process)
    ASBP.get_artifacts()
    ASBP.make_average_size()
    ASBP.set_average_size()
    print("'Average Size (bp)' has ben set.", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
