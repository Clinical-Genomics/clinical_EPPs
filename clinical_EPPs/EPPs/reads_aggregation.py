#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import sys
import os

DESC = """
"""


class SumReadsRML():
    def __init__(self, pools, process_types):
        self.pools = pools
        self.process_types = process_types
        self.passed_pool_replicates = {}
        self.failed_pools = []
        self.passed_pools = {}

    def _sum_reads_per_pool(self, pool):
        """Sum passed sample reads from all lanes and runs. Return total reads in Milions"""
        total_reads = 0.0
        for sample in pool.samples:
            nr_lanes = 0
            arts = lims.get_artifacts(samplelimsid = sample.id, process_type = self.process_types)
            for art in arts:
                if art.qc_flag == 'PASSED' and '# Reads' in art.udf:
                    total_reads += float(art.udf.get('# Reads'))
                    nr_lanes +=1
            if nr_lanes:
                self.passed_pools[pool.name] = nr_lanes
            else:
                self.failed_pools.append(pool.id)
        return total_reads/1000000

    def _set_udfs(self, pool, M_reads):
        """Set Total Reads on all samps"""
        for samp in pool.samples:
            samp.udf['Total Reads (M)'] =  M_reads
            samp.put()

    def sum_reads(self):
        for pool in self.pools:
            M_reads = self._sum_reads_per_pool(pool)
            self._set_udfs(pool, M_reads)


class SumReads():
    def __init__(self, samples, process_types):
        self.process_types = process_types
        self.samples = samples
        self.failed_samps = 0
        self.passed_samps =0

    def sum_reads(self, sample):
        """Sum passed sample reads from all lanes and runs. Return total reads in Milions"""
        total_reads = 0.0
        arts = lims.get_artifacts(samplelimsid = sample.id, process_type = self.process_types)
        for art in arts:
            if art.qc_flag == 'PASSED' and '# Reads' in art.udf:
                total_reads += float(art.udf.get('# Reads'))
        return total_reads/1000000

    def set_udfs(self):
        """Set Total Reads on all samps"""
        for samp in self.samples:
            M_reads = self.sum_reads(samp)
            try:
                samp.udf['Total Reads (M)'] =  M_reads
                samp.put()
                self.passed_samps +=1
            except:
                self.failed_samps +=1
                pass

class PoolsAndSamples():
    def __init__(self, process):
        self.process = process
        self.samples = []
        self.pools = []

    def get_pools_and_samples(self):
        all_artifacts = self.process.all_inputs(unique=True)
        samples = []
        for a in all_artifacts:
            if len(a.samples) > 1:
                self.pools.append(a)
            elif len(a.samples) == 1:
                samples += a.samples
        self.samples = list(set(samples))


def main(lims, args):
    process = Process(lims, id = args.pid)
    PAS = PoolsAndSamples(process)
    PAS.get_pools_and_samples()
    abstract = ''
    if PAS.samples:
        abstract += 'Found Samples - Summing demultiplexed reads on sample level. '
        SR = SumReads(PAS.samples, args.process_types)
        SR.set_udfs()
        abstract += "Reads aggregated for "+str(SR.passed_samps)+" sample(s). "
    if PAS.pools:
        abstract += 'Found pools - Summing reads from all runs. '
        SRRML = SumReadsRML(PAS.pools, args.process_types)
        SRRML.sum_reads()
        abstract += "Reads summed for: "
        for k, v in SRRML.passed_pools.items():
            abstract += str(k) +' from '+str(v)+' lanes, '


    print >> sys.stderr, abstract

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'process_types',  nargs='+', 
                        help='Aggregate reads from this process type(s)')

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

