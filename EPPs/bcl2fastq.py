#!/usr/bin/env python
from __future__ import division

import sys
from argparse import ArgumentParser

from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.entities import Process
from genologics.lims import Lims

from clinical_EPPs.cg_api_client import CgApiClient
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
        self.updated_arts = 0
        self.q30treshhold = process.udf.get("Threshold for % bases >= Q30")
        self.reads_treshold = 1000
        all_artifacts = self.process.all_outputs(unique=True)
        self.sequencing_metrics = []
        self.not_updated_arts = len(filter(lambda a: len(a.samples) == 1, all_artifacts))
        self.failed_arts = 0
        self.cg_api_client = CgApiClient(base_url=CG_URL)

    def get_artifacts(self):
        """Prepparing output artifact dict."""
        for input_output in self.process.input_output_maps:
            inpt = input_output[0]
            outpt = input_output[1]
            if outpt["output-generation-type"] == "PerReagentLabel":
                art = outpt["uri"]
                sampname = art.samples[0].id
                well = inpt["uri"].location[1][0]
                if not sampname in self.artifacts:
                    self.artifacts[sampname] = {well: art}
                else:
                    self.artifacts[sampname][well] = art

    def get_fc_id(self):
        """Gettning FC id of the seq-run. Assuming only all samples come from only one flowcell"""
        try:
            self.flowcellname = self.process.all_inputs()[0].container.name
        except:
            sys.exit("Could not get FC id from Container name")

    def get_sequencing_metrics(self):
        """Geting the demultiplex statistics from the cg api."""
        try:
            self.sequencing_metrics = self.cg_api_client.get_sequencing_metrics_for_flow_cell(self.flowcellname)
        
        except:
            sys.exit(f"Error getting metrics for flowcell: {self.flowcellname}")

    def get_qc(self, q30, reads):
        if q30 * 100 >= self.q30treshhold and reads >= self.reads_treshold:
            return "PASSED"
        else:
            self.failed_arts += 1
            return "FAILED"

    def set_udfs(self):
        """Setting the demultiplex udfs"""

        for metrics in self.sequencing_metrics:
            sample_lims_id: str = metrics.sample_internal_id

            if sample_lims_id not in self.artifacts:
                continue

            lane: int = metrics.flow_cell_lane_number
            sample_artifact = self.artifacts[sample_lims_id].get(str(lane))

            sample_artifact.udf["% Perfect Index Read"] = float(metrics.sample_base_fraction_passing_q30)
            sample_artifact.udf["# Reads"] = metrics.sample_total_reads_in_lane
            sample_artifact.udf["% Bases >=Q30"] = float(metrics.sample_base_fraction_passing_q30)

            qc_flag = self.get_qc(float(metrics.sample_base_fraction_passing_q30), metrics.sample_total_reads_in_lane)
            sample_artifact.qc_flag = qc_flag
    
            sample_artifact.put()
            self.updated_arts += 1
            self.not_updated_arts -= 1


def main(lims, args):
    process = Process(lims, id=args.pid)
    if not "Threshold for % bases >= Q30" in process.udf:
        sys.exit("Threshold for % bases >= Q30 has not ben set.")
    BCL = BCLconv(process)
    BCL.get_fc_id()
    BCL.get_artifacts()
    BCL.get_sequencing_metrics()
    BCL.set_udfs()

    d = {"ca": BCL.updated_arts, "wa": BCL.not_updated_arts}
    abstract = ("Updated {ca} artifact(s). Skipped {wa} due to missing data in the demultiplex database. ").format(**d)

    if BCL.failed_arts:
        abstract = abstract + str(BCL.failed_arts) + " samples failed QC!"

    if BCL.failed_arts or BCL.not_updated_arts:
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
