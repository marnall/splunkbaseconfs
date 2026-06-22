#!/opt/splunk/bin/python
# Copyright 2014 (c) Helvetia Versicherungen, Switzerland
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>
# Output to XLS tool for Splunk
# note: this uses the code from below quoted sample on the internet, all original Copyright applies and is included.

from __future__ import absolute_import
__author__ = 'VTD'

# import Python Modules
import sys, datetime, getopt, os, splunk.Intersplunk, csv, re, time, calendar, xlwt, re, argparse, gzip, csv, splunk.mining.dcutils
from datetime import datetime
from six.moves.configparser import SafeConfigParser
from optparse import OptionParser
import codecs

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
import sys
 
import xlwt
import copy

from collections import deque #needed to quickly get the last line

sys.stdin = codecs.getreader('utf-8')(sys.stdin)

preview_flag = 7 # row number of the preview information
headersize = 10 # number of headerlines

try:
    results = csv.reader(sys.stdin)
    #tmp = results
    #results_row_count = sum(1 for row in tmp)
    #splunk.Intersplunk.generateErrorResults("count is : %s" % (results_row_count))
    #lastrun = open(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output + "_temp", "r")
    #lastrun_row_count = sum(1 for row in lastrun) # last_run = csv.reader(lastrun)
    #lastrun.close()

    #buffer = open(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output + "_temp", "a", 0)

except Exception as e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))
 
def csv_to_xls(output=None):
    if output is None:
        output = sys.stdout
    logger.info("parameters used: outputfile %s" % (output))
    int_re = re.compile(r'^\d+$')
    float_re = re.compile(r'^\d+\.\d+$')
    date_re = re.compile(r'^\d+-\d+-\d+|^\d+\/\d+\/\d+|^\d+\.\d+\.\d+')
    style = xlwt.XFStyle()

    workbook = xlwt.Workbook(encoding="UTF-8") #()
    sheet = workbook.add_sheet('one')

    row_num = 1

    for row in results:
        if row_num == preview_flag:
            if str(row).strip('[\']') == "preview:1": # need to improve this
                exit()
        if row_num >= headersize: #1:
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
                sheet.write(row_num - headersize, column_num, item, style) #sheet.write(row_num, column_num, unicode(item).encode("utf-8"), style)
                column_num += 1
        row_num += 1
        #return True
 
    workbook.save(output)
    return True #splunk.Intersplunk.generateErrorResults("lets go...")
 
 
if __name__ == '__main__':
    if len(sys.argv) < 2: # not enough parameters
        splunk.Intersplunk.generateErrorResults("Usage: outputxls [output.xls]")
        sys.exit(0)
    
    elif len(sys.argv) == 2: # only generate the xls file
        #print("only generate file...")
        output = None
        output = sys.argv[1]
        
        try:
            csv_to_xls(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output)

        except Exception as e:
            import traceback
            stack =  traceback.format_exc()
            splunk.Intersplunk.generateErrorResults("Error when generating a file only: Traceback: '%s'. %s" % (e, stack))

    elif len(sys.argv) > 2: #if we get more then one parameter we probably should send an email... erm...
        #print("send mail...")
        output = None
        output = sys.argv[1]

        try:
            csv_to_xls(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output)
            sender = sys.argv[2]
            receiver = sys.argv[3]
            subject = sys.argv[4]
            bodyText = sys.argv[5]
            smptHost = sys.argv[6]
            os.system(os.path.join(sys.path[0],"sendfile.py") + " '" + sender + "' '" + receiver + "' '" + subject + "' '" + bodyText + "' '" + output + "' '" + smptHost +"'")

        except Exception as e:
            import traceback
            stack =  traceback.format_exc()
            splunk.Intersplunk.generateErrorResults("Error when sending mail: Traceback: '%s'. %s" % (e, stack))
            exit()
"""
        try:
            sender = sys.argv[2]
            receiver = sys.argv[3]
            subject = sys.argv[4]
            bodyText = sys.argv[5]
            smptHost = sys.argv[6]
            #splunk.Intersplunk.generateErrorResults("sendfile.py '" + sender + "' '" + receiver + "' '" + subject + "' '" + bodyText + "' '" + output + "' '" + smptHost +"'")
            #splunk.Intersplunk.generateErrorResults(os.path.join(sys.path[0],"sendfile.py") + " '" + sender + "' '" + receiver + "' '" + subject + "' '" + bodyText + "' '" + output + "' '" + smptHost +"'")
            os.system(os.path.join(sys.path[0],"sendfile.py") + " '" + sender + "' '" + receiver + "' '" + subject + "' '" + bodyText + "' '" + output + "' '" + smptHost +"'")

        except Exception, e:
            import traceback
            stack =  traceback.format_exc()
            splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s - %s" % (e, stack, sys.argv))
"""