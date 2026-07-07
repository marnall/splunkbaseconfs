#!/usr/bin/env python

# Program name: nmonparser.py
# Compatibility: Python 3.x
# Purpose - nmon data processing for Splunk
# Author - Guilhem Marchand

# Licence:

# Copyright 2017 Octamis - Copyright 2017 Guilhem Marchand

# Load libs

from __future__ import print_function

import sys
import re
import os
import time
import datetime
import csv
import logging
from io import StringIO ## for Python 3
import platform
import optparse
import glob
import socket
import json
import subprocess

# Converter version
nmonparser_version = '3.0.0'

# LOGGING INFORMATION:
# - The program uses the standard logging Python module to display important messages in Splunk logs
# - When we want messages to be indexed within Splunk nmon_processing sourcetype, display the message
# in stdout. (splunk won't index logging messages)
# Typically, functional errors will be displayed in stdout while technical failure will be logged

#################################################
#      Parameters
#################################################

# The nmon sections to be proceeded is not anymore statically defined
# The sections are now defined through the nmonparser_config.json file located eith in default or local

# Sections of Performance Monitors with standard dynamic header but no "device" notion that would require the data
# to be transposed.
# You can add or remove any section depending on your needs
static_section = ""

# Some specific sections per OS
Solaris_static_section = ""

# Some specfic sections for micro partitions (AIX or Power Linux)
LPAR_static_section = ""

# This is the TOP section which contains Performance data of top processes
# It has a specific structure and requires specific treatment
top_section = ""

# This is the UARG section which contains full command line arguments with some other information such as PID, user,
# group and so on.
# It has a specific structure and requires specific treatment
uarg_section = ""

# Sections of Performance Monitors with "device" notion, data needs to be transposed by time to be fully exploitable
# This particular section will check for up to 10 subsection per Performance Monitor
# By default, Nmon create a new subsection (add an increment from 1 to x) per step of 150 devices
# 1500 devices (disks) will be taken in charge in default configuration
dynamic_section1 = ""

# Sections of Performance Monitors with "device" notion, data needs to be transposed by time to be fully exploitable
dynamic_section2 = ""

# disks extended statistics (DG*)
disk_extended_section = ""

# Sections of Performance Monitors for Solaris

# Zone, Project, Task... performance
solaris_WLM = ""

# Veritas Storage Manager
solaris_VxVM = ""

solaris_dynamic_various = ""

# AIX only dynamic sections
AIX_dynamic_various = ""

# AIX Workload Management
AIX_WLM = ""

# nmon_external
nmon_external = ""

# nmon external with transposition of data
nmon_external_transposed = ""

#################################################
#      Variables
#################################################

# Set logging format
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

# Initial states for Analysis
colddata = False
fifo = False

# Starting time of process
start_time = time.time()

# Verify SPLUNK_HOME environment variable is available, the script is expected to be launched by Splunk
# which will set this.
# for debugging or manual run, please set this variable manually
try:
    os.environ["SPLUNK_HOME"]
except KeyError:
    logging.error(
        'The environment variable SPLUNK_HOME could not be verified, if you want to run this script manually you need'
        ' to export it before processing')
    sys.exit(1)

# Guest Operation System type
ostype = platform.system().lower()

# If running Windows OS (used for directory identification)
is_windows = re.match(r'^win\w+', (platform.system().lower()))

# Current date
now = time.strftime("%d-%m-%Y %H:%M:%S")

# Current date in epoch time
if is_windows:
    now_epoch = int(time.time())
else:
    now_epoch = time.strftime("%s")

    # in case datetime fails
    if now_epoch == "%s":
        now_epoch = int(time.time())

# Minute of the hour, to be used for file naming convention
minute = time.strftime("%M")

# Python version
python_version = platform.python_version()

# SPLUNK_HOME environment variable
SPLUNK_HOME = os.environ['SPLUNK_HOME']

# Discover TA-metricator-hec-for-nmon path

if is_windows:
    TA_APP = SPLUNK_HOME + '\\etc\\apps\\TA-metricator-hec-for-nmon'
else:
    TA_APP = SPLUNK_HOME + '/etc/apps/TA-metricator-hec-for-nmon'

if is_windows:
    TA_APP_CLUSTERED = SPLUNK_HOME + '\\etc\\peer-apps\\TA-metricator-hec-for-nmon'
else:
    TA_APP_CLUSTERED = SPLUNK_HOME + '/etc/peer-apps/TA-metricator-hec-for-nmon'

# Empty APP
APP = ''

# Verify APP exist
if os.path.exists(TA_APP):
    APP = TA_APP
elif os.path.exists(TA_APP_CLUSTERED):
    APP = TA_APP_CLUSTERED
else:
    msg = 'The Application root directory could not be found, is the TA-metricator-hec-for-nmon installed ? We tried: ' + \
          str(TA_APP) + ' ' + str(TA_APP_CLUSTERED)
    logging.error(msg)
    sys.exit(1)

# Identify the Technical Add-on version
if is_windows:
    APP_CONF_FILE = APP + "\\default\\app.conf"
else:
    APP_CONF_FILE = APP + "/default/app.conf"

addon_version = "Unknown"
with open(APP_CONF_FILE, "r") as f:
    for line in f:
        addon_version_match = re.match(r'version\s*=\s*([\d|\.]*)', line)
        if addon_version_match:
            addon_version = addon_version_match.group(1)

# APP_VAR directory
if is_windows:
    APP_MAINVAR = SPLUNK_HOME + '\\var\\log\\metricator'
    APP_VAR = SPLUNK_HOME + '\\var\\log\\metricator\\var'
else:
    APP_MAINVAR = SPLUNK_HOME + '/var/log/metricator'
    APP_VAR = SPLUNK_HOME + '/var/log/metricator/var'
if not os.path.exists(APP_MAINVAR):
    os.mkdir(APP_MAINVAR)
if not os.path.exists(APP_VAR):
    os.mkdir(APP_VAR)

# ID reference file, will be used to temporarily store the last execution result for a given nmon file,
# and prevent Splunk from generating duplicates by relaunching the conversion process
# Splunk when using a custom archive mode, launches twice the custom script

# Supplementary note: Since V1.1.0, the ID_REF is overwritten if running real time mode
if is_windows:
    ID_REF = APP_VAR + '\\id_reference.txt'
else:
    ID_REF = APP_VAR + '/id_reference.txt'

# Config Reference file
if is_windows:
    CONFIG_REF = APP_VAR + '\\config_reference.txt'
else:
    CONFIG_REF = APP_VAR + '/config_reference.txt'

# BBB extraction flag
if is_windows:
    BBB_FLAG = APP_VAR + '\\BBB_status.flag'
else:
    BBB_FLAG = APP_VAR + '/BBB_status.flag'

# CSV Perf data repository
if is_windows:
    DATA_DIR = APP_VAR + '\\csv_workingdir\\'
else:
    DATA_DIR = APP_VAR + '/csv_workingdir/'
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

# CSV Perf data working directory (files are moved at the end from DATA_DIR to DATAWORKING_DIR)
if is_windows:
    DATAFINAL_DIR = APP_VAR + '\\csv_repository\\'
else:
    DATAFINAL_DIR = APP_VAR + '/csv_repository/'
if not os.path.exists(DATA_DIR):
    os.mkdir(DATA_DIR)

# CSV output repository
if is_windows:
    CONFIG_DIR = APP_VAR + '\\config_repository\\'
else:
    CONFIG_DIR = APP_VAR + '/config_repository/'
if not os.path.exists(CONFIG_DIR):
    os.mkdir(CONFIG_DIR)

# Network interface outdated state file (Unix only)
# remove any existing file at startup time
OUTDATED_NETIF_NMON_STATE= APP_VAR + '/outdated_network_int_nmon.state'
if os.path.exists(OUTDATED_NETIF_NMON_STATE):
    os.remove(OUTDATED_NETIF_NMON_STATE)

# Initialize some default values
day = "-1"
month = "-1"
year = "-1"
ZZZZ_timestamp = "-1"
INTERVAL = "-1"
SNAPSHOTS = "-1"
sanity_check = "-1"

# load configuration from json config file
# the config_file json may exist in default or local (if customized)
# this will define the list of nmon section we want to extract

if is_windows:
    if os.path.isfile(APP + "\\local\\nmonparser_config.json"):
        nmonparser_config = APP + "\\local\\nmonparser_config.json"
    else:
        nmonparser_config = APP + "\\default\\nmonparser_config.json"
else:
    if os.path.isfile(APP + "/local/nmonparser_config.json"):
        nmonparser_config = APP + "/local/nmonparser_config.json"
    else:
        nmonparser_config = APP + "/default/nmonparser_config.json"

with open(nmonparser_config) as nmonparser_config_json:
    config_json = json.load(nmonparser_config_json)

static_section = config_json['static_section']
Solaris_static_section = config_json['Solaris_static_section']
LPAR_static_section = config_json['LPAR_static_section']
top_section = config_json['top_section']
uarg_section = config_json['uarg_section']
dynamic_section1 = config_json['dynamic_section1']
dynamic_section2 = config_json['dynamic_section2']
disk_extended_section = config_json['disk_extended_section']
solaris_WLM = config_json['solaris_WLM']
solaris_VxVM = config_json['solaris_VxVM']
solaris_dynamic_various = config_json['solaris_dynamic_various']
AIX_dynamic_various = config_json['AIX_dynamic_various']
AIX_WLM = config_json['AIX_WLM']
nmon_external = config_json['nmon_external']
nmon_external_transposed = config_json['nmon_external_transposed']

#################################################
#      Arguments
#################################################

parser = optparse.OptionParser(usage='usage: %prog [options]', version='%prog '+nmonparser_version)

parser.set_defaults(mode='auto', datadir=DATA_DIR, configdir=CONFIG_DIR, dumpargs=False)

parser.add_option('-d', '--datadir', action='store', type='string', dest='datadir',
                  help='sets the output directory for data CSV files (Default: %default)')

opmodes = ['auto', 'fifo', 'colddata']

parser.add_option('-m', '--mode', action='store', type='choice', dest='mode', choices=opmodes,
                  help='sets the operation mode (Default: %default); supported modes: ' + ', '.join(opmodes))

parser.add_option('--use_fqdn', action='store_true', dest='use_fqdn', help='Use the host fully qualified '
                                                                           'domain name (fqdn) as the '
                                                                           'hostname value instead of the'
                                                                           ' value returned by nmon.\n'
                                                                           '**CAUTION:** This option must not be used'
                                                                           ' when managing nmon data generated out'
                                                                           ' of Splunk'
                                                                           ' (eg. central repositories)')

parser.add_option('--show_zero_values', action='store_true', dest='show_zero_values', help='Use this option to allow'
                                                                           ' the TA to generate metrics'
                                                                           ' with 0 values.\n'
                                                                           ' The default behavior is to remove any '
                                                                           ' metric having a zero value before it'
                                                                           ' reaches Splunk ingestion.')

parser.add_option('--splunk_http_url', action='store', type='string', dest='splunk_http_url',
                  help='Defines the URL for Splunk http forwarding, example:'
                  '--splunk_http_url  https://host.splunk.com:8088/services/collector/event')

parser.add_option('--splunk_http_token', action='store', type='string', dest='splunk_http_token',
                  help='Defines the value of the Splunk HEC token, example:'
                  '--splunk_http_token B07538E6-729F-4D5B-8AE1-30E93646C65A'),

parser.add_option('--splunk_metrics_index', action='store', type='string', dest='splunk_metrics_index',
                  help='Defines the name of the Splunk metrics index (default os-unix-nmon-metrics'),

parser.add_option('--splunk_events_index', action='store', type='string', dest='splunk_events_index',
                  help='Defines the name of the Splunk events index (default os-unix-nmon-events')

parser.add_option('--splunk_config_index', action='store', type='string', dest='splunk_config_index',
                  help='Defines the name of the Splunk config index (default os-unix-nmon-config')

parser.add_option('-n', '--no_local_log', action='store_true', dest='no_local_log', help='Do not write local log on'
                                                                              'machine file system')

parser.add_option('--dumpargs', action='store_true', dest='dumpargs',
                  help='only dump the passed arguments and exit (for debugging purposes only)')

parser.add_option('--debug', action='store_true', dest='debug', help='Activate debug for testing purposes')

parser.add_option('-s', '--silent', action='store_true', dest='silent', help='Do not output the per section detail'
                                                                              'logging to save data volume')

(options, args) = parser.parse_args()

if options.dumpargs:
    print("options: ", options)
    print("args: ", args)
    sys.exit(0)

# Set debug mode
if options.debug:
    debug = True
else:
    debug = False

# Set processing output verbosity
if options.silent:
    silent = True
else:
    silent = False

# Write / Don't write log on file system
if options.no_local_log:
    no_local_log = True
else:
    no_local_log = False

# Set hostname mode
if options.use_fqdn:
    use_fqdn = True
else:
    use_fqdn = False

# Allow / Disallow generation of zero values metrics
if options.show_zero_values:
    show_zero_values = True
else:
    show_zero_values = False

# Splunk http output
use_splunk_http = False
splunk_http_token_is_set = False

if options.splunk_http_url and options.splunk_http_token:
    use_splunk_http = True
    splunk_http_url = options.splunk_http_url
    splunk_http_token = options.splunk_http_token

    # Manage the default value provided for the demonstration purpose
    if "insert_your_splunk_http_token" in splunk_http_token:
        logging.error(
            "the Splunk http input token must be defined using the --splunk_http_token <token value> argument, "
            "forwarding to Splunk http input will be disabled")
        use_splunk_http = False
    else:
        splunk_http_token_is_set = True

elif options.splunk_http_url and not options.splunk_http_token:
    logging.error("the Splunk http input token must be defined using the --splunk_http_token <token value> argument, "
                  "forwarding to Splunk http input will be disabled")
    use_splunk_http = False

# Define default indexes destinations for Splunk
if options.splunk_metrics_index:
    splunk_metrics_index = options.splunk_metrics_index
else:
    splunk_metrics_index = 'os-unix-nmon-metrics'

if options.splunk_events_index:
    splunk_events_index = options.splunk_events_index
else:
    splunk_events_index = 'os-unix-nmon-events'

if options.splunk_config_index:
    splunk_config_index = options.splunk_config_index
else:
    splunk_config_index = 'os-unix-nmon-config'

# Splunk HEC only: store the final batch file to be streamed (remove any pre-existing file)
SPLUNK_HEC_BATCHFILE = APP_VAR + '/splunk_hec_perfdata_batch.dat'
if os.path.isfile(SPLUNK_HEC_BATCHFILE):
    os.remove(SPLUNK_HEC_BATCHFILE)

DATA_DIR = options.datadir
CONFIG_DIR = options.configdir

if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR)
    except Exception as ex:
        logging.error("Unable to create data output directory '%s': %s" % (DATA_DIR, ex))
        sys.exit(1)

if not os.path.exists(DATAFINAL_DIR):
    try:
        os.makedirs(DATAFINAL_DIR)
    except Exception as ex:
        logging.error("Unable to create data output directory '%s': %s" % (DATAFINAL_DIR, ex))
        sys.exit(1)

if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR)
    except Exception as ex:
        logging.error("Unable to create config output directory '%s': %s" % (CONFIG_DIR, ex))
        sys.exit(1)

#################################################
#      Functions
#################################################

# Return current time stamp in Nmon fashion


def currenttime():
    now = time.strftime("%d-%m-%Y %H:%M:%S")

    return now


# Replace % for common sections
def subpctreplace(line):
    # Replace bank char followed by %
    line = re.sub(r'\s%', '_PCT', line)

    # Replace % if part of a word
    line = re.sub(r'(?<=[a-zA-Z0-9])%', '_PCT', line)

    # Replace % at beginning of a word
    line = re.sub(r'(?<=[a-zA-Z0-9,])%(?=[a-zA-Z0-9]+|$)', 'PCT', line)

    # Replace any other %
    line = re.sub(r'%', '_PCT', line)

    return line


# Replace % for TOP section only
def subpcttopreplace(line):
    # Replace % (specific for TOP)
    line = re.sub(r'%', 'pct_', line)

    return line


# Replace others for all sections
def subreplace(line):
    # Replace blank space between 2 groups of chars
    line = re.sub(r'(?<=[a-zA-Z0-9]) (?=[a-zA-Z0-9]+|$)', '_', line)

    # Replace +
    line = re.sub(r'\+', '', line)

    # Replace "(" by "_"
    line = re.sub(r'\(', '_', line)

    # Replace ")" by nothing
    line = re.sub(r'\)', '', line)

    # Replace =0 by nothing
    line = re.sub(r'=0', '', line)

    # Replace any last work ending with _
    line = re.sub(r'_$', '', line)

    return line


# Convert month names (eg. JANV) to month numbers (eg. 01)
def monthtonumber(mydate):
    month_to_numbers = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06', 'JUL': '07',
                        'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}

    for k, v in month_to_numbers.items():
        mydate = mydate.replace(k, v)

    return mydate


# Convert month numbers (eg. 01) to month names (eg. JANV)
def numbertomonth(month):
    numbers_to_month = {'01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR', '05': 'MAY', '06': 'JUN', '07': 'JUL',
                        '08': 'AUG', '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'}

    for k, v in numbers_to_month.items():
        month = month.replace(k, v)

    return month


# Open ID_REF, global to be used in function or current scope
def openRef():
    global ref
    ref = open(ID_REF, "w")


# metrics_dictionary

def metrics_dict(metric):

    # nmon section (type to metric_name),
    dict = {
        "CPU_ALL": "cpu",
        "CPUnn": "cpu",
        "DGBACKLOG": "storage",
        "DGBUSY": "storage",
        "DGINFLIGHT": "storage",
        "DGIOTIME": "storage",
        "DGREAD": "storage",
        "DGREADMERGE": "storage",
        "DGREADS": "storage",
        "DGREADSERV": "storage",
        "DGSIZE": "storage",
        "DGWRITE": "storage",
        "DGWRITEMERGE": "storage",
        "DGWRITES": "storage",
        "DGWRITESERV": "storage",
        "DGXFER": "storage",
        "DISKBSIZE": "storage",
        "DISKBUSY": "storage",
        "DISKREAD": "storage",
        "DISKREADS": "storage",
        "DISKREADSERV": "storage",
        "DISKRIO": "storage",
        "DISKSVCTM": "storage",
        "DISKWAITTM": "storage",
        "DISKWIO": "storage",
        "DISKWRITE": "storage",
        "DISKWRITES": "storage",
        "DISKWRITESERV": "storage",
        "DISKXFER": "storage",
        "FCREAD": "adapters",
        "FCWRITE": "adapters",
        "FCXFERIN": "adapters",
        "FCXFEROUT": "adapters",
        "FILE": "kernel",
        "IOADAPT": "adapters",
        "JFSFILE": "storage",
        "JFSINODE": "storage",
        "LPAR": "cpu",
        "MEM": "memory",
        "MEMNEW": "memory",
        "MEMUSE": "memory",
        "NET": "network",
        "NETERROR": "network",
        "NETPACKET": "network",
        "NFSCLIV2": "network",
        "NFSSVRV2": "network",
        "NFSCLIV3": "network",
        "NFSSVRV3": "network",
        "NFSCLIV4": "network",
        "NFSSVRV4": "network",
        "PAGE": "kernel",
        "POOLS": "cpu",
        "PROC": "kernel",
        "PROCSOL": "kernel",
        "SEA": "adapters",
        "SEACHPHY": "adapters",
        "SEAPACKET": "adapters",
        "TOP": "processes",
        "UARG": "processes",
        "VM": "memory",
        "WLMBIO": "processes",
        "WLMCPU": "processes",
        "WLMMEM": "processes",
        "WLMPROJECTCPU": "processes",
        "WLMPROJECTMEM": "processes",
        "WLMTASKCPU": "processes",
        "WLMTASKMEM": "processes",
        "WLMUSERCPU": "processes",
        "WLMUSERMEM": "processes",
        "WLMZONECPU": "processes",
        "WLMZONEMEM": "processes",
        "UPTIME": "system",
        "PROCCOUNT": "processes",
        "DF_STORAGE": "storage",
        "DF_INODES": "storage"
    }

    # some metrics will auto-increment, we want to match the metric group
    # but NFS is a specific case where we need to match the version number
    metric_match = re.match("(^\w*[a-zA-z])[0-9]{0,}", metric)
    metric_nfs_match = re.match("(^NFS\w*)", metric)

    if metric_nfs_match:
        metric_grp = metric_nfs_match.group(1)
        if metric_grp in dict:
            return dict[metric_grp]
        else:
            return 'custom'
    elif metric_match:
        metric_grp = metric_match.group(1)
        if metric_grp in dict:
            return dict[metric_grp]
        else:
            return 'custom'
    else:
        return 'custom'


# Simple function to test numbers
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


# Simple function to get file size in bytes
def file_size(fname):
        statinfo = os.stat(fname)
        return statinfo.st_size


# Meta data
# The Meta data creation are not used currently due to the metrics specific Splunk licensing model
# this might change in the future.

def meta(currsection_meta,currsection_output,section,metric_category,OStype,SN,HOSTNAME):

    with open(currsection_meta, "w") as m:
        current_time = int(time.time())
        fsize = file_size(currsection_output)
        m.write("metric_timestamp,metric_name,OStype,serialnum,hostname,metric_category,metric_section,_value\n")
        m.write(str(current_time) + ",os.unix.nmon.meta.metric_fsize_bytes," + OStype + ',' + SN + ',' + HOSTNAME
                + ',' + metric_category + ',' + section + ',' + str(fsize) + '\n')


# Convert csv data into key=value format
def write_kv(input, kv_file):
    with open(kv_file, 'a') as f:
        reader = csv.DictReader(input)

        for row in reader:
            data = ""
            for k, v in row.items():
                data = ("%s=\"%s\" " % (k, v)) + data
            f.write(data + '\n')


# Stream to Splunk HEC
def write_kv_to_http(input, index, sourcetype):

    reader = csv.DictReader(input)
    http_data = ""
    event_batch_header = '", "index": "' + index + '", "source": "nmon_data:http", ' \
                                                   '"sourcetype": "' + str(sourcetype) + '", "event": "'

    for row in reader:
        data = ""
        for k, v in row.items():
            data = ("%s=\"%s\" " % (k, v)) + data

        # extract epochtime
        timestamp_match = re.match(r'.*timestamp="([0-9]*)".*', data)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
        else:
            logging.warn("failed to parse timestamp before streaming to http, applying now as the timestamp")
            timestamp = time.strftime("%s")

        # escape any double quote
        params = data.replace('"', '\\"')

        # This might be changed for a more Pythonic approach in the future!
        http_data = http_data + "\n" + '{"time": "' +\
                    str(timestamp) + event_batch_header + params + '"}'

    with open(SPLUNK_HEC_BATCHFILE, "a") as f:
        f.write(http_data)
        f.write("\n")

# Stream to Splunk HEC - process the performance data in a unique batch
def stream_to_splunk_http(url, token):

    FNULL = open('/dev/null', 'w')

    # This might be changed for a more Pythonic approach in the future!
    http_data = '-s -k --max-time 30 --connect-timeout 30 -H \"Authorization: Splunk ' + str(token) + '\" ' + \
                str(url) + ' -d @' + str(SPLUNK_HEC_BATCHFILE)

    cmd = "unset LIBPATH; unset LD_LIBRARY_PATH; curl" + " " + http_data
    subprocess.call([cmd], shell=True, stdout=FNULL, stderr=subprocess.PIPE)


####################################################################
#           Main Program
####################################################################

#################################
# Retrieve NMON data from stdin #
#################################

# Read nmon data from stdin
data = sys.stdin.readlines()

# Number of lines read
nbr_lines = len(data)

# Size of data read
bytes_total = len(''.join(data))

# Show current time and number of lines
msg = currenttime() + " Reading NMON data: " + str(nbr_lines) + " lines" + " " + str(bytes_total) + " bytes"
print(msg)

# Show Splunk Root Directory
msg = 'Splunk Root Directory ($SPLUNK_HOME): ' + str(SPLUNK_HOME)
print(msg)

# Show addon type
msg = "addon type: " + str(APP)
print(msg)

# Show application version
msg = "addon version: " + str(addon_version)
print(msg)

# Show program version
msg = "nmonparser version: " + str(nmonparser_version)
print(msg)

# Show type of OS we are running
print('Guest Operating System:', ostype)

# Show Python Version
print('Python version:', python_version)

# Prevent managing empty file
count = 0

# Exit if empty with error message
for line in data:
    count += 1

if count < 1:
    logging.error('Empty Nmon file!')
    sys.exit(1)

##################################################
# Extract Various data from AAA and BBB sections #
##################################################

# Set some default values
SN = "-1"
HOSTNAME = "-1"
DATE = "-1"
TIME = "-1"
logical_cpus = "-1"
virtual_cpus = "-1"
OStype = "Unknown"

# The hostname value returned by nmon and nmonparser.py can be overridden by setting the option
# override_sys_hostname="1" in local/nmon.conf or /etc/nmon.conf
# If so, we will search for a value to set the hostname
# default is use system host name (see above)
# If the option is activated, and we failed finding a value, fall back to system hostname (see above)

SPLUNK_HOSTNAME_OVERRIDE = False

# serial number override:
# the serial number used to achieve the frameID enrichment within the application can be overridden using the option:
# override_sys_serialnum="1" in local/nmon.conf or /etc/nmon.conf
# If so, we will search for the appropriated value in nmon.conf with the configuration name:
# override_sys_serialnum_value="<string>"

SERIALNUM_OVERRIDE = False
SERIALNUM_OVERRIDE_VALUE = "none"

if is_windows:
    SPLUNK_SYSTEM_INPUTS = SPLUNK_HOME + "\\etc\\system\\local\\inputs.conf"
else:
    SPLUNK_SYSTEM_INPUTS = SPLUNK_HOME + "/etc/system/local/inputs.conf"

if is_windows:
    NMON_SPLUNK_LOCAL_CONF = APP + "\\local\\nmon.conf"
else:
    NMON_SPLUNK_LOCAL_CONF = APP + "/local/nmon.conf"

# Unix only
NMON_SYS_LOCAL_CONF = "/etc/nmon.conf"

# Define the local conf with the higher priority
if os.path.isfile(NMON_SYS_LOCAL_CONF):
    NMON_LOCAL_CONF = NMON_SYS_LOCAL_CONF
elif os.path.isfile(NMON_SPLUNK_LOCAL_CONF):
    NMON_LOCAL_CONF = NMON_SPLUNK_LOCAL_CONF
else:
    NMON_LOCAL_CONF = "none"

if not NMON_LOCAL_CONF == "none" and os.path.isfile(NMON_LOCAL_CONF):

    with open(NMON_LOCAL_CONF, "r") as f:
        for config in f:

            override_sys_hostname_match = re.match(r'override_sys_hostname=\"1\"', config)
            if override_sys_hostname_match:
                SPLUNK_HOSTNAME_OVERRIDE = True

            override_sys_serialnum_match = re.match(r'override_sys_serialnum=\"1\"', config)
            if override_sys_serialnum_match:
                SERIALNUM_OVERRIDE = True

            override_sys_serialnum_value_match = re.match(r'override_sys_serialnum_value=\"([a-zA-Z0-9\-\_]*)\"', config)
            if override_sys_serialnum_value_match:
                SERIALNUM_OVERRIDE_VALUE = override_sys_serialnum_value_match.group(1)

# Enter only if the option has been activated
if SPLUNK_HOSTNAME_OVERRIDE:

    if os.path.isfile(SPLUNK_SYSTEM_INPUTS):

        with open(SPLUNK_SYSTEM_INPUTS, "r") as f:
            for config in f:
                splunk_hostname_match = re.match(r'host\s*=\s*(.+)\n', config)
                # If we have found a match, abort reading rest of file
                if splunk_hostname_match:
                    break
            if splunk_hostname_match:
                splunk_hostname = splunk_hostname_match.group(1)

                # override with the first occurrence only
                HOSTNAME = splunk_hostname
                print("HOSTNAME:", HOSTNAME)
            else:
                print("WARN: overriding the hostname value has been requested using override_sys_hostname in "
                      "local/nmon.conf but no value could be extracted from Splunk system/local/input.conf, reverted to"
                      "system value.")
                SPLUNK_HOSTNAME_OVERRIDE = False

elif use_fqdn:
    host = socket.getfqdn()
    if host:
        HOSTNAME = host
        print("HOSTNAME:", HOSTNAME)

for line in data:

    # Set HOSTNAME

    # if the option --use_fqdn has been set, use the fully qualified domain name by the running OS
    # The value will be equivalent to the stdout of the os "hostname -f" command
    # CAUTION: This option must not be used to manage nmon data out of Splunk ! (eg. central repositories)

    if not SPLUNK_HOSTNAME_OVERRIDE and not use_fqdn:
        host = re.match(r'^(AAA),(host),(.+)\n', line)
        if host:
            HOSTNAME = host.group(3)
            print("HOSTNAME:", HOSTNAME)

    # Set VERSION
    version = re.match(r'^(AAA),(version),(.+)\n', line)
    if version:
        VERSION = version.group(3)
        print("NMON VERSION:", VERSION)

    # Set SN
    if SERIALNUM_OVERRIDE:
        SN = SERIALNUM_OVERRIDE_VALUE
    else:
        sn = re.match(r'^BBB\w*,[^,]*,[^,]*,\"(?:systemid|serial_number)[^,]*IBM,(\w*)[\s|\"].*\n', line)
        if sn:
            SN = sn.group(1)

    # Set DATE
    date = re.match(r'^(AAA),(date),(.+)\n', line)
    if date:
        DATE = date.group(3)
        print("DATE of Nmon data:", DATE)

    # Set date details
    date_details = re.match(r'(AAA,date,)([0-9]+)[/|\-]([a-zA-Z-0-9]+)[/|\-]([0-9]+)', line)
    if date_details:
        day = date_details.group(2)
        month = date_details.group(3)
        year = date_details.group(4)

    # Set TIME
    time_match = re.match(r'^(AAA),(time),(.+)\n', line)
    if time_match:
        TIME = time_match.group(3)
        print("TIME of Nmon Data:", TIME)

    # Set INTERVAL
    interval = re.match(r'^(AAA),(interval),(.+)\n', line)
    if interval:
        INTERVAL = interval.group(3)
        print("INTERVAL:", INTERVAL)

    # Set SNAPSHOTS
    snapshots = re.match(r'^(AAA),(snapshots),(.+)\n', line)
    if snapshots:
        SNAPSHOTS = snapshots.group(3)
        print("SNAPSHOTS:", SNAPSHOTS)

    # Set logical_cpus (Note: AIX systems for example will have values behind AAA,cpus - should use the second
    # by default if it exists)
    LOGICAL_CPUS = re.match(r'^(AAA),(cpus),(.+),(.+)\n', line)
    if LOGICAL_CPUS:
        logical_cpus = LOGICAL_CPUS.group(4)
        print("logical_cpus:", logical_cpus)
    else:
        # If not defined in second position, set it from first
        LOGICAL_CPUS = re.match(r'^(AAA),(cpus),(.+)\n', line)
        if LOGICAL_CPUS:
            logical_cpus = LOGICAL_CPUS.group(3)
            print("logical_cpus:", logical_cpus)

    # Set virtual_cpus
    VIRTUAL_CPUS = re.match(r'^BBB[a-zA-Z].+Online\sVirtual\sCPUs.+:\s([0-9]+)\"\n', line)
    if VIRTUAL_CPUS:
        virtual_cpus = VIRTUAL_CPUS.group(1)
        print("virtual_cpus:", virtual_cpus)

    # Identify Linux hosts
    OStype_Linux = re.search(r'AAA,OS,Linux', line)
    if OStype_Linux:
        OStype = "Linux"

    # Identify Solaris hosts
    OStype_Solaris = re.match(r'^AAA,OS,Solaris,.+', line)
    if OStype_Solaris:
        OStype = "Solaris"

    # Identify AIX hosts
    AIX_LEVEL_match = re.match(r'^AAA,AIX,(.+)', line)
    if AIX_LEVEL_match:
        OStype = "AIX"

# Show NMON OStype
print("NMON OStype:", OStype)

# If HOSTNAME could not be defined
if HOSTNAME == '-1':
    print("ERROR: The hostname could not be extracted from Nmon data !")
    sys.exit(1)

# If DATE could not be defined
if DATE == '-1':
    print("date could not be extracted from Nmon data !")
    sys.exit(1)

# If TIME could not be defined
if TIME == '-1':
    print("time could not be extracted from Nmon data !")
    sys.exit(1)

# If logical_cpus could not be defined
if logical_cpus == '-1':
    print("The number of logical cpus (logical_cpus) could not be extracted from Nmon data !")
    sys.exit(1)

# If virtual_cpus could not be defined, set it equal to logical_cpus
if virtual_cpus == '-1':
    virtual_cpus = logical_cpus
    print("virtual_cpus: " + virtual_cpus)

# If SN could not be defined, not an AIX host, SN == HOSTNAME unless using SERIALNUM_OVERRIDE
if SERIALNUM_OVERRIDE:
    SN = SERIALNUM_OVERRIDE_VALUE
elif SN == '-1':
    SN = HOSTNAME
print("SerialNumber:", SN)

###############################
# NMON Structure Verification #
###############################

# The purpose of this section is to achieve some structure verification of the Nmon file
# to prevent data inconsistency

for line in data:

    # Verify we do not have any line that contain ZZZZ without beginning the line by ZZZZ
    # In such case, the nmon data is bad and buggy, converting it would generate data inconsistency

    # Search for ZZZZ truncated lines (eg. line containing ZZZZ pattern BUT not beginning the line)

    ZZZZ_truncated = re.match(r'.+ZZZZ,', line)
    if ZZZZ_truncated:
        # We do not use logging to be able to access this messages within Splunk (Splunk won't index error
        #  logging messages)

        msg = 'ERROR: hostname: ' + HOSTNAME + ' Detected Bad Nmon structure, found ZZZZ lines truncated! ' \
                                               '(ZZZZ lines contains the event timestamp and should always ' \
                                               'begin the line)'
        print(msg)
        msg = 'ERROR: hostname: ' + HOSTNAME + ' Ignoring nmon data'
        print(msg)
        sys.exit(1)

    # Search for old time format (eg. Nmon version V9 and prior)
    time_oldformat = re.match(r'(AAA,date,)([0-9]+)/([0-9]+)/([0-9]+)', line)
    if time_oldformat:
        msg = 'INFO: hostname: ' + HOSTNAME + ' Detected old Nmon version using old Date format (dd/mm/yy)'
        print(msg)

        day = time_oldformat.group(2)
        month = time_oldformat.group(3)
        year = time_oldformat.group(4)

        # Convert %y to %Y
        year = datetime.datetime.strptime(year, '%y').strftime('%Y')

        # Convert from months numbers to months name for compatibility with later Nmon versions
        # Note: we won't use here datetime to avoid issues with locale names of months

        month = numbertomonth(month)

        DATE = day + '-' + month + '-' + year

        msg = 'INFO: hostname: ' + HOSTNAME + ' Date converted to: ' + DATE
        print(msg)

# End for

################################
# Data status store #
################################

# Various status are stored in different files
# This includes the id check file, the config check file and status per section containing last epochtime proceeded
# These items will be stored in a per host dedicated directory

# create a directory under APP_VAR
# This directory will used to store per section last epochtime status
if is_windows:
    HOSTNAME_VAR = APP_VAR + '\\' + HOSTNAME + '_' + SN
else:
    HOSTNAME_VAR = APP_VAR + '/' + HOSTNAME + '_' + SN

if not os.path.isdir(HOSTNAME_VAR):
    try:
        os.mkdir(HOSTNAME_VAR)
    except Exception as e:
        msg = 'Error encountered during directory creation has failed due to:'
        msg = (msg, '%s' % e.__class__)
        logging.error(msg)

###############
# ID Check #
###############

# This section prevents Splunk from generating duplicated data for the same Nmon file
# While using the archive mode, Splunk may opens twice the same file sequentially
# If the Nmon file id is already present in our reference file, then we have already proceeded this Nmon and
# nothing has to be done
# Last execution result will be extracted from it to stdout

# Set default value for the last known epochtime
last_known_epochtime = 0

# Set the value in epochtime of the starting nmon
NMON_DATE = DATE + ' ' + TIME

# For Nmon V10 and more
timestamp_match = re.match(r'\d*-\w*-\w*\s\d*:\d*:\d*', NMON_DATE)
if timestamp_match:

    if is_windows:
        starting_epochtime = int(time.mktime(time.strptime(NMON_DATE, '%d-%b-%Y %H:%M:%S')))
    else:
        starting_epochtime = datetime.datetime.strptime(NMON_DATE, '%d-%b-%Y %H:%M:%S').strftime('%s')
        
        # in case datetime fails
        if starting_epochtime == "%s":
            starting_epochtime = int(time.mktime(time.strptime(NMON_DATE, '%d-%b-%Y %H:%M:%S')))
        
    starting_time = datetime.datetime.strptime(NMON_DATE, '%d-%b-%Y %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S')

else:
    # For Nmon v9 and prior

    if is_windows:
        starting_epochtime = int(time.mktime(time.strptime(NMON_DATE, '%d-%b-%Y %H:%M.%S')))
    else:
        starting_epochtime = datetime.datetime.strptime(NMON_DATE, '%d-%b-%Y %H:%M.%S').strftime('%s')

        # in case datetime fails
        if starting_epochtime == "%s":
            starting_epochtime = int(time.mktime(time.strptime(NMON_DATE, '%d-%b-%Y %H:%M.%S')))

    starting_time = datetime.datetime.strptime(NMON_DATE, '%d-%b-%Y %H:%M.%S').strftime('%d-%m-%Y %H:%M:%S')

# Search for last epochtime in data
for line in data:

    # Extract timestamp

    # Nmon V9 and prior do not have date in ZZZZ
    # If unavailable, we'll use the global date (AAA,date)
    ZZZZ_DATE = '-1'
    ZZZZ_TIME = '-1'

    # For Nmon V10 and more

    timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
    if timestamp_match:
        ZZZZ_TIME = timestamp_match.group(2)
        ZZZZ_DATE = timestamp_match.group(3)

        # Replace month names with numbers
        ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

        # Compose final timestamp
        ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

        # Convert in epochtime
        if is_windows:
            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
        else:
            ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S').strftime('%s')

            # in case datetime fails
            if ZZZZ_epochtime == "%s":
                ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

    # For Nmon V9 and less

    if ZZZZ_DATE == '-1':
        ZZZZ_DATE = DATE

        # Replace month names with numbers
        ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

        timestamp_match = re.match(r'^ZZZZ,(.+),(.+)\n', line)
        if timestamp_match:
            ZZZZ_TIME = timestamp_match.group(2)
            ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

            # Convert in epochtime
            if is_windows:
                ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
            else:
                ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S').strftime('%s')

                # in case datetime fails
                if ZZZZ_epochtime == "%s":
                    ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

# Set ending epochtime
# noinspection PyBroadException
try:
    if ZZZZ_epochtime:
        ending_epochtime = ZZZZ_epochtime
    else:
        ZZZZ_epochtime = starting_epochtime
except NameError:
    logging.info("The ending period of this Nmon file could not be determined, most probably the nmon process has not "
                 "yet generated any performance data, this should be resolved on next occurrence.")
    sys.exit(0)
except:
    logging.error("Encountered an Unexpected error while parsing this Nmon file Nmon, cannot continue")
    sys.exit(1)

# Evaluate if we are dealing with real time data or cold data
# This feature can be overridden by the --mode option
# Windows guest is not concerned
if options.mode == 'colddata':
    colddata = True
elif options.mode == 'fifo':
    fifo = True
elif is_windows:
    colddata = True
else:
    colddata = True

# IDs
if is_windows:
    ID_REF = HOSTNAME_VAR + '\\' + HOSTNAME + '.id_reference.txt'
    CONFIG_REF = HOSTNAME_VAR + '\\' + HOSTNAME + '.config_reference.txt'
    BBB_FLAG = HOSTNAME_VAR + '\\' + HOSTNAME + '.BBB_status.flag'
else:
    ID_REF = HOSTNAME_VAR + '/' + HOSTNAME + '.id_reference.txt'
    CONFIG_REF = HOSTNAME_VAR + '/' + HOSTNAME + '.config_reference.txt'
    BBB_FLAG = HOSTNAME_VAR + '/' + HOSTNAME + '.BBB_status.flag'

# NMON file id (concatenation of ids)
idnmon = DATE + ':' + TIME + ',' + HOSTNAME + ',' + SN + ',' + str(bytes_total) + ',' + str(starting_epochtime) + ',' +\
         str(ending_epochtime)

# Partial idnmon that won't contain ending_epochtime for compare operation, to used for cold data
partial_idnmon = DATE + ':' + TIME + ',' + HOSTNAME + ',' + SN + ',' + str(bytes_total) + ',' + str(starting_epochtime)

# Show Nmon ID
print("NMON ID:", idnmon)

# Show real time / cold data message
if colddata:
    if options.mode == 'colddata':
        msg = "ANALYSIS: Enforcing colddata mode using --mode option"
    else:
        msg = 'ANALYSIS: Assuming Nmon cold data'
    print(msg)
elif fifo:
    if options.mode == 'fifo':
        msg = "ANALYSIS: Enforcing fifo mode using --mode option"
    else:
        msg = 'ANALYSIS: fifo mode activated'
    print(msg)

# Open reference file for reading, if exists already
if os.path.isfile(ID_REF):

    with open(ID_REF, "r") as ref:

        for line in ref:

            # Notes: fifo mode will always proceed data

            if colddata:

                # Search for this ID
                idmatch = re.match(partial_idnmon, line)
                if idmatch:

                    # If ID matches, then the file has been previously proceeded, let's show last result of execution
                    for k in ref:
                        k = k.rstrip("\n").split(";")
                        print(k)

                    sys.exit(0)

                # If id does not match, recover the last known ending epoch time to proceed only new data
                else:
                    last_known_epochtime = starting_epochtime

# If we here, then this file has not been previously proceeded

# Open reference file for writing
msg = now + " Reading NMON data: " + str(nbr_lines) + " lines" + " " + str(bytes_total) + " bytes"

if colddata:
    openRef()

    # write id
    ref.write(msg + '\n')
    ref.write(idnmon + '\n')

# write starting epoch
msg = "Starting_epochtime: " + str(starting_epochtime)
print(msg)
if colddata:
    ref.write(msg + '\n')

# write last epochtime of Nmon data
msg = "Ending_epochtime: " + str(ZZZZ_epochtime)
print(msg)
if colddata:
    ref.write(msg + '\n')

# Show and save last known epoch time
msg = 'last known epoch time: ' + str(last_known_epochtime)
print(msg)
if colddata:
    ref.write(msg + '\n')

# Set last known epochtime equal to starting epochtime if the nmon has not been yet proceeded
if last_known_epochtime == 0:
    last_known_epochtime = starting_epochtime

####################
# Write CONFIG csv #
####################

# Extraction of the AAA and BBB sections with a supplementary header to allow Splunk identifying the host and
# timestamp as a multi-lines event
# In any case, the Configuration extraction will not be executed more than once per hour
# In the case of Real Time data, the extraction will only be achieved once per Nmon file

# Update 04/17/2015: In real time mode with very large system, the performance collect may starts before the
# configuration ends (eg. an AAA section, followed by Perf metrics and later the BBB section)
# This would implies partial configuration extraction to be proceeded
# The script now verifies that the BBB section has been successfully extracted before setting the status to
# do not extract

# Set section
section = "CONFIG"

# Set output file
config_output = APP_VAR + '/nmon_configdata.log'

# config_meta = DATA_DIR + HOSTNAME + minute + '_' + section + '.meta.metrics.csv'

# Set time_delta_limit, by default we should generate configuration by cycle of 24 hours unless the process
# has been restarted
time_delta_limit = 86400

# Set default for config_run:
# 0 --> Extract configuration
# 1 --> Don't Extract configuration
# default is extract
config_run = 0

# configuration data will always be extracted for cold data
# Only enter this section when mode is fifo
if fifo:

    # Search in ID_REF for a last matching execution
    if os.path.isfile(CONFIG_REF):

        with open(CONFIG_REF, "r") as f:

            for line in f:

                # Only proceed if hostname has the same value
                if HOSTNAME in line:

                    CONFIG_REFDETAILS = re.match(r'^.+:\s(\d+)', line)
                    config_lastepoch = CONFIG_REFDETAILS.group(1)

                    if config_lastepoch:

                        time_delta = (int(now_epoch) - int(config_lastepoch))

                        if time_delta < time_delta_limit:

                            # Only set the status to do not extract is the BBB_FLAG is not present
                            if not os.path.isfile(BBB_FLAG):
                                config_run = 1
                            else:
                                config_run = 0

                        elif time_delta > time_delta_limit:

                            config_run = 0

if config_run == 0:

    if fifo:

        # Only allow one extraction of the config section per nmon file
        limit = (int(starting_epochtime) + (4 * int(INTERVAL)))

        if int(last_known_epochtime) < int(limit):

            msg = "CONFIG section will be extracted"
            print(msg)

            # Initialize BBB_count
            BBB_count = 0

            # Open file for writing in append mode
            if not no_local_log:
                config = open(config_output, "ab")

            # counter
            count = 0

            # Write header
            config_header = 'timestamp="' + now_epoch + '", ' + 'date="' + DATE + ':' + TIME + '", ' \
                            + 'host="' + HOSTNAME + '", ' + 'serialnum="' + SN \
                            + '", configuration_content="' + '\n'

            # Write the header
            if not no_local_log:
                config.write(config_header)

            # For Splunk HEC
            if use_splunk_http:
                config_content = config_header

            for line in data:

                # Extract AAA and BBB sections, and write to config output
                AAABBB = re.match(r'^[AAA|BBB].+', line)

                if AAABBB:
                    # Increment
                    count += 1

                    # Host override feature, if this option is activated, we want this line to be rewritten
                    if 'AAA,host,' in line:
                        if SPLUNK_HOSTNAME_OVERRIDE:
                            line = 'AAA,host,' + str(HOSTNAME) + '\n'

                    # Serial number override
                    if 'AAA,SerialNumber,' in line:
                        if SERIALNUM_OVERRIDE:
                            line = 'AAA,SerialNumber,' + str(SERIALNUM_OVERRIDE_VALUE) + '\n'

                    # Increment the BBB counter
                    if "BBB" in line:
                        BBB_count += 1

                    # Write
                    if not no_local_log:
                        config.write(line)

                    if use_splunk_http:
                        config_content = config_content + str(line)

            # Write end of key=value and line return
            if not no_local_log:
                config.write('"\n')
                config.close()

            if use_splunk_http:

                # Set output pseudo files
                config_output_tmp = StringIO()
                config_output_final = APP_VAR + '/nmon_configdata.tmp'
                config_content = config_content + '"\n'

                # For /dev/null redirection
                FNULL = open('/dev/null', 'w')

                raw_params = config_content

                # replace quotes by a space, escape double quotes
                raw_params = re.sub(r"\'", " ", raw_params)
                raw_params = re.sub(r'\"', '\\"', raw_params)

                config_output_tmp.write(raw_params)
                config_output_tmp.seek(0)

                with open(config_output_final, "w") as f:

                    splunk_hec_header = '{\"index\": \"' + splunk_config_index + \
                                        '\", \"sourcetype\": \"nmon_config:http\", \"event\": \"'
                    f.write(splunk_hec_header)

                    for line in config_output_tmp:
                        line = line + "\\n"
                        f.write(line)
                    f.write('"}')

                # This might be changed for a more Pythonic approach in the future!
                http_data = '-s -k --max-time 30 --connect-timeout 30 -H \"Authorization: Splunk ' + str(splunk_http_token) + '\" ' +\
                            str(splunk_http_url) + ' -d @' + str(config_output_final)

                cmd = "unset LIBPATH; unset LD_LIBRARY_PATH; curl" + " " + http_data
                subprocess.call([cmd], shell=True, stdout=FNULL, stderr=subprocess.PIPE)

                # Clean
                if os.path.isfile(config_output_final):
                    os.remove(config_output_final)
                config_output_tmp.close()

            # Under 10 lines of data in BBB, estimate extraction is not complete
            if BBB_count < 10:
                with open(BBB_FLAG, "w") as bbb_flag:
                    bbb_flag.write("BBB_status KO")
            else:
                if os.path.isfile(BBB_FLAG):
                    os.remove(BBB_FLAG)

            # save Meta
            # metric_category = "configuration"
            # meta(config_meta, config_output, section, metric_category, OStype, SN, HOSTNAME)

            # Show number of lines extracted
            result = "CONFIG section: Wrote" + " " + str(count) + " lines"
            print(result)

            # Save the a combo of HOSTNAME: current_epochtime in CONFIG_REF
            with open(CONFIG_REF, "w") as f:
                f.write(HOSTNAME + ": " + str(now_epoch) + "\n")

        else:

            msg = "CONFIG section: Assuming we already extracted for this file"
            print(msg)

    elif colddata:

        msg = "CONFIG section will be extracted"
        print(msg)

        # Open file for writing in append mode
        if not no_local_log:
            config = open(config_output, "ab")

        # counter
        count = 0

        # Write header
        config_header = 'timestamp="' + now_epoch + '", ' + 'date="' + DATE + ':' + TIME + '", ' \
                        + 'host="' + HOSTNAME + '", ' + 'serialnum="' + SN \
                        + '", configuration_content="' + '\n'

        # Write the header
        if not no_local_log:
            config.write(config_header)

        # For Splunk HEC
        if use_splunk_http:
            config_content = config_header

        for line in data:

            # Extract AAA and BBB sections, and write to config output
            AAABBB = re.match(r'^[AAA|BBB].+', line)

            if AAABBB:
                # Increment
                count += 1

                # Write
                if not no_local_log:
                    config.write(line)

                if use_splunk_http:
                    config_content = config_content + str(line)

        # Write end of key=value and line return
        if not no_local_log:
            config.write('"\n')
            config.close()

        if use_splunk_http:

            # Set output pseudo files
            config_output_tmp = StringIO()
            config_output_final = APP_VAR + '/nmon_configdata.tmp'
            config_content = config_content + '"\n'

            # For /dev/null redirection
            FNULL = open('/dev/null', 'w')

            raw_params = config_content

            # replace quotes by a space, escape double quotes
            raw_params = re.sub(r"\'", " ", raw_params)
            raw_params = re.sub(r'\"', '\\"', raw_params)

            config_output_tmp.write(raw_params)
            config_output_tmp.seek(0)

            with open(config_output_final, "w") as f:

                splunk_hec_header = '{\"index\": \"' + splunk_config_index + \
                                    '\", \"sourcetype\": \"nmon_config:http\", \"source\": \"nmon_config:http\",' \
                                    ' \"event\": \"'
                f.write(splunk_hec_header)
                for line in config_output_tmp:
                    line = line + "\\n"
                    f.write(line)
                f.write('"}')

            # This might be changed for a more Pythonic approach in the future!
            http_data = '-s -k --max-time 30 --connect-timeout 30 -H \"Authorization: Splunk ' + str(splunk_http_token) + '\" ' +\
                        str(splunk_http_url) + ' -d @' + str(config_output_final)

            cmd = "unset LIBPATH; unset LD_LIBRARY_PATH; curl" + " " + http_data
            subprocess.call([cmd], shell=True, stdout=FNULL, stderr=subprocess.PIPE)

            # Clean
            if os.path.isfile(config_output_final):
                os.remove(config_output_final)
            config_output_tmp.close()

        # save Meta
        # metric_category = "configuration"
        # meta(config_meta, config_output, section, metric_category, OStype, SN, HOSTNAME)

        # Show number of lines extracted
        result = "CONFIG section: Wrote" + " " + str(count) + " lines"
        print(result)
        ref.write(result + '\n')

        # Save the a combo of HOSTNAME: current_epochtime in CONFIG_REF
        with open(CONFIG_REF, "w") as f:
            f.write(HOSTNAME + ": " + str(now_epoch) + "\n")

elif config_run == 1:
    # Show number of lines extracted
    result = "CONFIG section: will not be extracted (time delta of " + str(time_delta) +\
             " seconds is inferior to " + str(time_delta_limit) + " seconds)"
    print(result)

    if colddata:
        ref.write(result + '\n')

##########################
# Write PERFORMANCE DATA #
##########################

##########################################################################
# regular multi-dimension data managed as metrics for the metric datastore
##########################################################################

def multi_dimension_metrics_fn(section):

    header_found = False

    # Set output file
    currsection_output = APP_VAR + '/nmon_perfdata_metrics.log'

    # currsection_meta = DATA_DIR + HOSTNAME + '_' + minute + '_' + section + '.meta.metrics.csv'

    # counter
    count = 0

    event_count = 1

    # sanity_check
    sanity_check = 1

    # Initialize num_cols_header to 0 (see sanity_check)
    num_cols_header = 0

    # Sequence to search for
    seq = str(section) + ',' + 'T'

    # define default values for metric store
    metric_category = metrics_dict(section)
    metric_name = "os.unix.nmon." + metric_category + "." + section.lower()

    for line in data:

        # Extract sections
        if str(seq) in line:  # Don't use regex here for more performance

            # increment
            count += 1

    # Virtually always activates CPUnn
    if section == 'CPUnn':
        # increment
        count += 1

    if count >= 1:

        # Open StringIO for temp in memory
        membuffer = StringIO()
        membuffer2 = StringIO()

        # counter
        count = 0

        for line in data:

            # Extract sections (manage specific case of CPUnn), and write to output
            if section == "CPUnn":
                myregex = r'^' + 'CPU\d*' + '|ZZZZ.+'
            else:
                myregex = r'^' + section + '|ZZZZ.+'

            find_section = re.match(myregex, line)
            if find_section:

                # Replace trouble strings
                line = subpctreplace(line)
                line = subreplace(line)

                # csv header

                # Extract header excluding data that always has Txxxx for timestamp reference
                # For CPUnn, search for first core
                if section == "CPUnn":
                    myregex = '(' + 'CPU01' + ')\,([^T].+)'
                else:
                    myregex = '(' + section + ')\,([^T].+)'

                # Search for header
                fullheader_match = re.search(myregex, line)

                # Standard header extraction

                # For CPUnn, if first core were not found using CPU01, search for CPU000 (Solaris) and
                # CPU001 (Linux)
                if section == "CPUnn":
                    if not fullheader_match:
                        myregex = '(' + 'CPU000' + ')\,([^T].+)'
                        fullheader_match = re.search(myregex, line)

                    if not fullheader_match:
                        myregex = '(' + 'CPU001' + ')\,([^T].+)'
                        fullheader_match = re.search(myregex, line)

                if fullheader_match:
                    fullheader = fullheader_match.group(2)

                    # Replace "." by "_" only for header
                    fullheader = re.sub("\.", '_', fullheader)

                    # Replace any blank space before comma only for header
                    fullheader = re.sub(", ", ',', fullheader)

                    header_match = re.search(r'([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9,]*)', fullheader)

                    if header_match:
                        header = header_match.group(2)

                        # increment
                        count += 1

                        # Write header

                        # CPUnn has a specific multi-dimension mode with cpucore
                        if section == "CPUnn":
                            final_header = 'ZZZZ_epochtime' + ',' + 'cpucore' + ',' + header + '\n'

                        # for CPU_ALL and LPAR, we add the combo logical_cpus / virtual_cpus
                        elif section == 'CPU_ALL' or section == 'LPAR':
                            final_header = 'ZZZZ_epochtime' + ',' + 'logical_cpus' + ',' + 'virtual_cpus' +\
                                       ',' + header + '\n'

                        # UPTIME is a specific case since we extract the load average statistics
                        elif section == "UPTIME":
                            final_header = 'ZZZZ_epochtime' +\
                                           ',load_average_1min,load_average_5min,load_average_15min' + '\n'

                        # Other cases
                        else:
                            final_header = 'ZZZZ_epochtime' + ',' + header + '\n'

                        # Number of separators in final header
                        num_cols_header = final_header.count(',')

                        # Write header
                        membuffer.write(final_header)

                # Extract timestamp

                # Nmon V9 and prior do not have date in ZZZZ
                # If unavailable, we'll use the global date (AAA,date)
                ZZZZ_DATE = '-1'

                # For Nmon V10 and more

                timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
                if timestamp_match:
                    ZZZZ_TIME = timestamp_match.group(2)
                    ZZZZ_DATE = timestamp_match.group(3)

                    # Replace month names with numbers
                    ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                    # Compose final timestamp
                    ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                    if is_windows:
                        ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                    else:
                        ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')\
                            .strftime('%s')

                        # in case datetime fails
                        if ZZZZ_epochtime == "%s":
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

                #
                # Extract Data
                #

                if section == "CPUnn":
                    myregex = r'^' + '(CPU\d*)' + '\,(T\d+)\,(.+)\n'
                else:
                    myregex = r'^' + section + '\,(T\d+)\,(.+)\n'

                perfdata_match = re.match(myregex, line)

                if perfdata_match:

                    # CPUnn exception
                    if section == 'CPUnn':
                        perfdata_cpucore = perfdata_match.group(1)
                        perfdata = perfdata_match.group(3)


                    # UPTIME exception
                    # For uptime, we will extract the load average statistics to create these metrics from logs
                    elif section == 'UPTIME':
                        myregex = r'UPTIME,T\d*,\".*load[_\-\s]average:\s*([\d|\.]*);\s*([\d|\.]*);\s*([\d|\.]*)'
                        uptime_match = re.match(myregex, line)

                        if uptime_match:
                            uptime_load_average_1min = uptime_match.group(1)
                            uptime_load_average_5min = uptime_match.group(2)
                            uptime_load_average_15min = uptime_match.group(3)
                            perfdata = str(uptime_load_average_1min) + ',' +\
                                       str(uptime_load_average_5min) + ',' + str(uptime_load_average_15min)

                        else:
                            # extraction has failed
                            perfdata = '0,0,0'

                    else:
                        perfdata = perfdata_match.group(2)

                    # increment
                    count += 1

                    # final_perfdata
                    if section == 'CPUnn':
                        final_perfdata = ZZZZ_epochtime + ',' + perfdata_cpucore + ',' + perfdata + '\n'

                    elif section == 'CPU_ALL' or section == 'LPAR':
                        final_perfdata = ZZZZ_epochtime + ',' + logical_cpus + ',' + virtual_cpus +\
                                         ',' + perfdata + '\n'
                    else:
                        final_perfdata = ZZZZ_epochtime + ',' + perfdata + '\n'

                    # Analyse the first line of data: Compare number of fields in data with number of fields
                    # in header
                    # If the number of fields is higher than header, we assume this section is not consistent
                    # and will be entirely dropped
                    # This happens in rare times (mainly with old buggy nmon version) that the header is bad
                    # formatted (for example missing comma between fields identification)
                    # For performance purposes, we will test this only with first line of data and assume the
                    # data sanity based on this result
                    if count == 2:

                        # Number of separators in final header
                        num_cols_perfdata = final_perfdata.count(',')

                        if num_cols_perfdata > num_cols_header:

                            msg = 'WARN: hostname: ' + HOSTNAME + ' :' + section +\
                                  ' section data is not consistent: ' + str(num_cols_perfdata) +\
                                  ' fields in data, ' + str(num_cols_header) \
                                  + ' fields in header, extra fields detected (more fields in data ' \
                                    'than header), dropping this section to prevent data inconsistency'
                            print(msg)

                            if colddata:
                                ref.write(msg + "\n")

                            # Affect a sanity check to 1, bad data
                            sanity_check = 1

                        else:

                            # Affect a sanity check to 0, good data
                            sanity_check = 0

                    # Write perf data
                    membuffer.write(final_perfdata)

        if not sanity_check == 1:

            # Rewind temp
            membuffer.seek(0)

            if section == "CPUnn":
                writer = csv.writer(membuffer2)
                writer.writerow(
                    ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                     'hostname', '_value'])

            elif section == "DF_STORAGE" or section == "DF_INODES":
                writer = csv.writer(membuffer2)
                writer.writerow(
                    ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                     'hostname', 'dimension_mount', 'dimension_filesystem', '_value'])

            else:
                writer = csv.writer(membuffer2)
                writer.writerow(
                    ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                     'hostname', '_value'])

            # csv reader
            reader = csv.DictReader(membuffer)

            if section == "CPUnn":

                for d in reader:
                    csv_ZZZZ_epochtime = d.pop('ZZZZ_epochtime')
                    csv_cpucore = d.pop('cpucore')
                    for dimension, value in sorted(d.items()):

                        # value must be null, and must be a number, must not be equal to 0 by default
                        if show_zero_values:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "-0.0" or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name, cpucore and dimension
                                metric = metric_name + '.' + csv_cpucore + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME, value]
                                writer.writerow(row)

                        else:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "0" or value == "0.0"
                                                                     or value == "-0.0" or value == "0.00"
                                                                     or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name, cpucore and dimension
                                metric = metric_name + '.' + csv_cpucore + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME, value]
                                writer.writerow(row)

            elif section == "DF_STORAGE" or section == "DF_INODES":

                for d in reader:
                    csv_ZZZZ_epochtime = d.pop('ZZZZ_epochtime')
                    csv_mount = d.pop('mount')
                    csv_filesystem = d.pop('filesystem')
                    for dimension, value in sorted(d.items()):

                        # value must be null, and must be a number, must not be equal to 0 by default
                        if show_zero_values:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "-0.0" or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name and dimension
                                metric = metric_name + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME,
                                       csv_mount, csv_filesystem, value]
                                writer.writerow(row)

                        else:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "0" or value == "0.0"
                                                                     or value == "-0.0" or value == "0.00"
                                                                     or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name and dimension
                                metric = metric_name + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME,
                                       csv_mount, csv_filesystem, value]
                                writer.writerow(row)

            else:

                for d in reader:
                    csv_ZZZZ_epochtime = d.pop('ZZZZ_epochtime')
                    for dimension, value in sorted(d.items()):

                        # value must be null, and must be a number, must not be equal to 0 by default
                        if show_zero_values:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "-0.0" or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name and dimension
                                metric = metric_name + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME, value]
                                writer.writerow(row)

                        else:

                            if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                     or value == "0" or value == "0.0"
                                                                     or value == "-0.0" or value == "0.00"
                                                                     or value == '-nan'):
                                # increment
                                event_count += 1

                                # concatenate the metric_name and dimension
                                metric = metric_name + '.' + dimension

                                row = [csv_ZZZZ_epochtime, metric, OStype, SN, HOSTNAME, value]
                                writer.writerow(row)

                    # End for

        # Verify sanity check
        # Verify that the number of lines is at least 2 lines which should be the case if we are here (header + data)
        # In any case, don't allow empty files to kept in repository

        if sanity_check == 1:
            if os.path.isfile(currsection_output):
                os.remove(currsection_output)
        elif event_count < 2:
            if os.path.isfile(currsection_output):
                os.remove(currsection_output)
        else:

            # save Meta
            # meta(currsection_meta, currsection_output, section, metric_category, OStype, SN, HOSTNAME)

            # Show number of lines extracted
            result = section + " section: Wrote" + " " + str(event_count) + " line(s)"

            if not silent:
                print(result)

                if colddata:
                    ref.write(result + "\n")

            if not no_local_log:

                # Rewind temp
                membuffer2.seek(0)

                # Write final kv file in append mode
                write_kv(membuffer2, currsection_output)

            # If streaming to Splunk HEC is activated
            if use_splunk_http:

                # Rewind temp
                membuffer2.seek(0)

                # Transform to kv data and stream to http
                write_kv_to_http(membuffer2, splunk_metrics_index, "nmon_metrics_http")

        # close membuffer
        membuffer.close()
        membuffer2.close()

    # End for


# These are standard static sections common for all OS
for section in static_section:
    multi_dimension_metrics_fn(section)

# These sections are specific for Micro Partitions, can be AIX or PowerLinux
if OStype in ("AIX", "Linux", "Unknown"):
    for section in LPAR_static_section:
        multi_dimension_metrics_fn(section)

# Solaris specific
if OStype in ("Solaris", "Unknown"):
    for section in Solaris_static_section:
        multi_dimension_metrics_fn(section)

# nmon external
for section in nmon_external:
    multi_dimension_metrics_fn(section)


########################################################
# regular multi-dimension data managed as regular events
########################################################


def multi_dimension_events_fn(section):

    # for output file
    currsection_output = APP_VAR + '/nmon_perfdata_events.log'

    # currsection_meta = DATA_DIR + HOSTNAME + '_' + minute + '_' + section + '.meta.metrics.csv'

    # counter
    count = 0

    # sanity_check
    sanity_check = 1

    # Initialize num_cols_header to 0 (see sanity_check)
    num_cols_header = 0

    # Sequence to search for
    seq = str(section) + ',' + 'T'

    # define default values for metric store
    metric_category = metrics_dict(section)

    for line in data:

        # Extract sections
        if str(seq) in line:  # Don't use regex here for more performance

            # increment
            count += 1

    if count >= 1:

        # Open StringIO for temp in memory
        membuffer = StringIO()

        # counter
        count = 0

        for line in data:

            # Extract sections (manage specific case of CPUnn), and write to output
            myregex = r'^' + section + '|ZZZZ.+'

            find_section = re.match(myregex, line)
            if find_section:

                # Replace trouble strings
                line = subpctreplace(line)
                line = subreplace(line)

                # csv header

                # Extract header excluding data that always has Txxxx for timestamp reference
                myregex = '(' + section + ')\,([^T].+)'

                # Search for header
                fullheader_match = re.search(myregex, line)

                # Standard header extraction
                if fullheader_match:
                    fullheader = fullheader_match.group(2)

                    # Replace "." by "_" only for header
                    fullheader = re.sub("\.", '_', fullheader)

                    # Replace any blank space before comma only for header
                    fullheader = re.sub(", ", ',', fullheader)

                    header_match = re.search(r'([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9,]*)', fullheader)

                    if header_match:
                        header = header_match.group(2)

                        # header has been found
                        header_found = True

                        # increment
                        count += 1

                        # Write header
                        final_header = 'type' + ',' + 'serialnum' + ',' + 'hostname' + ',' + 'OStype' +\
                                       ',' + 'timestamp' + ',' + header + '\n'

                        # Number of separators in final header
                        num_cols_header = final_header.count(',')

                        # Write header
                        membuffer.write(final_header)

                # Extract timestamp

                # For Nmon V10 and more
                timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
                if timestamp_match:
                    ZZZZ_TIME = timestamp_match.group(2)
                    ZZZZ_DATE = timestamp_match.group(3)

                    # Replace month names with numbers
                    ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                    # Compose final timestamp
                    ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                    if is_windows:
                        ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                    else:
                        ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')\
                            .strftime('%s')

                        # in case datetime fails
                        if ZZZZ_epochtime == "%s":
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

                # Extract Data
                myregex = r'^' + section + '\,(T\d+)\,(.+)\n'
                perfdata_match = re.match(myregex, line)

                if perfdata_match:
                    perfdata = perfdata_match.group(2)

                    # increment
                    count += 1

                    # final_perfdata
                    final_perfdata = section + ',' + SN + ',' + HOSTNAME + ',' + OStype + ',' + \
                                     ZZZZ_epochtime + ',' + perfdata + '\n'

                    # Analyse the first line of data: Compare number of fields in data with number of fields
                    # in header
                    # If the number of fields is higher than header, we assume this section is not consistent
                    # and will be entirely dropped
                    # This happens in rare times (mainly with old buggy nmon version) that the header is bad
                    # formatted (for example missing comma between fields identification)
                    # For performance purposes, we will test this only with first line of data and assume the
                    # data sanity based on this result
                    if count == 2:

                        # Number of separators in final header
                        num_cols_perfdata = final_perfdata.count(',')

                        if num_cols_perfdata > num_cols_header:

                            msg = 'WARN: hostname: ' + HOSTNAME + ' :' + section +\
                                  ' section data is not consistent: ' + str(num_cols_perfdata) +\
                                  ' fields in data, ' + str(num_cols_header) \
                                  + ' fields in header, extra fields detected (more fields in data ' \
                                    'than header), dropping this section to prevent data inconsistency'
                            print(msg)

                            if colddata:
                                ref.write(msg + "\n")

                            # Affect a sanity check to 1, bad data
                            sanity_check = 1

                        else:

                            # Affect a sanity check to 0, good data
                            sanity_check = 0

                    # Write perf data
                    membuffer.write(final_perfdata)

        # Verify sanity check
        # Verify that the number of lines is at least 2 lines which should be the case if we are here (header + data)
        # In any case, don't allow empty files to kept in repository

        if sanity_check == 1:
            if os.path.isfile(currsection_output):
                os.remove(currsection_output)
        elif count < 1:
            if os.path.isfile(currsection_output):
                os.remove(currsection_output)
        else:

            # save Meta
            # meta(currsection_meta, currsection_output, section, metric_category, OStype, SN, HOSTNAME)

            # Show number of lines extracted
            result = section + " section: Wrote" + " " + str(count) + " line(s)"

            if not silent:
                print(result)

                if colddata:
                    ref.write(result + "\n")

            if not no_local_log:

                # Rewind temp
                membuffer.seek(0)

                # Write final kv file in append mode
                write_kv(membuffer, currsection_output)

            # If streaming to Splunk HEC is activated
            if use_splunk_http:

                # Rewind temp
                membuffer.seek(0)

                # Transform to kv data and stream to http
                write_kv_to_http(membuffer, splunk_events_index, "nmon_data_http")

        # close membuffer
        membuffer.close()


    # End for


# UPTIME is also managed as events
for section in nmon_external:
    if section == "UPTIME":
        multi_dimension_events_fn(section)

###################
# TOP section: has a specific structure with uncommon fields, needs to be treated separately
###################


def top_section_fn(section):

    # for the metric store
    currsection_output = APP_VAR + '/nmon_perfdata_metrics.log'

    # currsection_meta = DATA_DIR + HOSTNAME + '_' + minute + '_' + section + '.meta.metrics.csv'

    # counter
    count = 0

    # Sequence to search for
    seq = str(section) + ','

    # define default values for metric store
    metric_category = metrics_dict(section)
    metric_name = "os.unix.nmon." + metric_category + "." + section.lower()

    # AIX specific: some systems may generate the WLMclass dimension field
    top_has_wlm = False

    # Solaris specific: manage Project and Zone dimensions
    top_has_project = False

    for line in data:

        # Extract sections
        if str(seq) in line:  # Don't use regex here for more performance

            # increment
            count += 1

    if count >= 1:

        # Open StringIO for temp in memory
        membuffer = StringIO()
        membuffer2 = StringIO()

        # counter
        count = 0

        for line in data:

            # Extract sections, and write to output
            myregex = r'^' + 'TOP,.PID' + '|ZZZZ.+'
            find_section = re.match(myregex, line)
            if find_section:

                line = subpcttopreplace(line)
                line = subreplace(line)

                # csv header

                # Extract header excluding data that always has Txxxx for timestamp reference
                myregex = '(' + section + ')\,([^T].+)'
                fullheader_match = re.search(myregex, line)

                if fullheader_match:
                    fullheader = fullheader_match.group(2)

                    # Replace "." by "_" only for header
                    fullheader = re.sub("\.", '_', fullheader)

                    # Replace any blank space before comma only for header
                    fullheader = re.sub(", ", ',', fullheader)

                    header_match = re.search(r'([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9,]*)',
                                             fullheader)

                    if header_match:
                        header_part1 = header_match.group(1)
                        header_part2 = header_match.group(3)
                        header = header_part1 + header_part2

                        # increment
                        count += 1

                        membuffer.write(
                            'ZZZZ_epochtime' + ',' + header + '\n'),

                        # Manage AIX dim
                        if "WLMclass" in header:
                            top_has_wlm = True

                        # Manage Solaris dim
                        elif "Project" in header:
                            top_has_project = True

                # Extract timestamp

                # Nmon V9 and prior do not have date in ZZZZ
                # If unavailable, we'll use the global date (AAA,date)
                ZZZZ_DATE = '-1'
                ZZZZ_TIME = '-1'

                # For Nmon V10 and more

                timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
                if timestamp_match:
                    ZZZZ_TIME = timestamp_match.group(2)
                    ZZZZ_DATE = timestamp_match.group(3)

                    # Replace month names with numbers
                    ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                    ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                    if is_windows:
                        ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                    else:
                        ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')\
                            .strftime('%s')

                        # in case datetime fails
                        if ZZZZ_epochtime == "%s":
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

            # Extract Data
            perfdata_match = re.match('^TOP,([0-9]+),(T\d+),(.+)\n', line)
            if perfdata_match:
                perfdata_part1 = perfdata_match.group(1)
                perfdata_part2 = perfdata_match.group(3)
                perfdata = perfdata_part1 + ',' + perfdata_part2

                # increment
                count += 1

                # Write perf data

                membuffer.write(
                    ZZZZ_epochtime + ',' + perfdata + '\n'),

        # Rewind temp
        membuffer.seek(0)

        # re-init count
        count = 0

        writer = csv.writer(membuffer2)

        # Manage AIX dim
        if top_has_wlm:
            writer.writerow(
                ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                 'hostname', 'dimension_Command', 'dimension_PID', 'dimension_WLMclass', '_value'])
        # Manage Solaris dim
        elif top_has_project:
            writer.writerow(
                ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                 'hostname', 'dimension_Command', 'dimension_PID', 'dimension_Project', 'dimension_Zone',
                 '_value'])
        else:
            writer.writerow(
                ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                 'hostname', 'dimension_Command', 'dimension_PID', '_value'])

        # increment
        count += 1

        # csv reader
        reader = csv.DictReader(membuffer)

        # For AIX dim
        csv_WLMclass = "none"

        # For Solaris dim
        csv_Project = "none"
        csv_Zone = "none"

        for d in reader:
            csv_ZZZZ_epochtime = d.pop('ZZZZ_epochtime')
            csv_Command = d.pop('Command')
            csv_PID = d.pop('PID')

            # Manage AIX dim
            if top_has_wlm:
                csv_WLMclass = d.pop('WLMclass')

            # Manage Solaris dim
            elif top_has_project:
                csv_Project = d.pop('Project')
                csv_Zone = d.pop('Zone')

            for dimension, value in sorted(d.items()):

                # value must be null, must be a number, and to save money exclude non useful values
                if (value and is_number(value)) and (float(value) > 0):

                    # increment
                    count += 1

                    # concatenate the metric_name and dimension
                    metric = metric_name + '.' + dimension

                    # Manage AIX dim
                    if top_has_wlm:
                        row = [csv_ZZZZ_epochtime, metric, OStype, SN,
                               HOSTNAME, csv_Command, csv_PID, csv_WLMclass, value]

                    # Manage Solaris dim
                    elif top_has_project:
                        row = [csv_ZZZZ_epochtime, metric, OStype, SN,
                               HOSTNAME, csv_Command, csv_PID, csv_Project, csv_Zone, value]

                    else:
                        row = [csv_ZZZZ_epochtime, metric, OStype, SN,
                               HOSTNAME, csv_Command, csv_PID, value]

                    writer.writerow(row)

        # Verify that the number of lines is at least 2 lines which should be the case if we are here (header + data)
        # In any case, don't allow empty files to kept in repository
        if count < 1:
            if os.path.isfile(currsection_output):
                os.remove(currsection_output)
        else:

            # save Meta
            # meta(currsection_meta, currsection_output, section, metric_category, OStype, SN, HOSTNAME)

            # Show number of lines extracted
            result = section + " section: Wrote" + " " + str(count) + " line(s)"

            if not silent:
                print(result)

                if colddata:
                    ref.write(result + "\n")

            if not no_local_log:

                # Rewind temp
                membuffer2.seek(0)

                # Write final kv file in append mode
                write_kv(membuffer2, currsection_output)

            # If streaming to Splunk HEC is activated
            if use_splunk_http:

                # Rewind temp
                membuffer2.seek(0)

                # Transform to kv data and stream to http
                write_kv_to_http(membuffer2, splunk_metrics_index, "nmon_metrics_http")

        # close membuffer
        membuffer.close()
        membuffer2.close()

# End for

# Run
for section in top_section:

    top_section_fn(section)

###################
# UARG section: has a specific structure with uncommon fields, needs to be treated separately
###################

# Note: UARG is not continuously collected as progs arguments may not always change (mainly for real time)
# For this section specifically write from membuffer only

# UARG is applicable only for AIX and Linux hosts


def uarg_section_fn(section):

    # for the metric store
    currsection_output = APP_VAR + '/nmon_perfdata_events.log'

    # currsection_meta = DATA_DIR + HOSTNAME + '_' + minute + '_' + section + '.meta.metrics.csv'

    # counter
    count = 0

    # set oslevel default
    oslevel = "Unknown"

    # Sequence to search for
    seq = str(section) + ','

    # define default values for metric store
    metric_category = metrics_dict(section)

    for line in data:

        # Extract sections
        if str(seq) in line:  # Don't use regex here for more performance

            # increment
            count += 1

    if count >= 1:

        # Open StringIO for temp in memory
        membuffer = StringIO()

        # counter
        count = 0

        for line in data:

            # Extract sections, and write to output
            myregex = r'^' + 'UARG,.Time' + '|ZZZZ.+'
            find_section = re.match(myregex, line)
            if find_section:
                line = subpcttopreplace(line)
                line = subreplace(line)

                # csv header

                # Extract header excluding data that always has Txxxx for timestamp reference
                myregex = '(' + section + ')\,(.+)'
                fullheader_match = re.search(myregex, line)

                if fullheader_match:
                    fullheader = fullheader_match.group(2)

                    # Replace "." by "_" only for header
                    fullheader = re.sub("\.", '_', fullheader)

                    header_match = re.search(r'([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9,]*)',
                                             fullheader)

                    if header_match:
                        header_part1 = header_match.group(2)
                        header_part2 = header_match.group(3)
                        header = header_part1 + header_part2

                        # Specifically for UARG, set OS type based on header fields
                        os_match = re.search(r'PID,PPID,COMM,THCOUNT,USER,GROUP,FullCommand', header)

                        # Since V1.11, sarmon for Solaris implements UARG the same way Linux does
                        if os_match:
                            oslevel = 'AIX_or_Solaris'
                        else:
                            oslevel = 'Linux'

                        # increment
                        count += 1

                        # Write header
                        membuffer.write(
                            'type' + ',' + 'serialnum' + ',' + 'hostname' + ',' + 'OStype' + ',' +
                            'timestamp' + ',' + header + '\n'),

                # Extract timestamp

                # Nmon V9 and prior do not have date in ZZZZ
                # If unavailable, we'll use the global date (AAA,date)
                ZZZZ_DATE = '-1'
                ZZZZ_TIME = '-1'

                # For Nmon V10 and more

                timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
                if timestamp_match:
                    ZZZZ_TIME = timestamp_match.group(2)
                    ZZZZ_DATE = timestamp_match.group(3)

                    # Replace month names with numbers
                    ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                    ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                    if is_windows:
                        ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                    else:
                        ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S').strftime('%s')

                        # in case datetime fails
                        if ZZZZ_epochtime == "%s":
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

                # For Nmon V9 and less

                if ZZZZ_DATE == '-1':
                    ZZZZ_DATE = DATE
                    timestamp_match = re.match(r'^ZZZZ,(.+),(.+)\n', line)

                    if timestamp_match:
                        ZZZZ_TIME = timestamp_match.group(2)

                        # Replace month names with numbers
                        ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                        ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                        if is_windows:
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                        else:
                            ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')\
                                .strftime('%s')

                            # in case datetime fails
                            if ZZZZ_epochtime == "%s":
                                ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

            if oslevel == 'Linux':  # Linux OS specific header

                # Extract Data
                perfdata_match = re.match('^UARG,T\d+,([0-9]*),([a-zA-Z\-/_:\.0-9]*),(.+)\n', line)

                if perfdata_match:
                    # In this section, we statically expect 3 fields: PID,ProgName,FullCommand
                    # The FullCommand may be very problematic as it may almost contain any kind of char, comma included
                    # Let's separate groups and insert " delimiter

                    perfdata_part1 = perfdata_match.group(1)
                    perfdata_part2 = perfdata_match.group(2)
                    perfdata_part3 = perfdata_match.group(3)
                    perfdata = perfdata_part1 + ',' + perfdata_part2 + ',"' + perfdata_part3 + '"'

                    # increment
                    count += 1

                    # Write perf data
                    membuffer.write(
                        section + ',' + SN + ',' + HOSTNAME + ',' + OStype + ',' + ZZZZ_epochtime + ',' +
                        perfdata + '\n'),

            if oslevel == 'AIX_or_Solaris':  # AIX and Solaris OS specific header

                # Extract Data
                perfdata_match = re.match(
                    '^UARG,T\d+,\s*([0-9]*)\s*,\s*([0-9]*)\s*,\s*([a-zA-Z-/_:\.0-9]*)\s*,\s*([0-9]*)\s*,\s*([a-zA-Z-/_:'
                    '\.0-9]*\s*),\s*([a-zA-Z-/_:\.0-9]*)\s*,(.+)\n',
                    line)

                if perfdata_match:
                    # In this section, we statically expect 7 fields: PID,PPID,COMM,THCOUNT,USER,GROUP,FullCommand
                    # The FullCommand may be very problematic as it may almost contain any kind of char, comma included
                    # This field will have " separator added

                    perfdata_part1 = perfdata_match.group(1)
                    perfdata_part2 = perfdata_match.group(2)
                    perfdata_part3 = perfdata_match.group(3)
                    perfdata_part4 = perfdata_match.group(4)
                    perfdata_part5 = perfdata_match.group(5)
                    perfdata_part6 = perfdata_match.group(6)
                    perfdata_part7 = perfdata_match.group(7)

                    perfdata = perfdata_part1 + ',' + perfdata_part2 + ',' + perfdata_part3 + ',' + perfdata_part4 \
                               + ',' + perfdata_part5 + ',' + perfdata_part6 + ',"' + perfdata_part7 + '"'

                    # increment
                    count += 1

                    # Write perf data
                    membuffer.write(
                        section + ',' + SN + ',' + HOSTNAME + ',' + OStype + ',' + ZZZZ_epochtime + ',' +
                        perfdata + '\n'),

        # Verify that the number of lines is at least 2 lines which should be the case if we are here (header + data)
        # In any case, don't allow empty files to kept in repository
        if count > 1:

            # Show number of lines extracted
            result = section + " section: Wrote" + " " + str(count) + " line(s)"

            if not silent:
                print(result)

                if colddata:
                    ref.write(result + "\n")

            if not no_local_log:

                # Rewind temp
                membuffer.seek(0)

                # Write final kv file in append mode
                write_kv(membuffer, currsection_output)

            # If streaming to Splunk HEC is activated
            if use_splunk_http:

                # Rewind temp
                membuffer.seek(0)

                # Transform to kv data and stream to http
                write_kv_to_http(membuffer, splunk_events_index, "nmon_data_http")

            # close membuffer
            membuffer.close()

            # save Meta
            # meta(currsection_meta, currsection_output, section, metric_category, OStype, SN, HOSTNAME)

# End for

if OStype in ('AIX', 'Linux', 'Solaris', 'Unknown'):
    for section in uarg_section:
        uarg_section_fn(section)

#####################################################################
# regular mono-dimension data managed as metrics for the metric store
#####################################################################


def mono_dimension_events_fn(section):

    # for the metric store
    currsection_output = APP_VAR + '/nmon_perfdata_metrics.log'

    # currsection_meta = DATA_DIR + HOSTNAME + '_' + minute + '_' + section + '.meta.metrics.csv'

    # Sequence to search for
    seq = str(section) + ',' + 'T'

    # define default values for metric store
    metric_category = metrics_dict(section)
    metric_name = "os.unix.nmon." + metric_category + "." + section.lower()

    # verify if this is a DISK incremented section
    metric_increment_match = re.match("^(DISK[A-Z]*)\d*", section)
    if metric_increment_match:
        submetric_name = metric_increment_match.group(1)
        metric_name = "os.unix.nmon." + metric_category + "." + submetric_name.lower()

    # counter
    count = 0

    # event counter
    event_count = 1

    # sanity_check
    sanity_check = 1

    # Initialize num_cols_header to 0 (see sanity_check)
    num_cols_header = 0

    for line in data:

        # Extract sections
        if str(seq) in line:  # Don't use regex here for more performance

            # increment
            count += 1

    if count >= 1:

        # Open StringIO for temp in memory
        membuffer = StringIO()
        membuffer2 = StringIO()

        # counter
        count = 0

        for line in data:

            # Extract sections, and write to output
            myregex = r'^' + section + '[0-9]*' + '|ZZZZ.+'
            find_section = re.match(myregex, line)

            if find_section:

                line = subpctreplace(line)
                line = subreplace(line)

                # csv header

                # Extract header excluding data that always has Txxxx for timestamp reference
                myregex = '(' + section + ')\,([^T].+)'
                fullheader_match = re.search(myregex, line)

                if fullheader_match:
                    fullheader = fullheader_match.group(2)

                    # Replace "." by "_" only for header
                    fullheader = re.sub("\.", '_', fullheader)

                    # Replace any blank space before comma only for header
                    fullheader = re.sub(", ", ',', fullheader)

                    # Remove any blank space still present in header
                    fullheader = re.sub(" ", '', fullheader)

                    header_match = re.match(r'([a-zA-Z\-/_0-9]+,)([a-zA-Z\-/_0-9,]*)', fullheader)

                    if header_match:
                        header = header_match.group(2)

                        # Set the header
                        final_header = 'ZZZZ_epochtime' + ',' + header + '\n'

                        # increment
                        count += 1

                        # Number of separators in final header
                        num_cols_header = final_header.count(',')

                        # Write header
                        membuffer.write(final_header),

                # Extract timestamp

                # Nmon V9 and prior do not have date in ZZZZ
                # If unavailable, we'll use the global date (AAA,date)
                ZZZZ_DATE = '-1'
                ZZZZ_TIME = '-1'

                # For Nmon V10 and more

                timestamp_match = re.match(r'^ZZZZ,(.+),(.+),(.+)\n', line)
                if timestamp_match:
                    ZZZZ_TIME = timestamp_match.group(2)
                    ZZZZ_DATE = timestamp_match.group(3)

                    # Replace month names with numbers
                    ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                    ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                    if is_windows:
                        ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                    else:
                        ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S').strftime('%s')

                        # in case datetime fails
                        if ZZZZ_epochtime == "%s":
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

                # For Nmon V9 and less

                if ZZZZ_DATE == '-1':
                    ZZZZ_DATE = DATE
                    timestamp_match = re.match(r'^ZZZZ,(.+),(.+)\n', line)

                    if timestamp_match:
                        ZZZZ_TIME = timestamp_match.group(2)

                        # Replace month names with numbers
                        ZZZZ_DATE = monthtonumber(ZZZZ_DATE)

                        ZZZZ_timestamp = ZZZZ_DATE + ' ' + ZZZZ_TIME

                        if is_windows:
                            ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))
                        else:
                            ZZZZ_epochtime = datetime.datetime.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')\
                                .strftime('%s')

                            # in case datetime fails
                            if ZZZZ_epochtime == "%s":
                                ZZZZ_epochtime = int(time.mktime(time.strptime(ZZZZ_timestamp, '%d-%m-%Y %H:%M:%S')))

                # Extract Data
                myregex = r'^' + section + '\,(T\d+)\,(.+)\n'
                perfdata_match = re.match(myregex, line)
                if perfdata_match:
                    perfdata = perfdata_match.group(2)

                    # final perfdata
                    final_perfdata = ZZZZ_epochtime + ',' + perfdata + '\n'

                    # increment
                    count += 1

                    # Analyse the first line of data: Compare number of fields in data with number of fields
                    # in header
                    # If the number of fields is higher than header, we assume this section is not consistent and
                    # will be entirely dropped
                    # This happens in rare times (mainly with old buggy nmon version) that the header is bad
                    # formatted (for example missing comma between fields identification)
                    # For performance purposes, we will test this only with first line of data and assume the data
                    # sanity based on this result
                    if count == 2:

                        # Number of separators in final header
                        num_cols_perfdata = final_perfdata.count(',')

                        if num_cols_perfdata > num_cols_header:

                            msg = 'WARN: hostname: ' + HOSTNAME + ' :' + section +\
                                  ' section data is not consistent: ' + str(num_cols_perfdata) +\
                                  ' fields in data, ' + str(num_cols_header) +\
                                  ' fields in header, extra fields detected (more fields in data than header),' \
                                  ' dropping this section to prevent data inconsistency'
                            print(msg)

                            if colddata:
                                ref.write(msg + "\n")

                            if debug:
                                print("\nDebug information: header content:")
                                print(final_header)
                                print("Debug information: data sample:")
                                print(final_perfdata)

                            # Affect a sanity check to 1, bad data
                            sanity_check = 1

                            # If section is NET, create an empty state file
                            if section == "NET" and not colddata:
                                open(OUTDATED_NETIF_NMON_STATE, 'a').close()

                        else:

                            # Affect a sanity check to 0, good data
                            sanity_check = 0

                    # Write perf data
                    membuffer.write(ZZZZ_epochtime + ',' + perfdata + '\n'),

        if sanity_check == 0:

            # Reset counter
            count = 0

            # Rewind temp
            membuffer.seek(0)

            # Set writer
            writer = csv.writer(membuffer2)

            # For JFSFILE and JFSINODE, we use "dimension_mount" instead of regular "dimension_device" for the
            # mount point dimension
            # this is due to make easier the merge operation between JFSFILE and DF_STORAGE external collection

            if section == "JFSFILE" or section == "JFSINODE":
                writer.writerow(
                    ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                     'hostname', 'dimension_mount', '_value'])

            else:
                writer.writerow(
                    ['metric_timestamp', 'metric_name', 'OStype', 'serialnum',
                     'hostname', 'dimension_device', '_value'])

            # increment
            count += 1

            # csv reader
            reader = csv.DictReader(membuffer)

            for d in reader:
                csv_ZZZZ_epochtime = d.pop('ZZZZ_epochtime')
                for dimension, value in sorted(d.items()):

                    # value must be null, and must be a number, must not be equal to 0 by default
                    if show_zero_values:

                        if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                 or value == "-0.0" or value == '-nan'):

                            # increment
                            event_count += 1

                            row = [csv_ZZZZ_epochtime, metric_name, OStype, SN, HOSTNAME,
                                   dimension, value]
                            writer.writerow(row)

                    else:

                        if (value and is_number(value)) and not (value == "-1.0" or value == "-1"
                                                                 or value == "0" or value == "0.0"
                                                                 or value == "-0.0" or value == "0.00"
                                                                 or value == '-nan'):
                            # increment
                            event_count += 1

                            row = [csv_ZZZZ_epochtime, metric_name, OStype, SN, HOSTNAME,
                                   dimension, value]
                            writer.writerow(row)

                    # End for

            # Verify that the number of lines is at least 2 lines which should be the case if
            #  we are here (header + data)
            # In any case, don't allow empty files to kept in repository
            if event_count < 2:
                if os.path.isfile(currsection_output):
                    os.remove(currsection_output)
            else:

                # save Meta
                # meta(currsection_meta, currsection_output, section, metric_category, OStype, SN, HOSTNAME)

                # Show number of lines extracted
                result = section + " section: Wrote" + " " + str(event_count) + " line(s)"

                if not silent:
                    print(result)

                    if colddata:
                        ref.write(result + "\n")

                if not no_local_log:

                    # Rewind temp
                    membuffer2.seek(0)

                    # Write final kv file in append mode
                    write_kv(membuffer2, currsection_output)

                # If streaming to Splunk HEC is activated
                if use_splunk_http:

                    # Rewind temp
                    membuffer2.seek(0)

                    # Transform to kv data and stream to http
                    write_kv_to_http(membuffer2, splunk_metrics_index, "nmon_metrics_http")

                # close membuffer
                membuffer.close()
                membuffer2.close()

        elif sanity_check == 0:

            # Discard memory membuffer
            membuffer.close()
            membuffer2.close()

            # End for

########################
# Disk* Dynamic Sections
########################

# Because Big systems can a very large number of drives, Nmon create a new section for each step of 150 devices
# We allow up to 20 x 150 devices to be managed
# This will create a csv for each section (DISKBUSY, DISKBUSY1...), Splunk will manage this using a wildcard when
# searching for data
for section in dynamic_section1:
    mono_dimension_events_fn(section)

# Then proceed to sub section if any
for subsection in dynamic_section1:

    persubsection = [subsection + "1", subsection + "2", subsection + "3", subsection + "4", subsection + "5",
                  subsection + "6", subsection + "7", subsection + "8", subsection + "9", subsection + "10",
                  subsection + "11", subsection + "12", subsection + "13", subsection + "14", subsection + "15",
                  subsection + "17", subsection + "18", subsection + "19"]

    for section in persubsection:
        mono_dimension_events_fn(section)

########################
# Other Dynamic Sections
########################

for section in dynamic_section2:
    mono_dimension_events_fn(section)

#####################
# disk extended stats
#####################

# disks extended statistics
for section in disk_extended_section:
    mono_dimension_events_fn(section)

###########################
# AIX Only Dynamic Sections
###########################

# Run
if OStype in ("AIX", "Unknown"):
    for section in AIX_dynamic_various:
        mono_dimension_events_fn(section)
    for section in AIX_WLM:
        mono_dimension_events_fn(section)

##########################
# nmon external transposed
##########################

# nmon external with transposition
for section in nmon_external_transposed:
    mono_dimension_events_fn(section)

##################
# Solaris specific
##################

# Run
if OStype in ("Solaris", "Unknown"):
    for section in solaris_WLM:
        mono_dimension_events_fn(section)

    for section in solaris_VxVM:
        mono_dimension_events_fn(section)

    for section in solaris_dynamic_various:
        mono_dimension_events_fn(section)

##########################
# Move final Perf csv data
##########################

# cd to directory
os.chdir(DATA_DIR)

# current time
current_time = time.time()

# Move final perf data
for xfile in glob.glob('*.csv'):
    src = DATA_DIR + xfile
    dst = DATAFINAL_DIR + xfile
    os.rename(src, dst)

# Splunk HEC - Finally stream in batch mode and remove the batch file
if use_splunk_http:
    stream_to_splunk_http(splunk_http_url, splunk_http_token)

    if os.path.isfile(SPLUNK_HEC_BATCHFILE):
        os.remove(SPLUNK_HEC_BATCHFILE)

###################
# End
###################

if silent:
    # Print an informational message if running in silent mode
    print("Output mode is configured to run in minimal mode using the --silent option")

# Time required to process
end_time = time.time()
result = "Elapsed time was: %g seconds" % (end_time - start_time)
print(result)

if colddata:
    ref.write(result + "\n")

# exit
sys.exit(0)
