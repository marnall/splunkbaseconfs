#!/usr/bin/env python
__author__ = 'Michael Uschmann / MuS'
__date__ = '$Sep 4, 2015 10:48:46 AM$'
__version__ = '4.0.0'
__copyright__ = '2015 Michael Uschmann ALL RIGHTS RESERVED'


# enable / disable logger debug output
myDebug='no' # debug disabled
#myDebug='yes' # debug enabled

# import only basic modules and do some stuff before we start
import sys
import os
import logging
import logging.handlers
import splunk.Intersplunk
import datetime
import getopt
import csv
import re
import collections
import base64
import inspect
from os import path
from sys import modules, path as sys_path, stderr
from datetime import datetime
from ConfigParser import SafeConfigParser
from optparse import OptionParser

""" get SPLUNK_HOME form OS """
SPLUNK_HOME = os.environ['SPLUNK_HOME']

""" get myScript name and path """
myScript = os.path.basename(__file__)
myPath = os.path.dirname(os.path.realpath(__file__))

""" import additional modules """
import pyasn1
import ldap3
from ldap3 import ALL

# define the logger to write into log file
def setup_logging(n):
    logger = logging.getLogger(n)
    if myDebug == 'yes':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.ERROR)
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = '%s.log' % myScript
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

# start the logger for troubleshooting
if myDebug == 'yes': logger = setup_logging( 'Logger started ...' ) # logger

# some other def Fu
def myStart(): # calulate start time of script
    global t1
    t1 = datetime.now();
    return t1;

def myStop(): # calulate stop time of script
    global t2
    t2 = datetime.now();
    return t2;

def myTime(): # calulate duration time of test
    c = t2 - t1;
    itTook = (c.days * 24 * 60 * 60 + c.seconds) * 1000 + c.microseconds / 1000.0;
    return itTook;

# set empty lists
result_set = []
results = []

# starting the main
if myDebug == 'yes': logger.info( 'Starting the main task ...' ) # logger

# get previous search results from Splunk
try: # lets do it
    if myDebug == 'yes': logger.info( 'getting previous search results...' ) # logger
    myresults,dummyresults,settings = splunk.Intersplunk.getOrganizedResults() # getting search results form Splunk
    for r in myresults: # loop the results
        for k, v in r.items(): # get key value pairs for each result
            if k == 'server': # get key
                section_name = v # set value
            if k == 'port': # get key
                port = v # set value
            if k == 'scope': # get key
                scope = v # set value
                if myDebug == 'yes': logger.info( 'scope= %s  ' % scope ) # logger
            if k == 'ldap_filter': # get key
                ldap_filter = v # set value
                if myDebug == 'yes': logger.info( 'ldap_filter= %s  ' % ldap_filter ) # logger
            if k == 'basedn': # get key
                basedn = v # set value
            if k == 'timeout': # get key
                timeout = v # set value
            if k == 'sizelimit': # get key
                sizelimit = v # set value
            if k == 'attrs': # get key
                attrs = v # set value
            if k == 'fetch': # get key
                fetch = v # set value
            if k == 'response': # get key
                ldap_response = v # set value

except: # get error back
    if myDebug == 'yes': logger.info( 'INFO: no previous search results provided using [default]!' ) # logger

# or get user provided options in Splunk as keyword, option
try: # lets do it
    if myDebug == 'yes': logger.info( 'getting Splunk options...' ) # logger
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions() # get key value pairs from user search
    section_name = options.get('server','default') # get user option or use a default value
    section_name = 'myLDAP://%s' % section_name
    if myDebug == 'yes': logger.info( 'stanza name is : %s ...' % section_name) # logger
    port = options.get('port','389') # get user option or use a default value
    scope = options.get('scope','sub') # get user option or use a default value
    if myDebug == 'yes': logger.info( 'scope= %s  ' % scope ) # logger
    #ldap_filter = options.get('ldap_filter','0') # get user option or use a default value
    #if myDebug == 'yes': logger.info( 'ldap_filter= %s  ' % ldap_filter ) # logger
    basedn = options.get('basedn','basedn') # get user option or use a default value
    timeout = options.get('timeout','30') # get user option or use a default value
    sizelimit = options.get('sizelimit','10') # get user option or use a default value
    attrs = options.get('attrs','all') # get user option or use a default value
    fetch = options.get('fetch','nofetch') # get user option or use a default value
    ldap_response = options.get('response','no') # get user option or use a default value

except: # get error back
    if myDebug == 'yes': logger.info( 'INFO: no option provided using [default]!' ) # logger

# special one for LDAP filter option
try: # lets do it
    parser = OptionParser(usage="usage: %prog [options] filename", version="%prog 1.0")
    parser.add_option("-f", "--filter", action="store", dest="ldap_filter", default="(objectclass=*)", help="specify LDAP scope to be used in search")
    (options, args) = parser.parse_args()
    ldap_filter = options.ldap_filter
    if myDebug == 'yes': logger.info( 'ldap_filter= %s  ' % options.ldap_filter ) # logger

except: # get error back
    if myDebug == 'yes': logger.info( 'ERROR: no filter provided! This is wrong' ) # logger

# set path to inputs.conf file
try: # lets do it
    if myDebug == 'yes': logger.info( 'read the inputs.conf...' ) # logger
    configLocalFileName = os.path.join(myPath,'..','local','inputs.conf') # setup path to inputs.conf
    if myDebug == 'yes': logger.info( 'inputs.conf file: %s' % configLocalFileName ) # logger
    parser = SafeConfigParser() # setup parser to read the inputs.conf
    parser.read(configLocalFileName) # read inputs.conf options
    #if not os.path.exists(configLocalFileName): # if empty use settings from [default] stanza in inputs.conf
    #    splunk.Intersplunk.generateErrorResults(': No config found! Check your inputs.conf in local.') # print the error into Splunk UI
    #    exit(0) # exit on error

except Exception,e: # get error back
    logger.error( 'ERROR: No config found! Check your inputs.conf in local.' ) # logger
    logger.error( 'ERROR: %e' % e ) # logger
    splunk.Intersplunk.generateErrorResults(': No config found! Check your inputs.conf in local.') # print the error into Splunk UI
    sys.exit() # exit on error

# use user provided options or get [default] stanza options
try: # lets do it
    if myDebug == 'yes': logger.info( 'read the default options from inputs.conf...' ) # logger
    if myDebug == 'yes': logger.info( 'reading server from inputs.conf...' ) # logger
    server = parser.get(section_name, 'server')

except: # get error back
    logger.error( 'ERROR: unable to get server from inputs.conf' ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get server from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error

try:
    # always check username and password in inputs.conf, never provided by user!
    if myDebug == 'yes': logger.info( 'reading user/pwd from inputs.conf...' ) # logger
    password = parser.get(section_name, 'password')
    binddn = parser.get(section_name, 'binddn')

except: # get error back
    logger.error( 'ERROR: unable to get binddn from inputs.conf' ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get binddn from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error

try:
    # check for user provided basedn options or use [default] stanza
    if myDebug == 'yes': logger.info( 'reading basedn from inputs.conf...' ) # logger
    if basedn == 'basedn':
        basedn = parser.get(section_name, 'basedn')
    else:
        basedn = basedn

except: # get error back
    logger.error( 'ERROR: unable to get basedn from inputs.conf' ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get basedn from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error

#try:
#    # check for user provided ldap_filter options or use [default] stanza
#    if myDebug == 'yes': logger.info( 'reading ldap_filter from inputs.conf...' ) # logger
#    if ldap_filter == '0':
#        ldap_filter = parser.get(section_name, 'ldap_filter')
#        if myDebug == 'yes': logger.info( 'ldap_filter= %s  ' % ldap_filter ) # logger
#    else:
#        ldap_filter = ldap_filter
#        if myDebug == 'yes': logger.info( 'ldap_filter= %s  ' % ldap_filter ) # logger
#
#except: # get error back
#    logger.error( 'ERROR: unable to get ldap_filter from inputs.conf' ) # logger
#    splunk.Intersplunk.generateErrorResults(': unable to get ldap_filter from inputs.conf') # print the error into Splunk UI
#    sys.exit() # exit on error

try:
    # check for user provided port options or use [default] stanza
    if myDebug == 'yes': logger.info( 'reading port from inputs.conf...' ) # logger
    if port == '389':
        port = parser.get(section_name, 'port')
    else:
        port = port

except: # get error back
    logger.error( 'ERROR: unable to get port from inputs.conf' ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get port from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error

try:
    # check [default] stanza if we need ssl
    if myDebug == 'yes': logger.info( 'reading usessl from inputs.conf...' ) # logger
    usessl = parser.get(section_name, 'usessl')
    if usessl == '1':
        server = ldap3.Server(host=parser.get(section_name, 'server'), port=int(parser.get(section_name, 'port')), use_ssl='%s' % usessl,get_info=ALL)
        if myDebug == 'yes': logger.info( 'server : %s ' % server ) # logger
    else:
        server = ldap3.Server(host=parser.get(section_name, 'server'), port=int(parser.get(section_name, 'port')),get_info=ALL)
        if myDebug == 'yes': logger.info( 'server : %s ' % server ) # logger
    if myDebug == 'yes': logging.info( 'usessl is : %s ...' % usessl )

except Exception,e: # get error back
    logger.error( 'ERROR: unable to get uesssl from inputs.conf' ) # logger
    logger.error( 'ERROR: %s ' % e ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get uesssl from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error

try:
    # check for user provided scope options or use [default] stanza
    if myDebug == 'yes': logger.info( 'reading scope from inputs.conf...' ) # logger
    if scope == 'base':
        scope = ldap3.BASE
        if myDebug == 'yes': logger.info( 'scope is : %s  ...' % scope) # logger
    elif scope == 'one':
        scope = ldap3.LEVEL
        if myDebug == 'yes': logger.info( 'scope is : %s  ...' % scope) # logger
    else:
        scope = ldap3.SUBTREE
        if myDebug == 'yes': logger.info( 'scope is : %s  ...' % scope) # logger

except  Exception,e: # get error back
    logger.error( 'ERROR: unable to get scope from inputs.conf' ) # logger
    logger.error( 'ERROR: %s ' % e ) # logger
    splunk.Intersplunk.generateErrorResults(': unable to get scope from inputs.conf') # print the error into Splunk UI
    sys.exit() # exit on error


# do we use anonymouse bind or do we use a password?
if password == '0': # no password
    try: # lets do an anonymouse bind
        if myDebug == 'yes':
            logger.info( 'start anonymous LDAP bind...' ) # logger
            logger.info( 'using conn :  %s ' % server ) # logger
            logger.info( 'using scope :  %s ' % scope ) # logger
            logger.info( 'using sizelimit :  %s ' % sizelimit ) # logger
            logger.info( 'using ldap_filter :  %s ' % ldap_filter ) # logger
        l = ldap3.Connection(server, auto_bind=True, version=3)
    except Exception,e: # get error back
        logger.error( 'ERROR: anonymous LDAP bind failed.' ) # logger
        logger.error( 'ERROR: %s' % e) # logger
        splunk.Intersplunk.generateErrorResults(': anonymous LDAP bind failed.') # print the error into Splunk UI
        sys.exit() # exit on error

else: # we use a password - much better ;)
    try: # lets do an authenticated bind
        if myDebug == 'yes':
            logger.info( 'start simple LDAP bind...' ) # logger
            logger.info( 'using binddn :  %s ' % binddn ) # logger
            logger.info( 'using server :  %s ' % server ) # logger
            logger.info( 'using port :  %s ' % port ) # logger
            logger.info( 'using ldap_filter :  %s ' % ldap_filter ) # logger
        decoded_pwd = base64.b64decode(password) # get the password and decode it
        l = ldap3.Connection(server, user=binddn, password=decoded_pwd, auto_bind=True, read_only=True, version=3)
    except Exception,e: # get error back
        logger.error( 'ERROR: simple LDAP bind failed.' ) # logger
        logger.error( 'ERROR: %s' % e) # logger
        splunk.Intersplunk.generateErrorResults(': simple LDAP bind failed.') # print the error into Splunk UI
        sys.exit() # exit on error


# check what attributes will be returned, default all
try: # lets do it
    if myDebug == 'yes': logger.info( 'set attribute list and size limit for LDAP search...' ) # logger
    if attrs == 'all': # we get all attributes
        if myDebug == 'yes':
            logger.info( 'using all attributes for the query...' ) # logger
            logger.info( 'using basedn :  %s ' % basedn ) # logger
            logger.info( 'using scope :  %s ' % scope ) # logger
            logger.info( 'using ldap_filter :  %s ' % ldap_filter ) # logger
        searchParameters = { 'search_base': basedn, 'search_scope': scope, 'search_filter': ldap_filter, 'attributes': ['*'], 'paged_size': 5 }
        my_filter = '(&' + ldap_filter + ')'
        l.search(search_base=basedn, search_filter=my_filter, attributes=["*"], paged_size=5)
    else: # no, we only get certain attributes back
        if myDebug == 'yes': logger.info( 'using special attributes only for the query...' ) # logger

except Exception,e: # get error back
    logger.error( 'ERROR: unable to set attribute list for LDAP search.' ) # logger
    logger.error( 'ERROR: %s ' % e) # logger
    splunk.Intersplunk.generateErrorResults(': unable to set attribute list for LDAP search.') # print the error into Splunk UI
    sys.exit() # exit on error

# get and process the LDAP result
try: # lets do it
    if myDebug == 'yes': logger.info( 'processing LDAP results...' ) # logger
    entries = l.entries

    results = []
    for entry in entries: 
        if myDebug == 'yes': logger.info( 'found entry ...' ) # logger
        result = collections.OrderedDict() 
        result["dn"] = entry.entry_dn
        for attribute in entry.entry_attributes: 
            result[attribute] = []
            for key in entry[attribute]:
                result[attribute].append(str(key)) 
    
        results.append(result)
        if myDebug == 'yes': logger.info( 'appending to results...' ) # logger

except Exception,e: # get error back
    logger.error( 'ERROR: %s' % e) # logger
    splunk.Intersplunk.generateErrorResults(': %s' % e) # print the error into Splunk UI
    sys.exit() # exit on error

# unbind the LDAP connection!
try: # lets do it
    if myDebug == 'yes': logger.info( 'unbind the LDAP connection...' ) # logger
    l.unbind() # LDAP unbind

except: # get error back
    logger.error( 'ERROR: unbind failed!' ) # logger
    splunk.Intersplunk.generateErrorResults(': LDAP unbind failed!') # print the error into Splunk UI
    sys.exit() # exit on error

# print result into Splunk
if myDebug == 'yes': logger.info( 'printing to Splunk> ...' ) # logger
splunk.Intersplunk.outputResults(results) # print the result into Splunk UI
