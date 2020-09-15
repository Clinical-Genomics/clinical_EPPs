#!/usr/bin/env python

from clinical_EPPs.exceptions import Clinical_EPPsError, QueueArtifactsError

from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process

import sys
import click


def get_input_artifacts(process, lims):
    """Get input artifacts to sequence agregatipon step"""

    input_artifacts = []
    for inp, outp in process.input_output_maps:
        if outp.get("output-generation-type") == "PerAllInputs":
            continue
        out_art = Artifact(lims, id=outp["limsid"])
        if out_art.udf.get(udf) != True:
            continue
        input_artifacts.append(inp)
    return input_artifacts


def get_artifacts_to_requeue(output_artifacts):
    """Get input artifacts to define step"""

    artifacts_to_requeue = []
    for art in output_artifacts:
        process_id = output_artifacts["parent-process"]
        artifact_id = output_artifacts["limsid"]
        process = Process(lims, id=process_id)
        for inp, out in process.input_output_maps:
            if outp["limsid"] == artifact_id:
                artifact_to_requeue = Artifact(lims, id=inp["limsid"])
                artifacts_to_requeue.appned(artifact_to_requeue)
    return artifacts_to_requeue


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
    "-u", "--udf", required=True, help="UDF that will tell wich artifacts to move."
)
def main(process, workflow, stage, udf):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    process = Process(lims, id=process)
    artifacts = get_input_artifacts(process, lims)
    artifacts_to_requeue = get_artifacts_to_requeue(artifacts)
    check_same_sample_in_many_rerun_pools(artifacts_to_requeue)

    try:
        queue_artifacts(lims, artifacts_to_requeue, workflow, stage)
    except Clinical_EPPsError as e:
        sys.exit(e.message)


if __name__ == "__main__":
    main()
