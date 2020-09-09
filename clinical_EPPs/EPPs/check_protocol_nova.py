#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys


DESC = """The script is taylored for the Make Pool steps in the NovaSeq WF. Same script
for both Xp and Standard. It will check we are in the correct step based on the 
'Flowcell Type' and 'Protocol type' udfs selected in the parrent process.

It will allso set the denatudation volumes for Standard samples. Not for Xp.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

class CheckNovaSettings():

    def __init__(self, process, standard, xp):
        self.process = process
        self.artifacts = []
        self.standard = standard
        self.xp = xp
        self.parent_process = process.all_inputs()[0].parent_process
        self.flowcell_type = self.parent_process.udf.get('Flowcell Type')
        self.protocol_type = self.parent_process.udf.get('Protocol type')
        self.denaturation_volumes =  {'S1': {'Volume of Pool to Denature (ul)': 100.0,
                                                    'NaOH Volume (ul)' : 25.0,
                                                    'Tris-HCl Volume (ul)': 25.0,
                                                    'PhiX Volume (ul)': 0.6} ,
                                      'S2': {'Volume of Pool to Denature (ul)': 150.0,
                                                    'NaOH Volume (ul)' : 37,
                                                    'Tris-HCl Volume (ul)': 38,
                                                    'PhiX Volume (ul)': 0.9},
                                      'S4': {'Volume of Pool to Denature (ul)': 310,
                                                    'NaOH Volume (ul)' : 77,
                                                    'Tris-HCl Volume (ul)': 78,
                                                    'PhiX Volume (ul)': 1.9}}

    def get_artifacts(self):
        """Get output artifacts"""

        all_artifacts = self.process.all_outputs(unique=True)
        self.artifacts = filter(lambda a: a.output_type == "Analyte" , all_artifacts)

    def check_protocol_setings(self):
        """Will exit with warning if wrong protocol type"""
        if self.protocol_type == 'NovaSeq Standard' and self.process.type.name != self.standard:
            sys.exit('Wrong protocol type')
        elif self.protocol_type == 'NovaSeq Xp' and self.process.type.name != self.xp:
            sys.exit('Wrong protocol type')

    def set_volumes_for_standard(self):
        """Sets the denatudation volumes for Standard samples."""

        if self.protocol_type == 'NovaSeq Standard':
            for key, val in self.denaturation_volumes[self.flowcell_type].items():
                self.process.udf[key] = val
            self.process.put()

    def set_udfs(self):
        """Sets 'Flowcell Type' and 'Loading Workflow Type' on the artifacts. Needed in next step."""

        for art in self.artifacts:
            art.udf['Flowcell Type'] = self.flowcell_type
            art.udf['Loading Workflow Type'] = self.protocol_type
            art.put()

def main(lims, args):
    process = Process(lims, id = args.pid)
    CNS = CheckNovaSettings(process, standard = args.standard, xp = args.xp)
    CNS.get_artifacts()
    CNS.check_protocol_setings()
    CNS.set_volumes_for_standard()
    CNS.set_udfs()


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'standard',
                        help='Standard step')
    parser.add_argument('-x', dest = 'xp',
                        help='XP step')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

