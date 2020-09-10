#!/usr/bin/env python
DESC="""EPP script to calculate sample volume and EB volume from concentration and volume 
udf:s in Clarity LIMS.

Maya Brandi
"""
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys

class EBVolume():
    def __init__(self, process):
        self.process = process
        self.allowed_amounts_needed = [200, 300, 400, 500]
        self.artifacts = []
        self.passed_arts = 0
        self.failed_arts = 0
        self.missing_udfs = False

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte", all_artifacts)

    def check_udfs(self, artifact):
        try:
            amount_needed = float(artifact.udf['Amount needed (ng)'])
            concentration = float(artifact.udf['Concentration'])
        except:
            amount_needed = None
            concentration = None
            self.missing_udfs = True
        return amount_needed, concentration

    def apply_calculations(self):
        for artifact in self.artifacts:
            amount_needed, concentration = self.check_udfs(artifact)  
            if amount_needed and concentration:
                if amount_needed in self.allowed_amounts_needed:
                    samp_vol = amount_needed/concentration
                    artifact.udf['Sample Volume (ul)'] = samp_vol
                    artifact.udf['Volume H2O (ul)'] = 50 - samp_vol
                    artifact.put()
                    self.passed_arts +=1
                else:
                    sys.exit('"Amount needed (ng)" must have one of the values: %s.'  %(' ,'.join(str(x) for x in self.allowed_amounts_needed)))
            else:
                self.failed_arts +=1

def main(lims,args):
    process = Process(lims,id = args.pid)
    EBV = EBVolume(process)
    EBV.get_artifacts()
    EBV.apply_calculations()

    d = {'ca': EBV.passed_arts,
         'ia': EBV.failed_arts}

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if EBV.missing_udfs:
        sys.exit('Could not apply calculations for all samples. "Amount needed (ng)" and "Concentration" must be set.') 
    elif EBV.failed_arts:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file for runtime info and errors.')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
