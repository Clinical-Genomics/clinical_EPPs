#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process, Artifact

from datetime import date
import sys

DESC = """

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class SamplePlacementMap():

    def __init__(self, original_source, lims, udf_list):
        self.process = Process(lims, id = args.pid)
        self.lims = lims
        self.input_output_maps = self.process.input_output_maps
        self.orig = original_source
        self.placement_map = {}
        self.udf_list = udf_list

    def get_artifacts(self):
        for inp, outp in self.input_output_maps:
            if outp.get("output-generation-type") == "PerAllInputs":
                continue
            in_art = Artifact(self.lims,id = inp['limsid'])
            source = in_art.location
            out_art = Artifact(self.lims,id = outp['limsid'])
            dest = out_art.location
            if dest[0]:
                self.make_source_dest_dict(in_art, out_art)

    def make_source_dest_dict(self, source_art, dest_art):
        sample = source_art.samples[0]
        dest_well = dest_art.location[1]
        dest_cont = dest_art.location[0]
        source_well = source_art.location[1]
        source_cont = source_art.location[0]
        if not dest_cont in self.placement_map:
            self.placement_map[dest_cont] = {}
        self.placement_map[dest_cont][dest_well] = {'source_cont' : source_cont.name, 
                                            'source_well' : source_well, 
                                            'sample' : sample, 
                                            'artifact' : dest_art,
                                            'orig_cont' : sample.udf.get('Original Container', ''),
                                            'orig_well' : sample.udf.get('Original Well', '')}


    def make_html(self, resultfile):
        ### HEADER ###
        html = []
        html.append('<html><head><style>table, th, td {border: 1px solid black; border-collapse: collapse;}</style><meta content="text/html; charset=UTF-8" http-equiv="Content-Type"><link href="../css/g/queue-print.css" rel="stylesheet" type="text/css" media="screen,print"><title>')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</title></head>')
        html.append('<body><div id="header"><h1 class="title">')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</h1></div>')
        html.append('Created by: ' + USERNAME + ', ' + str(date.today().isoformat()))
        for container, container_info in list(self.placement_map.items()):
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
            html.append( '<tr><th style="width: 7%;" class="">Project Name</th><th style="width: 7%;" class="">Sample Name</th><th style="width: 7%;" class="">Sample Lims ID</th><th style="width: 7%;" class="">Original Container</th><th style="width: 7%;" class="">Original Well</th><th style="width: 7%;" class="">Source Container</th><th style="width: 7%;" class="">Source Well</th><th style="width: 7%;" class="">Dest. Well</th></tr></thead>')
            html.append( '<tbody>' )
    
            ## artifact list
            for dest_well , well_data in list(container_info.items()):
                sample = well_data['sample']
                html.append( '<tr><td style="width: 7%;">' )
                html.append( sample.project.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.id )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( well_data['orig_cont'] )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( well_data['orig_well'] )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( well_data['source_cont'] )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( well_data['source_well'] )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( dest_well )
                html.append( '</td></tr>' )
            html.append( '</tbody></table><br><br>' )
    

            ## VISUAL Platemap
            ## column headers
            coulmns = list(range(1,13))
            rows = ['A','B','C','D','E','F','G','H']
            html.append( '<table class="print-container-view"><thead><tr><th>&nbsp;</th>')
            for col in coulmns:
                html.append( '<th>' + str( col ) + '</th>' )
            html.append( '</tr></thead><tbody>' )
            for rowname in rows:
                html.append( '<tr style="height: 12%;"><td class="bold-column row-name">' + str(rowname) + '</td>')
                for col in coulmns:
                    well_location = str(rowname) + ":" + str( col )
                    if well_location in container_info:
                        well_info = container_info[ well_location ]
                        # This only happens if there is an artifact in the well
                        # This assumes that all artifacts have the required UDFs
                        html.append( '<td class="well" style="background-color: #CCC;">' )
                        html.append('Project : ' + well_info['sample'].project.name + '<br>')
                        html.append('Sample Name : ' + well_info['sample'].name+ '<br>')
                        html.append('Sample ID : ' + well_info['sample'].id+ '<br>')
                        if self.orig:
                            html.append('Original Container : ' + well_info['orig_cont'] + '<br>')
                            html.append('Original Well : ' + well_info['orig_well'] + '<br>')
                        else:
                            html.append('Source Container : ' + well_info['source_cont'] + '<br>')
                            html.append('Source Well : ' + well_info['source_well'] + '<br>')
                        for udf in self.udf_list:
                            try:
                                html.append(udf + ' : ' + str(round(well_info['artifact'].udf[udf],2))+ '<br>')
                            except:
                                pass
                    else:
                        # For wells that are empty:
                        html.append( '<td class="well" style="">&nbsp;</td>')
                    html.append( '</td>')
            html.append( '</body></table>')
        html.append('</html>')
        file = open( str( resultfile ) + ".html", "w" )
        file.write( ''.join( html ).encode('utf-8') )
        file.close()

def main(lims, args):
    SPM = SamplePlacementMap(args.orig, lims, args.udf_list)
    SPM.get_artifacts()
    SPM.make_html(args.res)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-r', dest = 'res', default=sys.stdout,
                        help=('Result file'))
    parser.add_argument('-o', dest = 'orig', action='store_true',
                        help=("Use this tag if you want the source wells to be original wells"
                              "input artifacts instead"))
    parser.add_argument('-u',  dest = 'udf_list', default = [], nargs='+',
                        help=('Udfs to show in placement map.'))
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
