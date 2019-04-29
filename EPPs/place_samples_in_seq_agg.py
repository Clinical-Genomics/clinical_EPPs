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

Single arts                                       --> Next Step
Cust001 - Pools --> split to pools from sort step --> Next Step
Non RML - Pools --> split in uniq sample arts     --> Next Step

Uniq sample arts are derived by 
    1.  geting the sample list of the pool
    2.  picking the input artifact to the Reception Control step, for 
        each sample in the list. This assuems the inputs will be one per 
        sample, wich is allways true since the Reception Control step is 
        the first step of any WF.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class PassSamples():

    def __init__(self, process, process_types):
        self.process = process
        self.process_types = process_types
        self.input_arts = self.process.all_inputs(unique=True)
        self.samples = []
        self.remove_from_WF = []
        self.send_to_next_step = []
        self.all_arts_in_sort = []
        self.next_step = ['CG002 - Sequence Aggregation']
        self.current_WF = ''
        self.next_step_stage = ''
        self.rXML = []
        self.uniq_artifacts = {}
        self.uniqe_RML_arts = {}
        self.abstract = ''

    def get_samples(self):
        for art in self.input_arts:
            self.samples += art.samples
            self.remove_from_WF.append(art)
        self.samples = list(set(self.samples))

    def get_artifacts(self):
        missing_cust = []
        for sample in self.samples:
            cust = sample.udf.get('customer')
            if not cust:
                missing_cust.append(sample.id)
                continue
            elif cust == 'cust001':
                ## this is a RML - get pools from sort step
                self._get_pools_from_sort(sample)
            else:
                ## this is a pool (or a sample) and we want to pass its samples to next step
                self._get_individual_artifacts(sample)
        if missing_cust:
            sys.exit( 'Could not queue samples to sequence aggregation because the following samples are missing customer udfs: '+', '.join(missing_cust))
        self._make_unique_pools()
        self.send_to_next_step += self.uniq_artifacts.values()
        self.send_to_next_step += self.uniqe_RML_arts.values()
        self.send_to_next_step = list(set(self.send_to_next_step))

    def _get_pools_from_sort(self, sample): ##---> will give manny duplicates
        self.all_arts_in_sort += lims.get_artifacts(samplelimsid = sample.id,
                            process_type = self.process_types)

    def _make_unique_pools(self):
        # Make uniqe. Also esure there are no replicates of the same RML. 
        # OBS doenst matter wich one we pick as long as it is a representative for the RML:
        for rml in self.all_arts_in_sort:
            rml_sample_key = [s.id for s in rml.samples]
            rml_sample_key = '_'.join(list(set(rml_sample_key)))
            ## Could put check here to make sure one sample doesnt occur in several RMLs. 
            ## But that shouldnt be possible. If thst happens. Tha lab has mixed tings up.
            self.uniqe_RML_arts[rml_sample_key] = rml

    def _get_individual_artifacts(self, sample):
        ## Assuming first artifact is allways named sample.id + 'PA1.
        first_sample_artifact = Artifact(lims, id = sample.id + 'PA1')
        self.uniq_artifacts[sample.id] = first_sample_artifact

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
            #newURI = art.uri[ : art.uri.rfind('?state') ]
            self.rXML.append( '<assign stage-uri="' + self.next_step_stage + '">' )
            self.rXML.append( '<artifact uri="' + art.uri + '"/>' )#### KANSKE newURI IST F art.uri
            self.rXML.append( '</assign>' )

    def remove_arts(self):
        for art in self.remove_from_WF:
            self.rXML.append( '<unassign workflow-uri="' + self.current_WF.uri + '">' )
            self.rXML.append( '<artifact uri="' + art.uri + '"/>' )
            self.rXML.append( '</unassign>' )

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
    PS = PassSamples(process, args.process_types)
    PS.get_samples()
    PS.get_artifacts()
    PS.get_current_WF()
    PS.get_next_step_stage_URI()
    PS.assign_arts()
    PS.remove_arts()
    PS.rout()

    abstract = 'Passed '+str(len(PS.send_to_next_step))+' arts to next step.'
    if PS.remove_from_WF:
        abstract += ' Removed ' + str(len(PS.remove_from_WF))+ ' artifacts from the wf.'
    print >> sys.stdout,abstract ## How do "flush this message in a correct way?"

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'process_types',  nargs='+', 
                        help='Get pools from these process type(s)')
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

