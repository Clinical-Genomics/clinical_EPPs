#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import sys


DESC = """EPP script to copy a process UDF from a process in the histry, 
          to a artifact udf on all artifacts of the current process.
          A the moment the cript looks only for pools in the current process. 
          This can be addjusted if needed in the future.

Written by Maya Brandi, Clinical Genomics, Stockholm, Sweden"""


class CopyUDF():
    def __init__(self, process, args):
        self.source_udf = args.source_udf
        self.target_udf = args.target_udf
        self.source_step = args.source_step
        self.process = process
        self.failded_udfs = False
        self.target_arts = []

    def get_pools(self):
        arts = [a for a in self.process.all_outputs() if a.type=='Analyte']
        for art in arts:
            if len(art.samples)>1:
                self.target_arts.append(art)


    def copy_udfs(self):
        """Following a artifact back in histroy till it gets to the source_process. Gets the 
        Source udf and copies it to the artifact target_udf"""
        for target_art in self.target_arts:
            art = target_art
            while art.parent_process and art.parent_process.type.name != self.source_step:
                if not art.input_artifact_list():
                    sys.exit('Artifact did not go through process: '+self.source_step)
                else:
                    art = art.input_artifact_list()[0]
            if not art.parent_process:
                sys.exit('Artifact did not go through process: '+self.source_step)
            if self.source_udf in art.parent_process.udf:
                target_art.udf[self.target_udf] = float(art.parent_process.udf[self.source_udf])
                target_art.put()
            else:
                sys.exit('Process: '+self.source_step+', does not have the udf: '+self.source_udf )

def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDF = CopyUDF(process, args)
    CUDF.get_pools()
    CUDF.copy_udfs()

    if CUDF.failded_udfs:
        sys.exit('failed to copy some udfs')
    else:
        print >> sys.stderr, 'UDFs were succsessfully copied!'

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('-u', dest = 'source_udf',
                        help=('process UDF to copy'))
    parser.add_argument('-t', dest = 'target_udf',
                        help=('artifact UDF to be set'))
    parser.add_argument('-s', dest = 'source_step',
                        help=('Name of step from wich we want to copy. '
                              'Eg: "CG002 - Aggregate QC (DNA)"'))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)

