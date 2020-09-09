#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys
import os


DESC = """
"""

class SumReadsRML():
    def __init__(self, process):
        self.process = process
        self.pool_representatives = [] 
        self.passed_pool_replicates = {}
        
    def get_pool_representatives(self):
        """make unique sample list based on one sample from each pool. Pool representative samples."""
        all_pools = self.process.all_inputs(unique=True)
        samples = []
        for p in all_pools:
            samples.append(p.samples[0])
        self.pool_representatives = list(set(samples))
   
    def get_pool_replicates(self, pool_representative):
        """Given any submitted sample ("pool_representative") that is part of the pool we are looking for,
           return all replicates (lanes and/ore reruns) of the pool thats been run throuh sequencing.

        The function assumes a submitted sample will occure in only one pool

                                        <-- pool_replicate_11
        submitted sample_X <--> pool_1  <-- pool_replicate_12
                                        <-- pool_replicate_13

                                        <-- pool_replicate_21
        submitted sample_Y <--> pool_2  <-- pool_replicate_22
                                        <-- pool_replicate_23
        ..."""   

        pools = []
        pool_replicates = []
    
        out_arts = lims.get_artifacts(samplelimsid = pool_representative.id,
                   process_type = ["CG002 - Illumina Sequencing (Illumina SBS)"])
        out_arts = list(set(out_arts))
        for a in out_arts:
            pools += a.parent_process.all_inputs()
        pools = list(set(pools))
        for pool in pools:
            if pool_representative in pool.samples:
                pool_replicates.append(pool)
        return pool_replicates

 
    def sum_reads(self, pool_replicates):
        """Sum passed reads from all pool_replicates. Set 'Total Reads (M)' for each samp in the pool. 
        Will be the same for all samples in the pool."""
        total_reads = 0.0
        pool_name = pool_replicates[0].name
        self.passed_pool_replicates[pool_name] = 0
        for pool in pool_replicates:
            if pool.qc_flag == 'PASSED' and 'Clusters PF R1' in pool.udf:
                total_reads += float(pool.udf.get('Clusters PF R1'))
                self.passed_pool_replicates[pool_name] +=1
        M_reads = total_reads/1000000
        for s in pool_replicates[0].samples:
            s.udf['Total Reads (M)'] =  M_reads
            s.put()
        

    def set_udfs(self):
        """Set Total Reads on all samps"""
        for pool_representative in self.pool_representatives:
            pool_replicates = self.get_pool_replicates(pool_representative)
            self.sum_reads(pool_replicates)


def main(lims, args):
    process = Process(lims, id = args.pid)
    SR = SumReadsRML(process)
    SR.get_pool_representatives()
    SR.set_udfs()

    abstract = "Reads summed for: "
    for k, v in SR.passed_pool_replicates.items():
        abstract += str(k) +' from '+str(v)+' lanes, '

    print >> sys.stderr, abstract 

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
