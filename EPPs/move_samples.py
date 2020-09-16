#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError
from clinical_EPPs.utils import get_artifacts, filter_artifacts, queue_artifacts
from clinical_EPPs.options import *
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process

import sys
import click


@click.command()
@OPTION_PROCESS
@OPTION_WORKFLOW_ID
@OPTION_STAGE_ID
@OPTION_UDF
@OPTION_INPUT_OUTPUT
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
