#!/usr/bin/env python
import os
import sys
import logging

import xlsxwriter
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from clinicaladmin.database import db, app, ApplicationDetails, ApplicationTagData, MethodDescription, Customers, Invoice
from clinical_EPPs.invoice_templates import InvoiceTemplate

from datetime import date


DESC = """"""

class GetLimsData():
    def __init__(self, process, split):
        self.process = process
        self.discount = float(process.udf['Discount (%)'])
        self.invoicer_name = None
        self.invoicer = None
        self.client = None
        self.final_client = None
        self.samples = []
        self.passed_arts = []
        self.failed_arts = []
        self.failed_samps = 0
        self.sample_info = {}
        self.process_info = {}
        self.from_info = []
        self.to_info = []
        self.comment = []
        self.invoice_ref = ''
        self.split = split
        self.abstract = ''    

    def set_invoicer_and_client(self, invoicer, client):
        self.invoicer_name = invoicer
        if invoicer == 'KTH':
            self.invoicer = 'cust000'
        elif invoicer == 'KI':
            self.invoicer = 'cust999'
        else:
            sys.exit('invoicer must be KTH ore KI!')
        if not client in ['KI', 'cust']:
            sys.exit('client must be KI ore cust')
        if client == 'KI':
            self.client = 'cust999'
        try:
            self.final_client = self.client = self.process.all_outputs()[0].samples[0].udf['customer']
            if client == 'cust':
                self.client = self.final_client 
        except:
            sys.exit('Could not find customer id')


    def get_price(self, app_tag, priority, version):
        ## getting price from admin database
        app_tag = ApplicationDetails.query.filter_by(application_tag = app_tag, version = version).first()
        price = float(app_tag.__dict__[priority + '_price'])
        if self.discount > 0:
            price = price * (100 - self.discount) /100.0
        if self.split and self.invoicer_name == 'KTH':
            price = price*float(app_tag.percent_charged_to_kth.rstrip('%'))*0.01
        elif self.split and self.invoicer_name == 'KI':
            price = price*(1 - float(app_tag.percent_charged_to_kth.rstrip('%'))*0.01 )
        return price

    def _get_sample_udfs(self, samp):
        ##GETTING LIMS SAMPLE UDFS
        try:
            udfs = {'app_tag' : samp.udf['Sequencing Analysis'],
                    'priority' : samp.udf['priority'],
                    'version' : samp.udf['Application Tag Version']}
            return udfs
        except:
            self.failed_samps +=1
            return None

    def format_sample_info(self):
        artifacts = self.process.all_inputs(unique=True)
        for a in artifacts:
            self.samples+=a.samples
        self.samples = list(set(self.samples))
        for samp in self.samples:
            s_id = samp.id
            self.sample_info[s_id] = {'Prov':'',
                        'Clinical Genomics ID':'',
                        'Analys':'',
                        'Order ID':'',
                        'Kommentar':'',
                        'Pris':''}
            udfs = self._get_sample_udfs(samp)
            if udfs:    
                price = self.get_price(udfs['app_tag'], udfs['priority'], udfs['version'])
                self.sample_info[s_id]['Analys'] = udfs['app_tag']
                self.sample_info[s_id]['Pris'] = price
            self.sample_info[s_id]['Prov'] = samp.name
            self.sample_info[s_id]['Clinical Genomics ID'] = samp.id
            self.sample_info[s_id]['Kommentar'] = samp.date_received
            self.sample_info[s_id]['Order ID'] = samp.project.name


    def format_from_info(self):
        admin_db_data = Customers.query.filter_by(customer_number = self.invoicer).first()
        if self.invoicer == 'cust000': 
            self.from_info.append(('Enhet','Clinical Genomics'))
            self.from_info.append(('Projektnummer', admin_db_data.clinical_genomics_project_account_KTH))
        elif self.invoicer == 'cust999':  
            self.from_info.append(('Enhet','Karolinska Institutet')) 
            self.from_info.append(('Projektnummer', admin_db_data.clinical_genomics_project_account_KI))
        else:
            sys.exit('Error: Expected invoicer to be cust000 or cust999')
        self.from_info.append(('Kontaktperson', admin_db_data.invoicing_contact_person))
        self.from_info.append(('E-post', admin_db_data.invoicing_email))
        self.from_info.append(('Telefon', '??'))

    def format_to_info(self):
        admin_db_data = Customers.query.filter_by(customer_number = self.client).first()
        self.to_info = [('Kontaktperson', admin_db_data.invoicing_contact_person),
                    ('E-post',admin_db_data.invoicing_email),
                    ('Referens', admin_db_data.invoicing_reference),
                    ('Namn',admin_db_data.customer_name),
                    ('Fakturaadress', admin_db_data.invoicing_address)]

    def format_comments(self):
        admin_db_data = Customers.query.filter_by(customer_number = self.client).first()
        self.comment = [('Avtaltets diarienummer', admin_db_data.agreement_diarie_number),
                        ('Avser analyser under perioden', 'last invoice date - ' + str(date.today()))] 

    def format_invoice_ref(self):
        old_invoices = Invoice.query.filter_by(customer = self.final_client).all()
        new_inv_nr = 0 
        for inv in old_invoices:
            inv_nr = inv.invoice_id.split('_')[1]
            if int(inv_nr) > new_inv_nr:
                new_inv_nr = int(inv_nr) 
        new_inv_nr = str(new_inv_nr + 1)
        if len(new_inv_nr)==1:
            new_inv_nr = '0' + new_inv_nr
        self.invoice_ref = '_'.join([self.final_client.replace('cust',''), str(new_inv_nr), self.invoicer_name])
        if new_inv_nr == '01':
            self.abstract += 'Could not find old invoice in the admin database. Invoice nr is set to 01. '


def main(lims, args):
    process = Process(lims, id = args.pid)
    GLD = GetLimsData(process, args.split)
    GLD.set_invoicer_and_client(args.invoicer, args.client)
    GLD.format_sample_info()
    GLD.format_from_info()
    GLD.format_to_info()
    GLD.format_comments()
    GLD.format_invoice_ref()
    
    filep = args.file +'_'+GLD.invoice_ref + '.xlsx'
    workbook = xlsxwriter.Workbook(filep)

    IT = InvoiceTemplate(workbook)
    IT.make_heading_section(args.invoicer, GLD.invoice_ref)
    IT.make_from_section(GLD.from_info)
    IT.make_to_section(GLD.to_info)
    IT.make_comments_section(GLD.comment)
    IT.make_samples_section(GLD.sample_info)
    workbook.close()
 
    if GLD.failed_samps:
        sys.exit('Could not generate complete invoice. Some requiered sample udfs are missing. Requiered udfs are : "Sequencing Analysis", "priority" and "Application Tag Version"')
    if not GLD.abstract:
        GLD.abstract = 'Invoice generated successfully! '
    if GLD.discount:
        GLD.abstract += "Discount: "+str(GLD.discount)+"%."
    print >> sys.stderr, GLD.abstract


if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('-p', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('-f', dest = 'file',
                        help=('File path to new invoice file'))
    parser.add_argument('-i', dest = 'invoicer',
                        help=('KTH ore KI'))
    parser.add_argument('-c', dest = 'client',
                        help=('KI ore cust'))
    parser.add_argument('-s', dest = 'split', action='store_true',
                        help=('Split invoice'))

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    main(lims, args)

