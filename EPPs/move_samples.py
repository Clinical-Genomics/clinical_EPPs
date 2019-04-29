#!/usr/bin/env python
# -*- coding: utf-8 -*-

from optparse import OptionParser
import glsapiutil
from xml.dom.minidom import parseString
import sys
DEBUG = False


def getStageURI( wfName, stageName ):

    response = ""

    wURI = api.getBaseURI() + "configuration/workflows"
    wXML = api.GET( wURI )
    wDOM = parseString( wXML )

    workflows = wDOM.getElementsByTagName( "workflow" )
    for wf in workflows:
        name = wf.getAttribute( "name" )
        if name == wfName:
            wfURI = wf.getAttribute( "uri" )
            wfXML = api.GET( wfURI )
            wfDOM = parseString( wfXML )
            stages = wfDOM.getElementsByTagName( "stage" )
            for stage in stages:
                stagename = stage.getAttribute( "name" )
                if stagename == stageName:
                    response = stage.getAttribute( "uri" )
                    break
            break
    return response

def routeAnalytes( stageURI, input_art , udf):

    ANALYTES = []		### Cache, prevents unnessesary GET calls

    artifacts_to_route = []

    ## Step 1: Get the step XML
    processURI = args.stepURI + "/details"
    processXML = api.GET( processURI )
    processDOM = parseString( processXML )

    ## Step 2: Cache Output Analytes
    if input_art:
        analytes = processDOM.getElementsByTagName( "input" )
    else:
        analytes = processDOM.getElementsByTagName( "output" )
    for analyte in analytes:
        if input_art or analyte.getAttribute( "type" ) == "Analyte":
            analyteURI = analyte.getAttribute( "uri" )
            if analyteURI in ANALYTES:
                pass
            else:
                ANALYTES.append( analyteURI )
                analyteXML = api.GET( analyteURI )
                analyteDOM = parseString( analyteXML )

                ## Step 3: Add the analytes to the list of ones to be routed
                if api.getUDF( analyteDOM , udf ) == 'true':
                    artifacts_to_route.append( analyteURI )


    def pack_and_send( stageURI, a_ToGo ):
        ## Step 4: Build and submit the routing message
        rXML = '<rt:routing xmlns:rt="http://genologics.com/ri/routing">'
        rXML = rXML + '<assign stage-uri="' + stageURI + '">'
        for uri in a_ToGo:
            rXML = rXML + '<artifact uri="' + uri + '"/>'
        rXML = rXML + '</assign>'
        rXML = rXML + '</rt:routing>'
        response = api.POST( rXML, api.getBaseURI() + "route/artifacts/" )
        return response

    # Sends seperate routing messages for each stage
    r = pack_and_send( stageURI, artifacts_to_route )
    if len( parseString( r ).getElementsByTagName( "rt:routing" ) ) > 0:
        msg = str( len(artifacts_to_route) ) + " samples were added to the " + stageURI + " step. "
    else:
        msg = r
    print msg


def setupArguments():

    Parser = OptionParser()
    Parser.add_option('-u', "--username", action='store', dest='username')
    Parser.add_option('-p', "--password", action='store', dest='password')
    Parser.add_option('-s', "--stepURI", action='store', dest='stepURI')
    Parser.add_option("--workflow", action='store', dest='workflow')
    Parser.add_option("--stage", action='store', dest='stage')
    Parser.add_option("--udf", action='store', dest='udf')
    Parser.add_option("-i", action='store_true', dest='input',
                        help=("Use this tag if you run the script from a QC step."))

    return Parser.parse_args()[0]

def main():

    global args
    args = setupArguments()

    global api
    api = glsapiutil.glsapiutil2()
    api.setURI( args.stepURI )
    api.setup( args.username, args.password )

    stageURI = getStageURI(args.workflow, args.stage)
    if not stageURI:
        sys.exit( "Could not retrieve the workflow / stage combination")

    routeAnalytes( stageURI , args.input, args.udf)

if __name__ == "__main__":
    main()
