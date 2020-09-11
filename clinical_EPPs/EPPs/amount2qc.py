#!/usr/bin/env python
DESC="""EPP script to calculate amount in ng from concentration and volume 
udf:s in Clarity LIMS. The script checks that the 'Volume (ul)' and 
'Concentration' udf:s are defined. Sets qc-flaggs based on amount treshold
Johannes Alneberg, 
Maya Brandi
Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field
import logging
import sys



class Amount2QC:
    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.correct_artifacts = []
        self.wrong_factor1 = []
        self.wrong_factor2 = []
        self.amount_treshold = None
        self.low_conc = 0

    def get_treshold(self):
        if 'Minimum required amount (ng)' in self.process.udf:
            treshold = self.process.udf['Minimum required amount (ng)']
            if treshold != '-':
                self.amount_treshold = treshold

        
    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "ResultFile"]
        self.wrong_factor1 = self.check_udf_is_defined(self.artifacts, 'Concentration')
        if not self.process.type.name == 'CG002 - Qubit QC (Library Validation)':
            self.wrong_factor2 = self.check_udf_is_defined(self.correct_artifacts, 'Volume (ul)')

    def set_qc(self):
        if self.amount_treshold:
            for artifact in self.correct_artifacts:
                if 'Amount (ng)' in artifact.udf and artifact.udf['Amount (ng)']:
                    if artifact.udf['Amount (ng)'] < self.amount_treshold:
                        artifact.qc_flag = "FAILED"
                        self.low_conc +=1
                    else:
                        artifact.qc_flag = "PASSED"
                    artifact.put()
                    set_field(artifact)

    def apply_calculations(self):
        """For each result file of the process: if its corresponding inart has the udf 
        'Dilution Fold', the result_udf: 'Amount (ng)' is calculated as
        'Amount (ng)' =  'Concentration'*'Volume (ul)'*'Dilution Fold'
        otherwise its calculated as
        'Amount (ng)' =  'Concentration'*'Volume (ul)'"""
        if self.correct_artifacts:
            logging.info("result_udf: Amount (ng), udf1: Concentration, operator: *, udf2: Volume (ul)")
            for artifact in self.correct_artifacts:
                try:
                    artifact.udf['Amount (ng)']
                except KeyError:
                    artifact.udf['Amount (ng)']=0 
                try:
                    inart = self.process.input_per_sample(artifact.samples[0].name)[0]
                    dil_fold = inart.udf['Dilution Fold']
                except:
                    dil_fold = None
                if self.process.type.name == 'CG002 - Qubit QC (Library Validation)':
                    vol = 27
                else:
                    vol = artifact.udf['Volume (ul)']
                logging.info(("Updating: Artifact id: {0}, "
                             "result_udf: {1}, udf1: {2}, "
                             "operator: *, udf2: {3}").format(artifact.id, 
                                                                artifact.udf.get('Amount (ng)',0),
                                                                artifact.udf['Concentration'],
                                                                vol))
                prod = eval('{0}{1}{2}'.format(artifact.udf['Concentration'],'*',vol))
                if dil_fold:
                    prod = eval('{0}{1}{2}'.format(prod, '*', dil_fold))
                artifact.udf['Amount (ng)'] = prod
                artifact.put()
                logging.info('Updated Amount (ng) to {0}.'.format(artifact.udf['Amount (ng)']))
                
    def check_udf_is_defined(self, artifacts, udf):
        """ Filter and Warn if udf is not defined for any of artifacts. """
        incorrect_artifacts = []
        correct_artifacts = []
        for artifact in artifacts:
            if (udf in artifact.udf):
                correct_artifacts.append(artifact)
            else:
                logging.warning(("Found artifact for sample {0} with {1} "
                                 "undefined/blank, skipping").format(artifact.samples[0].name, udf))
                incorrect_artifacts.append(artifact)
        self.correct_artifacts = correct_artifacts
        return  incorrect_artifacts 


def main(lims,args):
    process = Process(lims, id = args.pid)
    A2QC = Amount2QC(process)
    A2QC.get_artifacts()
    A2QC.get_treshold()
    A2QC.apply_calculations()
    A2QC.set_qc()
    d = {'ca': len(A2QC.correct_artifacts),
         'ia': len(A2QC.wrong_factor1)+ len(A2QC.wrong_factor2) }

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs. ").format(**d)
    if not A2QC.amount_treshold:
        abstract = 'Unable to set QC-flaggs. "Minimum requiered amount (ng)" has not been set.'
        sys.exit(abstract)
    elif len(A2QC.wrong_factor1)+ len(A2QC.wrong_factor2):
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log',
                        help='Log file for runtime info and errors.')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
