#!/opt/splunk/bin/python
# Copyright 2014 (c) Helvetia Versicherungen, Switzerland
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>
# XLS(X) to CSV tool for Splunk
# note: this uses the code from below quoted sample on the internet, all original Copyright applies and is included.
# from http://stackoverflow.com/questions/9884353/xls-to-csv-convertor by http://stackoverflow.com/users/953553/andi

__author__ = 'VTD'

# import Python Modules
import sys, datetime, getopt, os, splunk.Intersplunk, csv, re, time, calendar, xlrd, re, argparse, gzip, csv, splunk.mining.dcutils
from datetime import datetime
from six.moves.configparser import SafeConfigParser
from optparse import OptionParser
from io import open
import six
from six.moves import range

logger = splunk.mining.dcutils.getLogger()


# -*- coding: utf-8 -*-
from os import sys

def csv_from_excel(excel_file,csv_file,sheetnr):
    workbook = xlrd.open_workbook(excel_file)
    #all_worksheets = workbook.sheet_names()
    #for worksheet_name in all_worksheets:
        #worksheet = workbook.sheet_by_name(worksheet_name)
        #your_csv_file = open(''.join([os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/",worksheet_name,'.csv']), 'wb')

    worksheet = workbook.sheet_by_index(int(sheetnr))
    your_csv_file = open(csv_file, 'wb')
    wr = csv.writer(your_csv_file, quoting=csv.QUOTE_ALL)

    for rownum in range(worksheet.nrows):
        wr.writerow([six.text_type(entry).encode("utf-8") for entry in worksheet.row_values(rownum)])
    your_csv_file.close()

if __name__ == "__main__":
    csv_from_excel(os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/" + sys.argv[1], os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/" + sys.argv[3], sys.argv[2])
