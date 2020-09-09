#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
import sys
from datetime import datetime as dt

DESC = """Script to set dates on sample from process

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class SampleDatesSetter():

    def __init__(self, process, pudf, sudf):
        self.process = process
        self.sudf = sudf
        self.date = self._get_date(pudf)
        self.samples = []


    def _get_date(self, pudf):
        """Get date from process udf. If no pudf return todays date."""

        if pudf:
            date = self.process.udf.get(pudf)
        else:
            date = dt.today().date()
        if not date:
            sys.exit(pudf + ' is not set.')
        return date


    def get_samples(self, artifacts, check_qc=False):
        """Get samples. If check_qc, ignore failed samples."""

        for art in artifacts: 
            if check_qc and art.qc_flag=='FAILED':
                continue
            self.samples += art.samples
        self.samples = set(self.samples)


    def set_date(self):
        """Set the date on sample level."""

        for sample in self.samples:
            sample.udf[self.sudf] = self.date
            sample.put()


def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id = args.pid)
    SDS = SampleDatesSetter(process, args.pudf, args.sudf)

    if args.sequencing_date:
        artifacts = [a for a in process.all_outputs() if a.type=='Analyte']
        SDS.get_samples(artifacts, check_qc=True)
    else:
        artifacts = process.all_inputs()
        SDS.get_samples(artifacts)

    SDS.set_date()


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process.')
    parser.add_argument('--sudf',
                        help='UDF on sample to set.')
    parser.add_argument('--pudf',
                        help='UDF on process to fetch. If None, todays date will be used.')
    parser.add_argument('--sequencing_date', action='store_true',
                        help='Special conditions when setting the sequencing date.')
    args = parser.parse_args()
    main(args)
