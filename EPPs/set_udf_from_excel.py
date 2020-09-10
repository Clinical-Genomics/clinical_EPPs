#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

from openpyxl import load_workbook
import json
from statistics import mean, median
import numpy
from clinical_EPPs import WELL_TRANSFORMER
import pandas as pd
from pandas import ExcelWriter
from pandas import ExcelFile


import logging
import sys

DESC = """epp script to ...
    Reads a excel file with column names: Well, col_name 1, col_name 2, etc.

    On the artifact located in the well, sets the value from col_name 1 on udf 1, col_name on udf 2, etc. 
    Not in prod yet. 


Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class File2UDF():

    def __init__(self, process, udfs, col_names):
        self.process = process
        self.all_artifacts = process.all_outputs(unique=True)
        self.artifacts = {}
        self.passed_arts = []
        self.failed_arts = []
        self.result_file = None
        self.udfs = udfs
        self.col_names = col_names


    def get_artifacts(self):
        out_artifacts = filter(lambda a: a.output_type == "ResultFile" , self.all_artifacts)
        for out_art in out_artifacts:
            art =  out_art.input_artifact_list()[0]
            well = art.location[1].replace(':','')
            self.artifacts[well] = out_art

    def get_result_file(self, result_file):
        if os.path.isfile(result_file):
            self.result_file = result_file
        else:
            shared_files = filter(lambda a: a.output_type == "SharedResultFile" , self.all_artifacts)
            for shared_file in shared_files:
                if shared_file.id == result_file:
                    self.result_file = shared_file.files[0].content_location.split('scilifelab.se')[1]
                    break



    def set_udfs(self):
        """"""
        df = pd.read_excel(self.result_file)
        for i, row in df.iterrows():
            well = row['Well']
            if well in self.artifacts:
                art = self.artifacts[well]
                for ind, col_name in enumerate(self.col_names):
                    try:
                        art.udf[self.udfs[ind]] = row[col_name]
                        self.passed_arts.append(art.id)
                    except:
                        self.failed_arts.append(art.id)
                art.put()



def main(lims, args):
    process = Process(lims, id = args.pid)
    F2UDF = File2UDF(process,args.udfs, args.col_names)
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
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                       help='Lims id for current Process')
    parser.add_argument('--result_file', default=None,
                       help=(''))

    parser.add_argument('--udfs', default=None, nargs='+',
                       help=(''))
    parser.add_argument('--col_names', default=None, nargs='+',
                       help=(''))


    args = parser.parse_args()
    if not args.result_file:
        sys.exit('Dilution File missing!')
    if len(args.udfs)!=len(args.col_names):
        sys.exit('udfs to be set has to be of the same numer as col_names!')


    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

