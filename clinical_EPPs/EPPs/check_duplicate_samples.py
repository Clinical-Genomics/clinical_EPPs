#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import logging
import sys

DESC = """EPP script to check for duplicate samples in a step.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

def get_duplicate_samples(analytes):
    all_samples = []
    duplicated_samples = []
    for art in analytes:
        for sample in art.samples:
            if sample.id in all_samples:
                duplicated_samples.append(sample.id)
            all_samples.append(sample.id)
    return set(duplicated_samples)

def main(lims, args):
    process = Process(lims, id = args.p)
    duplicates = get_duplicate_samples(process.all_inputs())

    if duplicates:
        sys.exit('Samples: ' +', '.join(duplicates)+ ' appeared more than once in this step.')
    else:
        print('No duplicated samples!', file=sys.stderr) 

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p',
                        help='Lims id for current Process')

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
