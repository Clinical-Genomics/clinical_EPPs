#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger
from clinical_EPPs.configs.config import CG_URL
from cgface.api import CgFace
import logging
import sys

DESC = """Epp script to calculate calculate Missing Reads, set the Rerun check box and set the Sequencing QC flag.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class MissingReads():

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.passed_arts = []
        self.failed_arts = []
        self.cgface_obj = CgFace(url=CG_URL)

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte" , all_artifacts)


    def get_missing_reads(self):
        for art in self.artifacts:
            samples = art.samples
            udfs_ok = True
            try:
                reads_total = samples[0].udf['Total Reads (M)']
                app_tag = samples[0].udf['Sequencing Analysis']
                data_analysis = samples[0].udf.get('Data Analysis')
            except:
                udfs_ok = False
            if udfs_ok:
                try:
                    target_amount_reads = self.cgface_obj.apptag(tag_name = app_tag, key = 'target_reads')
                except:
                    sys.exit("Could not find application tag: "+app_tag+' in database.')
                # Converting from reads to milion reads, as all ather vareables are in milions.
                target_amount = target_amount_reads/1000000                  
                if app_tag[0:3]=='WGS' or app_tag[0:3]=='WGT':
                    if data_analysis=='MIP':
                        # minimum reads is 92% of target reads for MIP samples
                        reads_min = 0.92*target_amount
                    else:
                        # minimum reads is 100% of target reads for other WGS and WGT samples
                        reads_min = target_amount
                else:
                    # minimum reads is 75% of target reads for all other samples
                    reads_min = 0.75*target_amount
                reads_missing = reads_min - reads_total
                if reads_missing > 0:
                    for sample in samples:
                        sample.udf['Reads missing (M)'] = target_amount - reads_total
                        sample.put()
                    art.udf['Rerun'] = True
                    art.qc_flag = 'FAILED'
                else:
                    for sample in samples:
                        sample.udf['Reads missing (M)'] = 0
                        sample.put()
                    art.udf['Rerun'] = False
                    art.qc_flag = 'PASSED'
                art.put()
                self.passed_arts.append(art)
            else:
                self.failed_arts.append(art)



def main(lims, args):
    process = Process(lims, id = args.pid)
    MR = MissingReads(process)
    MR.get_artifacts()
    MR.get_missing_reads()


    d = {'ca': len(MR.passed_arts),
         'ia': len(MR.failed_arts)}
    abstract = ("Updated {ca} sample(s), skipped {ia} sample(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    print >> sys.stderr, abstract

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', default=sys.stdout, dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

