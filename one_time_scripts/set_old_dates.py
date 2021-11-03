#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from datetime import datetime

import logging
import sys

DESC = """
One time script to set historical dates on samples. 

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


def set_prep_dates(lims):
    logging.basicConfig(filename="prepp.log", level=logging.INFO)
    logger = logging.getLogger(__name__)
    process_types = [
        "CG002 - Aggregate QC (Library Validation) (Dev)",
        "Aggregate QC (Library Validation) (Dev) v2",
        "Aggregate QC (Library Validation) (Dev) v3",
        "CG002 - Aggregate QC (Library Validation)",
        "Aggregate QC (Library Validation) TWIST v1",
        "Aggregate QC (Library Validation) TWIST v2",
        "Aggregate QC (Library Validation) (RNA) v1",
        "Aggregate QC (Library Validation) (RNA) v2",
        "Aggregate QC (Library Validation)",
        "Aggregate QC (Library Validation) (Cov) v1",
    ]
    steps = lims.get_processes(type=process_types)
    logger.info(str(len(steps)))
    print(len(steps))
    for i, step in enumerate(steps):
        if not step.date_run:
            continue
        print(i)
        date = datetime.strptime(step.date_run, "%Y-%m-%d").date()
        for art in step.all_inputs():
            for samp in art.samples:
                old_date = samp.udf.get("Library Prep Finished")
                # print(old_date, date)
                if old_date and old_date >= date:
                    # print("skipping")
                    continue
                try:
                    logger.info(f"uppdating {samp.id}")
                    logger.info(f"{old_date} {date}")
                    print(f"updating {samp.id}")
                    samp.udf["Library Prep Finished"] = date
                    samp.put()
                except:
                    pass


def set_seq_dates(lims):
    logging.basicConfig(filename="seq.log", level=logging.INFO)
    logger = logging.getLogger(__name__)
    process_types = ["CG002 - Sequence Aggregation"]
    steps = lims.get_processes(type=process_types)
    logger.info(str(len(steps)))
    print(len(steps))
    for i, step in enumerate(steps):
        if not step.date_run:
            continue
        print(i)
        date = datetime.strptime(step.date_run, "%Y-%m-%d").date()
        for art in step.all_inputs():
            for samp in art.samples:
                if not samp.udf.get("Passed Sequencing QC"):
                    continue
                old_date = samp.udf.get("Sequencing Finished")
                # print(old_date, date)
                if old_date and old_date >= date:
                    # print("skipping")
                    continue
                try:
                    logger.info(f"uppdating {samp.id}")
                    logger.info(f"{old_date} {date}")
                    print(f"updating {samp.id}")
                    samp.udf["Sequencing Finished"] = date
                    samp.put()
                except:
                    logger.error(f"failed sample {samp.id}")


def set_rec_dates(lims):
    process_types = [
        "CG002 - Reception Control (Dev)",
        "CG002 - Reception Control",
        "Reception Control TWIST v1",
        "Reception Control no placement v1",
        "Reception Control (RNA) v1",
    ]
    steps = lims.get_processes(type=process_types)
    print(len(steps))
    for i, step in enumerate(steps):
        if not step.date_run:
            continue
        print(i)
        date = step.udf.get("date arrived at clinical genomics")
        if not date:
            date = datetime.strptime(step.date_run, "%Y-%m-%d").date()
        for art in step.all_inputs():
            for samp in art.samples:
                old_date = samp.udf.get("Received at")
                print(old_date, date)
                if old_date and old_date >= date:
                    print("skipping")
                    continue
                samp.udf["Received at"] = date
                samp.put()


def set_deliv_dates(lims):
    logging.basicConfig(filename="del.log", level=logging.INFO)
    logger = logging.getLogger(__name__)
    process_types = ["CG002 - Delivery", "Delivery v1"]

    steps = lims.get_processes(type=process_types)
    logger.info(str(len(steps)))
    print(len(steps))
    for i, step in enumerate(steps):
        if not step.date_run:
            continue
        print(i)

        date = datetime.strptime(step.date_run, "%Y-%m-%d").date()
        for art in step.all_inputs():
            for samp in art.samples:
                old_date = samp.udf.get("Delivered at")
                # print(old_date, date)
                if old_date and old_date >= date:
                    # print("skipping")
                    continue
                try:
                    logger.info(f"uppdating {samp.id}")
                    logger.info(f"{old_date} {date}")
                    print(f"updating {samp.id}")
                    samp.udf["Delivered at"] = date
                    samp.put()
                except:
                    logger.error(f"failed sample {samp.id}")


def main(lims, args):
    if args.prep:
        set_prep_dates(lims)
    if args.seq:
        set_seq_dates(lims)
    if args.rec:
        set_rec_dates(lims)
    if args.deliv:
        set_deliv_dates(lims)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument(
        "-p",
        dest="prep",
        action="store_true",
        default=False,
        help="Set prepared date. (Last prep step if prep qc ok)",
    )
    parser.add_argument(
        "-s",
        dest="seq",
        action="store_true",
        default=False,
        help="Set sequencing date. (Last seq step if seq qc ok)",
    )
    parser.add_argument(
        "-r",
        dest="rec",
        action="store_true",
        default=False,
        help="Set received date. (First reception comtrol step)",
    )
    parser.add_argument(
        "-d",
        dest="deliv",
        action="store_true",
        default=False,
        help="Set delivered date. (Last delivery step)",
    )

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)
