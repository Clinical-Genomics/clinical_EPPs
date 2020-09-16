#!/usr/bin/env python

from clinical_EPPs.exceptions import (
    Clinical_EPPsError,
    QueueArtifactsError,
    DuplicateSampleError,
)
from clinical_EPPs.utils import (
    get_artifacts,
    filter_artifacts,
    queue_artifacts,
    get_latest_artifact,
)

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Stage

import sys
import click


def get_artifacts_to_requeue(lims, rerun_arts, step_name):
    """Get input artifacts to define step"""

    artifacts_to_requeue = []

    for art in rerun_arts:
        representative_sample = art.samples[0]
        rerun_step_in_arts = lims.get_artifacts(
            samplelimsid=representative_sample.id,
            type="Analyte",
            process_type=[step_name],
        )
        if not rerun_step_in_arts:
            sys.exit(f'could not find artifact to requeue for {art.id}')
        requeue_art = get_latest_artifact(rerun_step_in_arts)

        artifacts_to_requeue.append(requeue_art)

    return set(artifacts_to_requeue)


def check_same_sample_in_many_rerun_pools(rerun_arts):

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


option_process = click.option(
    "-p", "--process", required=True, help="Lims id for current Process"
)


@click.command()
@option_process
@click.option("-w", "--workflow", required=True, help="Destination workflow id.")
@click.option("-s", "--stage", required=True, help="Destination stage id.")
@click.option(
    "-n", "--step-name", required=True, help="Name of the step before the rerun step."
)
@click.option(
    "-u", "--udf", required=True, help="UDF that will tell wich artifacts to rerun."
)
def main(process, workflow, stage, udf, step_name):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=process)
    artifacts = get_artifacts(process, False)
    rerun_arts = filter_artifacts(artifacts, udf, True)
    if rerun_arts:
        artifacts_to_requeue = get_artifacts_to_requeue(lims, rerun_arts, step_name)
        check_same_sample_in_many_rerun_pools(artifacts_to_requeue)

        try:
            queue_artifacts(lims, artifacts_to_requeue, workflow, stage)
        except Clinical_EPPsError as e:
            sys.exit(e.message)


if __name__ == "__main__":
    main()
