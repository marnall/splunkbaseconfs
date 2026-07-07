#!/opt/splunk/bin/python
# Copyright 2014/2020 (c) Helvetia Versicherungen, Switzerland
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>
# CSV to XLS tool for Splunk
# note: this uses the code from below quoted sample on the internet, all original Copyright applies and is included.
from __future__ import print_function
__author__ = 'VTD'

# import Python Modules
import sys, datetime, getopt, os, splunk.Intersplunk, csv, re, time, calendar, xlwt, re, argparse, gzip, csv, splunk.mining.dcutils
from datetime import datetime
from six.moves.configparser import SafeConfigParser
from optparse import OptionParser

logger = splunk.mining.dcutils.getLogger()

"""
Converts the specified CSV file to XLS using xlwt.
 
 
Copyright 2012 Kevin Richardson
 
Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:
 
The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
"""
import csv
import re
import codecs
import sys
#workarround for utf8 encoded strings resulting in a exception (cp00vtd 13.07.2012)
reload(sys)
sys.setdefaultencoding("utf-8")
 
import xlwt
 
 
def csv_to_xls(csv_filename, output=None):
    if output is None:
        output = sys.stdout
    logger.info("parameters used: inputfile %s" % (csv_filename))
    logger.info("parameters used: outputfile %s" % (output))
    int_re = re.compile(r'^\d+$')
    float_re = re.compile(r'^\d+\.\d+$')
    date_re = re.compile(r'^\d+-\d+-\d+$')
    style = xlwt.XFStyle()

    # modified in 0.1.1 added codecs.open(csv_filename, 'U', encoding='utf-8') instead of open(csv_filename, 'rb') 
    with codecs.open(csv_filename, 'U', encoding='utf-8') as csv_file:
        # modified in 0.1.1, .Workbook() -> -Workbook(encoding="utf-8")
        workbook = xlwt.Workbook(encoding="utf-8")
        sheet = workbook.add_sheet('one')

        reader = csv.reader(csv_file)
        row_num = 0
        for row in reader:
            column_num = 0
            for item in row:
                format = 'general'
                if re.match(date_re, item):
                    format = 'M/D/YY'
                elif re.match(float_re, item):
                    item = float(item)
                    format = '0.00'
                elif re.match(int_re, item):
                    item = float(item)
                    format = '0'
                style.num_format_str = format
                sheet.write(row_num, column_num, item, style)
                column_num += 1
            row_num += 1
 
        workbook.save(output)
 
 
if __name__ == '__main__':
    logger.info("xsv2xls.py is run...")
    if len(sys.argv) < 2:
        print( 'Usage: csv2xls.py input.csv [output.xls]')
        logger.info("Usage: csv2xls input.csv [output.xls]")
        sys.exit(0)
    
    output = None
    if len(sys.argv) == 3:
        output = sys.argv[2]
        
    #csv_to_xls(os.environ['SPLUNK_HOME'] + "/etc/apps/TA-XLS/lookups/" + sys.argv[1], os.environ['SPLUNK_HOME'] + "/etc/apps/TA-XLS/lookups/" + output)
    csv_to_xls(os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/" + sys.argv[1], os.environ['SPLUNK_HOME'] + "/var/run/splunk/csv/" + output)

