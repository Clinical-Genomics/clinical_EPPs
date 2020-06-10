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

    def __init__(self, process):
        self.process = process
        self.pools = []
        self.udf_list = ['Sample Volume (ul)', 'Volume of sample (ul)', 'Volume of RSB (ul)', 'EB Volume (ul)',]

    def get_artifacts(self):
        all_artifacts = self.process.all_outputs(unique=True)
        self.pools = filter(lambda a: a.output_type == "Analyte" , all_artifacts)

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
        for pool in self.pools:
            artifacts = pool.input_artifact_list()
            nr_samples = len(artifacts)
            total_amount = pool.udf.get('Total Amount (ng)')
            total_volume = round(pool.udf.get('Total Volume (ul)'),2)
            wather = round(pool.udf.get('Volume H2O (ul)'),2)
            # Data about this specific container
            html.append( '<table class="group-contents"><thead><tr><th class="group-header" colspan="10"><h2>'+ pool.name )
            html.append( '</h2>' )
            html.append( '<table><tbody><tr><td class="group-field-label">Container LIMS ID: </td><td class="group-field-value">' )
            html.append( pool.id )
            html.append( '</td></tr><tr><td class="group-field-label">Nr samples in pool: </td><td class="group-field-value">' )
            html.append( str(nr_samples) )
            html.append( '</td></tr><tr><td class="group-field-label">Total amount: </td><td class="group-field-value">' )
            html.append( str(total_amount))
            html.append( '</td></tr><tr><td class="group-field-label">Total volume: </td><td class="group-field-value">' )
            html.append( str(total_volume))
            html.append( '</td></tr><tr><td class="group-field-label">H2O to add: </td><td class="group-field-value">' )
            html.append( str(wather))
            html.append( '</td></tr></tbody></table><br></th></tr>' )
    
            ## Columns Header
            html.append( """<tr>
                    <th style="width: 7%;" class="">Sample Lims ID</th>
                    <th style="width: 7%;" class="">Source Well</th>
                    <th style="width: 7%;" class="">Amount of Sample</th>
                    <th style="width: 7%;" class="">Volume of Sample</th>
                    <th style="width: 7%;" class="">Pool Name</th>
                    <th style="width: 7%;" class="">Source Container</th></tr></thead>""")
            html.append( '<tbody>' )
    
            ## artifact list
            for art in artifacts:
                sample = art.samples[0]
                if art.udf.get('Amount taken (ng)') and art.udf.get('Amount taken (ng)') < 187.5 :
                    html.append( '<tr><td style="background-color: #F08080; width: 7%;">' )
                else:
                    html.append( '<tr><td style="width: 7%;">' )
                html.append( sample.id )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append(  art.location[1])
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( str(round(art.udf.get('Amount taken (ng)'),2)))
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( str(round(art.udf.get('Volume of sample (ul)'),2)))
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( pool.name )
                html.append( '</td><td class="" style="width: 7%;">' )
                html.append( art.container.name)
                html.append( '</td></tr>' )
            html.append( '</tbody></table><br><br>' )
    
        html.append('</html>')
        file = open( str( resultfile ) + ".html", "w" )
        file.write( ''.join( html ).encode('utf-8') )
        file.close()

def main(lims, args):
    process = Process(lims, id = args.pid)
    SPM = SamplePlacementMap(process)
    SPM.get_artifacts()
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
