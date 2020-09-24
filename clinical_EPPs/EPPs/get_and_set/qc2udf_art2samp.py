#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys

DESC = """epp script to set a sample udf, based on artifact qc-flagg

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class ArtQC2SampUDF():

    def __init__(self, process, dest_udf, sequencing):
        self.process = process
        self.dest_udf = dest_udf
        if sequencing:
            all_artifacts = self.process.all_outputs(unique=True)
            self.artifacts = filter(lambda a: a.output_type == "Analyte" ,all_artifacts)
        else:
            self.artifacts = self.process.all_inputs(unique=True)
        self.passed_samps = []
        self.failed_samps = []


    def set_udf(self):
        for art in self.artifacts:
            try:
                if art.qc_flag == 'PASSED':
                    for samp in art.samples:
                        ## if art is pool, the art.qc_flagg is "copied" to all samps in the pool
                        samp.udf[self.dest_udf] = 'True'
                        samp.put()
                        self.passed_samps.append(samp)
                else:
                    for samp in art.samples:
                        samp.udf[self.dest_udf] = 'False'
                        samp.put()
                        self.passed_samps.append(samp)
            except:
                self.failed_samps.append(art)
        self.passed_samps = list(set(self.passed_samps))
        self.failed_samps = list(set(self.failed_samps))

def main(lims, args):
    process = Process(lims, id = args.pid)
    A2S = ArtQC2SampUDF(process, args.dest_udf, args.sequencing)
    A2S.set_udf()
    d = {'du': A2S.dest_udf,
         'fa': len(A2S.failed_samps),
         'pa': len(A2S.passed_samps)}

    if A2S.failed_samps:
        abstract = ("Could not set '{du}' UDF for some sample(s). Either the qc-falg(s) were "
                    "not set, or there is no {du} on sample level").format(**d)
        sys.exit(abstract)
    else:
        abstract = ("The '{du}' UDF, was successfully set on {pa} samples.").format(**d)
        print >> sys.stderr, abstract


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--dest_udf',
                        help=("Sample udf to be set based on artifact qc_flagg"))
    parser.add_argument('--sequencing', action='store_true',
                        help=("Use this tag if current Process is a sequencing step"))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
