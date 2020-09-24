#!/usr/bin/env python

from clinical_EPPs.exceptions import (
    Clinical_EPPsError,
    QueueArtifactsError,
    MissingArtifactError,
    WhatToCallThisError
)
from clinical_EPPs.utils import (
    queue_artifacts,
    get_latest_artifact,
    get_sample_artifact,
    get_process_samples,
    get_lims_log_file
)
from clinical_EPPs import options
from genologics.lims import Lims
from genologics.entities import Process, Artifact, Sample

import logging
import sys
import click


def get_pools_and_samples_to_queue(
    lims: Lims, process_type: list(str), samples: list(Sample)
) -> list(Artifact):
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
    break_send_to_next_step = False
    send_to_next_step = []
    for sample in samples:
        cust = sample.udf.get("customer")
        if not cust:
            logging.warning(f"Sample {sample.id} has no customer.")
            continue
            break_send_to_next_step = True
        elif cust == "cust001":
            ## this is a RML - get pools from sort step
            try:
                artifact = get_latest_artifact(lims, sample.id, process_type)
            except MissingArtifactError as e:
                logging.warning(e.message)
                break_send_to_next_step = True
                continue
        else:
            ## this is a pool (or a sample) and we want to pass its samples to next step
            artifact = get_sample_artifact(lims, sample)
        send_to_next_step.append(artifact)
    if break_send_to_next_step:
        raise WhatToCallThisError('Issues getting pools and or samples to queue. See log')
    return set(send_to_next_step)


@click.command()
@options.workflow_id("Destination workflow id.")
@options.stage_id("Destination stage id.")
@options.process_type(
    "The name(s) of the process type(s) from where we want to fetch the pools"
)

@click.pass_context
def place_samples_in_seq_agg(ctx, workflow_id, stage_id, process_type):
    """Queueing artifacts with given udf==True, to stage in workflow.
    Raising error if quiueing fails."""
    
    process = ctx.obj['process']
    lims = ctx.obj['lims']

    samples = get_process_samples(process)

    try:
        artifacts = get_pools_and_samples_to_queue(lims, process_type, samples)
        queue_artifacts(lims, artifacts, workflow_id, stage_id)
        print("Artifacts have been queued.", file=sys.stdout)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()