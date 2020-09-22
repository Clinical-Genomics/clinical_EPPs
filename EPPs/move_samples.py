#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError
from clinical_EPPs.utils import get_artifacts, filter_artifacts, queue_artifacts, cg_epp_logger
from clinical_EPPs import options
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process

import logging
import sys
import click


@click.command()
@options.log()
@options.process()
@options.workflow_id("Destination workflow id.")
@options.stage_id("Destination stage id.")
@options.udf("UDF that will tell wich artifacts to move.")
@options.input_artifacts(
    "Use this flag if you want to queue the input artifacts of the current process. Default is to queue the output artifacts (analytes) of the process."
)
def main(process, workflow_id, stage_id, udf, input_artifacts, log):
    """Queueing artifacts with <udf==True>, to stage with <stage-id>
    in workflow with <workflow-id>. Raising error if quiueing fails."""
    
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    cg_epp_logger(log)
    process = Process(lims, id=process)
    artifacts = get_artifacts(process, input_artifacts)
    filtered_artifacts = filter_artifacts(artifacts, udf, True)

    try:
        queue_artifacts(lims, artifacts, workflow_id, stage_id)
        print("Artifacts have been queued.", file=sys.stdout)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()
