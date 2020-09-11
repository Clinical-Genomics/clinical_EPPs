#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import sys


DESC = """
"""


class CopyUDF():
    def __init__(self, process, sample_udf, art_udf):
        self.artifacts = [a for a in process.all_outputs() if a.type=='Analyte']
        self.sample_udf = sample_udf
        self.art_udf = art_udf
        self.failed_udfs = 0

    def copy(self):
        for art in self.artifacts:
            sample = art.samples[0]
            udf = art.udf.get(self.art_udf)
            if udf is not None:
                sample.udf[self.sample_udf] = udf
                sample.put()
            else:
                self.failed_udfs += 1

def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args.sample_udf, args.art_udf)
    CUDF.copy()

    if CUDF.failed_udfs:
        sys.exit('Failed to copy udf for %s samples.' % (str(CUDF.failed_udfs)) )
    else:
        print('UDFs were successfully copied!', file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'sample_udf', help=(''))
    parser.add_argument('-a', dest = 'art_udf',
                        help=(''))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
