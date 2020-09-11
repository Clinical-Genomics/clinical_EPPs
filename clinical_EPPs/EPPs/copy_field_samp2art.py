#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys


DESC = """
"""


class CopyUDF():
    def __init__(self, process, samp_udf, art_udf):
        self.process = process
        self.artifacts = []
        self.samp_udf = samp_udf
        self.art_udf = art_udf
        self.failded_udfs = False
        self.missing_samp_udf = False

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]


    def copy(self):
        for art in self.artifacts:
            sample = art.samples[0]
            if self.samp_udf in sample.udf:
                art.udf[self.art_udf] = str(sample.udf[self.samp_udf])
                art.put()
            else:
                self.failded_udfs = True 

def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args.samp_udf, args.art_udf)
    CUDF.get_artifacts()
    CUDF.copy()

    if CUDF.failded_udfs:
        sys.exit('failed to copy some udfs')
    else:
        print('UDFs were succsessfully copied!', file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('-s', dest = 'samp_udf', help=(''))
    parser.add_argument('-a', dest = 'art_udf', 
                        help=(''))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
