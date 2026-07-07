#!/opt/splunk/bin/python
# Copyright 2015 (c) Helvetia Versicherungen, Switzerland
# Author: Dominique Vocat <dominique.vocat@helvetia.ch>
# Remove file o /var/run/splunk tool for Splunk
# note: we do no hard checking and this is a potential loophole for now...

__author__ = 'VTD'

# import Python Modules
import sys, datetime, getopt, os, splunk.Intersplunk
from ConfigParser import SafeConfigParser
from optparse import OptionParser

parm = sys.argv[1]
if not parm.endswith(('.csv','.xls')):
    splunk.Intersplunk.generateErrorResults("Error : only allowed legal file extensions are .csv or .xls: '%s'." % parm)
    exit()

try:
    os.remove(os.environ['SPLUNK_HOME'] + "/var/run/splunk/" + parm)
except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))