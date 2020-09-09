#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
import sys
import csv

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO) 

DESC = """
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

class CheckConfigurations():

    def __init__(self, lims):
        self.lims = lims
        self.all_active = {'steps':[],'workflows':[]}
        self.search_results = {'steps':[],'workflows':[]}
        self.automations = []
        self.udfs = []

    def _get_active(self):
        """Get the names of all active workflows and steps. 
        These are the names to search for in configurations and step UDFs.
        """
        
        logging.info("Searching for active workflows and steps.\n")
        workflows = self.lims.get_workflows()
        for workflow in workflows:
            if workflow.status == 'ACTIVE':
                self.all_active['workflows'].append(workflow.name)
                for protocol in workflow.protocols:
                    for step in protocol.steps:
                        self.all_active['steps'].append(step.name)
        self.all_active['steps'] = set(self.all_active['steps'])
        self.all_active['workflows'] = set(self.all_active['workflows'])


    def _save_to_csv(self, search_results, file_name):
        """search_results: list of dicts with keys as in fieldnames below.
        """

        file = open(file_name, 'w')
        fieldnames = ['search','udf_processes','udf_name','automation_processes','automation_name','automation_bash']
        fc = csv.DictWriter(file, fieldnames=fieldnames) 
        fc.writeheader()
        fc.writerows(search_results)
        file.close()


    def _search_entity(self, entity):
        """Searches automations and step udfs for given entity (workflows or steps).
        Saves results to csv.

        Argument:
            entity: workflows, protokols, steps """

        logging.info("\n\nSearching automations and step udfs for active %s.\n" % (entity))
        for name in self.all_active[entity]:
            automations_results = self.search_automations(search_by=name)
            udf_results = self.search_steps_for_udf(search_by=name)
            if automations_results:
                self.search_results[entity] += automations_results
            if udf_results:
                self.search_results[entity] += udf_results

        self._save_to_csv(self.search_results[entity], 'active_%s_search.csv' % (entity))        


    def serarch_all_active(self):
        """Search all automations and step udfs for all active workflow and step names.
        """

        self._get_active()

        self._search_entity('steps')
        self._search_entity('workflows')


    def search_automations(self, search_by = None):
        """Script to search for Automations. 

        The argument search_by could be a script name, eg: bcl2fastq.py, 
        or a script argument, eg: CG002 - Aggregate QC (Library Validation).
        """

        if not self.automations:
            self.automations = self.lims.get_automations()
        search_results = []
        for automation in self.automations:
            bash_string = automation.string
            for process_type in automation.process_types:
                if process_type.name[0:8]!='obsolete' and bash_string.find(search_by) != -1:
                    process_ids = [t.id for t in automation.process_types]
                    search_results.append({'search' : search_by,
                                            'automation_processes' : process_ids,
                                            'automation_bash' : bash_string, 
                                            'automation_name' : automation.name, 
                                            'udf_processes' : '',
                                            'udf_name' : ''})
                                            
                    logging.info("AUTOMATION: Searching for '%s'." % (search_by))
                    logging.info("Button: %s" % (automation.name))
                    logging.info("Bash string: %s" % (bash_string))
                    logging.info("Processes: %s \n" % (process_ids))
                    break
        return search_results


    def search_steps_for_udf(self, search_by=None):
        """Script to search step udf presets.

        The argument could be whatever preset you want to serch for. 
        Eg: 'Concentration' or 'CG002 - Aggregate QC (Library Validation)'.
        """

        if not self.udfs:
            self.udfs = self.lims.get_udfs(attach_to_category='ProcessType')
        search_results = []

        for udf in self.udfs:
            if udf.presets and (search_by in udf.presets) and (udf.attach_to_name[0:8] != 'obsolete'):
                search_results.append({'search' : search_by,
                                        'automation_processes' : '',
                                        'automation_bash' : '', 
                                        'automation_name' : '',
                                        'udf_processes' : udf.attach_to_name,
                                        'udf_name' : udf.name})

                logging.info("PROCESS UDF PRESTES: Searching for '%s'" % (search_by))
                logging.info( "Process Name: %s" % (udf.attach_to_name))
                logging.info( "Udf: %s" % (udf.name))
                logging.info( "Presets: %s \n" % ', '.join(udf.presets))
        return search_results


    def print_all_bash(self):
        """Just print out all automations in bash."""

        automations = self.lims.get_automations()
        for automation in automations:
            logging.info( automation.string)


def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)

    CC = CheckConfigurations(lims)
    if args.udf_preset:
        udf_results = CC.search_steps_for_udf(search_by=args.udf_preset)
    elif args.automation_string:
        search_results = CC.search_automations(search_by=args.automation_string)
    elif args.print_all_bash:
        CC.print_all_bash()
    elif args.all_active:
        CC.serarch_all_active()



if __name__ == "__main__":
    Parser = ArgumentParser(description=DESC)
    Parser.add_argument('-s', dest='automation_string',
                        help = 'Search automation by automation_string. Any subset of the automation bash string is valid. Could be a script name, eg: bcl2fastq.py, or a script argument, eg: CG002 - Aggregate QC (Library Validation) ')
    Parser.add_argument('-p', action='store_true', dest='print_all_bash', help = 'Print all automations')
    Parser.add_argument('-u', dest='udf_preset', help = 'Search Process UDFs by udf_preset')
    Parser.add_argument('-a', action='store_true', dest='all_active', help = 'Check all active step and workflow names')

    args = Parser.parse_args()
    main(args)
