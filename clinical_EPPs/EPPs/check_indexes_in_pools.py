#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process, ReagentType
from genologics.epp import EppLogger

import logging
import sys

DESC = """epp script to check for duplicate indexes in pools. Comparing sequences. Not index names. 

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

class Pool():
    def __init__(self, pool):
        self.pool = pool
        self.pooled_arts = [] 
        self.index_dict = {}
        self.duplicates = []
        self.all_indexes = []

    def _recursive_find_samples_in_pool(self, artifact_list):
        for art in artifact_list:
            if len(art.samples)==1:
                self.pooled_arts.append(art)
            else:
                self._recursive_find_samples_in_pool(art.input_artifact_list())

    def get_indexes(self):
        self._recursive_find_samples_in_pool(self.pool.input_artifact_list())
        for art in self.pooled_arts:
            reagent_label_names = art.reagent_labels
            for name in reagent_label_names:
                reagent_types = lims.get_reagent_types(name=name)
                sequence = reagent_types[0].sequence #(Will never be morte than one. names are unique)
                self.all_indexes.append(sequence)
                if sequence in list(self.index_dict.keys()):
                    self.index_dict[sequence][art] = {'name':name,'sequence':sequence}
                else:
                    self.index_dict[sequence] = {art : {'name':name,'sequence':sequence}}

    def check_dupl(self):
        for i, index1 in enumerate(self.all_indexes):
            for j, index2 in enumerate(self.all_indexes):
                if i!=j:
                    min_lengt = min(len(index1),len(index2))
                    if index1[:min_lengt]==index2[:min_lengt]:
                        self.duplicates.append(index1)
                        self.duplicates.append(index2)
        self.duplicates=list(set(self.duplicates))

class CheckIndex():

    def __init__(self, process, log_file):
        self.logfile = open(log_file, 'a')
        self.process = process
        self.pools = []
        self.duplicates = False

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs()
        self.pools = [a for a in all_artifacts if a.output_type == "Analyte"]

    def check_each_pool(self):
        for pool in self.pools:
            P = Pool(pool)
            P.get_indexes()
            P.check_dupl()
            if P.duplicates:
                self.add_to_log(P)

    def add_to_log(self, P):
        self.logfile.write('\n\nDuplicates in Pool: '+ P.pool.name +'\n')
        self.logfile.write(', '.join(['sample','index name', 'index sequence']))
        for index in P.duplicates:
            self.duplicates = True
            art_dict = P.index_dict[index]
            for art, index_info in list(art_dict.items()):
                self.logfile.write('\n'+', '.join([art.name, index_info['name'], index_info['sequence']]))

    def close_log(self):
        self.logfile.close()

def main(lims, args):
    process = Process(lims, id = args.pid)
    CI = CheckIndex(process, args.log)
    CI.get_artifacts()
    CI.check_each_pool()
    CI.close_log()

    if CI.duplicates:
        sys.exit('Warning: Duplicated indexes. See log file!')
    else:
        print('No duplicate indexes', file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', default = None , dest = 'log',
                        help='Log file')

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
