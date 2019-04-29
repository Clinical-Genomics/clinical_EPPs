#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
import sys

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO) 
#logging.basicConfig(filename='check_lims_config.log', format='%(levelname)s:%(message)s', level=logging.INFO) 

DESC = """
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

class CheckConfigurations():

    def __init__(self, lims):
        self.lims = lims
        self.workflows = []
        self.protocols = []
        self.steps = []
        self.automations = []
        self.udfs = []

    def _get_active(self):
        """Get the names of all active workflows, protocols and steps. 
        These are the names to search for in configurations and step UDFs."""
        
        logging.info("Searching for active workflows, protocols and steps.")
        workflows=self.lims.get_workflows(status='ACTIVE')
        for workflow in workflows:
            self.workflows.append(workflow.name)
            for protocol in workflow.protocols:
                self.protocols.append(protocol.name)
            for step in workflow.stages:
                self.steps.append(step.name)
        self.steps = set(self.steps)
        self.protocols = set(self.protocols)
        self.workflows = set(self.workflows)

    def serarch_active(self):
        """Search automations and step udfs for active (workflow, protocol, step) names.
        Log where ever a name is found.
        """

        self._get_active()

        logging.info("Searching automations and step udfs for ACTIVE STEP NAMES.")
        for step in self.steps:
            self.search_automations(search_by=step)
            self.search_steps_for_udf(search_by=step)

        logging.info("Searching automations and step udfs for ACTIVE PROTOCOL NAMES.")
        for protocol in self.protocols:
            self.search_automations(search_by=protocol)
            self.search_steps_for_udf(search_by=protocol)

        logging.info("Searching automations and step udfs for ACTIVE WORKFLOW NAMES.")
        for workflow in self.workflows:
            self.search_automations(search_by=workflow)
            self.search_steps_for_udf(search_by=workflow)


    def search_automations(self, search_by = None):
        """Script to search for Automations. 

        The argument search_by could be a script name, eg: bcl2fastq.py, 
        or a script argument, eg: CG002 - Aggregate QC (Library Validation).
        """
        if not self.automations:
            automations = self.lims.get_automations()
        for automation in self.automations:
            bash_string = automation.string
            if bash_string.find(search_by) != -1:
                logging.info("AUTOMATION: Searching for '%s'." % (search_by))
                logging.info("Button: %s" % (automation.name))
                logging.info("Bash string: %s" % (bash_string))
                logging.info("Processes: %s \n" % (automation.process_types))


    def search_steps_for_udf(self, search_by=None):
        """Script to search step udf presets.

        The argument could be whatever preset you want to serch for. 
        Eg: 'Concentration' or 'CG002 - Aggregate QC (Library Validation)'.
        """

        if not self.udfs:
            self.udfs = self.lims.get_udfs(attach_to_category='ProcessType')

        for udf in self.udfs:
            if udf.presets and search_by in udf.presets:
                logging.info("PROCESS UDF PRESTES: Searching for '%s'" % (search_by))
                logging.info( "Process Name: %s" % (udf.attach_to_name))
                logging.info( "Udf: %s" % (udf.name))
                logging.info( "Presets: %s \n" % ', '.join(udf.presets))


    def print_all_bash(self):
        """Just print out all automations in bash."""

        automations = self.lims.get_automations()
        for automation in automations:
            logging.info( automation.string)

def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    CC = CheckConfigurations(lims)
    if args.udf_preset:
        CC.search_steps_for_udf(args.udf_preset)
    elif args.automation_string:
        CC.search_automations(args.automation_string)
    elif args.print_all_bash:
        CC.print_all_bash()
    elif args.all_active:
        CC.serarch_active()


if __name__ == "__main__":
    Parser = ArgumentParser(description=DESC)
    Parser.add_argument('-s', dest='automation_string',
                        help = 'Search automation by automation_string. Any subset of the automation bash string is valid. Could be a script name, eg: bcl2fastq.py, or a script argument, eg: CG002 - Aggregate QC (Library Validation) ')
    Parser.add_argument('-p', action='store_true', dest='print_all_bash', help = 'Print all automations')
    Parser.add_argument('-u', dest='udf_preset', help = 'Search Process UDFs by udf_preset')
    Parser.add_argument('-a', action='store_true', dest='all_active', help = 'Check all active step names')

    args = Parser.parse_args()
    main(args)