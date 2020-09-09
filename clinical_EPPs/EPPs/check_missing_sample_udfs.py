#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys

DESC = """EPP script to check missing reads and dates on all samples

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

def check_udfs_on_samples(process):
    """Checks udfs on sample level and exits if udf is misisng"""
    
    for art in process.all_inputs():
        sample = art.samples[0]
        if not sample.udf.get('Reads missing (M)'):
            sys.exit('Reads missing (M) must be set on all samples')
        if not sample.udf.get('Received at'):
            sys.exit('Recieved date must be set on all samples')

def main(lims, args):
    process = Process(lims, id = args.p)
    check_udfs_on_samples(process)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', help='Lims id for current Process')

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
