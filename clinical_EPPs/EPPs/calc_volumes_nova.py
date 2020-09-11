#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import sys


DESC = """Script to calculate sample volumes for NovaSeq Standard and NovaSeq Xp

"""


class NovaSeqSampleVolumes():
    def __init__(self, process):
        self.warning = []
        self.process = process
        self.minimum_per_sample_volume = None
        self.min_sample = None
        self.bulk_pool_vol = None
        self.adjusted_bulk_pool_vol = None
        self.final_conc = None
        self.total_sample_vol = None
        self.RSB_vol = None
        self.nr_samples = None
        self.total_reads = None
        self.artifacts = []
        self.missing_samp_udf = False
        self.run_mode_dict =  {'NovaSeq Standard' : {'S1': 100, 'S2': 150, 'S4': 310, 'SP': 100},
                                'NovaSeq Xp'      : {'S1': 18 , 'S2': 22 , 'S4': 30, 'SP': 18}}

    def get_artifacts(self):
        """Get outpout artifacts and count nr samples"""

        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]
        self.nr_samples = len(self.artifacts)

    def get_process_udfs(self):
        """Get process level udfs needed to perform volume calcualtions"""

        self.flowcell_type = self.process.udf.get('Flowcell Type')
        self.protocol_type = self.process.udf.get('Protocol type')
        self.final_conc = self.process.udf.get('Final Loading Concentration (pM)')
        self.minimum_per_sample_volume = self.process.udf.get('Minimum Per Sample Volume (ul)')

    def calculate_bulk_volume(self):
        """Bulk volume is depending on flowcell type and protocol type."""
        self.bulk_pool_vol = self.run_mode_dict[self.protocol_type][self.flowcell_type]

    def calculate_average_reads_to_sequence(self):
        all_reads = [float(art.udf.get('Reads to sequence (M)', 0)) for art in self.artifacts]
        if 0 in all_reads:
            self.warning.append('Reads to sequence seems to be None or 0 for some samples!')
        self.total_reads =  sum(all_reads)


    def calculate_per_sample_volume(self):
        """For each output artifact, calcualte volume and update min_sample. (The art with the 
        smallest 'Per Sample Volume (ul)')"""

        for art in self.artifacts:
            fraction_of_pool = float(art.udf.get('Reads to sequence (M)', 0))/float(self.total_reads)
            if not art.udf.get('Concentration (nM)'):
                self.warning.append('Concentration (nM) udf seems to be None or 0 for some smaples.')
                continue
            sample_vol = fraction_of_pool*(((self.final_conc * (5/1000.0) ) / float(art.udf['Concentration (nM)']) ) * self.bulk_pool_vol )
            art.udf['Per Sample Volume (ul)'] = sample_vol
            art.put()

            if not self.min_sample:
                self.min_sample = art
            elif self.min_sample.udf.get('Per Sample Volume (ul)') > sample_vol:
                self.min_sample = art

    def calculate_adjusted_per_sample_volume(self):
        """ If the smallest Per Sample Volume (ul) value is less than minimum_per_sample_volume, 
        then calculate the ratio needed to increase the smallest volume to minimum_per_sample_volume.
        the ratio is then used to set the Adjusted Per Sample Volume (ul) field value for all samples."""

        min_volume = self.min_sample.udf.get('Per Sample Volume (ul)')
        if min_volume and min_volume< self.minimum_per_sample_volume:
            ratio = self.minimum_per_sample_volume/min_volume
        else:
            ratio = 1
        for art in self.artifacts:
            art.udf['Adjusted Per Sample Volume (ul)'] = art.udf.get('Per Sample Volume (ul)',0)*ratio
            art.put()
        self.adjusted_bulk_pool_vol = self.bulk_pool_vol*ratio

    def calculate_RSB_volume(self):
        """Calculate RSB volume based on the total sample volume in the pool"""

        self.total_sample_vol = sum([art.udf['Adjusted Per Sample Volume (ul)'] for art in self.artifacts])
        self.RSB_vol = self.adjusted_bulk_pool_vol - self.total_sample_vol

    def set_pool_info(self):
        """Set process level UDFs"""

        self.process.udf['Adjusted Bulk Pool Volume (ul)'] = self.adjusted_bulk_pool_vol
        self.process.udf['Bulk Pool Volume (ul)'] = self.bulk_pool_vol
        self.process.udf['Total Sample Volume (ul)'] = round(self.total_sample_vol, 2)
        self.process.udf['RSB Volume (ul)'] = round(self.RSB_vol, 2)
        self.process.udf['Total nr of Reads Requested (sum of reads to sequence)'] = str(self.total_reads)
        self.process.put()





def main(lims, args):
    process = Process(lims, id = args.pid)
    NSSV = NovaSeqSampleVolumes(process)
    NSSV.get_artifacts()
    NSSV.get_process_udfs()
    NSSV.calculate_bulk_volume()
    NSSV.calculate_average_reads_to_sequence()
    NSSV.calculate_per_sample_volume()
    NSSV.calculate_adjusted_per_sample_volume()
    NSSV.calculate_RSB_volume()
    NSSV.set_pool_info()


    if NSSV.warning:
        unique_warnings = list(set(NSSV.warning))
        sys.exit(' '.join(unique_warnings))
    else:
        print('UDFs were succsessfully copied!', file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

