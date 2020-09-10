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
Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""



class PassSamples():

    def __init__(self, process, rerun_steps):
        self.process = process
        self.all_arts = self._get_all_arts()
        self.rerun_arts = {}
        self.current_WF = self._get_current_WF()
        self.rerun_steps = rerun_steps
        self.rerun_stage = self._get_next_step_stage_URI(self.rerun_steps)
        self.warning_duplicate_samples = []
        self.xml = []

    def _get_all_arts(self):
        """Get output analytes of the process"""
        all_arts=[]
        for art in self.process.all_outputs(unique=True):
            if art.type == 'Analyte':
                all_arts.append(art)
        return all_arts

    def get_artifacts(self):
        """Get samples/pools to rerun"""
        for art in self.all_arts:
            try:
                rerun = art.udf['Rerun']
            except:
                rerun = False
            if rerun:
                self._get_rerun_arts(art)

    def _get_rerun_arts(self, art):
        """For each sample/pool to rerun, find in history the artifact to rerun"""
        all_arts_in_sort=[]
        for sample in art.samples:
            sample_id = sample.id
            out_arts = lims.get_artifacts(samplelimsid = sample_id,
                            process_type = self.rerun_steps)
            all_arts_in_sort += out_arts
        correct_process=None
        for art in all_arts_in_sort:
            if correct_process:
                if art.parent_process.date_run > correct_process.date_run:
                    correct_process = art.parent_process
            else:
                correct_process = art.parent_process
        for art  in all_arts_in_sort:
            if art.parent_process == correct_process:
                art_sample_key = [s.id for s in art.samples]
                art_sample_key = '_'.join(list(set(art_sample_key)))
                self.rerun_arts[art_sample_key] = art

    def check_same_sample_in_many_rerun_pools(self):
        """Check that the same sample does not occure in more than one of the pools to rerun."""
        all_samples = []
        for s in self.rerun_arts.keys():
            all_samples += s.split('_')
        for s in set(all_samples):
            all_samples.remove(s)
        self.warning_duplicate_samples = list(set(all_samples))

    def _get_current_WF(self):
        art = self.process.all_inputs()[0]
        art_XML = api.GET(APIURI + 'artifacts/' + art.id)
        art_dom = parseString( art_XML )
        WF_node = art_dom.getElementsByTagName('workflow-stage')[-1]
        wf_id = WF_node.getAttribute('uri').split('/stages/')[0].split('/')[-1]
        try:
            return Workflow(lims,id = wf_id)
        except:
            sys.exit('Could not get the current Work Flow. Contact lims developer.')

    def _get_next_step_stage_URI(self, next_step):
        for stage in self.current_WF.stages:
            if stage.name in next_step:
                return stage.uri
        sys.exit('Could not get the next step Stage. Contact lims developer.')

    def assign_arts(self):
        for key, art in self.rerun_arts.items():
            self.make_assig_xml(art.uri, self.rerun_stage)

    def make_assig_xml(self, art_uri, next_step_uri):
        self.xml.append( '<assign stage-uri="' + next_step_uri + '">' )
        self.xml.append( '<artifact uri="' + art_uri + '"/>' )
        self.xml.append( '</assign>' )

    def rout(self):
        routeXML = "".join( self.xml )
        if len(routeXML) > 0:
            routeXML = '<rt:routing xmlns:rt="http://genologics.com/ri/routing">' + routeXML + '</rt:routing>'
            responseXML = api.POST( routeXML, APIURI + "route/artifacts/" )
            if 'exception' in responseXML:
                sys.exit('XML routing error. Contact Lims Developer. '+responseXML)

def main(lims, args):
    process = Process(lims, id = args.pid)
    PS = PassSamples(process, args.rerun_steps)
    PS.get_artifacts()
    PS.check_same_sample_in_many_rerun_pools()
    PS.assign_arts()
    PS.rout()

    abstract = ''
    if PS.rerun_arts:
        abstract += str(len(PS.rerun_arts)) + ' artifacts were sent for rerun: '+', '.join(PS.rerun_arts.keys())+'.'
    if PS.warning_duplicate_samples:
        abstract += 'WARNING: some samples were sent for rerun as part of more than one pool'
    print(abstract, file=sys.stderr)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-s', dest = 'rerun_steps',  nargs='+', 
                        help='Steps for rerun.')
    
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)

