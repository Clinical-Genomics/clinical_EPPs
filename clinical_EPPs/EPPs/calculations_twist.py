#!/usr/bin/env python
DESC="""EPP script to performe calculations in some different steps in the twist WF


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
        self.iom = process.input_output_maps
        self.artifacts = []
        self.amount_fail = False
        self.okej = 0
        self.failed = 0
        self.missing_udfs = []
        self.low_conc = 0

    def get_artifacts(self, process_type):
        if process_type== 'libval':
            self.artifacts = [io[1]['uri'] for io in self.iom if io[1]['output-generation-type'] == 'PerInput']
        else:
            all_artifacts = self.process.all_outputs(unique=True)
            self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]

    def calculate_volumes_for_aliquot(self):
        for art in self.artifacts:
            amount = art.udf.get('Amount (ng)')
            concentration = art.udf.get('Concentration')
            amount_needed = art.udf.get('Amount needed (ng)')
            if None in [amount, concentration, amount_needed]:
                self.failed +=1
                self.missing_udfs += ['Amount (ng)', 'Concentration', 'Amount needed (ng)']
                continue
            art.udf['Sample Volume (ul)'] = amount_needed/float(concentration)
            art.udf['Volume H2O (ul)'] = 30 - art.udf['Sample Volume (ul)']
            art.put()
            self.okej +=1
    
    def calculate_volumes_for_pooling(self):
        all_volumes = [] 
        for pool in self.artifacts:
            total_volume = 0
            pool_size = pool.udf.get('Total Amount (ng)')
            artifacts = pool.input_artifact_list()
            total_reads = 0
            for art in artifacts:
                reads = art.samples[0].udf.get('Reads missing (M)')
                if reads:
                    total_reads += reads
            if total_reads == 0:
                sys.exit('All samples seem to have Missing Reads = 0. You dont want to sequence any of the samples?')
            for art in artifacts:
                reads = art.samples[0].udf.get('Reads missing (M)')
                concentration = art.udf.get('Concentration')
                if None in [reads, concentration]:
                    self.missing_udfs += ['Reads missing (M)', 'Concentration']
                    total_volume = None
                    break
                fract_of_pool = reads/float(total_reads)
                amount = pool_size * fract_of_pool
                vol = amount/concentration
                if vol>15:
                    vol=15
                if amount<187.5:
                    pool.qc_flag='FAILED'
                    self.amount_fail = True
                art.udf['Amount taken (ng)'] = amount
                art.udf['Volume of sample (ul)'] = vol
                art.put()            
                total_volume += vol
            if total_volume:
                pool.udf['Total Volume (ul)'] = total_volume
                all_volumes.append(total_volume)
                self.okej +=1
            else:
                self.failed +=1
        for pool in self.artifacts:
            if pool.udf.get('Total Volume (ul)'):
                pool.udf['Volume H2O (ul)'] = max(all_volumes) - pool.udf.get('Total Volume (ul)')
            pool.put()
            

    def calcualate_amount_for_libval(self):
        sample_volume = self.process.udf.get('Sample Volume (ul)')
        amount_needed = self.process.udf.get('Amount Needed (ng)')
        for art in self.artifacts:
            concentration = art.udf.get('Concentration')
            if concentration == None:
                self.failed +=1
                self.missing_udfs += ['Concentration']
                continue
            art.udf['Amount (ng)'] = concentration*sample_volume
            if art.udf['Amount (ng)'] < amount_needed:
                art.qc_flag = 'FAILED'
            else:
                art.qc_flag = 'PASSED'
            art.put()
            self.okej +=1

def main(lims,args):
    process = Process(lims, id = args.pid)
    AT = CalculationsTwist(process)
    AT.get_artifacts(args.calculate)
    if args.calculate == 'pooling':
        AT.calculate_volumes_for_pooling()
    elif args.calculate == 'libval':
        AT.calcualate_amount_for_libval()
    elif args.calculate == 'aliquot':
        AT.calculate_volumes_for_aliquot()
    else:
        sys.exit('Non valid argument given. -c can take pooling/libval/aliquot')
    
    abstract = ''
    if AT.amount_fail:
        abstract += 'Input amount low for samples in pool. Generate placement map for more info. '
    if AT.failed:
        missing = ', '.join( list(set(AT.missing_udfs)))
        abstract += 'Failed to perform calculations for '+ str(AT.failed)+ ' samples. Some of the following udfs are invalid or missing: ' +   missing + '. '
    if AT.okej:
        abstract += 'Performed calculations for '+ str(AT.okej)+ ' samples.'

    if AT.failed or AT.amount_fail:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument("-c", dest='calculate', help = 'pooling/libval/aliquot')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
