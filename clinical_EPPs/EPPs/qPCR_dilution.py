#!/usr/bin/env python

from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

from openpyxl import load_workbook
import json
from statistics import mean, median
import numpy
from clinical_EPPs.constants.well_transformer import WELL_TRANSFORMER
import pandas as pd
from pandas import ExcelWriter
from pandas import ExcelFile


import logging
import sys

DESC = """epp script to ...
    dilution_file   - qPCR Result file. Uploded by user.

Written by Maya Brandi, Science for Life Laboratory, Stockholm, Sweden
"""


class QpcrDilution():

    def __init__(self, process, log):
        self.log = log 
        self.process = process
        self.artifacts = {}
        self.passed_arts = 0
        self.failed_arts = 0
        self.dilution_data = {}
        self.removed_replicates = 0
        self.failed_samples = 0

    def get_artifacts(self):
        in_arts = self.process.all_inputs(unique=True)
        all_artifacts = self.process.all_outputs(unique=True)
        out_artifacts = [a for a in all_artifacts if a.output_type == "ResultFile"]
        for a in out_artifacts:
            samp = a.samples[0].id
            self.artifacts[samp] = a

    def get_file(self):
        try:
            for f in self.process.shared_result_files():
                if f.name =='qPCR Result File':
                    qPCR_file = f.files[0]
            return qPCR_file.content_location.split('scilifelab.se')[1]
        except:
            sys.exit('could not read dilutionfile')


    def make_dilution_data(self, dilution_file):
        """
        Reads the qPCR dilution Resultfile. 
        Uses WELL_TRANSFORMER to conect each well in the file to its original well.
        Stores the data from the qPCR file in a dict with original well as keyes."""
        dilution_file = self.get_file()
        df = pd.read_excel(dilution_file)
        for self.index, row in df.iterrows():
            well = row['Well']
            Cq = round(row['Cq'],3)
            SQ = row['SQ']
            if not (numpy.isnan(Cq) or numpy.isnan(SQ)):
                orwell = WELL_TRANSFORMER[well]['well']
                dilut = WELL_TRANSFORMER[well]['dilut']
                if dilut in ['1E03','2E03','1E04']:
                    if not orwell in list(self.dilution_data.keys()):
                        self.dilution_data[orwell] = {
                            'SQ' : {'1E03':[],'2E03':[],'1E04':[]},
                            'Cq' : {'1E03':[],'2E03':[],'1E04':[]}}
                    self.dilution_data[orwell]['SQ'][dilut].append(SQ)
                    self.dilution_data[orwell]['Cq'][dilut].append(Cq)

    def set_all_samples(self):
        """ For each sample:
            Checks dilution thresholds as described in am doc 1499.
            Calculates concentration and sets udfs for those samples that passed the check. """
        for samp_id, art in list(self.artifacts.items()):
            self.log.write('\n############################################\n')
            self.log.write('Sample: ' + samp_id + '\n')
            try:
                PA = PerArtifact(art, self.dilution_data, samp_id, self.log)
                PA.check_dilution_range()
                PA.check_distance_find_outlyer()
                for dil in list(PA.index.keys()):
                    ind = PA.index[dil]
                    if type(ind)==int:
                        self.removed_replicates += 1
                    if ind != 'Fail':
                        self.log.write(dil + ' Measurements : ' + str(PA.Cq[dil])+'\n')
                        if PA.poped_dilutes[dil]:
                            self.log.write('Removed measurement: ' + str(PA.poped_dilutes[dil]) + '\n')
                if PA.failed_sample:
                    self.failed_samples +=1
                else:
                    passed = PA.set_udfs()
                    if passed:
                        self.passed_arts +=1
                    else:
                        self.failed_arts +=1
            except:
                self.log.write('Could not make calculations for this sample. Some data might be missing in the dilution file.\n')
                self.failed_arts +=1

class PerArtifact():
    """Artifact specific class do determine messuement outlyers and calculate dilution.
    CHECK 1.
        Compares the Cq-values within each dilution for the sample.
        If they differ by more than 0.4 within the dilution:
            a)  The the Cq-value differing moste from the mean, is removed and 
                its index is stored in self.index.
            b)  If the two remaining Cq-values still differ by more than 0.4,
                The self.failed_sample is set to true
    CHECK 2.
        Compares the Cq-values between the different dilution series; 1E03, 2E03 and 1E04:
        If 0.7 >mean(2E03)-mean(1E03)> 1.5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(2E03)-2E03|)) 
                Its index is stored in self.index
        If 2.5 >mean(1E04)-mean(1E03)> 5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(1E04)-1E04|)) 
                Its index is stored in self.index
        This is repeated untill 0.7 <mean(2E03)-mean(1E03)< 1.5 and 2.5 <mean(1E04)-mean(1E03)< 5,
        or untill a dilution series contains only one value. If this hapens, self.failed_sample is set to true."""
    def __init__(self, artifact, dilution_data, sample_id, log):
        self.log = log
        self.sample_id = sample_id
        self.dilution_data = dilution_data
        self.artifact = artifact
        self.size_bp = 470
        self.outart = artifact
        self.well = self.outart.location[1]
        self.Cq = { '1E03' : self.dilution_data[self.well]['Cq']['1E03'], 
                    '2E03' : self.dilution_data[self.well]['Cq']['2E03'], 
                    '1E04' : self.dilution_data[self.well]['Cq']['1E04']}
        self.index = {'1E03' : None, '2E03' : None, '1E04' : None}
        self.poped_dilutes = {'1E03' : None, '2E03' : None, '1E04' : None}
        self.failed_sample = False

    def check_dilution_range(self):
        """CHECK 1.
        Compares the Cq-values within each dilution for the sample.
        If they differ by more than 0.4 within the dilution:
            a)  The the Cq-value differing moste from the mean, is removed and 
                its index is stored in self.index.
            b)  If the two remaining Cq-values still differ by more than 0.4,
                The self.failed_sample is set to true"""
        for dil, values in list(self.Cq.items()):
            error_msg = 'To vide range of values for dilution: ' + dil + ' : ' + str(values)
            array = numpy.array(self.Cq[dil])   
            diff_from_mean = numpy.absolute(array - mean(array))
            while max(self.Cq[dil])-min(self.Cq[dil])> 0.4:
                ind = self.index[dil]
                if type(ind)==int:
                    self.log.write(error_msg)
                    self.failed_sample = True
                    self.index[dil] = 'Fail'
                    return 
                else:
                    ind = numpy.argmax(diff_from_mean)
                    self.index[dil] = int(ind)
                    self.poped_dilutes[dil] = self.Cq[dil].pop(ind)
                    array = numpy.array(self.Cq[dil])
                    diff_from_mean = numpy.absolute(array - mean(array))


    def check_distance_find_outlyer(self):
        """CHECK 2.
        Compares the Cq-values between the different dilution series; 1E03, 2E03 and 1E04:

        If 0.7 >mean(2E03)-mean(1E03)> 1.5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(2E03)-2E03|)) 
                Its index is stored in self.index

        If 2.5 >mean(1E04)-mean(1E03)> 5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(1E04)-1E04|)) 
                Its index is stored in self.index

        This is repeated untill 0.7 <mean(2E03)-mean(1E03)< 1.5 and 2.5 <mean(1E04)-mean(1E03)< 5,
        or untill a dilution series contains only one value. If this hapens, self.failed_sample is set to true."""

        D1_in_range, D2_in_range = self._check_distance()
        while not (D1_in_range and D2_in_range):
            self._find_outlyer(D1_in_range, D2_in_range)
            if self.failed_sample:
                return
            for dilute, ind in list(self.index.items()):
                if type(ind)==int and len(self.Cq[dilute])==3:
                    self.poped_dilutes[dilute] = self.Cq[dilute].pop(ind) 
            D1_in_range, D2_in_range = self._check_distance()            



    def set_udfs(self):
        """ This will only happen if failed_sample is still False:
        1. For every outlyer stored in self.index, removes its coresponding SQ messuement.
        2. Calculates the zise adjusted concentraion based on the remaining SQ messuements.
        3. Sets the artifact udfs; Concentration, Concentration (nM) and Size (bp)"""

        for dilute, ind in list(self.index.items()):
            if type(ind)==int:
                self.dilution_data[self.well]['SQ'][dilute].pop(ind)
                # removing outlyer

        SQ_1E03 = mean(self.dilution_data[self.well]['SQ']['1E03'])
        SQ_2E03 = mean(self.dilution_data[self.well]['SQ']['2E03'])
        SQ_1E04 = mean(self.dilution_data[self.well]['SQ']['1E04'])
        orig_conc = (SQ_1E03*1000+SQ_2E03*2000+SQ_1E04*10000)/3
        size_adjust_conc_M = orig_conc*(452/self.size_bp)
        size_adjust_conc_nM= size_adjust_conc_M*1000000000

        try:
            self.outart.udf['Concentration'] = size_adjust_conc_M
            self.outart.udf['Size (bp)'] = int(self.size_bp)
            self.outart.udf['Concentration (nM)'] = size_adjust_conc_nM
            if self.outart.udf['Concentration (nM)'] < 2:
                self.outart.qc_flag = "FAILED"
            else:
                self.outart.qc_flag = "PASSED"
            self.outart.put()
            return True
        except:
            return False


    def _error_log_msg(self, dil):
        """Log for failed sample"""
        self.log.write(dil + ' Measurements : ' + str(self.Cq[dil]) + '\n')
        self.log.write('Removed measurement: ' + str(self.poped_dilutes[dil]) + '\n')
        self.log.write('One outlyer removed, but distance still to big. \n\n')


    def _check_distance(self):
        """Compares the difference between the mean of the triplicates for the different dilutions. 
        Checkes wether the differences are within accepted ranges:
        0.7 <mean(2E03)-mean(1E03)< 1.5 and 2.5 <mean(1E04)-mean(1E03)< 5"""
        D1 = mean(self.Cq['1E04'])-mean(self.Cq['1E03'])
        D1_in_range = 2.5 < D1 < 5
        D2 = mean(self.Cq['2E03'])-mean(self.Cq['1E03'])   
        D2_in_range = 0.7 < D2 < 1.5
        return D1_in_range, D2_in_range

    def _find_outlyer(self, D1_in_range, D2_in_range):
        """        
        If 0.7 >mean(2E03)-mean(1E03)> 1.5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(2E03)-2E03|)) 
                Its index is stored in self.index

        If 2.5 >mean(1E04)-mean(1E03)> 5:
            The bigest outlyer from the two series are compared and the bigest one, removed:
                max(max(|mean(1E03)-1E03|), max(|mean(1E04)-1E04|)) 
                Its index is stored in self.index"""

        control_1E03 = False
        if not D1_in_range:
            array = numpy.array(self.Cq['1E03'])
            diff_from_mean_1E03 = numpy.absolute(array - mean(array))
            outlyer_1E03 = max(diff_from_mean_1E03)
            array = numpy.array(self.Cq['1E04'])
            diff_from_mean_1E04 = numpy.absolute(array - mean(array)) 
            outlyer_1E04 = max(diff_from_mean_1E04)
            if outlyer_1E03 > outlyer_1E04:
                ind = self.index['1E03']
                if type(ind)==int:
                    self._error_log_msg('1E03')
                    self.failed_sample = True
                    self.index['1E03'] = 'Fail'
                    return 
                else:
                    control_1E03 = True
                    self.index['1E03'] = int(numpy.argmax(diff_from_mean_1E03))
            else:
                ind = self.index['1E04']
                if type(ind)==int:
                    self._error_log_msg('1E04')
                    self.failed_sample = True
                    self.index['1E04'] = 'Fail'
                    return 
                else:
                    self.index['1E04'] = int(numpy.argmax(diff_from_mean_1E04))
        if not D2_in_range:
            array = numpy.array(self.Cq['2E03'])
            diff_from_mean_2E03 = numpy.absolute(array - numpy.median(array))/numpy.median(array).tolist()
            outlyer_2E03 = max(diff_from_mean_2E03)
            array = numpy.array(self.Cq['1E03'])
            diff_from_mean_1E03 = numpy.absolute(array - numpy.median(array))/numpy.median(array).tolist()
            outlyer_1E03 = max(diff_from_mean_1E03)
            if outlyer_2E03 > outlyer_1E03:
                ind = self.index['2E03']
                if type(ind)==int:
                    self._error_log_msg('2E03')
                    self.failed_sample = True
                    self.index['2E03'] = 'Fail'
                    return 
                else:
                    self.index['2E03'] = int(numpy.argmax(diff_from_mean_2E03))
            else:
                if self.index['1E03']:
                    if control_1E03 and self.index['1E03'] != numpy.argmax(outlyer_1E03):
                        self.log.write('Distance to big. Conflicting outlyers. ')
                        self.failed_sample = True
                        self.index['1E03'] = 'Fail'
                        return 
                    elif not control_1E03:
                        self._error_log_msg('1E03')
                        self.failed_sample = True
                        self.index['1E03'] = 'Fail'
                        return 
                else:
                    self.index['1E03'] = int(numpy.argmax(diff_from_mean_1E03))


def main(lims, args):
    log = open(args.log, 'a')
    process = Process(lims, id = args.pid)
    QD = QpcrDilution(process, log)
    QD.get_artifacts()
    QD.make_dilution_data(args.dil_file)
    QD.set_all_samples()

    d = {'ca': QD.passed_arts,
         'ia': QD.failed_arts}
    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)
   
    if QD.removed_replicates:
        abstract += ' WARNING: Removed replicate from ' +str(QD.removed_replicates)+ ' samples. See log file for details.'  

    if QD.failed_samples:
        abstract += ' WARNING: Failed to set udfs on '+ str(QD.failed_samples)+' samples, due to unstable dilution messurements'
 
    log.close()
    if QD.failed_arts or QD.failed_samples:
        sys.exit(abstract)
    else:
        print(abstract, file=sys.stderr)

if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                       help='Lims id for current Process')
    parser.add_argument('--log', default=sys.stdout,
                       help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--dil_file', default=None,
                       help=('File name for qPCR result file.'))

    args = parser.parse_args()
    if not args.dil_file:
        sys.exit('Dilution File missing!')

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    main(lims, args)
