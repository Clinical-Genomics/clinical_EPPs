#!/usr/bin/env python
from __future__ import division

import sys
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from clinical_EPPs.cg_api_client import CgAPIClient
from clinical_EPPs.config import CG_URL

DESC = """
"""


##--------------------------------------------------------------------------------
##--------------------------------LIMS EPP----------------------------------------
##--------------------------------------------------------------------------------


class SequencingQualityChecker:
    def __init__(self, process):
        self.process = process
        self.sample_artifacts = {}

        self.not_updated_artifacts = self.count_single_sample_artifacts()
        self.updated_artifacts = 0
        self.failed_artifacts = 0

        self.q30_threshold = process.udf.get("Threshold for % bases >= Q30")
        self.reads_threshold = 1000
        self.sequencing_metrics = []

        self.cg_api_client = CgAPIClient(base_url=CG_URL)

    def count_single_sample_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        return len(list(filter(lambda a: len(a.samples) == 1, all_artifacts)))


    def get_artifacts(self):
        """Preparing output artifact dict."""
        for input_output in self.process.input_output_maps:
            input_map = input_output[0]
            output_map = input_output[1]
            if output_map["output-generation-type"] == "PerReagentLabel":
                artifact = output_map["uri"]
                sample_name = artifact.samples[0].id
                lane = input_map["uri"].location[1][0]
                if not sample_name in self.sample_artifacts:
                    self.sample_artifacts[sample_name] = {lane: artifact}
                else:
                    self.sample_artifacts[sample_name][lane] = artifact

    def get_flow_cell_id(self):
        try:
            self.flowcellname = self.process.all_inputs()[0].container.name
        except:
            sys.exit("Could not get flow cell id from container.")

    def get_sequencing_metrics(self):
        """Get sequencing metrics from the cg api."""
        try:
            self.sequencing_metrics = self.cg_api_client.get_sequencing_metrics_for_flow_cell(self.flowcellname)
        
        except:
            sys.exit(f"Error getting sequencing metrics for flowcell: {self.flowcellname}")
    
    def is_valid_quality(self, q30_score : float, reads : int):
        return q30_score * 100 >= self.q30_threshold and reads >= self.reads_threshold

    def get_quality_control_flag(self, q30, reads):
        if self.is_valid_quality(q30, reads):
            return "PASSED"
        else:
            self.failed_artifacts += 1
            return "FAILED"

    def set_udfs(self):
        """Setting the demultiplex udfs"""

        for metrics in self.sequencing_metrics:
            sample_lims_id: str = metrics.sample_internal_id

            if sample_lims_id not in self.sample_artifacts:
                continue

            lane = str(metrics.flow_cell_lane_number)
            sample_artifact = self.sample_artifacts[sample_lims_id].get(lane)

            sample_artifact.udf["# Reads"] = metrics.sample_total_reads_in_lane
            sample_artifact.udf["% Bases >=Q30"] = metrics.sample_base_fraction_passing_q30

            qc_flag = self.get_quality_control_flag(metrics.sample_base_fraction_passing_q30, metrics.sample_total_reads_in_lane)
            sample_artifact.qc_flag = qc_flag
    
            sample_artifact.put()
            self.updated_artifacts += 1
            self.not_updated_artifacts -= 1


def main(lims, args):
    process = Process(lims, id=args.pid)
    if not "Threshold for % bases >= Q30" in process.udf:
        sys.exit("Threshold for % bases >= Q30 has not ben set.")

    quality_checker = SequencingQualityChecker(process)
    quality_checker.get_flow_cell_id()
    quality_checker.get_artifacts()
    quality_checker.get_sequencing_metrics()
    quality_checker.set_udfs()

    quality_summary: str = f"Updated {quality_checker.updated_artifacts} artifacts. Skipped {quality_checker.not_updated_artifacts} due to missing sequencing metrics. "

    if quality_checker.failed_artifacts:
        quality_summary = quality_summary + str(quality_checker.failed_artifacts) + " samples failed QC!"

    if quality_checker.failed_artifacts or quality_checker.not_updated_artifacts:
        sys.exit(quality_summary)
    else:
        print(quality_summary, file=sys.stderr)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("-p", dest="pid", help="Lims id for current Process")

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
