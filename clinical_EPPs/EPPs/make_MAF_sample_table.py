#!/usr/bin/env python
from argparse import ArgumentParser
import pandas as pd

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process

import logging
import sys
import os



DESC = """EPP script to generate MAFF sample info excel sheet

Written by Maya Brandi, Clinical Genomics, Stockholm, Sweden"""


class MAF2CSV():
    def __init__(self, process, MAF_file):
        self.process = process
        self.in_analytes = [a for a in process.all_inputs() if a.type=='Analyte']
        self.out_analytes = [a for a in process.all_outputs() if a.type=='Analyte']
        plate_name = self.out_analytes[0].container.name
        self.MAF_file = MAF_file + '_Sample_information_MAF_' + str(plate_name) + '.xlsx'
        self.headers = []
        self.comments = {}
        self.data = {}
        self.gender_fail = []
        self.final_volume_fail = []

    def make_csv(self):
        i= 0
        for analyte in self.out_analytes:
            i += 1
            sample = analyte.samples[0]
                    
            self.data['U_CUSTOMER_SAMPLE_ID'].append('CG-' + str(sample.id)) 
            self.data['U_SPECIES'].append('Human')
            self.data['SAMPLE_TYPE'].append(1)
            self.data['U_DNA_RNA_TYPE'].append(1)
            self.data['U_SAMPLE_CONCENTRATION'].append(4)
            self.data['U_CONC_MEASURE_METHOD'].append('Qubit')            
            self.data['U_SAMPLE_SOURCE_NAME'].append('Blood')

            try:
                if not sample.udf['Gender']=='unknown':
                    self.data['U_SEX'].append(sample.udf['Gender'])
            except:
                self.gender_fail.append(sample.id)
            try:
                self.data['U_SAMPLE_VOLUME'].append(analyte.udf['Final Volume (uL)'])
            except:
                self.final_volume_fail.append(sample.id)

            ## append empty value to the rest of the collumns
            for header in self.headers:
                if len(self.data[header]) != i:
                    self.data[header].append('')

        df = pd.DataFrame(self.data) 
        df = df[self.headers]
        writer = pd.ExcelWriter(self.MAF_file, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Sample information', index=False, startcol=0)
        worksheet = writer.sheets['Sample information']
        worksheet.set_column('A:T', 10)
        for cell, comment in self.comments.items():
            worksheet.write_comment(cell, comment)
        writer.save()


    def set_header_section(self):
        self.headers = ['U_CUSTOMER_SAMPLE_ID', 'U_SPECIES', 'SAMPLE_TYPE',
            'U_SAMPLE_SOURCE_NAME', 'U_DNA_RNA_TYPE', 'U_DNA_EXTRACTION_METHOD',
            'U_SEX', 'U_SAMPLE_VOLUME', 'U_SAMPLE_CONCENTRATION', 'U_260_230_RATIO',
            'U_260_280_RATIO', 'U_SAMPLE_AMOUNT', 'U_CONC_MEASURE_METHOD',
            'U_AFFECTION_STATUS', 'U_FAMILY_ID_TXT', 'U_FATHER_ID_TXT',
            'U_MOTHER_ID_TXT', 'U_TWIN_PAIR', 'U_DONOR_ID', 'U_TWINNR']
        self.data = {key : [] for key in self.headers}
        self.comments = {'F1': '\nExtraction method or kit (max 50 letters). For example:\n\nSDS\nQIAmp\nOragene\nChemagen', 'R1': 'For zygosity analysis', 'G1': '\nM = Male\nF = Female', 'I1': 'For liquid samples [ng/ul]\n\nA comma (,) is used as the decimal separator!', 'S1': 'For example:\nCustomer Study Donor Id for zygosity analysis', 'H1': '\nFor liquid samples [ ul ]\n\nA comma (,) is used as the decimal separator!', 'J1': '\nPurity (260/230)\n\nA comma (,) is used as the decimal separator!', 'T1': '\nTwin individual number, for zygosity analysis', 'K1': '\nPurity (260/280)\n\nA comma (,) is used as the decimal separator!', 'M1': 'Spec = Spectrophotometric\nPico = Picogreen\nNano = Nanodrop\nQubit = Qubit\n\netc.', 'B1': 'For example: Human, mouse, rat and so forth. ', 'L1': '\nFor dry samples [ng]\n\nA comma (,) is used as the decimal separator!', 'N1': '\n0 = Not known\n1 = Control/Not affected\n2 = Case/Affected', 'C1': '\n1 = Individual\n2 = Pool sample\n6 = Virtual individual\n9 = Positive control\n10 = Negative control', 'E1': '\n1 = Genomic DNA\n2 = mtDNA\n3 = cDNA\n4 = ssDNA\n5 = mRNA\n6 = Total RNA\n7 = wga DNA\n8 = Biotinylated DNA\n9 = Bisulfite treated DNA\n10= miRNA', 'D1': '\nBlood\nTissue\nCultured cells\nSaliva\nFilterpaperSpot\nBuccal swabs'}




def main(lims, args):
    process = Process(lims, id = args.pid)
    M2CSV = MAF2CSV(process, args.MAF_file)
    M2CSV.set_header_section()
    M2CSV.make_csv()
    abstract = ''
    if M2CSV.gender_fail:
        abstract += 'Gender udf missing for samples: '+', '.join(M2CSV.gender_fail) + '. '
    if M2CSV.final_volume_fail:
        abstract += 'Final Volume udf missing for samples: '+ ', '.join(M2CSV.final_volume_fail)
    
    if abstract:
        logging.warning(abstract)
        sys.exit(abstract)
    else:
        print >> sys.stderr, 'MAF xlsx file was succsessfully generated!'

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-l', dest = 'log', default=sys.stdout,
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('-f', dest = 'MAF_file',
                        help=('File path to new MAF-xlsx file'))    
                        
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()
    logging.basicConfig(
                    level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename = args.log,
                    filemode='w')

    main(lims, args)
