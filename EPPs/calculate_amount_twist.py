#!/usr/bin/env python
DESC="""EPP script to calculate amount 

Maya Brandi


Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
import sys



class CalculationsTwist:
    def __init__(self, process):
        self.process = process
        self.pool_size = 1500
        self.pools = []
        self.okej = 0
        self.failed = 0
        self.low_conc = 0

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.pools = filter(lambda a: a.output_type == "Analyte" , all_artifacts)

    def calculate_volumes(self):
        for pool in self.pools:
            artifacts = pool.input_artifact_list()
            total_reads = 0
            for art in artifacts:
                reads = art.samples[0].udf.get('Reads missing (M)')
                total_reads += reads
            for art in artifacts:
                reads = art.samples[0].udf.get('Reads missing (M)')
                fract_of_pool = reads/float(total_reads)
                amount = self.pool_size * fract_of_pool
                vol = amount/art.udf.get('Concentration')
                art.udf['Volume of sample (ul)'] = vol
                art.put()

def main(lims,args):
    process = Process(lims, id = args.pid)
    AT = CalculationsTwist(process)
    AT.get_artifacts()
    AT.calculate_volumes()
    
    abstract = ''
    if AT.failed:
        abstract += 'Failed to perform calculations for '+ str(AT.failed)+ ' samples. Some udfs are invalid or missing. '
    if AT.okej:
        abstract += 'Perform calculations for '+ str(AT.okej)+ ' samples.'

    if AT.failed:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
