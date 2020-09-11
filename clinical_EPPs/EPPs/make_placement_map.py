#!/usr/bin/env python
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process

from datetime import date

from art_hist import make_hist_dict_no_stop, make_hist_dict
import sys

DESC = """

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class SamplePlacementMap():

    def __init__(self, process, original_source, other_source):
        self.original_source = original_source
        self.other_source = other_source
        self.process = process
        self.mastermap = {}
        self.udf_list = ['Sample Volume (ul)', 'Volume of sample (ul)', 'Volume of RSB (ul)', 'EB Volume (ul)',]


    def _make_source_dest_dict(self, source_art, dest_art):
        sample = source_art.samples[0]
        dest_well = dest_art.location[1]
        dest_cont = dest_art.location[0]
        source_well = source_art.location[1]
        source_cont = source_art.location[0]
        if not dest_cont in self.mastermap:
            self.mastermap[dest_cont] = {}
        self.mastermap[dest_cont][dest_well] = {'source_cont' : source_cont, 'source_well' : source_well, 'sample' : sample, 'artifact' : dest_art}

    def build_mastermap(self):
        """Depending on the arguments .. we get the source well location from 
        the output artifact from the specified step"""
        hist_dict = None
        artifacts = None

        if self.original_source:
            hist_dict = make_hist_dict_no_stop(self.process.id)
        elif self.other_source:
            hist_dict = make_hist_dict(self.process.id, [self.other_source])
        else:
            all_artifacts = self.process.all_outputs(unique=True)
            artifacts = [a for a in all_artifacts if a.output_type == "Analyte"]

        if hist_dict:
            for dest_art, source_art in list(hist_dict.items()):
                self._make_source_dest_dict(source_art, dest_art)
            return
        elif artifacts:
            for dest_art in artifacts:
                source_art = dest_art.input_artifact_list()[0] #No pooling so only one inart per outart
                self._make_source_dest_dict(source_art, dest_art)

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
        for container, container_info in list(self.mastermap.items()):
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
            html.append( '<tr><th style="width: 7%;" class="">Project Name</th><th style="width: 7%;" class="">Sample Name</th><th style="width: 7%;" class="">Sample Lims ID</th><th style="width: 7%;" class="">Original Container</th><th style="width: 7%;" class="">Source Container</th><th style="width: 7%;" class="">Source Well</th><th style="width: 7%;" class="">Dest. Well</th></tr></thead>')
            html.append( '<tbody>' )
    
            ## artifact list
            for dest_well , well_data in list(container_info.items()):
                sample = well_data['sample']
                original_container = sample.udf.get('Original Container')
                source_well = well_data['source_well'] 
                source_cont = well_data['source_cont']
                html.append( '<tr><td style="width: 7%;">' )
                html.append( sample.project.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( sample.id )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( original_container if original_container else '' )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( source_cont.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( source_well )
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
                        if well_info['artifact'].qc_flag and well_info['artifact'].qc_flag == 'FAILED':
                            html.append( '<td class="well" style="background-color: #F08080;">' )
                        else:
                            html.append( '<td class="well" style="background-color: #CCC;">' )
                        html.append('Project : ' + well_info['sample'].project.name + '<br>')
                        html.append('Sample Name : ' + well_info['sample'].name+ '<br>')
                        html.append('Sample ID : ' + well_info['sample'].id+ '<br>')
                        html.append('Source Container : ' + well_info['source_cont'].name + '<br>')
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

    def make_html_for_sequencing(self,resultfile):
        ### HEADER ###
        html = []
        html.append('<html><head><style>table, th, td {border: 1px solid black; border-collapse: collapse;}</style><meta content="text/html; charset=UTF-8" http-equiv="Content-Type"><link href="../css/g/queue-print.css" rel="stylesheet" type="text/css" media="screen,print"><title>')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</title></head>')
        html.append('<body><div id="header"><h1 class="title">')
        html.append(self.process.type.name) #self.process.protocol_name
        html.append('</h1></div>')
        html.append('Created by: ' + USERNAME + ', ' + str(date.today().isoformat()))
        for container, container_info in list(self.mastermap.items()):
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
            html.append( '<tr><th style="width: 7%;" class="">Sample Lims ID</th><th style="width: 7%;" class="">Dest Well</th><th style="width: 7%;" class="">Source Well</th><th style="width: 7%;" class="">Source Container</th><th style="width: 7%;" class="">Volume od sample (ul)</th><th style="width: 7%;" class="">Volume of RSB (ul)</th></tr></thead>')
            html.append( '<tbody>' )

            ## artifact list
            for dest_well in ['1:1' ,'2:1' ,'3:1' ,'4:1' ,'5:1' ,'6:1' ,'7:1' ,'8:1']:
                if dest_well in list(container_info.keys()):
                    well_data = container_info[dest_well]
                    sample = well_data['sample']
                    source_well = well_data['source_well']
                    source_cont = well_data['source_cont']
                    html.append( '<tr><td style="width: 7%;">' )
                    html.append( sample.id)
                    html.append( '</td><td class="" style="width: 7%;">' )
                    html.append( dest_well )
                    html.append( '</td><td class="" style="width: 7%;">' )
                    html.append( source_well )
                    html.append( '</td><td class="" style="width: 7%;">' )
                    html.append( source_cont.name )
                    html.append( '</td><td class="" style="width: 7%;">' )
                    html.append( str( well_data['artifact'].udf['Volume of sample (ul)'] ) )
                    html.append( '</td><td class="" style="width: 7%;">' )
                    html.append( str(well_data['artifact'].udf['Volume of RSB (ul)']) )
                    html.append( '</td></tr>' )
            html.append( '</tbody></table><br><br>' )
        html.append('</html>')
        file = open( str( resultfile ) + ".html", "w" )
        file.write( ''.join( html ) )
        file.close()


def main(lims, args):
    process = Process(lims, id = args.pid)
    SPM = SamplePlacementMap(process, args.orig, args.other_source)
    SPM.build_mastermap()
    if args.dest_96well:
        SPM.make_html(args.res)
    else:
        SPM.make_html_for_sequencing(args.res)


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--res', default=sys.stdout,
                        help=('Result file'))
    parser.add_argument('--orig', action='store_true',
                        help=("Use this tag if you want the source wells to be original wells"
                              "input artifacts instead"))
    parser.add_argument('--other_source', default = None, 
                        help=("The source well step if other than this or original."))
    parser.add_argument('--dest_96well', action='store_true',
                        help=("Use this tag if destination is 96 well plate"))
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
