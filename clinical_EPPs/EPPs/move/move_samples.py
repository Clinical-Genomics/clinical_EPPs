#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError
from clinical_EPPs.get.artifacts import get_artifacts, filter_artifacts
from clinical_EPPs.put.queue import queue_artifacts
from clinical_EPPs import options
from genologics.lims import Lims
from genologics.entities import Process

import logging
import sys
import click


@click.command()
@options.workflow_id("Destination workflow id.")
@options.stage_id("Destination stage id.")
@options.udf("UDF that will tell wich artifacts to move.")
@options.input_artifacts(
    "Use this flag if you want to queue the input artifacts of the current process. Default is to queue the output artifacts (analytes) of the process."
)

@click.pass_context
def move_samples(ctx, workflow_id, stage_id, udf, input_artifacts):
    """Script to move aritfats to another stage.
    
    Queueing artifacts with <udf==True>, to stage with <stage-id>
    in workflow with <workflow-id>. Raising error if quiueing fails."""

    process = ctx.obj['process']
    lims = ctx.obj['lims']

    artifacts = get_artifacts(process, input_artifacts)
    filtered_artifacts = filter_artifacts(artifacts, udf, True)

    try:
        queue_artifacts(lims, filtered_artifacts, workflow_id, stage_id)
        click.echo("Artifacts have been queued.")
    except Clinical_EPPsError as e:
        sys.exit(e.message)
