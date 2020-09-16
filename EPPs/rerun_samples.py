#!/usr/bin/env python

from clinical_EPPs.exceptions import (
    Clinical_EPPsError,
    DuplicateSampleError,
)
from clinical_EPPs.utils import (
    get_artifacts,
    filter_artifacts,
    queue_artifacts,
    get_latest_artifact,
)
from clinical_EPPs.options import *


from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Stage

import sys
import click


def get_artifacts_to_requeue(lims: Lims, rerun_arts: list, process_type: list)-> list:
    """Get input artifacts to define step (output artifacts of sort step)
    Args:
        lims: Lims
        rerun_arts: List # Artifacts with Rerun flag
        process_type: List[str] # Name of step(s) before the requeue step
    """

    artifacts_to_requeue = []

    for art in rerun_arts:
        representative_sample_id = art.samples[0].id
        requeue_art = get_latest_artifact(lims, representative_sample_id, "Analyte", process_type)
        artifacts_to_requeue.append(requeue_art)
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
@OPTION_PROCESS
@OPTION_WORKFLOW_ID
@OPTION_STAGE_ID
@OPTION_PROCESS_TYPE
@OPTION_UDF
def main(process, workflow, stage, udf, process_type):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=process)
    artifacts = get_artifacts(process, False)
    rerun_arts = filter_artifacts(artifacts, udf, True)
    if rerun_arts:
        artifacts_to_requeue = get_artifacts_to_requeue(lims, rerun_arts, process_type)
        check_same_sample_in_many_rerun_pools(artifacts_to_requeue)
        try:
            queue_artifacts(lims, artifacts_to_requeue, workflow, stage)
            print('Artifacts have been queued.', file=sys.stdout)
        except Clinical_EPPsError as e:
            sys.exit(e.message)


if __name__ == "__main__":
    main()
