#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger
import logging
import sys

DESC = """

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class CopyUDFS():

    def __init__(self, process):
        self.process = process
        self.artifacts = process.all_inputs(unique=True)
        self.passed_arts = 0
        self.failed_arts = 0

    def set_udfs(self):
        for art in self.artifacts:
            if art.parent_process:
                sys.exit('This is not the first step for these samples. Can therefor not get the original container.')
            if len(art.samples)!=1:
                sys.exit('Error: more than one sample per artifact. Unable to copy udfs. Assumes a 1-1 relation between sample and artifact.')
            sample = art.samples[0]
            try:
                sample.udf['Original Well'] = art.location[1]
                sample.udf['Original Container'] = art.location[0].name
                sample.put()
                self.passed_arts +=1
            except:
                self.failed_arts +=1

def main(lims, args):
    process = Process(lims, id = args.pid)
    CUDFS= CopyUDFS(process)
    CUDFS.set_udfs()

    d = {'ca': CUDFS.passed_arts,
         'ia': CUDFS.failed_arts}

    abstract = ("Updated {ca} artifacts(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    if CUDFS.failed_arts:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
