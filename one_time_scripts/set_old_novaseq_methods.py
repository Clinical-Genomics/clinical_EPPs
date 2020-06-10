#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from datetime import datetime

import logging
import sys

DESC = """
One time script to set historical methods on nova seq runs. 

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

def set_prep_dates(lims):
    process_types = ['Define Run Format and Calculate Volumes (Nova Seq)']
    steps = lims.get_processes(type=process_types)
    print(len(steps))
    for i, step in enumerate(steps):
        if not step.date_run:
            continue
        after = datetime.strptime('2019-03-25', '%Y-%m-%d').date()
        before = datetime.strptime('2020-03-10', '%Y-%m-%d').date()
        step_date = datetime.strptime(step.date_run, '%Y-%m-%d').date()
        if after <= step_date <= before:
            print(i)
            step.udf['Method'] = '1830'
            step.udf['Version'] =  4
            step.put() 
            print('set methond on step', step.id) 
def main(lims):
    set_prep_dates(lims)

if __name__ == "__main__":
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims)
