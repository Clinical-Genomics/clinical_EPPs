#!/usr/bin/env python
DESC="""EPP script to calculate conc in ng from concentration and volume 
udf:s in Clarity LIMS. The script checks that the 'Volume (ul)' and 
'Concentration' udf:s are defined. Sets qc-flaggs based on conc treshold

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



class Concentration2QC:
    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.correct_artifacts = []
        self.wrong_factor1 = []
        self.wrong_factor2 = []
        self.conc_treshold = None
        self.low_conc = 0

    def get_treshold(self):
        if 'Minimum required Concentration' in self.process.udf:
            treshold = self.process.udf['Minimum required Concentration']
            if treshold != '-':
                self.conc_treshold = treshold
        
    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "ResultFile"]
        self.wrong_factor1 = self.check_udf_is_defined(self.artifacts, 'Concentration')

    def set_qc(self):
        if self.conc_treshold:
            for artifact in self.correct_artifacts:
                if 'Concentration' in artifact.udf and artifact.udf['Concentration']:
                    if artifact.udf['Concentration'] < float(self.conc_treshold):
                        artifact.qc_flag = "FAILED"
                        self.low_conc +=1
                    else:
                        artifact.qc_flag = "PASSED"
                    artifact.put()
                    set_field(artifact)

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
    C2QC = Concentration2QC(process)
    C2QC.get_artifacts()
    C2QC.get_treshold()
    C2QC.set_qc()
    d = {'ca': len(C2QC.correct_artifacts),
         'ia': len(C2QC.wrong_factor1)+ len(C2QC.wrong_factor2) }

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if len(C2QC.wrong_factor1)+ len(C2QC.wrong_factor2):
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file for runtime info and errors.')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
