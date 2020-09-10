#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys


DESC = """
"""


class CopyUDF():
    def __init__(self, process, udfs, aggregate_qc_step):
        self.process = process
        self.artifacts = []
        self.udfs = udfs
        self.failded_udfs = '' 
        self.falied_processes = ''
        self.aggregate_qc_step = aggregate_qc_step

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte" , all_artifacts)

    def get_udfs_from_lowpriostep(self, outpt):
        sample = outpt.samples[0].name
        child_processes = []
        parent_process = outpt.parent_process
        while parent_process:
            parent_inputs = [a for a in parent_process.all_inputs() if a.type=='Analyte'] 
            for parent_input in parent_inputs:
                sample_names = [s.name  for s in parent_input.samples]
                if sample in sample_names:
                    child_processes =  lims.get_processes(type = self.aggregate_qc_step,
                                                inputartifactlimsid = parent_input.id)
                    if child_processes:
                        for udf in self.udfs:
                            try:
                                outpt.udf[udf] = parent_input.udf[udf]
                                outpt.put()
                                logging.info('Sample {0}: Copied "Concentration (nM)" from output artifact of "{1}" to output artifact of current process'.format(sample, self.aggregate_qc_step))
                            except:
                                self.failded_udfs = 'Failed to copy some udfs.'
                        return True
                    else:
                        parent_process = parent_input.parent_process
        return False 

    def get_udfs_from_highpriostep(self, artifact, stop_process):
        sample = artifact.samples[0].name
        parent_process = artifact.parent_process
        while parent_process:
            parent_inputs = [a for a in parent_process.all_inputs() if a.type=='Analyte']        
            for parent_input in parent_inputs:
                sample_names = [s.name  for s in parent_input.samples]
                if sample in sample_names:
                    if parent_process.type.name == stop_process:
                        try:
                            artifact.udf['Concentration (nM)'] = parent_process.udf['Final Concentration (nM)']
                            artifact.put()
                            logging.info('Sample {0}: Copied "Final Concentration (nM)" from process "{1}" to output artifact udf "Concentration (nM)"'.format(sample, stop_process))
                        except:
                            self.failded_udfs = 'Failed to copy some udfs.'
                        return True
                    else:
                        parent_process = parent_input.parent_process
                    break
        return False
                    


def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args.udfs, args.qcstep, args.log)
    CUDF.get_artifacts()
    for art in CUDF.artifacts:
        if args.priostep:
            if not CUDF.get_udfs_from_highpriostep(art, args.priostep):
                if not CUDF.get_udfs_from_lowpriostep(art):
                    CUDF.falied_processes = 'Some of the samples has not gone through any of the processes: '+args.qcstep+' or '+args.priostep + '. '

    if CUDF.failded_udfs or CUDF.falied_processes:
        sys.exit(CUDF.falied_processes + CUDF.failded_udfs)
    else:
        print('UDFs were succsessfully copied!', file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('-u', dest = 'udfs', nargs='+', 
                        help=(''))
    parser.add_argument('-q', dest = 'qcstep', 
                        help=(''))
    parser.add_argument('-r', dest = 'priostep', default = None,
                        help=('Use this option if there is a step with higher prio then the qc-step.'))
    args = parser.parse_args()
    logging.basicConfig(filename = args.log, filemode='w', level=logging.DEBUG)
    logging.info('Sample')
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
