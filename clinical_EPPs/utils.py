from genologics.entities import Process, Artifact
from genologics.config import BASEURI
from genologics.lims import Lims

from operator import attrgetter
import sys

from clinical_EPPs.exceptions import QueueArtifactsError


def get_process_samples(process):
    """Get all samples in a process"""

    all_samples = []
    for art in process.all_inputs():
        all_samples += art.samples

    return set(all_samples)


def get_sample_artifact(lims, sample):
    """Returning the initial artifact related to a sample.
    Assuming first artifact is allways named sample.id + 'PA1."""

    return Artifact(lims, id=sample.id + "PA1")


def get_artifacts(process: Process, inputs: bool) -> list:
    """If inputs is True, return all input analytes of the process,
    otherwise return all output analytes of the process"""

    if inputs:
        artifacts = process.all_inputs(unique=True)
    else:
        artifacts = [a for a in process.all_outputs(unique=True) if a.type == "Analyte"]
    return artifacts


def filter_artifacts(artifacts: list, udf: str, value) -> list:
    """return a list of only artifacts with udf==value"""

    return [a for a in artifacts if a.udf.get(udf) == value]


def queue_artifacts(lims: Lims, artifacts: list, workflow_id: str, stage_id: str):
    """Queue artifacts to stage in workflow"""

    stage_uri = (
        f"{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}"
    )

    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
    except:
        raise QueueArtifactsError("Failed to queue artifacts.")


def get_latest_artifact(
    lims: Lims, sample_id: str, artifact_type: str, process_type: list
) -> Artifact:
    """Searching for all artifacts associated with sample_id that were produced by
    process_type and that are of type artifact_type. Returning the artifact with
    latest parent_process.date_run. If there are many such artifacts only one will
    be returned."""

    artifacts = lims.get_artifacts(
        samplelimsid=sample_id,
        type=artifact_type,
        process_type=process_type,
    )

    if not artifacts:
        sys.exit(f"Could not find artifacts")
    sorted(artifacts, key=attrgetter("parent_process.date_run"))

    return artifacts[-1]
