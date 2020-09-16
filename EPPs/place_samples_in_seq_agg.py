#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError
from clinical_EPPs.utils import (
    get_artifacts,
    filter_artifacts,
    queue_artifacts,
    get_latest_artifact,
    get_process_samples,
    get_sample_artifact,
)
from clinical_EPPs.options import *
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Artifact

import sys
import click


def get_artifacts(lims: Lims, process_type: list, samples: list)-> list:
    """Get samples and pools to place in sequence aggregation. 
    Sort of specific script:
    Single arts                                       --> Next Step
    Cust001 - Pools --> split to pools from sort step --> Next Step
    Non RML - Pools --> split in uniq sample arts     --> Next Step

    Args:
        lims: Lims
        rerun_arts: List # Artifacts with Rerun flag
        process_type: List[str] # Name of step(s) before the requeue step
    """

    missing_cust = []
    send_to_next_step = []
    for sample in samples:
        cust = sample.udf.get("customer")
        if not cust:
            missing_cust.append(sample.id)
            continue
        elif cust == "cust001":
            ## this is a RML - get pools from sort step
            artifact = get_latest_artifact(lims, sample.id, "Analyte", process_type)
        else:
            ## this is a pool (or a sample) and we want to pass its samples to next step
            artifact = get_individual_artifact(lims, sample)
        send_to_next_step.append(artifact)
    if missing_cust:
        sys.exit(
            "Could not queue samples to sequence aggregation because the following samples are missing customer udfs: "
            + ", ".join(missing_cust)
        )

    return set(send_to_next_step)


@click.command()
@OPTION_PROCESS
@OPTION_WORKFLOW_ID
@OPTION_STAGE_ID
@OPTION_STEP_NAME
def main(process, workflow, stage, step_name):

    """Queueing artifacts with given udf==True, to stage in workflow.
    Raising error if quiueing fails."""

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=process)
    samples = get_process_samples(process)
    artifacts = get_artifacts(lims, step_name, samples)
    try:
        queue_artifacts(lims, artifacts, workflow, stage)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()
