#!/usr/bin/env python
DESC="""EPP script to calculate amount 

Maya Brandi


Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process, Artifact
import sys



class CalculateAmount:
    def __init__(self, process, lims):
        self.process = process
        self.iom = self.process.input_output_maps
        self.lims = lims
        self.artifacts = []
        self.missing_udfs = 0

    def get_artifacts(self):
        artifact_ids = [io[1]['limsid'] for io in self.iom if io[1]['output-generation-type'] == 'PerInput']
        self.artifacts = [Artifact(self.lims, id=id) for id in artifact_ids if id is not None]

    def apply_calculations(self):
        """Calculate amount and set qc for twist samples"""

        if not self.artifacts:
            return

        for artifact in self.artifacts:
            vol = artifact.udf.get('Volume (ul)')
            conc = artifact.udf.get('Concentration')
            if conc is not None and vol is not None:
                amount = conc*vol
                artifact.udf['Amount (ng)'] = amount
                if amount >= 250 and 500 >= conc >= 8.33:
                    artifact.qc_flag = 'PASSED'
                elif 100 <= amount < 250 and 100 >= conc >= 1.66:
                    artifact.qc_flag = 'PASSED'
                else:
                    artifact.qc_flag = 'FAILED'
                artifact.put()
            else:
                self.missing_udfs += 1
                
                

def main(lims,args):
    process = Process(lims, id = args.pid)
    CA = CalculateAmount(process, lims)
    CA.get_artifacts()
    CA.apply_calculations()
    

    if CA.missing_udfs:
        sys.exit('Udfs missing for some samples.')
    else:
        print >> sys.stderr, 'Calculated Amount for all samples'

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)
