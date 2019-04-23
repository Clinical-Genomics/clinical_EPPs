#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
import sys

DESC = """
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""

class CheckConfigurations():

    def __init__(self, lims):
        self.lims = lims

    def search_automations(self, search_by = None):
        """Script to search for Automations. 
        The argument search_by could be a script name, eg: bcl2fastq.py, 
        or a script argument, eg: CG002 - Aggregate QC (Library Validation) """
        automations = self.lims.get_automations()
        for automation in automations:
            bash_string = automation.string
            if bash_string.find(search_by) != -1:
                print "Bash string: %s" % (bash_string)
                print "Button: %s" % (automation.name)
                print "Processes: %s \n" %s (automation.steps)

    def print_all_bash(self):
        """Just print out all automations in bash"""
        automations = self.lims.get_automations()
        for automation in automations:
            print automation.string

    def search_steps_for_udf(self, search_by):
        """script to search for: eg bcl2fastq.py"""        
        udfs = self.lims.get_udfs(attach_to_category='ProcessType')
        for udf in udfs:
            if udf.presets and search_by in udf.presets:
                print "Process Name: %s" % (udf.attach_to_name)
                print "Udf: %s \n" % (udf.name)

def main(args):
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    CC = CheckConfigurations(lims)
    if args.udf_preset:
        CC.search_steps_for_udf(args.udf_preset)
    elif args.automation_string:
        CC.search_automations(args.automation_string)
    elif args.print_all_bash:
        CC.print_all_bash()
 

if __name__ == "__main__":
    Parser = ArgumentParser(description=DESC)
    Parser.add_argument('-a', dest='automation_string',
                        help = 'Search automation by automation_string. Any subset of the automation bash string is valid. Could be a script name, eg: bcl2fastq.py, or a script argument, eg: CG002 - Aggregate QC (Library Validation) ')
    Parser.add_argument('-p', action='store_true', dest='print_all_bash', help = 'Print all automations')
    Parser.add_argument('-u', dest='udf_preset', help = 'Search Process UDFs by udf_preset')

    args = Parser.parse_args()
    main(args)
