#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys

DESC = """epp script to calculate EB Volume from Concentration udf

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class Pool2Sequence():

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.passed_arts = []
        self.failed_arts = []
        self.total_vol = None
        self.reads_expected = None
        self.nr_samps = None
        self.average_reads = None
        self.low_sample_vol = False
        self.final_concentration_in_pool = None

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte" , all_artifacts)

    def get_process_udfs(self):
        try:
            self.total_vol = float(self.process.udf['Total Volume (ul)'])
            self.reads_expected = self.process.udf['Number of Reads Expected']
            self.final_concentration_in_pool = float(self.process.udf['Final Concentration (nM)'])
        except:
            sys.exit('Seems like some process udfs have not been filed in!')

    def calculate_stuff(self):
        total_reads = 0
        for art in self.artifacts:
            try:
                total_reads +=  float(art.udf['Reads to sequence (M)'])
            except:
                sys.exit("'Reads to sequence (M)' - missing for some samples!")

        self.nr_samps = len(self.artifacts)
        self.average_reads = float(total_reads)/self.nr_samps


    def set_udfs(self):
        total_sample_vol = 0
        total_reads = 0
        for art in self.artifacts:
            try:
                conc = art.udf['Concentration (nM)']
                reads = float(art.udf['Reads to sequence (M)'])
                art.udf['Sample Volume (ul)'] = self.total_vol/self.nr_samps*(self.final_concentration_in_pool/conc)*(reads/self.average_reads)
                total_sample_vol += art.udf['Sample Volume (ul)']
                total_reads += reads
                art.put()
                self.passed_arts.append(art)
                if art.udf['Sample Volume (ul)'] < 1:
                    self.low_sample_vol = True
            except:
                self.failed_arts.append(art)
        try:
            self.process.udf['EB Volume (ul)'] = str(round(self.total_vol - total_sample_vol, 2))
            self.process.udf['Total nr of Reads Requested (sum of reads to sequence)'] = str(total_reads)
            self.process.put()
        except:
            sys.exit('Could not set process UDFs. Needs debugging.')

def main(lims, args):
    process = Process(lims, id = args.pid)
    P2S = Pool2Sequence(process)
    P2S.get_artifacts()
    P2S.get_process_udfs()
    P2S.calculate_stuff()
    P2S.set_udfs()

    d = {'ca': len(P2S.passed_arts),
         'ia': len(P2S.failed_arts)}
    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs. ").format(**d)
    if P2S.low_sample_vol:
        abstract += "WARNING: LOW SAMPLE VOLUME(S)!"
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
