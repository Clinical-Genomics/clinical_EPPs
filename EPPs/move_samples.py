#!/usr/bin/env python
# -*- coding: utf-8 -*-
from argparse import ArgumentParser
from clinical_EPPs.exceptions import QueueArtifactsError

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
import sys

DESC = """Script for queuing artifacts."""



def get_artifacts(process, input_analyte):
    """"""

    if input_analyte:
        artifacts = process.all_inputs(unique=True)
    else:
        artifacts = [a for a in process.all_outputs(unique=True) if a.type=='Analyte']
    return artifacts


def queue_artifacts(artifacts, workflow_id, stage_id):
    """"""

    stage_uri = f'{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}'

    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
    except:
        raise QueueArtifactsError('Failed to queue artifacts.')
         
  
def main(lims, args):
    process = Process(lims, id = args.process)
    artifacts = get_artifacts(process, args.input_analyte)

    try:
        queue_artifacts(artifacts, args.workflow, args.stage)
    except NIPToolError as e:
        sys.exit(e.message)
        #raise click.Abort()

if __name__ == "__main__":
    ## change to click
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest='process', 
                        help='Lims id for current Process')
    parser.add_argument('-w', dest='workflow',
                        help='Destination workflow id.')
    parser.add_argument('-s', dest='stage',
                        help='Destination stage id.')
    parser.add_argument('-u', dest='udf',
                        help='UDF that will tell wich artifacts to move.')
    parser.add_argument('-i', dest='input_analyte', action='store_true',
                        help='Use this tag if you run the script from a QC step.')
    
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    main(lims, args)


