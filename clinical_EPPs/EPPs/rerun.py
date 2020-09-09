#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from argparse import ArgumentParser
import xml.dom.minidom
from genologics.config import BASEURI,USERNAME,PASSWORD
import re
import glsapiutil
from xml.dom.minidom import parseString
from art_hist import make_hist_dict

DEBUG = "false"
api = None

#####################################################################################
### In this example, the output artifacts could be routed to one or both of these two potential WF/stage combinations
### Configuration is required --- need to create artifact UDFs which will be the checkboxes we examine
### See lines 85 and 87 for the UDF names "Go to Inv" "Go to Seq" 
#####################################################################################

def setupGlobalsFromURI( uri ):
    global HOSTNAME
    global VERSION
    tokens = uri.split( "/" )
    HOSTNAME = "/".join(tokens[0:3])
    VERSION = tokens[4]


def getStageURI( wfName, stageName ):
    response = ""
    wURI = HOSTNAME + "/api/" + VERSION + "/configuration/workflows"
    wXML = api.getResourceByURI( wURI )
    wDOM = parseString( wXML )
    workflows = wDOM.getElementsByTagName( "workflow" )
    for wf in workflows:
        name = wf.getAttribute( "name" )
        if name == wfName:
            wfURI = wf.getAttribute( "uri" )
            wfXML = api.getResourceByURI( wfURI )
            wfDOM = parseString( wfXML )
            stages = wfDOM.getElementsByTagName( "stage" )
            for stage in stages:
                stagename = stage.getAttribute( "name" )
                if stagename == stageName:
                    response = stage.getAttribute( "uri" )
                    break
            break
    return response


def routeAnalytes(Inv, Seq, stop_processes):
    hist_dict = make_hist_dict(args.limsid, stop_processes)
    hist_dict_uri = {k.uri : v.uri for k, v in hist_dict.items()}
    ANALYTES = []       ### Cache, prevents unnessesary GET calls
    GoTo_Inv = []
    GoTo_Seq = []
    ## Step 1: Get the process XML #technically step XML not process
    processURI = HOSTNAME + "/api/" + VERSION + "/steps/" + args.limsid + "/details" #
    processXML = api.getResourceByURI( processURI )
    processDOM = parseString( processXML )
    ## Step 2: Harvest Output Analytes
    analytes = processDOM.getElementsByTagName( "output" )
    ## Step 3: looks for ones
    for analyte in analytes:
        if analyte.getAttribute( "type" ) == "Analyte":
            analyteURI = analyte.getAttribute( "uri" )
            if analyteURI in ANALYTES:
                pass
            else:
                ANALYTES.append( analyteURI )
                analyteXML = api.getResourceByURI( analyteURI )
                analyteDOM = parseString( analyteXML )

                ## Step 4: Add the analytes to the list of ones to be routed
                if api.getUDF( analyteDOM , "Rerun" ) == 'false':
                    GoTo_Inv.append( analyteURI )
                if api.getUDF( analyteDOM , "Rerun" ) == 'true':
                    wf_input_analyte_uri = hist_dict[analyteURI]
                    GoTo_Seq.append( wf_input_analyte_uri )

    def pack_and_go( stageURI, a_ToGo ):
        ## Step 5: Build and submit the routing message
        rXML = '<rt:routing xmlns:rt="http://genologics.com/ri/routing">'
        rXML = rXML + '<assign stage-uri="' + stageURI + '">'
        for uri in a_ToGo:
            rXML = rXML + '<artifact uri="' + uri + '"/>'
        rXML = rXML + '</assign>'
        rXML = rXML + '</rt:routing>'

        response = api.createObject( rXML, HOSTNAME + "/api/" + VERSION + "/route/artifacts/" )

    #Two seperate routing messages
    Mi_r = pack_and_go( Seq, GoTo_Seq)
    Hi_r = pack_and_go( Inv, GoTo_Inv)

    nr_seq = len(list(set(GoTo_Seq)))
    nr_inv =  len(list(set(GoTo_Inv)))

    msg = str( nr_seq ) + " Samples were added to the " + args.rerun_step + " Step. " + str( nr_inv ) + " Samples were added to the " + args.continue_step + " Step."
    print msg
    status = "OK"
    api.reportScriptStatus( args.stepURI, status, msg )

def main():

    global api
    global args

    parser = ArgumentParser()
    parser.add_argument( "-l", "--limsid", help="the limsid of the process under investigation")
    parser.add_argument( "-s", "--stepURI", help="the URI of the step that launched this script")
    parser.add_argument( "-w", "--workflow", help="")
    parser.add_argument( "-c", "--continue_step", help="")
    parser.add_argument( "-r", "--rerun_step", help="")
    parser.add_argument( "-p", '--stop_processes', help="", type=str, default=None, nargs='*')

    args = parser.parse_args()
    api = glsapiutil.glsapiutil()
    setupGlobalsFromURI( args.stepURI )
    api.setHostname( HOSTNAME )
    api.setVersion( VERSION )
    api.setup( USERNAME, PASSWORD)
    args.stepURI
    SeqURI = getStageURI( args.workflow, args.rerun_step )
    InvURI = getStageURI( args.workflow, args.continue_step )
    if SeqURI == "" or InvURI == "":
        print "Could not retrieve the workflow / stage combination"

    
    routeAnalytes(InvURI, SeqURI, args.stop_processes)

if __name__ == "__main__":
    main()

