#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError
from clinical_EPPs.utils import (
    get_artifacts,
    filter_artifacts,
    queue_artifacts,
    get_latest_artifact,
)
from clinical_EPPs.options import *
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Artifact

import sys
import click


def get_samples_process(process):

    all_samples = []
    for art in process.all_inputs():
        all_samples += art.samples

    return set(all_samples)


def get_pool_from_sort(lims, process_types, sample):
    all_arts_in_sort = lims.get_artifacts(
        samplelimsid=sample.id, process_type=process_types, type="Analyte"
    )
    pool = get_latest_artifact(all_arts_in_sort)
    return pool


def get_individual_artifact(lims, sample):
    ## Assuming first artifact is allways named sample.id + 'PA1.
    return Artifact(lims, id=sample.id + "PA1")


def get_artifacts(lims, process_types, samples):
    missing_cust = []
    send_to_next_step = []
    for sample in samples:
        cust = sample.udf.get("customer")
        if not cust:
            missing_cust.append(sample.id)
            continue
        elif cust == "cust001":
            ## this is a RML - get pools from sort step
            artifact = get_pool_from_sort(lims, process_types, sample)
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
    samples = get_samples_process(process)
    artifacts = get_artifacts(lims, step_name, samples)
    try:
        queue_artifacts(lims, artifacts, workflow, stage)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()
