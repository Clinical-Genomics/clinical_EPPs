#!/home/glsai/miniconda2/envs/epp_master/bin/python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys
import csv


DESC = """epp script to generate Bravo CSV file
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class BravoCSV():

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.failed_arts = []

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]

    def make_csv_1471(self, csv_file):
        csv_file = csv_file+'bravo_normalization.csv'
        with open( csv_file , 'wb') as bravo_csv:
            wr = csv.writer(bravo_csv)
            art_dict = {a.location[1] : a  for a in self.artifacts}
            for col in range(1,13):
                for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                    well = row + ':' + str(col)
                    if well in art_dict:
                        art = art_dict[well]
                        try:
                            row_list = [row + str(col) , str(art.udf['Volume Buffer (ul)']), str(art.udf['Sample Volume (ul)'])]
                            wr.writerow(row_list)
                        except:
                            self.failed_arts.append(art.name)


    def make_csv_1564(self, udf, csv_file):
        csv_file = csv_file+'_'+udf.replace(' ','')+'_bravo_normalization.csv'
        with open( csv_file , 'wb') as bravo_csv:
            wr = csv.writer(bravo_csv)
            wr.writerow(['SourceBC','SourceWell','DestinationWell','Volume'])
            art_dict = {a.location[1] : a  for a in self.artifacts}
            for col in range(1,13):
                for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                    well = row + ':' + str(col)
                    if well in art_dict:
                        art = art_dict[well]
                        try:
                            row_list = ['abc',row + str(col), row + str(col) ,  str(art.udf[udf])]
                            wr.writerow(row_list)
                        except:
                            self.failed_arts.append(art.name)
                    else:
                        row_list = ['abc',row + str(col), row + str(col) ,  '0']
                        wr.writerow(row_list)



def main(lims, args):
    process = Process(lims, id = args.pid)
    BCSV = BravoCSV(process)
    BCSV.get_artifacts()
    if args.doc1564:
        BCSV.make_csv_1564('Sample Volume (ul)', args.sample_volume_file)
        BCSV.make_csv_1564('Volume Buffer (ul)', args.buffer_volume_file)
    if args.doc1471:
        BCSV.make_csv_1471(args.csv)

    d = {'ia': ', '.join(BCSV.failed_arts)}

    if BCSV.failed_arts:
        abstract = ("Wrong and/or blank values for some udfs. Could not add sample "
                 "information to Bravo CSV for the following samples: {ia}").format(**d)
        sys.exit(abstract)
    else:
        abstract = "Bravo CSV sucsessfully generated."
        print(abstract, file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--csv', default=None,
                        help=('csv file'))
    parser.add_argument('--doc1471', action='store_true',
                            help='Use this flagg to generate 1471 bravo file')
    parser.add_argument('--doc1564', action='store_true',
                            help='Use this flagg to generate 1564 bravo file')
    parser.add_argument('--sample_volume_file', default=None,
                        help=('csv file'))
    parser.add_argument('--buffer_volume_file', default=None,
                        help=('csv file'))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
