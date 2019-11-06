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
        warning = ''
        self.process = process
        self.run_mode_dict =  {'NovaSeq Standard' : {'S1': 100, 'S2': 150,'S4': 310, 'SP': 100},
                                'NovaSeq Xp'      : {'S1': 18 , 'S2': 22 ,'S4': 30, 'SP': 18}}
        iseq_define_step = self.process.all_inputs()[0].parent_process
        existing_pool_volume = iseq_define_step.udf.get('Final Total Sample Volume (ul)')
        flowcell_type = iseq_define_step.udf.get('Flowcell Type')
        protocol_type = iseq_define_step.udf.get('Protocol type')
        messured_pool_conc = self.process.udf.get('Pool Concentration')
        final_concentration = self.process.udf.get('Final Loading Concentration')
        min_final_volume = self.run_mode_dict[protocol_type][flowcell_type]
        volume_of_pool = (final_concentration*min_final_volume)/messured_pool_conc
        if existing_pool_volume < volume_of_pool:
            warning += 'You have to little sample pool volume to work with! '
        process.udf['Existing Volume of Sample Pool (ul)'] = existing_pool_volume
        process.udf['RSB Volume (ul)'] = min_final_volume - volume_of_pool
        process.udf['Volume of Sample Pool (ul)'] = volume_of_pool
        process.udf['Min Volume of Final Pool (ul)'] = min_final_volume
        process.udf['Flowcell Type'] = flowcell_type
        process.udf['Protocol Type'] = protocol_type
        process.put() 
        if min_final_volume < volume_of_pool:
            warning += 'Final loading concentration is bigger than the concentration of your pool.'
        if warning:
            sys.exit(warning)

def main(lims, args):
    process = Process(lims, id = args.p)
    CD = CalculateDilution(process)
    
    print >> sys.stderr 

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p',
                        help='Lims id for current Process')

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
