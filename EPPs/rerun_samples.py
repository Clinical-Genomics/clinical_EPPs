#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError, DuplicateSampleError

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process, Stage

import sys
import click


def get_rerun_artifacts(process, udf):
    """Get artifacts to rerun"""

    rerun_arts = []
    for art in process.all_outputs(unique=True):
        if art.type != "Analyte":
            continue
        if art.udf.get(udf) != True:
            continue
        rerun_arts.append(art)
    return rerun_arts


def get_latest_artifact(artifacts):
    """Get artifact with oldest parent_process.date_run"""

    latest = artifacts[0]
    for artifact in artifacts:
        if artifact.parent_process.date_run > latest.parent_process.date_run:
            latest = artifact
    return latest


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
        rerun_art = get_latest_artifact(rerun_step_in_arts)
        artifacts_to_requeue.append(rerun_art)

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


def queue_artifacts(lims, artifacts, workflow_id, stage_id):
    """Queue artifacts to stage in workflow"""
    stage_uri = (
        f"{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}"
    )
    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
    except:
        raise QueueArtifactsError("Failed to queue artifacts.")


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
    rerun_arts = get_rerun_artifacts(process, udf)
    if rerun_arts:
        artifacts_to_requeue = get_artifacts_to_requeue(lims, rerun_arts, step_name)
        check_same_sample_in_many_rerun_pools(artifacts_to_requeue)

        try:
            queue_artifacts(lims, artifacts_to_requeue, workflow, stage)
        except Clinical_EPPsError as e:
            sys.exit(e.message)


if __name__ == "__main__":
    main()
