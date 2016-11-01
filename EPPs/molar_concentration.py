#!/usr/bin/env python
DESC = """EPP script to calculate molar concentration given the 
weight concentration, in Clarity LIMS. Before updating the artifacts, 
the script verifies that 'Concentration' and 'Size (bp)' udf:s are not blank,
Artifacts that do not fulfill the requirements, will not be updated.

Maya Brandi
""" 

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import logging
import sys


class MolarConc():

    def __init__(self, process, aggregate):
        self.process = process
        self.aggregate = aggregate
        self.artifacts = []
        self.passed_arts = []
        self.failed_arts = []

    def get_artifacts(self):
        if self.aggregate:
            self.artifacts = self.process.all_inputs(unique=True)
        else:
            all_artifacts = self.process.all_outputs(unique=True)
            self.artifacts = filter(lambda a: a.output_type == "ResultFile" , all_artifacts)

    def get_treshold(self):
        self.process.udf['Minimum']


    def apply_calculations(self):
        for art in self.artifacts:
            udfs_ok = True
            for udf in ['Size (bp)', 'Concentration']:
                try:
                    float(art.udf[udf])
                except:
                    udfs_ok = False
            if udfs_ok:
                factor = 1e6 / (328.3 * 2 * art.udf['Size (bp)'])
                cons_nM = art.udf['Concentration'] * factor
                art.udf['Concentration (nM)'] = cons_nM
                if cons_nM > 2:
                    art.qc_flag = "PASSED"
                else:
                    art.qc_flag = "FAILED"
                art.put()
                self.passed_arts.append(art)
            else:
                self.failed_arts.append(art)            



def main(lims, args):
    process = Process(lims, id = args.pid)
    MC = MolarConc(process, args.aggregate)
    MC.get_artifacts()
    MC.apply_calculations()


    d = {'ca': len(MC.passed_arts),
         'ia': len(MC.failed_arts)}

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if MC.failed_arts:
        sys.exit(abstract)
    else:
        print >> sys.stderr, abstract

if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--aggregate', action='store_true',
                        help=("Use this tag if your process is aggregating "
                              "results. The default behaviour assumes it is "
                              "the output artifact of type analyte that is "
                              "modified while this tag changes this to using "
                              "input artifacts instead"))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
