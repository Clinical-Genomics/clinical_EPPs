#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process , Workflow, Stage, Artifact
from xml.dom.minidom import parseString
import logging
import sys
import glsapiutil
import platform
import xml.etree.ElementTree as ET

HOSTNAME = platform.node()
VERSION = 'v2'
APIURI = BASEURI + '/api/' + VERSION + '/'

api = glsapiutil.glsapiutil2()
api.setHostname( 'http://'+HOSTNAME ) ##api only seems to work with http, not https. Find out why, and how this should be done.
api.setVersion( VERSION )
api.setup( USERNAME, PASSWORD )



DESC = """
Script to pass samples and pools to next step. Sort of specific script:

getting all input artifacts from the latest Pool All Samples - step. 
These are passed to the NovaSeq WF

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class PassSamples():

    def __init__(self, process, process_types, nova_seq_step):
        self.process = process
        self.process_types = process_types
        self.nr_samps = 0
        self.nr_pools = 0
        self.input_arts = self.process.all_inputs(unique=True)
        self.send_to_next_step = []
        self.next_step = [nova_seq_step]
        self.current_WF = ''
        self.next_step_stage = ''
        self.rXML = []
        self.abstract = ''

    def get_samples(self):
        sample_representative = self.process.all_inputs()[0].samples[0].id
        all_arts = lims.get_artifacts(samplelimsid = sample_representative, process_type = self.process_types)
        latest_art = all_arts[-1] #fixa
        self.send_to_next_step = latest_art.parent_process.all_inputs()

    def get_current_WF(self):
        # This should be done in a better way...
        # pick any art from the current wf:
        art = self.input_arts[0]
        art_XML = api.GET(APIURI + 'artifacts/' + art.id)
        art_dom = parseString( art_XML )
        # look for the last "workflow-stage" node, since that's
        # where we currently are
        WF_node = art_dom.getElementsByTagName('workflow-stage')[-1]
        wf_id = WF_node.getAttribute('uri').split('/stages/')[0].split('/')[-1]
        self.current_WF = Workflow(lims,id = wf_id)
        if not self.current_WF:
            sys.exit('Could not get the current Work Flow. Contact lims developer.')

    def get_next_step_stage_URI(self):
        for stage in self.current_WF.stages:
            if stage.name in self.next_step:
                self.next_step_stage = stage.uri
                break
        if not self.next_step_stage:
            sys.exit('Could not get the next step Stage. Contact lims developer.')

    def assign_arts(self):
        for art in self.send_to_next_step:
            if len(art.samples)>1:
                self.nr_pools += 1
            elif len(art.samples)==1:
                self.nr_samps += 1
            #newURI = art.uri[ : art.uri.rfind('?state') ]
            self.rXML.append( '<assign stage-uri="' + self.next_step_stage + '">' )
            self.rXML.append( '<artifact uri="' + art.uri + '"/>' )#### KANSKE newURI IST F art.uri
            self.rXML.append( '</assign>' )

    def rout(self):
        routeXML = "".join( self.rXML )
        if len(routeXML) > 0:
            routeXML = '<rt:routing xmlns:rt="http://genologics.com/ri/routing">' + routeXML + '</rt:routing>'
            responseXML = api.POST( routeXML, APIURI + "route/artifacts/" )
            if 'exception' in responseXML:
                sys.exit('XML routing error. Contact Lims Developer. '+responseXML)
            self.passed=True

def main(lims, args):
    process = Process(lims, id = args.pid)
    PS = PassSamples(process, args.process_types, args.nova_seq_step)
    PS.get_samples()
    PS.get_current_WF()
    PS.get_next_step_stage_URI()
    PS.assign_arts()
    PS.rout()

    abstract = 'Passed '+str(PS.nr_samps)+' samples and '+str(PS.nr_pools) +' pools to the NovaSeq Protocol.'
    print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('-p', dest = 'process_types',  nargs='+', 
                        help='Get pools from these process type(s)')
    parser.add_argument('-s', dest = 'nova_seq_step', 
                        help='Place samples in this step)')
                
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

