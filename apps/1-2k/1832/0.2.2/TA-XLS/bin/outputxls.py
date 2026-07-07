#!/opt/splunk/bin/python
# Copyright 2014 (c) Helvetia Versicherungen, Switzerland
# Coypright 2020 (c) Bob van Bussel
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>, Bob Van Bussel <bob.vanbussel@concanon.com>
# Output to XLS tool for Splunk
# note: this uses the code from below quoted sample on the internet, all original Copyright applies and is included.

__author__ = 'VTD'

import sys, datetime, getopt, os, splunk.Intersplunk, csv, re, time, calendar, re, argparse, gzip, csv, splunk.mining.dcutils
import xlsxwriter
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
 
import xlsxwriter
import copy
import os
import subprocess

from collections import deque #needed to quickly get the last line

sys.stdin = codecs.getreader('utf-8')(sys.stdin)

preview_flag = 7 # row number of the preview information
headersize = 10 # number of headerlines

try:
    results = csv.reader(sys.stdin)

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

    #workbook = xlwt.Workbook(encoding="UTF-8") #()
    workbook = xlsxwriter.Workbook(output,{'strings_to_numbers':  True}) #()

    sheet = workbook.add_worksheet('Sheet1')
    sheet.set_column('A:A', 20)
    row_num = 1
    for row in results:
        if row_num == preview_flag:
            if str(row).strip('[\']') == "preview:1": # need to improve this
                exit()
        if row_num >= headersize + 4: #1:
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
                sheet.write(row_num - headersize - 4, column_num, item) #sheet.write(row_num, column_num, unicode(item).encode("utf-8"), style)
                column_num += 1
        row_num += 1
    workbook.close()
    return True #splunk.Intersplunk.generateErrorResults("lets go...")
 
 
if __name__ == '__main__':
    if len(sys.argv) < 2: # not enough parameters
        splunk.Intersplunk.generateErrorResults("Usage: outputxls [output.xls]")
        sys.exit(0)
    
    elif len(sys.argv) == 2: # only generate the xls file
        output = None
        output = sys.argv[1]
        
        try:
            csv_to_xls(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output)

        except Exception as e:
            import traceback
            stack =  traceback.format_exc()
            splunk.Intersplunk.generateErrorResults("Error when generating a file only: Traceback: '%s'. %s" % (e, stack))
"""
    elif len(sys.argv) > 2: #if we get more then one parameter we probably should send an email... erm...
        #print("send mail...")
        output = None
        output = sys.argv[1]

        try:
            csv_to_xls(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output)
            #attachment_name= os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + output
            sender = sys.argv[2]
            receiver = sys.argv[3]
            smtpHost = sys.argv[4]
            use_tls = sys.argv[5]
            use_ssl = sys.argv[6]
            subject = sys.argv[7]
            bodyText = sys.argv[8]
            #username = sys.argv[7] # use "" if no SMTP authentication is required
            #passwd = sys.argv[8] # ignored if no SMTP authentication is required
            #port = sys.argv[9]
            sendresults = sys.argv[9]
            inline = sys.argv[10]
            raw = sys.argv[11]
            sendxlsx = sys.argv[12]
            attachment_name= output 
            #os.system(os.path.join(sys.path[0],"sendfile.py") + " '" + sender + "' '" + receiver + "' '" + subject + "' '" + bodyText + "' '" + output + "' '" + smptHost + "' '" + username + "' '" + passwd + "' '" + port + "'")
            #splunk.Intersplunk.generateErrorResults(os.system('/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py " from="' + sender + '" to="' + receiver + '" server="' + smtpHost + '" use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject="' + subject + '" message="' + bodyText + '" sendresults=' + sendresults + ' inline=' + inline + ' format=' + raw + ' attachment_name="' + attachment_name + '" sendxlsx=' + sendxlsx + '"'))
            #splunk.Intersplunk.generateErrorResults(os.system('"/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py' + ' from="' + sender + '" to="' + receiver + '" server="' + smtpHost + '" use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject="' + subject + '" message="' + bodyText + '" sendresults=' + sendresults + ' format="' + raw + '" attachment_name="' + attachment_name + '" sendxlsx="' + sendxlsx + '"'))
            #splunk.Intersplunk.generateErrorResults(os.system('"/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py' + ' from="' + sender + '" to="' + receiver + '" server="' + smtpHost + '" use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject="' + subject + '" message="' + bodyText + '" sendresults=' + sendresults + ' format="' + raw + '" attachment_name="' + attachment_name + '" sendxlsx="' + sendxlsx + '"'))
            #os.system('/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py' + ' from="' + sender + '" to="' + receiver + '" server="' + smtpHost + '" use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject="' + subject + '" message="' + bodyText + '" sendresults=' + sendresults + ' format=' + raw + ' attachment_name="' + attachment_name + '" sendxlsx=' + sendxlsx + '"')
            #os.system("/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py" + " 'from='" + sender + "' to='" + receiver + "' server='" + smtpHost + "' use_tls=" + use_tls + " use_ssl=" + use_ssl + " subject='" + subject + "' message='" + bodyText + "' sendresults=" + sendresults + " format='" + raw + "' attachment_name='" + attachment_name + "' sendxlsx=" + sendxlsx + "'")
            #os.system('/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py' + ' from="' + sender + '" to="' + receiver + '" server="' + smtpHost + '" use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject="' + subject + '" message="' + bodyText + '" sendresults=' + sendresults + ' inline=' + inline + ' format=' + raw + ' attachment_name="' + attachment_name + '" sendxlsx=' + sendxlsx + '"')
            #os.system("/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py from='" + sender + "' to='" + receiver + "' server='" + smtpHost + "' use_tls=" + use_tls + " use_ssl=" + use_ssl + " subject='" + subject + "' message='" + bodyText + "' sendresults=" + sendresults + " inline=" + inline + " format=" + raw + " attachment_name='" + attachment_name + "' sendxlsx=" + sendxlsx + '"')
            #splunk.Intersplunk.generateErrorResults(os.system("'/opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py" + ' from=' + sender + ' to=' + receiver + ' server=' + smtpHost + ' use_tls=' + use_tls + ' use_ssl=' + use_ssl + ' subject=' + subject + ' message=' + bodyText + ' sendresults=' + sendresults + ' format=' + raw + ' attachment_name=' + attachment_name + ' sendxlsx=' + sendxlsx + "'"))
            #cmd = "'/opt/splunk/bin/python /opt/splunk/etc/apps/TA-XLS/bin/sendemailcustom.py from='" + sender + "' to='" + receiver + "' server='" + smtpHost + "' use_tls=" + use_tls + " use_ssl=" + use_ssl + " subject='" + subject + "' message='" + bodyText + "' sendresults=" + sendresults + " format=" + raw + " attachment_name='" + attachment_name + "' sendxlsx=" + sendxlsx + "'"
            #subprocess.call(cmd, shell=True)

        except Exception as e:
            import traceback
            stack =  traceback.format_exc()
            splunk.Intersplunk.generateErrorResults("Error when sending mail: Traceback: '%s'. %s" % (e, stack))
            exit()
"""
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