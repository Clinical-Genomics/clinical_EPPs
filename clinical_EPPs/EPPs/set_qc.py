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
from genologics.entities import Process, Artifact
from genologics.epp import EppLogger
from genologics.epp import set_field
import logging
import sys



class SetQC:
    def __init__(self, lims, pid):
        self.lims = lims
        self.process = Process(lims, id = pid)
        self.input_output_maps = self.process.input_output_maps
        self.artifacts = []
        self.wrong_factor1 = []
        self.wrong_factor2 = []
        self.udfs = {}
        self.conc_treshold = None
        self.qc_fail = 0
        self.qc_pass = 0
        self.missing_udf = 0


    def get_artifacts(self):
        for inp, outp in self.input_output_maps:
            if outp.get("output-generation-type") == "PerAllInputs":
                continue
            self.artifacts.append( Artifact(self.lims,id = outp['limsid']))


    def get_tresholds(self, tresholds, udfs):
        if len(tresholds) != len(udfs):
            sys.exit('nr of threshold udfs, has to match nr of target udfs!')
        for ind, treshold in enumerate(tresholds):
            if treshold in self.process.udf:
                self.udfs[udfs[ind]] = self.process.udf[treshold]
            else:
                sys.exit('No threshold: '+treshold)


    def set_qc(self):
        if self.udfs:
            for artifact in self.artifacts:
                qc_flag = 'UNKNOWN'
                missing_udf = 0
                for udf, treshold in list(self.udfs.items()):
                    if udf in artifact.udf and artifact.udf[udf]:
                        if artifact.udf[udf] < float(treshold):
                            qc_flag = "FAILED"
                        elif qc_flag != 'FAILED':
                            qc_flag = "PASSED"
                    else:
                        missing_udf = 1
                if missing_udf:
                    qc_flag = 'UNKNOWN'
                    self.missing_udf += missing_udf
                if qc_flag=='FAILED':
                    self.qc_fail+=1
                elif qc_flag=='PASSED':
                    self.qc_pass+=1
                artifact.qc_flag = qc_flag
                artifact.put()

def main(lims,args):
    C2QC = SetQC(lims, args.pid)
    C2QC.get_artifacts()
    C2QC.get_tresholds(args.tres, args.udfs)
    C2QC.set_qc()

    abstract = ''
    if C2QC.qc_pass:
        abstract += str(C2QC.qc_pass) + ' samples passed QC. '
    if C2QC.qc_fail:
        abstract += str(C2QC.qc_fail) + ' samples failed QC. '
    if C2QC.missing_udf:
        abstract += 'Could not set QC-flaggs on '+str(C2QC.missing_udf)+' samples, due to missing udfs.'



    if C2QC.qc_fail or C2QC.missing_udf:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log',
                        help='Log file for runtime info and errors.')
    parser.add_argument('-t', dest = 'tres', nargs='+',
                        help=('Trhreshold process udfs. (has to be ordered as target udfs)'))
    parser.add_argument('-u', dest = 'udfs', nargs='+',
                        help=('Target udfs. (has to be ordered as threshold udfs)'))

    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)

