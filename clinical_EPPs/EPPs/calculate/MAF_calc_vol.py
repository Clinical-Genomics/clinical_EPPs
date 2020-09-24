#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import logging
import sys

DESC = """EPP script to calculate dilution volumes from Concentration udf

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class CalculateDilution():

    def __init__(self, process):
        self.process = process
        self.out_analytes = [a for a in process.all_outputs() if a.type=='Analyte']
        self.passed_arts = []
        self.failed_arts = []
        self.min_final_vol = 15
        self.final_conc = 4 

    def apply_calculations(self):
        for art in self.out_analytes:
            sample_conc = art.udf.get('Concentration')
            qc_flag='FAILED'
            if sample_conc is None or sample_conc<4:
                logging.exception('Too low or Missing concentration') 
                self.failed_arts.append(art)
                continue
            elif sample_conc<20:
                sample_vol= self.min_final_vol*self.final_conc/art.udf['Concentration']
            elif 20<=sample_conc<244:
                sample_vol=3
                qc_flag='PASSED'
            elif 244<=sample_conc<364:
                sample_vol=2
            elif 364<=sample_conc<724:
                sample_vol=1
            elif 724<=sample_conc<1444:
                sample_vol=0.5
            else:
                self.failed_arts.append(art)
                continue
            final_vol=sample_vol*art.udf['Concentration']/self.final_conc
            if final_vol<self.min_final_vol:
                self.failed_arts.append(art)
                continue
            else:
                art.qc_flag=qc_flag
                art.udf['Final Volume (uL)'] = final_vol
                art.udf['Volume H2O (ul)'] =  final_vol - sample_vol
                art.udf['Volume of sample (ul)'] = sample_vol
                art.put()
                self.passed_arts.append(art)


def main(lims, args):
    process = Process(lims, id = args.p)
    CD = CalculateDilution(process)
    CD.apply_calculations()


    d = {'ca': len(CD.passed_arts),
         'ia': len(CD.failed_arts)}
    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if CD.failed_arts:
        sys.exit(abstract)
    else:
        print >> sys.stderr, abstract 

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest='log' , default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    logging.basicConfig(
                    level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename = args.log,
                    filemode='w')
    main(lims, args)
