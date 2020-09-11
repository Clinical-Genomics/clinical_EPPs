#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process, ReagentType
from genologics.epp import EppLogger

import logging
import sys

DESC = """epp script to check for duplicate indexes in step

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class CheckIndex():

    def __init__(self, process):
        self.process = process
        self.all_artifacts = []
        self.duplicates = []
        self.index_dict = {}
        self.all_indexes = []
        self.logfile = None

    def get_artifacts(self):
        all_artifacts = self.process.all_inputs()
        self.all_artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]

    def get_samples(self):
        for art in self.all_artifacts:
            reagent_label_names = art.reagent_labels
            for name in reagent_label_names:
                reagent_types = lims.get_reagent_types(name=name)
                if len(reagent_types)==1: #(Will never be morte than one. names are unique)
                    sequence = reagent_types[0].sequence
                    sequence_short = sequence.split('-')[0]
                    self.all_indexes.append(sequence_short)
                    if sequence_short in list(self.index_dict.keys()):
                        self.index_dict[sequence_short][art] = {'name':name,'sequence':sequence}
                    else:
                        self.index_dict[sequence_short] = {art : {'name':name,'sequence':sequence}}


    def check_dupl(self):
        for i, index1 in enumerate(self.all_indexes):
            for j, index2 in enumerate(self.all_indexes):
                if i!=j:
                    min_lengt = min(len(index1),len(index2))
                    if index1[:min_lengt]==index2[:min_lengt]:
                        self.duplicates.append(index1)
                        self.duplicates.append(index2)
        self.duplicates=list(set(self.duplicates))

    def make_log(self, log_file):
        self.logfile = open(log_file, 'a')
        self.logfile.write(', '.join(['sample','index name', 'index sequence']))
        for index in self.duplicates:
            art_dict = self.index_dict[index]
            for art, index_info in list(art_dict.items()):
                self.logfile.write('\n'+', '.join([art.name, index_info['name'], index_info['sequence']]))
        self.logfile.close()

def main(lims, args):
    process = Process(lims, id = args.pid)
    CI = CheckIndex(process)
    CI.get_artifacts()
    CI.get_samples()
    CI.check_dupl()


    if CI.duplicates:
        CI.make_log(args.log)
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

