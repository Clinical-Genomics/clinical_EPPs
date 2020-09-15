#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process

import sys
import click


DESC = """Script for queuing artifacts."""


def get_artifacts(process, input_analyte):
    """"""

    if input_analyte:
        artifacts = process.all_inputs(unique=True)
    else:
        artifacts = [a for a in process.all_outputs(unique=True) if a.type=='Analyte']
    return artifacts


def queue_artifacts(lims, artifacts, workflow_id, stage_id):
    """"""

    #stage_uri = f'{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}'
    stage_uri = BASEURI+'/api/v2/configuration/workflows/'+workflow_id+'/stages/' + stage_id
    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
    except:
        raise QueueArtifactsError('Failed to queue artifacts.')
         
option_process = click.option('-p', '--process', required=True, help='Lims id for current Process')

@click.command()
@option_process
@click.option('-w', '--workflow', required=True, help='Destination workflow id.')
@click.option('-s', '--stage', required=True, help='Destination stage id.')
@click.option('-u', '--udf', required=True, help='UDF that will tell wich artifacts to move.')
@click.option('-i', '--input-analyte', default=False, is_flag=True,
                       help='Use this flag if you run the script from a QC step.')
def main(process, workflow, stage, udf, input_analyte):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id = process)
    artifacts = get_artifacts(process, input_analyte)

    try:
        queue_artifacts(lims, artifacts, workflow, stage)
    except Clinical_EPPsError as e:
        sys.exit(e.message)

if __name__ == "__main__":
    main()


