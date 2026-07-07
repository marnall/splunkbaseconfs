#
# Splunk/NetWitness REST API scripted input
# Version : 0.9.1
# Date: 05 Jul 2022
#
# written by Rui Ataide <rataide+splunkapps@gmail.com>
#
# This software is provided "as is" without express or implied warranty or support
#
#  == CHANGELOG ==
# - Version 0.9.1: (05 Jul 2022)
#   > Update Contact Details
# - Version 0.9.0: (05 Oct 2020)
#   > Ported to Python3 for Splunk 8.0
# - Version 0.8.5: (25 Jun 2018)
#   > Use http://docs.splunk.com/Documentation/Splunk/6.0/AdvancedDev/SetupExampleCredentials to avoid storing credentials in clear-text
# - Version 0.8.4: (24 Apr 2017)
#   > FIX: Changed TLS negotiation from TLSv1 to just TLS to support latest version using TLS 1.2
# - Version 0.8.3: (07 Apr 2017)
#   > FIX: Parsing of child devices for newer versions of SA 
#   > Matched script and app version numbers
#   > Updated Decoder Dashboard for better rendering of packet drops with sparkline
# - Version 0.8.1: (03 Jun 2014)
#   > FIX: Threading code for clean thread exit on completion
# - Version 0.7: (28 May 2013)
#   > Includes fix_ssl_version() to replace hack of Python's ssl.py
#   > Use threads to collect data, larger environments will need this. Current number of threads hardcoded
#   > Allow user to specify 'nwadmin' configuration file as an argument to allow for multiple instances of data collection
#     - If none is specified 'nwadmin.conf' will be used by default 
#   > Changed output format to be all key value pairs (Might break users custom content extractions)
#     - Change from "<service>[<path>]:" to "service=<service> path=<path> "
# - Version 0.6.7: (07 Nov 2012)
#   > Improved Error logging for exceptions other than urllib2 exceptions
# - Version 0.6: (18 Oct 2012)
#   > Log successful runs for better stats dashboard
# - Version 0.4: (09 Sep 2012)
#   > Added code to pull connected device stats for brokers
# - Version 0.3: (05 Sep 2012)
#   > Using timeout on web calls by default they seem hang forever (Timeout hardcoded at 5sec)
# - Version 0.2: (23 Aug 2012)
#   > Added code to pull connected device stats for concentrators
# - Version 0.1: (11 Jun 2012)

import xml.dom.minidom
import urllib.request, urllib.error, urllib.parse
import re
import time
import sys
import traceback
import threading
import queue


stats_path = { 'decoder' : ['/decoder/stats', '/decoder/parsers/stats', '/database/stats', '/index/stats', '/sdk/stats', '/sys/stats'] ,
               'concentrator' : ['/concentrator/stats', '/database/stats', '/index/stats', '/sdk/stats', '/sys/stats'],
               'broker' : ['/broker/stats', '/index/stats', '/sdk/stats', '/sys/stats'],
               'appliance' : ['/appliance/stats/device', '/appliance/stats/filesystem', '/appliance/stats/temperature', '/sys/stats'] }

def fix_ssl_version():
    import ssl

    orig_wrap_socket = ssl.wrap_socket

    def wrap_socket(*args, **kargs):
        kargs['ssl_version'] = ssl.PROTOCOL_TLS
        return orig_wrap_socket(*args, **kargs)

    ssl.wrap_socket = wrap_socket


# access the credentials in /servicesNS/nobody/netwitness_query/admin/passwords
def getCredentials(sessionKey):
   import splunk.entity as entity
   myapp = 'netwitness_admin'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,owner='nobody', sessionKey=sessionKey)
   except Exception as e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials
   for i, c in list(entities.items()):
        return c['username'], c['clear_password']
   raise Exception("No credentials have been found")


def get_stats(opener, url, tag):
    # use the opener to fetch a URL
    site = opener.open(url,timeout=_TIMEOUT)
    doc = xml.dom.minidom.parseString(site.read())
    a_str = str(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time()))) + " " + tag + ""
    for node in doc.getElementsByTagName("node"):
        child = node.childNodes
        name = str(node.getAttribute("name"))
        try:
            value = str(child[0].data)
        except:
            value = 'NULL'
        if (re.search('[\s+,=]', value)):
            value = '"' + value + '"'
        a_str += ' ' + name.replace(".", "_") + '=' + value
    return a_str

def worker():
    name = (threading.current_thread()).getName()
    while True:
        (opener,url,tag) = q.get()
        if (tag == "Terminate"):
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' received terminate command.\r\n')
            q.task_done()
            break
        else: 
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' processing url=' + url + '\r\n')
            try:
                # for eachhost in webhost.readlines():
                result = get_stats(opener,url,tag)
                with some_rlock:
                    print(result)
            except urllib.error.URLError as e:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Thread name=' + name + ' error=' + str(e) + ' processing url=' + url + '\r\n')
                c = sys.exc_info()[0]
                e = sys.exc_info()[1]
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Reason="' + str(e) + '" Class="' + str(c) + '"\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
            except:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Thread name=' + name + ' error=' + str(sys.exc_info()[0]) + ' processing url=' + url + '\r\n')
                c = sys.exc_info()[0]
                e = sys.exc_info()[1]
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Reason="' + str(e) + '" Class="' + str(c) + '"\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())

            q.task_done()

def process_device_service(PROTOCOL, SERVER, PORT, USERNAME, PASSWORD, TYPE):
    # create a password manager
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    # Add the username and password.
    # If we knew the realm, we could use it instead of None.
    password_mgr.add_password(None, PROTOCOL + "://" + SERVER + ":" + PORT, USERNAME, PASSWORD)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    # create "opener" (OpenerDirector instance)
    opener = urllib.request.build_opener(handler)
    for path in stats_path[TYPE]:
        a_url = PROTOCOL + "://" + SERVER + ":" + PORT + path + "?force-content-type=text/xml"
        q.put((opener, a_url, SERVER + ": service=" + TYPE + " path=" + path + ""))
    # If device is a concentrator find which devices it connects to and pull aggregation stats for those
    if ( TYPE == 'concentrator' or TYPE == 'broker' ):
        a_url = PROTOCOL + "://" + SERVER + ":" + PORT + "/" + TYPE + "/devices?force-content-type=text/plain"
        devices = opener.open(a_url,timeout=_TIMEOUT).read()
        for device in devices.splitlines():
            #device = device.rstrip(' =')
            device = re.search('.*?/devices/([^/]*)/.*',device.decode(encoding="ascii", errors="ignore")).group(1)
            a_url = PROTOCOL + "://" + SERVER + ":" + PORT + "/" + TYPE + "/devices/" + device + "/stats?force-content-type=text/xml"
            q.put((opener, a_url, SERVER + ": service=" + TYPE + " path=" + "/" + TYPE + "/devices/" + device + "/stats"))

## MAIN STARTS HERE ##

sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: SSL, applying TLS fix\n')
fix_ssl_version()
 
MAX_THREADS = 16
q = queue.Queue()
some_rlock = threading.RLock()

for i in range(MAX_THREADS):
     t = threading.Thread(target=worker,name='NWAdmin-Worker-'+str(i+1))
     # t.daemon = True
     t.start()
try:
    # Just take the first parameter passed to the application as the configuration file name.
    config_file = sys.argv[1]
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Using new configuration file: ' + config_file + '.conf\r\n')
except:
    config_file = 'nwadmin'

# Try to get authentication from Splunk PassThrough REST Endpoint for all connections
try:
    sessionKey = sys.stdin.readline().strip()
    if len(sessionKey) == 0:
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Did not receive a session key from splunkd. Please enable passAuth in inputs.conf. Trying configuration file ' + config_file + '.conf.\r\n')
        SPLK_PASS = 'ReadFromFile'
    else:
        # now get app credentials - might exit if no creds are available. _USERNAME will be re-read from config file
        USERNAME, SPLK_PASS = getCredentials(sessionKey)
        #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - DEBUG: Password read from Splunk is "' + USERNAME + ':' + SPLK_PASS + '"\r\n')

except:
    pass 
try:
    # Will make this part of the Splunk config file later set low as script runs every minute
    _TIMEOUT = 30
    # read configuration from nwsd.conf in the app/default or app/local directory
    from splunk.clilib.cli_common import getMergedConf
    for key in list(getMergedConf(config_file).keys()):
        try:
            _PROTOCOL = getMergedConf(config_file)[key]['protocol']
            _SERVER = getMergedConf(config_file)[key]['server']
            _PORT = getMergedConf(config_file)[key]['port']
            _USERNAME = getMergedConf(config_file)[key]['username']
            #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - DEBUG: Password read from Splunk is "' + SPLK_PASS + '"\r\n')
            if (SPLK_PASS == 'ReadFromFile' ):
                _PASSWORD = getMergedConf(config_file)[key]['password']
            else: 
                _PASSWORD = SPLK_PASS
            _TYPE = getMergedConf(config_file)[key]['type']
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Processing ' + key + ' entry from configuration file \'' + config_file + '\'\r\n')
            try:
                # for eachhost in webhost.readlines():
                process_device_service(_PROTOCOL, _SERVER, _PORT, _USERNAME, _PASSWORD, _TYPE)
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Successfully processed entry ' + key + ' for ' + _TYPE + ' device at ' + _PROTOCOL + '://' + _SERVER + ':' + _PORT + '/\r\n')
            except urllib.error.URLError as e:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: ' + str(e) + ' processing ' + _TYPE + ' device at ' + _PROTOCOL + '://' + _SERVER + ':' + _PORT + '/\r\n')
                c = sys.exc_info()[0]
                e = sys.exc_info()[1]
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Reason="' + str(e) + '" Class="' + str(c) + '"\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
            except:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: ' + str(sys.exc_info()[0]) + ' processing ' + _TYPE + ' device at ' + _PROTOCOL + '://' + _SERVER + ':' + _PORT + '/\r\n')
                c = sys.exc_info()[0]
                e = sys.exc_info()[1]
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Reason="' + str(e) + '" Class="' + str(c) + '"\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
        except:
            c = sys.exc_info()[0]
            e = sys.exc_info()[1]
            if (key != 'default'):
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Processing ' + key + ' entry from configuration file Reason="' + str(e) + '" Class="' + str(c) + '"\r\n')
    q.join()
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Successfully terminated processing' + '\r\n')
    # End All Threads
    for i in range(MAX_THREADS):
        q.put((None,None,"Terminate"))
    q.join()
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Successfully terminated all threads' + '\r\n')
except:
    #pass          
    c = sys.exc_info()[0]
    e = sys.exc_info()[1]
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Reason="' + str(e) + '" Class="' + str(c) + '"\n')
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
