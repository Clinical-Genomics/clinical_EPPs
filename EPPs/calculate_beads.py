#!/usr/bin/env python
DESC="""EPP script to calculate Volume Beads and Volume H2O.
Maya Brandi
"""
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process

import sys

class VolumeBeads():
    def __init__(self, process):
        self.process = process
        self.artifacts = [a for a in process.all_outputs() if a.type=='Analyte']
        self.passed_arts = 0
        self.failed_arts = 0
        self.missing_udfs = False

    def apply_calculations(self):
        for art in self.artifacts:
            samp_vol = art.udf.get('Sample Volume (ul)')
            if not isinstance(samp_vol, (int,float)):
                self.failed_arts +=1
                continue
            if samp_vol < 50:
                vol_H2O = 50 - samp_vol
            else:
                vol_H2O = 0
            vol_beads = 2*(samp_vol + vol_H2O)
            art.udf['Volume H2O (ul)'] = vol_H2O
            art.udf['Volume Beads (ul)'] = vol_beads
            art.put()
            self.passed_arts += 1

def main(lims,args):
    process = Process(lims,id = args.pid)
    VB = VolumeBeads(process)
    VB.apply_calculations()

    d = {'ca': VB.passed_arts,
         'ia': VB.failed_arts}

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if VB.failed_arts:
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

    main(lims, args)
