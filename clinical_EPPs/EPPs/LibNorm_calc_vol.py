#!/usr/bin/env python

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


class EBVol():

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.passed_arts = []
        self.failed_arts = []
        self.final_vol = 5.0

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]


    def apply_calculations(self):
        for art in self.artifacts:
            udfs_ok = True
            try:
                int(art.udf['Concentration (nM)'])
            except:
                udfs_ok = False
            try:
                int(art.udf['Final Concentration (nM)'])
            except:
                udfs_ok = False
            if udfs_ok:
                art.udf['Volume of sample (ul)'] = art.udf['Final Concentration (nM)']*self.final_vol/art.udf['Concentration (nM)']
                art.udf['Volume of RSB (ul)'] = self.final_vol-art.udf['Volume of sample (ul)']
                art.put()
                self.passed_arts.append(art)
            else:
                self.failed_arts.append(art)            



def main(lims, args):
    process = Process(lims, id = args.pid)
    EBV = EBVol(process)
    EBV.get_artifacts()
    EBV.apply_calculations()


    d = {'ca': len(EBV.passed_arts),
         'ia': len(EBV.failed_arts)}
    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    print(abstract, file=sys.stderr) 

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
