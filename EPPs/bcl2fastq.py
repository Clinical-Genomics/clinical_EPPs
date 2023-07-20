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


class BCLconv:
    def __init__(self, process):
        self.process = process
        self.artifacts = {}

        self.not_updated_artifacts = self.get_number_of_artifacts_with_one_sample()
        self.updated_artifacts = 0
        self.failed_artifacts = 0

        self.q30treshhold = process.udf.get("Threshold for % bases >= Q30")
        self.reads_treshold = 1000
        self.sequencing_metrics = []

        self.cg_api_client = CgAPIClient(base_url=CG_URL)

    def get_number_of_artifacts_with_one_sample(self):
        all_artifacts = self.process.all_outputs(unique=True)
        return len(list(filter(lambda a: len(a.samples) == 1, all_artifacts)))


    def get_artifacts(self):
        """Preparing output artifact dict."""
        for input_output in self.process.input_output_maps:
            input = input_output[0]
            output = input_output[1]
            if output["output-generation-type"] == "PerReagentLabel":
                artifact = output["uri"]
                sample_name = artifact.samples[0].id
                lane = input["uri"].location[1][0]
                if not sample_name in self.artifacts:
                    self.artifacts[sample_name] = {lane: artifact}
                else:
                    self.artifacts[sample_name][lane] = artifact

    def get_fc_id(self):
        """Get FC id of the sequencing run. Assuming all samples come from one flowcell."""
        try:
            self.flowcellname = self.process.all_inputs()[0].container.name
        except:
            sys.exit("Could not get FC id from Container name")

    def get_sequencing_metrics(self):
        """Get sequencing metrics from the cg api."""
        try:
            self.sequencing_metrics = self.cg_api_client.get_sequencing_metrics_for_flow_cell(self.flowcellname)
        
        except:
            sys.exit(f"Error getting sequencing metrics for flowcell: {self.flowcellname}")

    def get_quality_control_flag(self, q30, reads):
        if q30 * 100 >= self.q30treshhold and reads >= self.reads_treshold:
            return "PASSED"
        else:
            self.failed_artifacts += 1
            return "FAILED"

    def set_udfs(self):
        """Setting the demultiplex udfs"""

        for metrics in self.sequencing_metrics:
            sample_lims_id: str = metrics.sample_internal_id

            if sample_lims_id not in self.artifacts:
                continue

            lane = str(metrics.flow_cell_lane_number)
            sample_artifact = self.artifacts[sample_lims_id].get(lane)

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
    BCL = BCLconv(process)
    BCL.get_fc_id()
    BCL.get_artifacts()
    BCL.get_sequencing_metrics()
    BCL.set_udfs()

    abstract: str = f"Updated {BCL.updated_artifacts} artifacts. Skipped {BCL.not_updated_artifacts} due to missing sequencing metrics. "

    if BCL.failed_artifacts:
        abstract = abstract + str(BCL.failed_artifacts) + " samples failed QC!"

    if BCL.failed_artifacts or BCL.not_updated_artifacts:
        sys.exit(abstract)
    else:
        print >> sys.stderr, abstract


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument("-p", dest="pid", help="Lims id for current Process")

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
