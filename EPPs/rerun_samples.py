#!/usr/bin/env python

from clinical_EPPs.exceptions import (
    Clinical_EPPsError,
    DuplicateSampleError,
    MissingArtifactError,
    WhatToCallThisError
)
from clinical_EPPs.utils import (
    get_artifacts,
    filter_artifacts,
    queue_artifacts,
    get_latest_artifact,
    get_lims_log_file
)
from clinical_EPPs import options


from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Stage

import pathlib
import logging
import sys
import click


def get_artifacts_to_requeue(lims: Lims, rerun_arts: list, process_type: list) -> list:
    """Get input artifacts to define step (output artifacts of sort step)
    Args:
        lims: Lims
        rerun_arts: List # Artifacts with Rerun flag
        process_type: List[str] # Name of step(s) before the requeue step
    """

    artifacts_to_requeue = []
    break_rerun = False
    for art in rerun_arts:
        representative_sample_id = art.samples[0].id ## hantera med if samples..
        try:
            requeue_art = get_latest_artifact(
            lims, representative_sample_id, process_type
        )
        except MissingArtifactError as e:
            logging.warning(e.message)
            break_rerun = True
            continue
        artifacts_to_requeue.append(requeue_art)
    if break_rerun:
        raise WhatToCallThisError('Issues finding artifacts to requeue. See log')
    return set(artifacts_to_requeue)


def check_same_sample_in_many_rerun_pools(rerun_arts: list):
    """Check that the same sample does not occure in more than one of the pools to rerun."""

    all_samples = []

    for art in rerun_arts:
        all_samples += art.samples
    for s in set(all_samples):
        all_samples.remove(s)
    duplicate_samples = list(set(all_samples))
    if duplicate_samples:
        raise DuplicateSampleError(
            f"Waring same sample in many pools: {' ,'.join(duplicate_samples)}"
        )


@click.command()
@options.log()
@options.process()
@options.workflow_id("Destination workflow id.")
@options.stage_id("Destination stage id.")
@options.process_type(
    "The name(s) of the process type(s) before the requeue step. Fetching artifact to requeue from here."
)
@options.udf("UDF that will tell wich artifacts to move.")
def main(process, workflow_id, stage_id, udf, process_type, log):

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    log_path = pathlib.Path(log)
    if not log_path.is_file():
       log_path = get_lims_log_file(lims, log)
    logging.basicConfig(filename = str(log_path.absolute()), filemode='a', level=logging.INFO)
    process = Process(lims, id=process)

    artifacts = get_artifacts(process, False)
    rerun_arts = filter_artifacts(artifacts, udf, True)
    if rerun_arts:
        try:
            artifacts_to_requeue = get_artifacts_to_requeue(lims, rerun_arts, process_type)
            check_same_sample_in_many_rerun_pools(artifacts_to_requeue)
            queue_artifacts(lims, artifacts_to_requeue, workflow_id, stage_id)
            print("Artifacts have been queued.", file=sys.stdout)
        except Clinical_EPPsError as e:
            sys.exit(e.message)


if __name__ == "__main__":
    main()
