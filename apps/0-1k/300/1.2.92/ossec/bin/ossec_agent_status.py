#!/opt/splunk/bin/python
############################################################
#
# For all enabled remote agents, collect agent status.
#
############################################################
import sys
import os


# Before importing, make sure we're running from the /bin
# directory. Splunk scripted inputs may be running in /
# by default.
if os.getcwd() == '/' and 'SPLUNK_HOME' in os.environ:
    wd = os.environ['SPLUNK_HOME'] + '/etc/apps/ossec/bin'
    if os.path.isdir(wd):
        os.chdir(wd)
import pyOSSEC


# Enable debugging?
if '-v' in sys.argv:
    VERBOSE = True
else:
    VERBOSE = False


# Get the server configuration
cfg = pyOSSEC.parse_config()
if len(cfg) == 0:
    print 'WARNING: No agent configuration found. See ossec_servers.conf'

if VERBOSE:
        print 'Server config: '
        print cfg
        print


# Retrieve agent status from each server
for hostname in cfg:
    hostconf = cfg[hostname]

    if 'AGENT_CONTROL' in hostconf:
        if VERBOSE:  print 'Querying', hostname

        if len(hostconf['AGENT_CONTROL']) > 0:
            try:
                ossec = pyOSSEC.OSSECServer(hostname)
                if VERBOSE: print 'OSSEC interface initialized.'

                status = ossec.agent_status()
                if VERBOSE: print 'Agent status retrieved...'

                # Destroy the object and release any file locks
                ossec = None
            except Exception, e:
                status = [ 'Error: Unable to run data collection. ' + str(e) ]
                ossec = None
            
            for line in status:
                line = 'Server: ' + hostname + ', ' + line
                print line

