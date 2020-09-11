#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import sys

DESC = """Script to set denaturation volumes for NovaSeq Xp, based on flowcell type.
The script is taylored for the Xp Denature & ExAmp step in the NovaSeq WF.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class DenaturateXP():
    """Will set denaturation volumes for NovaSeq Xp, based on flowcell type.
    All information could be set on process level (since its the same for all 
    pools in the step), but we save some of it on the artifacts because the 
    next step requires so."""

    def __init__(self, process):
        self.process = process
        self.artifacts = []
        self.process_settings = {'S1': {'DPX1 Volume (ul)': 126,
                                        'DPX2 Volume (ul)': 18,
                                        'DPX3 Volume (ul)': 66},
                                 'S2': {'DPX1 Volume (ul)': 126,
                                        'DPX2 Volume (ul)': 18,
                                        'DPX3 Volume (ul)': 66},
                                 'S4': {'DPX1 Volume (ul)': 315,
                                        'DPX2 Volume (ul)': 45,
                                        'DPX3 Volume (ul)': 165},
                                 'SP': {'DPX1 Volume (ul)': 126,
                                        'DPX2 Volume (ul)': 18,
                                        'DPX3 Volume (ul)': 66}}
        self.artifact_settings = {'S1': {'Loading Workflow Type': 'NovaSeq Xp',
                                        'Flowcell Type' : 'S1',
                                        'BP Aliquot Volume (ul)': 18,
                                        'Mastermix per Lane (ul)': 63,
                                        'NaOH Volume (ul)': 4,
                                        'Tris-HCl Volume (ul)': 5,
                                        'PhiX Volume (ul)' : 0.7},
                                 'S2': {'Loading Workflow Type': 'NovaSeq Xp',
                                        'Flowcell Type' : 'S2',
                                        'BP Aliquot Volume (ul)': 22,
                                        'Mastermix per Lane (ul)': 77,
                                        'NaOH Volume (ul)': 5,
                                        'Tris-HCl Volume (ul)': 6,
                                        'PhiX Volume (ul)' : 0.8},
                                 'S4': {'Loading Workflow Type': 'NovaSeq Xp',
                                        'Flowcell Type' : 'S4',
                                        'BP Aliquot Volume (ul)': 30,
                                        'Mastermix per Lane (ul)': 105,
                                        'NaOH Volume (ul)': 7,
                                        'Tris-HCl Volume (ul)': 8,
                                        'PhiX Volume (ul)' : 1.1},
                                  'SP': {'Loading Workflow Type': 'NovaSeq Xp',
                                        'Flowcell Type' : 'SP',
                                        'BP Aliquot Volume (ul)': 18,
                                        'Mastermix per Lane (ul)': 63,
                                        'NaOH Volume (ul)': 4,
                                        'Tris-HCl Volume (ul)': 5,
                                        'PhiX Volume (ul)' : 0.7}}
    
    def get_artifacts(self):
        """Get output artifacts"""

        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]
 

    def set_udfs(self):
        """Set pprocess level udfs and artifact level udfs based on Flowcell Type.
        Flowcell type is fetched from any input artifact 'Flowcell Type' udf. 
        The inarts will allways have this udf."""

        flowcell_type = self.process.all_inputs()[0].udf.get('Flowcell Type')

        for key, val in list(self.process_settings[flowcell_type].items()):
            self.process.udf[key] = val
        self.process.put()

        for art in self.artifacts:
            for key, val in list(self.artifact_settings[flowcell_type].items()):
                art.udf[key] = val
                art.put()


def main(lims, args):
    process = Process(lims, id = args.pid)
    DXP = DenaturateXP(process)
    DXP.get_artifacts()
    DXP.set_udfs()


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
