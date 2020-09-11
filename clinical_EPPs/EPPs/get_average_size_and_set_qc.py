#!/home/glsai/miniconda2/envs/epp_master/bin/python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process

import sys
import numpy as np

DESC = """epp script to calculate Average Size (bp) from a subset of the samples actual Sizes. 

Average Size (bp) is then applyed to all samples

NTC samples are ignored

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class AverageSizeBP():

    def __init__(self, process, lower_treshold, upper_treshold):
        self.lower_treshold = lower_treshold
        self.upper_treshold = upper_treshold
        self.process = process
        self.all_artifacts = []
        self.artifacts = []
        self.size_list = []
        self.qc_flag = 'PASSED'
        self.average_size = None

    def get_artifacts(self):
        self.all_artifacts = self.process.all_inputs(unique=True)
        for art in self.all_artifacts:
            if not art.name[0:3] == 'NTC':
                self.artifacts.append(art)

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
        if self.lower_treshold is not None and int(self.average_size) < int(self.lower_treshold):
            self.qc_flag = 'FAILED'
        elif self.upper_treshold and int(self.average_size) > int(self.upper_treshold):
            self.qc_flag = 'FAILED'

    def set_average_size(self):
        if self.average_size:
            for art in self.all_artifacts:
                art.udf['Average Size (bp)'] = str(self.average_size)
                if art.qc_flag == 'PASSED':
                    art.qc_flag = self.qc_flag
                art.put()


def main(lims, args):
    process = Process(lims, id = args.pid)
    ASBP = AverageSizeBP(process, args.lower_tres, args.upper_tres)
    ASBP.get_artifacts()
    ASBP.make_average_size()
    ASBP.set_average_size()
    print("'Average Size (bp)' has ben set.", file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-lt', dest = 'lower_tres', default = None,
                        help='Treshold for qc flags')
    parser.add_argument('-ut', dest = 'upper_tres', default = None,
                        help='Treshold for qc flags')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

