#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.entities import Process
from genologics.config import BASEURI,USERNAME,PASSWORD

import sys


DESC = """EPP to calculate volumes for a nova seq run, based on iseq results
"""


class CaculateVolumes():
    def __init__(self, process, source_step):
        self.process = process
        self.sample_volumes = []
        self.outputs = [a for a in self.process.all_outputs() if a.type=='Analyte']
        self.minimum_per_sample_volume = process.udf.get('Minimum Per Sample Volume (ul)')
        self.iseq_reads_dict = {}
        self.adjusted_samp_vol_dict = {}
        self.total_expected_reads = 0
        self.total_iseq_reads = 0
        self.failed_art = []
        self.source_step = source_step
        self.total_sample_vol_based_on_min_per_samp = 0
        self.final_total_volume = 0
        self.minimum_total_volume = None
        self.run_mode_dict =  {'NovaSeq Standard' : {'S1': 100, 'S2': 150,'S4': 310, 'SP': 100},
                                'NovaSeq Xp'      : {'S1': 18 , 'S2': 22 ,'S4': 30, 'SP': 18 }}

    def get_process_udfs(self):
        """Get process level udfs needed to perform volume calcualtions"""

        self.flowcell_type = self.process.udf.get('Flowcell Type')
        self.protocol_type = self.process.udf.get('Protocol type')
        self.minimum_total_volume = self.process.udf.get('Minimum Total Volume (ul)')
        self.minimum_per_sample_volume = self.process.udf.get('Minimum Per Sample Volume (ul)')

    def get_bulk_volume(self):
        """Bulk volume is depending on flowcell type and protocol type."""
        
        if not self.minimum_total_volume:
            self.minimum_total_volume = self.run_mode_dict[self.protocol_type][self.flowcell_type]
            
    def get_reads(self):
        """Get number of iseq reads and number of expected nova seq reads."""

        for outpt in self.outputs:
            sample = outpt.samples[0] # only onse sample per art
            arts = lims.get_artifacts(process_type=self.source_step, samplelimsid=sample.id)
            if not arts:
                self.failed_art.append(outpt)
                continue
            n_reads =  arts[-1].udf.get('# Reads') #using latest art?
            if not n_reads:
                self.failed_art.append(outpt)
                continue
            self.iseq_reads_dict[outpt] = n_reads
            self.total_iseq_reads += n_reads
            self.total_expected_reads += sample.udf['Reads missing (M)']

    def calculate_sample_volumes(self):
        """Calucalte volume of sample based on fractions of reads"""

        for outpt, n_reads in self.iseq_reads_dict.items():
            outpt.udf['Read Pairs iSeq (M)'] = n_reads
            outpt.udf['Part sample in iSeq pool'] = outpt.udf['Read Pairs iSeq (M)']/self.total_iseq_reads
            outpt.udf['Expected part in NovaSeq pool'] = outpt.samples[0].udf['Reads missing (M)']/self.total_expected_reads
            outpt.udf['Normalising Factor'] = outpt.udf['Expected part in NovaSeq pool']/outpt.udf['Part sample in iSeq pool']
            outpt.put()
            self.sample_volumes.append(outpt.udf['Normalising Factor']*1)
            
    def adjust_based_on_min_per_sample(self):
        """adjust volumes based on minimum per sample volume"""

        min_sample_volume = min(self.sample_volumes)
        if min_sample_volume and min_sample_volume < self.minimum_per_sample_volume:
            ratio = self.minimum_per_sample_volume/min_sample_volume
        else:
            ratio = 1
        for outpt in self.outputs:
            adjusted_samp_vol = outpt.udf.get('Normalising Factor', 0)*ratio
            self.adjusted_samp_vol_dict[outpt] = adjusted_samp_vol
            self.total_sample_vol_based_on_min_per_samp += adjusted_samp_vol

    def adjust_based_on_total_min(self):
        """adjust volumes based on minimum per sample volume"""

        if self.total_sample_vol_based_on_min_per_samp < self.minimum_total_volume:
            ratio = self.minimum_total_volume/self.total_sample_vol_based_on_min_per_samp
        else:
            ratio = 1
        for outpt, vol in self.adjusted_samp_vol_dict.items():
            adjusted_samp_vol = vol*ratio
            outpt.udf['Adjusted Per Sample Volume (ul)'] = adjusted_samp_vol
            self.final_total_volume += adjusted_samp_vol
            outpt.put()

    def set_pool_info(self):
        """Set process level UDFs"""

        
        self.process.udf['Minimum Total Volume (ul)'] = self.minimum_total_volume
        self.process.udf['Total Volume (ul) - based on minimum per sample'] = round(self.total_sample_vol_based_on_min_per_samp, 2)
        self.process.udf['Final Total Sample Volume (ul)'] = self.final_total_volume
        self.process.udf['Total iSeq reads (M)'] = self.total_iseq_reads
        self.process.udf['Total nr of Reads Requested (M) (sum of reads to sequence)'] = self.total_expected_reads
        self.process.put()



def main(lims, args):
    process = Process(lims, id = args.pid)
    CV = CaculateVolumes(process, args.step)
    CV.get_process_udfs()
    CV.get_bulk_volume()
    CV.get_reads()
    CV.calculate_sample_volumes()
    CV.adjust_based_on_min_per_sample()
    CV.adjust_based_on_total_min()
    CV.set_pool_info()

    if CV.failed_art:
        sys.exit('Artifacts: '+ ', '.join( CV.failed_art)+", don't seem to have passed the iseq BCL conversion and demultiplexing step. No UDFs found.")
    else:
        print >> sys.stderr, 'UDFs were succsessfully copied!'



if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'step',
                        help=(''))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
