#!/usr/bin/env python
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD,VERSION
from genologics.entities import Process, Artifact
import sys

DESC="""script to make hist_dict...."""
BASEURI='http://localhost:9080'

lims = Lims(BASEURI, USERNAME, PASSWORD, VERSION)
lims.check_version()

def make_hist_dict_no_stop(process_id):
    """ arg stop_processes: list of process type names - eg: 
        ['CG002 - Aliquot Samples for Library Pooling', 'CG002 - Sort HiSeq X Samples (HiSeq X)']

        For each output artifact (assumed not to be pooles) of the current process:
        walk throuh its history untill a stop_process is encountered. 
        Get its corresponding input artifact to the stop_process.
        Add to the hist_dict
            key:    output artifact of current process
            value:  input artifact of the stop process"""
    current_process = Process(lims, id = process_id)
    out_arts = [a for a in current_process.all_outputs() if a.type=='Analyte']
    if not out_arts:
        out_arts = [a for a in current_process.all_inputs() if a.type=='Analyte']

    hist_dict = {}
    for out_art in out_arts:
        sample = out_art.samples[0].name
        parent_process = out_art.parent_process
        first_process = parent_process
        while parent_process:
            #We folow the sample history until it's parent process is the one we look for
            parent_inputs = [a for a in parent_process.all_inputs() if a.type=='Analyte']
            for parent_input in parent_inputs:
                sample_names = [s.name  for s in parent_input.samples]
                if sample in sample_names:
                    parent_process = parent_input.parent_process
                    if parent_process:
                        first_process = parent_process
                    break
        # Appends the in_art to the stop_process, that corresponds to the out_art of 
        # the current_process. Assumes a 1-1 relation.
        if not first_process:
            first_process = current_process
        parent_inputs = [a for a in first_process.all_inputs() if a.type=='Analyte']
        for parent_input in parent_inputs:
            sample_names = [s.name  for s in parent_input.samples]
            if sample in sample_names:
                hist_dict[out_art] = parent_input
                break
                #   assumes only one in_art analyte per out_art analyte, to the stop_ptocess


    return hist_dict


def make_hist_dict(process_id, stop_processes):
    """ arg stop_processes: list of process type names - eg: 
        ['CG002 - Aliquot Samples for Library Pooling', 'CG002 - Sort HiSeq X Samples (HiSeq X)']

        For each output artifact (assumed not to be pooles) of the current process:
        walk throuh its history untill a stop_process is encountered. 
        Get its corresponding input artifact to the stop_process.
        Add to the hist_dict
            key:    output artifact of current process
            value:  input artifact of the stop process"""
    current_process = Process(lims, id = process_id)
    out_arts = [a for a in current_process.all_outputs() if a.type=='Analyte']
    hist_dict = {}
    for out_art in out_arts:
        sample = out_art.samples[0].name
        parent_process = out_art.parent_process
        while parent_process and parent_process.type.name not in stop_processes: 
            #We folow the sample history until it's parent process is the one we look for
            parent_inputs = parent_process.all_inputs()
            for parent_input in parent_inputs:
                sample_names = [s.name  for s in parent_input.samples]
                if sample in sample_names:
                    parent_process = parent_input.parent_process
                    break
        if not parent_process:
            # This will hapen if the sample did never pass throuh any of the stop_processes
            sys.exit('Sample ' + sample + ' did never pass through processes: '+ ', '.join(stop_processes))
        else:
            # Appends the in_art to the stop_process, that corresponds to the out_art of 
            # the current_process. Assumes a 1-1 relation.
            parent_inputs = parent_process.all_inputs()
            for parent_input in parent_inputs:
                sample_names = [s.name  for s in parent_input.samples]
                if sample in sample_names:
                    hist_dict[out_art] = parent_input
                    break
                    #   assumes only one in_art analyte per out_art analyte, to the stop_ptocess


    return hist_dict


def procHistory(proc, samplename):
    """Quick wat to get the ids of parent processes from the given process, 
    while staying in a sample scope"""
    hist=[]
    artifacts = lims.get_artifacts(sample_name = samplename, type = 'Analyte')
    not_done=True
    starting_art=proc.input_per_sample(samplename)[0].id
    while not_done:
        not_done=False
        for o in artifacts:
            if o.id == starting_art:
                if o.parent_process is None:
                    #flow control : if there is no parent process, we can stop iterating, we're done.
                    not_done=False
                    break #breaks the for artifacts, we are done anyway.
                else:
                    not_done=True #keep the loop running
                hist.append(o.parent_process)
                for i in o.parent_process.all_inputs():
                    if i in artifacts:
                        # while increment
                        starting_art=i.id
                        break #break the for allinputs, if we found the right one
                break # breaks the for artifacts if we matched the current one
    return hist

def main(lims, args):
    make_hist_dict(args.pid, args.proc)

if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                       help='Lims id for current Process')
    parser.add_argument('--proc', default=None, nargs='*',
                       help=('File name for qPCR result file.'))

    args = parser.parse_args()
    main(lims, args)


