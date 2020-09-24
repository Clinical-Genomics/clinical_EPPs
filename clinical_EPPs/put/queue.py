from genologics.entities import Process, Artifact, Sample
from genologics.config import BASEURI
from genologics.lims import Lims

from clinical_EPPs.get.ids import unique_list_of_ids
import logging
import pathlib
from typing import List
LOG = logging.getLogger(__name__)

from clinical_EPPs.exceptions import QueueArtifactsError, MissingArtifactError




def queue_artifacts(lims: Lims, artifacts: List[Artifact], workflow_id: str, stage_id: str) -> None:
    """Queue artifacts to stage in workflow."""

    if not artifacts:
        LOG.warning("Failed trying to queue empty list of artifacts.")
        raise MissingArtifactError("No artifacts to queue.")
    stage_uri = (
        f"{BASEURI}/api/v2/configuration/workflows/{workflow_id}/stages/{stage_id}"
    )

    artifact_ids = unique_list_of_ids(artifacts)
    try:
        lims.route_artifacts(artifacts, stage_uri=stage_uri)
        LOG.info(f"Queueing artifacts to {stage_uri}.")
        LOG.info(
            f"The following artifacts have been queued: {' ,'.join(artifact_ids)}"
        )
    except:
        raise QueueArtifactsError("Failed to queue artifacts.")
