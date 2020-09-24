#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process

import pandas as pd
import sys
import os



DESC = """epp script to ...
    Reads a excel file with column names: Well, col_name 1, col_name 2, etc.

    On the artifact located in the well, sets the value from col_name 1 on udf 1, col_name on udf 2, etc. 
    Not in prod yet. 


Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class File2UDF():

    def __init__(self, process):
        self.process = process
        self.all_artifacts = process.all_outputs(unique=True)
        self.artifacts = {}
        self.passed_arts = []
        self.failed_arts = []
        self.result_file = None


    def get_artifacts(self):
        for art in self.all_artifacts:
            try:
                col,row = art.location[1].split(':')
                if len(row)==1:
                    row = '0'+row
                well = col + row
                self.artifacts[well] = art
            except:
                ## shared file - skip
                pass

    def get_result_file(self, result_file):
        if result_file and os.path.isfile(result_file):
            self.result_file = result_file
        else:
            qubit_files = filter(lambda a: a.name in ["Qubit Result File", "Quantit Result File"], self.all_artifacts)
            if len(qubit_files)>1:
                sys.exit('more than one Qubit Result File')
            else:
                self.result_file = qubit_files[0].files[0].content_location.split('scilifelab.se')[1]

    def set_udfs(self):
        df = pd.read_excel(self.result_file, header=None)
        for i, row in df.iterrows():
            well = row[0]
            if well in self.artifacts:
                art = self.artifacts[well]
                try:
                    conc = int(row[2]) # will fail if nan
                    art.udf['Concentration'] = row[2]
                    self.passed_arts.append(art.id)
                except:
                    self.failed_arts.append(art.id)
                art.put()



def main(lims, args):
    process = Process(lims, id = args.pid)
    F2UDF = File2UDF(process)
    F2UDF.get_result_file(args.result_file)
    F2UDF.get_artifacts()
    F2UDF.set_udfs()

    F2UDF.passed_arts.sort()
    F2UDF.failed_arts.sort()
    F2UDF.passed_arts = set(F2UDF.passed_arts)
    F2UDF.failed_arts = set(F2UDF.failed_arts)

    d = {'ca': len(F2UDF.passed_arts),
         'ia': len(F2UDF.failed_arts)}
    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if F2UDF.failed_arts:
        sys.exit(abstract)
    else:
        print >> sys.stderr, abstract

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                       help='Lims id for current Process')
    parser.add_argument('--result_file', default=None,
                       help=(''))


    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

