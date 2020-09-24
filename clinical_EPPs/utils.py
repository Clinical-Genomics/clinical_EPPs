from genologics.entities import Process, Artifact, Sample
from genologics.config import BASEURI
from genologics.lims import Lims

from operator import attrgetter
import sys
import logging
import pathlib

from clinical_EPPs.exceptions import QueueArtifactsError, MissingArtifactError


def get_process_samples(process: Process) -> list(Sample):
    """Get all samples in a process"""

    all_samples = []
    for art in process.all_inputs():
        all_samples += art.samples

    return set(all_samples)


def get_sample_artifact(lims: Lims, sample: Sample) -> Artifact:
    """Returning the initial artifact related to a sample.
    Assuming first artifact is allways named sample.id + 'PA1."""

    return Artifact(lims, id=f"{sample.id}PA1")


def get_artifacts(process: Process, inputs: bool) -> list(Artifact):
    """If inputs is True, returning all input analytes of the process,
    otherwise returning all output analytes of the process"""

    if inputs:
        artifacts = process.all_inputs(unique=True)
    else:
        artifacts = [a for a in process.all_outputs(unique=True) if a.type == "Analyte"]
    return artifacts


def filter_artifacts(artifacts: list(Artifact), udf: str, value) -> list(Artifact):
    """Returning a list of only artifacts with udf==value"""

    return [a for a in artifacts if a.udf.get(udf) == value]


def unique_list_of_ids(entity_list: list) -> list(str):
    """Arg: entity_list: list of any type of genologics entity.
    Retruning unique list of entity ids."""

    return set([e.id for e in entity_list])


def queue_artifacts(lims: Lims, artifacts: list(Artifact), workflow_id: str, stage_id: str) -> None:
    """Queue artifacts to stage in workflow."""

    if not artifacts:
        logging.warning("Failed trying to queue empty list of artifacts.")
        raise MissingArtifactError("No artifacts to queue.")
    stage_uri = (
        f"{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}"
    )

    artifact_ids = unique_list_of_ids(artifacts)
    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
        logging.info(f"Queueing artifacts to {stage_uri}.")
        logging.info(
            f"The following artifacts have been queued: {' ,'.join(artifact_ids)}"
        )
    except:
        raise QueueArtifactsError("Failed to queue artifacts.")


def get_latest_artifact(lims: Lims, sample_id: str, process_type: list(str)) -> Artifact:
    """Getting the most recently generated artifact by process_type and sample_id.

    Searching for all artifacts (Analytes) associated with <sample_id> that
    were produced by <process_type>. 
    
    Returning the artifact with latest parent_process.date_run. 
    If there are many such artifacts only one will be returned."""

    artifacts = lims.get_artifacts(
        samplelimsid=sample_id,
        type="Analyte",
        process_type=process_type,
    )
    if not artifacts:
        raise MissingArtifactError(
            message=f"Could not find a artifact with sample: {sample_id} generated by process: {' ,'.join(process_type)}"
        )
    sorted(artifacts, key=attrgetter("parent_process.date_run"))

    return artifacts[-1]


def get_lims_log_file(lims: Lims, file_id: str) -> pathlib.Path:
    """Searching for a log Artifact with file_id. 
    
    If the artifact is found, returning the path to the attached file. 
    Otherwise returning the file_id."""

    log_artifact = Artifact(lims, id=file_id)

    try:
        files = log_artifact.files
    except:
        files = None

    if files:
        something = BASEURI.split(":")[1]
        file_path = files[0].content_location.split(something)[1]
    else:
        file_path = file_id

    return pathlib.Path(file_path)
