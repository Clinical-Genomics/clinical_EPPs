#!/home/glsai/miniconda2/envs/epp_master/bin/python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import csv
import sys

DESC = """epp script to generate Bravo CSV file
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class ToCSV():

    def __init__(self, process):
        self.process = process
        self.plate_dict = {}
        self.failed_arts = []
        self.csv_files = []

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte" , all_artifacts)
        for art in all_artifacts:
            if art.output_type == "Analyte":
                plate_name = art.location[0].name
                well = art.location[1]
                if plate_name not in self.plate_dict:
                    self.plate_dict[plate_name] = {well: art}
                else:
                    self.plate_dict[plate_name][well] = art


    def make_csv(self, udf, csv_files):
        for i, plate in enumerate(self.plate_dict):
            art_dict = self.plate_dict[plate]
            try:
                csv_file = csv_files[i] + '_'+plate.replace(' ','')+'_buffer.csv'
            except:
                sys.exit('Did not generate csv files for all plates. You have more plates than there are csv file placeholders!')
            with open( csv_file , 'wb') as bravo_csv:
                wr = csv.writer(bravo_csv)
                wr.writerow(['SourceBC','SourceWell','DestinationWell', 'Volume'])
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
    TCSV = ToCSV(process)
    TCSV.get_artifacts()
    TCSV.make_csv(args.udf, args.csvs)

    d = {'ia': ', '.join(TCSV.failed_arts)}

    if TCSV.failed_arts:
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
    parser.add_argument('--csvs', default=[], nargs='+',
                        help=('csv files'))
    parser.add_argument('--udf', dest = 'udf', default = None,
                            help='udfs to add')

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
