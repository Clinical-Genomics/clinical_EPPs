#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys

DESC = """EPP script to calculate missing reads for a pool

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class MissingReadsPool():

    def __init__(self, process):
        self.out_analytes = [a for a in process.all_outputs() if a.type=='Analyte']

    def apply_calculations(self):
        for art in self.out_analytes:
            if len(art.samples) == 1:
                continue
            missing_reads_pool = 0
            for samp in art.samples:
                missing_reads_pool += samp.udf.get('Reads missing (M)', 0)
            art.udf['Missing reads Pool (M)'] = missing_reads_pool
            art.put()
                

def main(lims, args):
    process = Process(lims, id = args.p)
    MRP = MissingReadsPool(process)
    MRP.apply_calculations()
    print >> sys.stderr

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', help='Lims id for current Process')

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
