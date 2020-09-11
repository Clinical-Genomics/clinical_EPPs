#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import logging
import sys


DESC = """EPP script to copy UDFs between artifacts from different processes which 
not nessearily are part of the same work flow! For this to work, the script 
asumes a one to one relation between:
    Input artifacts of the current process,
    Sample,
    Input artifacts of the sought process

Written by Maya Brandi, Clinical Genomics, Stockholm, Sweden"""

class CopyUDF():
    def __init__(self, process, udfs, aggregate_qc_step, target_out):
        self.udfs = udfs
        self.aggregate_qc_step = aggregate_qc_step
        self.failded_udfs = False
        self.no_qc_step = []
        if target_out:
            self.target_arts = [a for a in process.all_outputs() if a.type=='Analyte']
        else:
            self.target_arts = [a for a in process.all_inputs() if a.type=='Analyte']


    def copy_udfs(self):
        """ For every target_art in the current process:
                Finds the source_art from the seeked agregate_qc_step
                Copies the requested udfs from source_art to target_art."""
        for target_art in self.target_arts:
            ## Since inputs are never pools, target_art.samples will allways be a list 
            ## of only one sample:
            sample = target_art.samples[0]
            ## Getting arifacts asociated with sample and generated from all processes 
            ## of type aggregate_qc_step:
            arts = lims.get_artifacts(process_type = self.aggregate_qc_step,
                        sample_name = sample.name)
            ## Getting the most recent aggregate_qc_step
            if not arts:
                self.no_qc_step.append(target_art.id)
                continue
            latest_process = arts[0].parent_process
            for art in arts:
                if art.parent_process.date_run > latest_process.date_run:
                    latest_process = art.parent_process
            ## Getting input artifact asociated with sample, from latest_process. 
            for source_art in latest_process.all_inputs():
                ## Again, since latest_process inpputs are never pools, 
                ## source_art.samples will allways be a list of only one sample
                if source_art.type=='Analyte' and source_art.samples[0]==sample:
                    ## update udfs of artifacts in current process
                    for udf in self.udfs:
                        try:
                            target_art.udf[udf] = source_art.udf[udf]
                            target_art.put()
                        except Exception as e:
                            logging.exception(e)
                            self.failded_udfs = True
                    break


def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args.udfs, args.qcstep, args.target_out)
    CUDF.copy_udfs()
    warning = ''

    if CUDF.no_qc_step:
        warning += 'Some samples did not go through aggregate qc step: ' + ', '.join(CUDF.no_qc_step)
    if CUDF.failded_udfs:
        warning += 'Failed to copy some udfs'

    if warning:
        sys.exit(warning)
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
                        help=('list of UDFs to copy'))
    parser.add_argument('-q', dest = 'qcstep', nargs='+',
                        help=('Name of qc-step from wich we want to copy. '
                              'Eg: "CG002 - Aggregate QC (DNA)"'))
    parser.add_argument('-d', dest = 'target_out', action='store_true',
                        help=('Use this flagg if the target analytes should the outputs '
                              'of the current process. By default, the target analytes '
                              'are the inputs of the current process.'))
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
