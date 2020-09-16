from genologics.entities import Process, Artifact
from genologics.lims import Lims



def get_artifacts(process: Process, inputs: bool) --> list:
    """If inputs is True, return all input analytes of the process,
    otherwise return all output analytes of the process"""

    if inputs:
        artifacts = process.all_inputs(unique=True)
    else:
        artifacts = [a for a in process.all_outputs(unique=True) if a.type == "Analyte"]
    return artifacts


def filter_artifacts(artifacts: list, udf: str, value) --> list:
    """return a list of only artifacts with udf==value"""

    filtered_artifacts = [a for a in artifacts if a.udf.get(udf)==value]
    return filtered_artifacts


def queue_artifacts(lims: Lims, artifacts: list, workflow_id: str, stage_id: str):
    """Queue artifacts to stage in workflow"""

    stage_uri = (
        f"{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}"
    )

    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
    except:
        raise QueueArtifactsError("Failed to queue artifacts.")


def get_latest_artifact(artifacts: list) --> Artifact:
    """Get artifact with oldest parent_process.date_run"""

    latest = artifacts[0]
    for artifact in artifacts:
        if artifact.parent_process.date_run > latest.parent_process.date_run:
            latest = artifact
    return latest


