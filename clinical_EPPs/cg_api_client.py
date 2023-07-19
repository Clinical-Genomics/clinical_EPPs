import json
from typing import Dict, List
import requests

from clinical_EPPs.models import SequencingMetrics


class CgApiClient:
    def __init__(self, base_url):
        self.base_url = base_url

    def apptag(self, tag_name, key=None, entry_point="/applications"):
        res = requests.get(self.base_url + entry_point + "/" + tag_name)

        if key:
            return json.loads(res.text)[key]
        else:
            return json.loads(res.text)

    def get_sequencing_metrics_for_flow_cell(
        self, flow_cell_id: str
    ) -> List[SequencingMetrics]:
        metrics_endpoint: str = f"/flowcells/{flow_cell_id}/sequencing_metrics"
        try:
            response = requests.get(self.base_url + metrics_endpoint)
            response.raise_for_status()
            metrics_data: Dict = response.json()
            return [SequencingMetrics.parse_obj(metric) for metric in metrics_data]

        except requests.RequestException as e:
            raise Exception(f"Failed to get metrics for flowcell {flow_cell_id}, {e}")
