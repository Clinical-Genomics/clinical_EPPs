#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError
from clinical_EPPs.utils import get_artifacts, filter_artifacts, queue_artifacts
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process

import sys
import click

option_process = click.option(
    "-p", "--process", required=True, help="Lims id for current Process"
)


@click.command()
@option_process
@click.option("-w", "--workflow", required=True, help="Destination workflow id.")
@click.option("-s", "--stage", required=True, help="Destination stage id.")
@click.option(
    "-u", "--udf", required=True, help="UDF that will tell wich artifacts to move."
)
@click.option(
    "-i",
    "--inputs",
    default=False,
    is_flag=True,
    help="Use this flag if you run the script from a QC step.",
)
def main(process, workflow, stage, udf, inputs):
    """Queueing artifacts with given udf==True, to stage in workflow.
    Raising error if quiueing fails."""

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=process)
    artifacts = get_artifacts(process, inputs)
    filtered_artifacts = filter_artifacts(artifacts, udf, True)

    try:
        queue_artifacts(lims, artifacts, workflow, stage)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()
