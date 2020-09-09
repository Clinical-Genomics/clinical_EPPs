#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Artifact

from clinical_EPPs.configs.config import CG_URL
from cgface.api import CgFace

DESC = """Script to set the Reads Missing (M) udf for all samples befor they go 
into any workflow. The Reads Missing (M) is at this point defined only by the 
Sequencing Analysis. Numers are fetched from cgface"""

class SetMissingReads():
    def __init__(self, lims, pid):
        self.lims = lims
        self.process = Process(lims, id = pid)
        self.input_output_maps = self.process.input_output_maps
        self.samples = []
        self.failed_samples = 0
        self.cgface_obj = CgFace(url=CG_URL)


    def get_samples(self):

        for inp, outp in self.input_output_maps:
            inart =  Artifact(self.lims,id = inp['limsid'])
            outart =  Artifact(self.lims,id = outp['limsid']) if outp else None
            sample = inart.samples[0]
            self.samples.append((sample, outart))


    def set_reads_missing(self, sample, art):
        """Sets the 'Reads missing (M)' udf, based on the application tag. 
        If out-arts exist, set the qc-flaggs on the out-arts"""

        try:
            app_tag = sample.udf['Sequencing Analysis']
            target_amount = self.cgface_obj.apptag(tag_name = app_tag, key = 'target_reads')
            sample.udf['Reads missing (M)'] = target_amount/1000000
            if art:
                art.qc_flag = "PASSED"
                art.put()
        except:
            self.failed_samples += 1
            if art:
                art.qc_flag = "FAILED"
                art.put()
        sample.put()

    def check_samples(self):
        for samp , art in self.samples:
            self.set_reads_missing(samp, art)

def main(lims, pid):
    SMR = SetMissingReads(lims, pid)
    SMR.get_samples()
    SMR.check_samples()


    if SMR.failed_samples:
        sys.exit('Faild to get missing reads for '+str(SMR.failed_samples)+' sample.')
    else:
        print >> sys.stderr, 'Reads Missing has been set for all samples.'


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', default = None , dest = 'pid',
                        help='Lims id for current Process')
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args.pid)

