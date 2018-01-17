#!/usr/bin/env python
from __future__ import division
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger


from xml.dom.minidom import parseString
from collections import namedtuple
import string
from datetime import date

from art_hist import make_hist_dict_no_stop
import logging
import sys

DESC = """

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class SamplePlacementMap():

    def __init__(self, process):
        self.process = process
        self.hist_dict = make_hist_dict_no_stop(process.id)
        self.mastermap = {}
        self.udf_list = ['Sample Volume (ul)', 'Volume of sample (ul)']

    def make_mastermap(self):
        for art, orig_art in self.hist_dict.items():
            sample = orig_art.samples[0]
            dest_well = art.location[1]
            dest_cont = art.location[0]
            orig_well = orig_art.location[1]
            orig_cont = orig_art.location[0]
            if not dest_cont in self.mastermap:
                self.mastermap[dest_cont] = {}
            self.mastermap[dest_cont][dest_well] = {'orig_cont' : orig_cont, 'orig_well' : orig_well, 'sample' : sample, 'artifact' : art}

    def make_html(self,resultfile):
        ### HEADER ###
        html = []
        html.append('<html><head><style>table, th, td {border: 1px solid black; border-collapse: collapse;}</style><meta content="text/html; charset=UTF-8" http-equiv="Content-Type"><link href="../css/g/queue-print.css" rel="stylesheet" type="text/css" media="screen,print"><title>')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</title></head>')
        html.append('<body><div id="header"><h1 class="title">')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</h1></div>')
        html.append('Created by: ' + USERNAME + ', ' + str(date.today().isoformat()))
        for container, container_info in self.mastermap.items():
            # Data about this specific container
            html.append( '<table class="group-contents"><br><br><thead><tr><th class="group-header" colspan="10"><h2>Sample placement map: '+ container.name )
            html.append( '</h2>' )
            html.append( '<table><tbody><tr><td class="group-field-label">' )
            html.append( container.type.name)
            html.append( ': </td><td class="group-field-value">' )
            html.append( container.name)
            html.append( '</td></tr><tr><td class="group-field-label">Container LIMS ID: </td><td class="group-field-value">' )
            html.append( container.id )
            html.append( '</td></tr></tbody></table><br></th></tr>' )
    
            ## Columns Header
            html.append( '<tr><th style="width: 7%;" class="">Project Name</th><th style="width: 7%;" class="">Sample Name</th><th style="width: 7%;" class="">Sample Lims ID</th><th style="width: 7%;" class="">Original Container</th><th style="width: 7%;" class="">Original Well</th><th style="width: 7%;" class="">Dest. Well</th></tr></thead>')
            html.append( '<tbody>' )
    
            ## artifact list
            for dest_well , well_data in container_info.items():
                sample = well_data['sample']
                orig_well = well_data['orig_well'] 
                orig_cont = well_data['orig_cont']
                html.append( '<tr><td style="width: 7%;">' )
                html.append( sample.project.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.id )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( orig_cont.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( orig_well )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( dest_well )
                html.append( '</td></tr>' )
            html.append( '</tbody></table><br><br>' )
    
            ## VISUAL Platemap
            html.append( '<table class="print-container-view "><thead><tr><th>&nbsp;</th>')
    
            ## column headers
            for col in range(1,13):
                html.append( '<th>' + str( col ) + '</th>' )
            html.append( '</tr></thead><tbody>' )
            for rowname in ['A','B','C','D','E','F','G','H']:
                html.append( '<tr style="height: 12%;"><td class="bold-column row-name">' + rowname + '</td>')
    
                for col in range(1,13):
                    well_location = rowname + ":" + str( col )
                    if well_location in container_info:
                        well_info = container_info[ well_location ]
                        # This only happens if there is an artifact in the well
                        # This assumes that all artifacts have the required UDFs
                        html.append( '<td class="well" style="width: 20%;background-color: #CCC;">' )
                        html.append('Project : ' + well_info['sample'].project.name + '<br>')
                        html.append('Sample Name : ' + well_info['sample'].name+ '<br>')
                        html.append('Sample ID : ' + well_info['sample'].id+ '<br>')
                        html.append('Original Well : ' + well_info['orig_well'] + '<br>')
                        for udf in self.udf_list:
                            try:
                                html.append(udf + ' : ' + str(well_info['artifact'].udf[udf])+ '<br>')
                            except:
                                pass
                    else:
                        # For wells that are empty:
                        html.append( '<td class="well" style="width: 8%;">&nbsp;</td>')
                    html.append( '</td>')


        html.append( '</body></html>')
        file = open( str( resultfile ) + ".html", "w" )
        file.write( ''.join( html ) )
        file.close()


def main(lims, args):
    process = Process(lims, id = args.pid)
    SPM= SamplePlacementMap(process)
    SPM.make_mastermap()
    SPM.make_html(args.res)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--res', default=sys.stdout,
                        help=('Result file'))
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)