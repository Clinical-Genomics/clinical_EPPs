#!/usr/bin/env python

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
        self.udfs = udfs
        self.failded_udfs = False
        self.failed_art = []
        self.aggregate_qc_step = aggregate_qc_step

    def get_processes(self):
        """Prepparing output artifact dict."""
        for input_output in self.process.input_output_maps:
            inpt = input_output[0]['uri']
            outpt = input_output[1]['uri']
            try:
                if input_output[1]['output-type'] == 'Analyte':
                    sample = outpt.samples[0].name
                    child_processes = []
                    parent_process = outpt.parent_process
                    while not child_processes:
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
                                        except:
                                            self.failded_udfs = True
                                    break
                                else:
                                    parent_process = parent_input.parent_process
            except:
                self.failed_art.append(inpt.name)


def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args.udfs, args.qcstep)
    CUDF.get_processes()

    if CUDF.failed_art:
        sys.exit('Artifacts: '+ ', '.join( CUDF.failed_art)+", don't seem to have passed the QC step. No UDFs found.")
    if CUDF.failded_udfs:
        sys.exit('failed to copy some udfs')
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
    parser.add_argument('-q', dest = 'qcstep', nargs='+', 
                        help=(''))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
