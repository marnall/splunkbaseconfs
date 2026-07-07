#
# Splunk/NetWitness REST API Query Meta scripted input
# Version : 0.9.4	
# Date: 05 Jul 2022
#
# written by Rui Ataide <rataide+splunkapps@gmail.com>
#
# This software is provided "as is" without express or implied warranty or support
#
#  == CHANGELOG ==
# - Version 0.9.5: (05 Jul 2022)
#   > Update Contact Details
# - Version 0.9.4: (06 Aug 2021)
#   > Logging now uses Python's logging module and destination of app log messages can be directed to a file.
#     - Default value is "stderr" to continue to log to STDERR for backwards compatibilty although message format is slightly changed
#   > Added new configuration option SKIP_DELTA
#     - If data is older than SKIP_DELTA seconds the app will jump to the end of NWDB to avoid severe fall-behind issues
# - Version 0.9.3: (02 Jul 2021)
#   > Added code to get the first set of credentials for own app only. In some cases other credentials are returned
#   > Added additional logging around credential retrieval from Splunk via passAuth = splunk-system-user
# - Version 0.9.2: (05 Aug 2020)
#   > Fixed TypeError issue with hashing
# - Version 0.9.1: (31 Jul 2020)
#   > Addressed AppInspect Feedback
# - Version 0.9.0: (30 Jul 2020)
#   > Ported to Python3 for Splunk 8.0
# - Version 0.8.11: (17 Jun 2018)
#   > New Feature: Split SMTP sessions into multiple events based on mailfrom meta key from IR Expanded Parser
# - Version 0.8.10: (07 Jun 2018)
#   > New Feature: Added the ability to "mask/hash" any field via configuration option
#     - Also includes option to keep a prefix of specified length
#   > Added new hunting pack keys to props/transforms for MV_ADD issue
# - Version 0.8.9: (13 Dec 2017)
#   > Changed logic to attempt to obtain new credentials on 401 Unauthorized errors
# - Version 0.8.8: (24 Apr 2017)
#   > FIX: Changed TLS negotiation from TLSv1 to just TLS to support latest version using TLS 1.2
# - Version 0.8.6: (22 Feb 2017)
#   > Changed the loading of the JSON response to better handle enconding errors
# - Version 0.8.5: (22 Jun 2016)
#   > Changed main while True loop further so it recovers from every possible error
#   > Two new configuration settings SLEEP & VERBOSE
# - Version 0.8.4: (18 May 2016)
#   > Changed handling of summary query errors, we can no longer exit as the script now runs on a loop
#     - Sleeping 60 seconds and then trying again
# - Version 0.8.3: (18 Dec 2015)
#   > Changed read/write MID file functions to expand ENV vars (e.g. $SPLUNK_HOME)
#   > ERROR to WARN on passAuth missing as we check config file too
# - Version 0.8.1: (06 Nov 2015)
#   > Changed design to loop directly in script instead of being launched regularly via inputs.conf
#     - Currently sleeps 5 seconds between collections
#     - Should massively improve performance and reduce fall-behind situations
#   > FIX: id1 needs to be lower than id2 with API, extra check put in to never do reverse queries
# - Version 0.8.0: (22 Oct 2015)
#   > Use http://docs.splunk.com/Documentation/Splunk/6.0/AdvancedDev/SetupExampleCredentials to avoid storing credentials in clear-text
# - Version 0.7.0: (12 Mar 2015)
#   > Added support for SDK/API changes introduced in 10.4 (id2 can no longer be missing or zero)
#   > From 10.4 Release Notes:
#     - New option on query call to reverse returned result set to go from newest to oldest (reverse id1/id2 parameters).
# - Version 0.6.4: (23 Oct 2013)
#   > Removed default settings hard-coded in script (They don't make sense)
#   > Per config setting error logging and exit on configuration errors
# - Version 0.6.3: (18 Oct 2013)
#   > Cap running batches to the last meta id from the first run to avoid endless running as end of meta moves forward
# - Version 0.6.2: (14 Oct 2013)
#   > Added config filename to event to help tracking if multiple inputs are executed for different queries
# - Version 0.6.1: (04 Sep 2013)
#   > Improved error logging on get_summary() call
#   > Remove trailing '/' if one exists in TOP_LEVEL_URL to avoid '//' in requests and log messages
# - Version 0.6: (29 May 2013)
#   > FIX: Meta id was rolling over back to 0 when the end of a complete session matched the end of the REST call return dataset
# - Version 0.5: (08 Apr 2013)
#   > Initial release (Some code copied from existing Splunk App)

# TODO: Perform basic validation of NW_QUERY, at least inclusion of time meta

import json
import urllib.request, urllib.error, urllib.parse
import re
import time
import sys
import traceback
import os
import hashlib
import logging


# Splunk CIM mappings
nw_2_splunk = { 'action' : 'action' , 'ad.domain.dst' : 'affected_user_group' ,
                'ad.domain.src' : 'user_group' , 'ad.username.dst' : 'affected_user' ,
                'ad.username.src' : 'user' , 'alert.id' : 'rule_number' ,
                'client' : 'http_user_agent' , 'did' : 'dvc_host' ,
                'city.dst' : 'dest_city' , 'country.dst' : 'dest_country' ,
                'domain.dst' : 'dest_domain' , 'ip.dst' : 'dest_ip' ,
                'email.dst' : 'recipient' , 'email.src' : 'sender' ,
                'ipv6.dst' : 'dest_ipv6' , 'latdec.dst' : 'dest_lat' ,
                'longdec.dst' : 'dest_long' , 'org.dst' : 'dest_org' ,
                'email.subject' : 'subject' , 'eth.dst' : 'dest_mac' ,
                'eth.src' : 'src_mac' , 'filename' : 'file_name' ,
                'alias.host' : 'dest_host' , 'ip.proto' : 'proto' ,
                'ipv6.proto' : 'proto' , 'city.src' : 'src_city' ,
                'country.src' : 'src_country' , 'domain.src' : 'src_domain' ,
                'ip.src' : 'src_ip' , 'ipv6.src' : 'src_ipv6' ,
                'latdec.src' : 'src_lat' , 'longdec.src' : 'src_long' ,
                'org.src' : 'src_org' , 'subject' : 'subject' ,
                'tcp.dstport' : 'dest_port' , 'tcp.srcport' : 'src_port' ,
                'udp.srcport' : 'src_port' , 'udp.dstport' : 'dest_port' ,
                'useragent' : 'http_user_agent' , 'wlan.ssid' : 'ssid' }

nw_hash = { }

def getprotobynumber(proto):
    proto_number_to_name = { '0' : 'IP' , '1' : 'ICMP' , '2' : 'IGMP' , '3' : 'GGP' , '4' : 'IP-ENCAP' , '5' : 'ST2' , '6' : 'TCP' ,
                            '7' : 'CBT' , '8' : 'EGP' , '9' : 'IGP' , '10' : 'BBN-RCC-MON' , '11' : 'NVP-II' , '12' : 'PUP' , '13' : 'ARGUS' ,
                            '14' : 'EMCON' , '15' : 'XNET' , '16' : 'CHAOS' , '17' : 'UDP' , '18' : 'MUX' , '19' : 'DCN-MEAS' , '20' : 'HMP' ,
                            '21' : 'PRM' , '22' : 'XNS-IDP' , '23' : 'TRUNK-1' , '24' : 'TRUNK-2' , '25' : 'LEAF-1' , '26' : 'LEAF-2' , '27' : 'RDP' ,
                            '28' : 'IRTP' , '29' : 'ISO-TP4' , '30' : 'NETBLT' , '31' : 'MFE-NSP' , '32' : 'MERIT-INP' , '33' : 'SEP' , '34' : '3PC' ,
                            '35' : 'IDPR' , '36' : 'XTP' , '37' : 'DDP' , '38' : 'IDPR-CMTP' , '39' : 'TP++' , '40' : 'IL' , '41' : 'IPV6' ,
                            '42' : 'SDRP' , '43' : 'IPV6-ROUTE' , '44' : 'IPV6-FRAG' , '45' : 'IDRP' , '46' : 'RSVP' , '47' : 'GRE' , '48' : 'MHRP' ,
                            '49' : 'BNA' , '50' : 'ESP' , '51' : 'AH' , '52' : 'I-NLSP' , '53' : 'SWIPE' , '54' : 'NARP' , '55' : 'MOBILE' ,
                            '56' : 'TLSP' , '57' : 'SKIP' , '58' : 'IPV6-ICMP' , '59' : 'IPV6-NONXT' , '60' : 'IPV6-OPTS' , '62' : 'CFTP' , '64' : 'SAT-EXPAK' ,
                            '65' : 'KRYPTOLAN' , '66' : 'RVD' , '67' : 'IPPC' , '69' : 'SAT-MON' , '70' : 'VISA' , '71' : 'IPCV' , '72' : 'CPNX' ,
                            '73' : 'CPHB' , '74' : 'WSN' , '75' : 'PVP' , '76' : 'BR-SAT-MON' , '77' : 'SUN-ND' , '78' : 'WB-MON' , '79' : 'WB-EXPAK' ,
                            '80' : 'ISO-IP' , '81' : 'VMTP' , '82' : 'SECURE-VMTP' , '83' : 'VINES' , '84' : 'TTP' , '85' : 'NSFNET-IGP' , '86' : 'DGP' ,
                            '87' : 'TCF' , '88' : 'EIGRP' , '89' : 'OSPFIGP' , '90' : 'Sprite-RPC' , '91' : 'LARP' , '92' : 'MTP' , '93' : 'AX.25' ,
                            '94' : 'IPIP' , '95' : 'MICP' , '96' : 'SCC-SP' , '97' : 'ETHERIP' , '98' : 'ENCAP' , '100' : 'GMTP' , '101' : 'IFMP' ,
                            '102' : 'PNNI' , '103' : 'PIM' , '104' : 'ARIS' , '105' : 'SCPS' , '106' : 'QNX' , '107' : 'A/N' , '108' : 'IPComp' ,
                            '109' : 'SNP' , '110' : 'Compaq-Peer' , '111' : 'IPX-in-IP' , '112' : 'VRRP' , '113' : 'PGM' , '115' : 'L2TP' , '116' : 'DDX' ,
                            '117' : 'IATP' , '118' : 'ST' , '119' : 'SRP' , '120' : 'UTI' , '121' : 'SMP' , '122' : 'SM' , '123' : 'PTP' , '124' : 'ISIS' ,
                            '125' : 'FIRE' , '126' : 'CRTP' , '127' : 'CRUDP' , '128' : 'SSCOPMCE' , '129' : 'IPLT' , '130' : 'SPS' , '131' : 'PIPE' ,
                            '132' : 'SCTP' , '133' : 'FC' , '254' : 'DIVERT' }
    try:
        return proto_number_to_name[proto]
    except:
        return proto

# Fix Python SSL wrapper to use TLSv1 instead of SSLv23 as it causes issues with NW SSL implementation
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
   myapp = 'netwitness_query'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,owner='nobody', sessionKey=sessionKey)
   except Exception as e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials for my app
   for i, c in list(entities.items()):
        if 'eai:acl' in c:
            if 'app' in c['eai:acl'] :
                if c['eai:acl']['app'] == myapp :
                    return c['username'], c['clear_password']
   raise Exception("No credentials have been found")


# Encode Unicode strings safely - Should reduce skipped sessions and improve stdout output
# Fix provided by Matt, further tuned by me
def safe_str(obj):
    try:
        return str(obj)
    except UnicodeEncodeError:
        return str(obj).encode('unicode_escape')
    except UnicodeDecodeError:
        return str(obj).encode('latin-1')

def int_to_mac(i, s):
    h = str(hex(i))
    m = h[2:].upper()
    #pad with extra 0s if less then 12 characters long
    while (len(m) < 12):
        m = '0' + m
    #split in groups of 2 and re-join with ':' between them
    b = [m[x:x + 2] for x in range(0, 12, 2)]
    mac = s.join(b)
    return mac      


def event_split(event):
    start = event.find(' mailfrom=')
    #print start
    if (start > 0):
        splits = []
        prefix = event[:start]
        #print prefix
        next = event.find(' mailfrom=',start+10)
        #print next
        while (next > 0):
           splits.append(event[start:next])
           #print event[start:next]
           start = next 
           next = event.find(' mailfrom=',start+10)
           #print next
        last = event.find(' requestpayload=',start)  
        if (last == -1):
           last = event.find(' payload_req=',start)
        #print last
        if ( last > 0):
           splits.append(event[start:last])
           suffix = event[last:]
           #print suffix
           for evt in splits:
               print(prefix + evt + suffix)
        else:   
            print(event)
    else:
        print(event)

def get_stats(opener, url):
    global meta_count
    global session_count
    global SMTP_SPLIT
    # use the opener to fetch a URL
    site = opener.open(url)
    site = str(site.read(), errors='replace')
    try: 
        group = None
        last_complete_meta_id = 0
        meta = json.loads(site)
        d = {}
        meta_id = '0'
        event_str = ''
        action = ''
        current_group = 'NOT_SET'
        first_id = meta['results']['id1']
        last_id = meta['results']['id2']
        last_complete_meta_id = 0
        # Extract host information from TOP_LEVEL_URL
        rex = re.match(r"https?://(?P<host>[^:]+):\d+/?", TOP_LEVEL_URL, re.IGNORECASE)
        if ( rex != None) :
            rest_host = ' rest_host=' + rex.group('host')
        else:
            rest_host = ''
        # Add config filename to event for tracking
        conf = ' config=' + config_file
        # Start processing output from REST call    
        for row in meta['results']['fields']:
            # now row is a dictionary
            type = str(row['type']).lower()
            group = str(row['group'])
            meta_id = str(row['id1'])
            meta_count += 1
            if (current_group == 'NOT_SET'):
                current_group = group
            else:
                # If data belongs to a new session, output current session and make new session the current one
                if (current_group != group):
                    last_complete_meta_id = meta_id
                    event_str += rest_host
                    event_str += conf
                    event_split(event_str)
                    session_count += 1
                    event_str = ''
                    current_group = group

            #convert in to MAC Address human readable
            if (type in ['eth.src', 'eth.dst', 'alias.mac']):
                # Quick fix for 9.8 changes to MAC Address returned value
                try:
                    value = int_to_mac(int(value), ':')
                except:
                    value = value
                
            # Convert Protocol from number to name    
            if (type in ['ip.proto', 'ipv6.proto']):
                value = getprotobynumber(value)    

            #place " around values with spaces, commas and other special characters
            if (re.search('[\s+,=]', safe_str(row['value']))):
                value = '"' + safe_str(row['value']) + '"'
            else:
                value = safe_str(row['value'])
            #make time the first field on the list and rename it to _time
            if (type == "time"):
                # no need for trailing space as events already start with a space
                event_str = '_time=' + value + event_str
                delta = int(time.time()) - int(value)
                if delta > SKIP_DELTA and SKIP_DELTA > 0 :
                    logging.warning('Session time delta (' + str(delta) + ' > ' + str(SKIP_DELTA) + ') Skipping. Completed_id=' + str(last_complete_meta_id) + ' Meta_id=' + str(meta_id) + ' Last_id=' + str(last_id) )
                    return (1, last_id, last_id)

            else:
                # Map e-mail addresses to To: and From: based on previous value of action meta
                if (type == "action" and value in ['sendto', 'sendfrom']):
                    action = value
                if (type == "email" and action != ""):
                    if (action == "sendto"):
                        type = "recipient"
                    else:
                        type = "sender" 
                    action = ""
                
                if (type in list(nw_hash.keys()) ):
                    if (int(nw_hash[type][1]) > 0 ):
                        event_field = str(nw_hash[type][0]) + '=' + value[:int(nw_hash[type][1])] 
                        if (SMTP_SPLIT or event_str.find(event_field) == -1):
                            event_str += ' ' + event_field
                    value = hashlib.md5(value.encode('utf-8')).hexdigest()

                try:
                    event_field = nw_2_splunk[type] + '=' + value
                except:
                    event_field = type.replace(".", "_") + '=' + value
                # Check if this combinarion exists before adding it to the end of the event if splitting events add always
                if (SMTP_SPLIT or event_str.find(event_field) == -1):
                    event_str += ' ' + event_field

        if (int(meta_id) == int(last_id) or int(first_id) > int(last_id) or int(last_complete_meta_id) == 0 ):
           if (int(first_id) > int(last_id)):
              last_complete_meta_id = last_id
           else:
              last_complete_meta_id = meta_id
           if ( meta_id == '0'):
              logging.info('All done. No new data was processed. Completed_id=' + str(last_complete_meta_id) + ' Meta_id=' + str(meta_id) + ' Last_id=' + str(last_id) + ' First_id=' + str(first_id) )
           else:
              event_str += rest_host
              event_str += conf
              event_split(event_str)
              session_count += 1
              event_str = ''
              logging.info('All done. Completed_id=' + str(last_complete_meta_id) + ' Meta_id=' + str(meta_id) + ' Last_id=' + str(last_id) + ' First_id=' + str(first_id) )
           return (1, last_complete_meta_id,last_id)
        else:
           logging.info('More data to process. Completed_id=' + str(last_complete_meta_id) + ' Meta_id=' + str(meta_id) + ' Last_id=' + str(last_id) + ' Remaining=' + str(int(last_id)-int(meta_id)) )
           return (0, last_complete_meta_id,last_id)
    except:
        c = sys.exc_info()[0]
        e = sys.exc_info()[1]
        #Error pulling only one session issue error message and return empty
        logging.error('While trying to process sessions ( sessionid=' + str(group) + ' ) Reason="' + str(e) + '" Class="' + str(c) ,exc_info=True)
        return (-1, last_complete_meta_id)


def get_summary():
    global opener 
    global NW_PASSWORD
    s_url = TOP_LEVEL_URL + "/sdk?msg=summary&flags=1&expiry=0&force-content-type=application/json"
    try:
        site = opener.open(s_url)
        meta = json.load(site)
        match = re.search('mid1=(\d+)\s+mid2=(\d+)\s+msize=(\d+)\s+mmax=(\d+)\s+pid1=(\d+)\s+pid2=(\d+)\s+psize=(\d+)\s+pmax=(\d+)\s+time1=(\d+)\s+time2=(\d+)\s+ptime1=(\d+)\s+ptime2=(\d+)\s+sid1=(\d+)\s+sid2=(\d+)\s+ssize=(\d+)\s+smax=(\d+)\s+stotalsize=(\d+)\s+isize=(\d+)\s+memt=(\d+)\s+memu=(\d+)\s+memp=(\d+)\s+hostname=(\S+)\s+version=(.*)', meta['string'])
        return match.groups()
    except urllib.error.HTTPError as e:
        logging.error('[get_summary] message=' + str(e)+ ' - URL=' + s_url )
        if e.code == 401:
            logging.error('Authentication error will try to re-read credentials.')
            USER, PASS = getCredentials(sessionKey)
            if PASS == NW_PASSWORD :
                logging.error('Password has not changed.')
                return (None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None)
            else:
                NW_PASSWORD = PASS
                logging.warning('New password detected trying again.')
                opener = create_opener()
                return get_summary()
    except urllib.error.URLError as e:
        logging.error('[get_summary] message=' + str(e)+ ' - URL=' + s_url )
        return (None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None)
 
def read_last_id(LAST_ID_FILE):
    try:
        f = open (os.path.expandvars(LAST_ID_FILE), 'r')
    except:
        return -1
    last = f.read()
    try:
        id = int(last) 
    except:
        id = -1
    f.close()
    return id

def write_last_id(LAST_ID_FILE,s):
    try:
        f = open (os.path.expandvars(LAST_ID_FILE), 'w')
    except:
        return 0
    f.write(str(s))
    f.close()
    return 1
        
def create_opener():
    # create a password manager
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    # Add the username and password.
    # If we knew the realm, we could use it instead of None.
    password_mgr.add_password(None, TOP_LEVEL_URL, NW_USERNAME, NW_PASSWORD)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    # create "opener" (OpenerDirector instance)
    opener = urllib.request.build_opener(handler)
    return opener

## MAIN STARTS HERE ##
config_ok = True

try:
    # Just take the first parameter passed to the application as the configuration file name.
    config_file = sys.argv[1]
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + 'Using new configuration file: ' + config_file + '.conf\r\n')
except:
    config_file = 'nwsdk_query'
# read configuration from nwsdk_query.conf in the app/default or app/local directory
from splunk.clilib.cli_common import getMergedConf
try:
    LOG = getMergedConf(config_file)['other']['logging']
except:
    LOG = 'stderr'

if LOG.lower() == 'stderr':
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(pathname)s: [%(levelname)s] %(message)s')
else:
    logging.basicConfig(filename=LOG, filemode='a', level=logging.INFO, format='%(asctime)-15s %(pathname)s: [%(levelname)s] %(message)s')

try:
    TOP_LEVEL_URL = getMergedConf(config_file)['rest']['top_level_url']
except:
    config_ok = False
    logging.error('Couldn\'t read TOP_LEVEL_URL from ' + config_file + '.conf.')

# Try to get authentication from Splunk PassThrough REST Endpoint
try:
    logging.info('Waiting on sessionKey.')
    sessionKey = sys.stdin.readline().strip()
    logging.info('Got sessionKey.')
    if len(sessionKey) == 0:
        logging.warning('Did not receive a session key from splunkd. Please enable passAuth in inputs.conf. Trying configuration file ' + config_file + '.conf.')
        NW_USERNAME = getMergedConf(config_file)['rest']['username']
        NW_PASSWORD = getMergedConf(config_file)['rest']['password']
    else:
        # now get app credentials - might exit if no creds are available
        logging.info('Waiting on getCredentials.')
        NW_USERNAME, NW_PASSWORD = getCredentials(sessionKey)
        logging.info('getCredentials returned username=' + NW_USERNAME )
        NW_USERNAME = getMergedConf(config_file)['rest']['username']
        logging.info('Configuration overwrote username=' + NW_USERNAME )
except:
    config_ok = False
    logging.error('Couldn\'t read authentication details PassAuth or from ' + config_file + '.conf.')

try:
    NW_QUERY = getMergedConf(config_file)['rest']['query']
except:
    config_ok = False
    logging.error('Couldn\'t read NW_QUERY from ' + config_file + '.conf.')
try:
    LAST_MID_FILE = getMergedConf(config_file)['rest']['last_mid_file']
except:
    config_ok = False
    logging.error('Couldn\'t read LAST_MID_FILE from ' + config_file + '.conf.')
try:
    MAX_META = int(getMergedConf(config_file)['rest']['max_meta'])
except:
    logging.error('Couldn\'t read MAX_META from ' + config_file + '.conf. Setting MAX_META to 500000.')
    MAX_META = 500000
try:
    SLEEP = int(getMergedConf(config_file)['rest']['sleep'])
except:
    logging.warning('Couldn\'t read SLEEP from ' + config_file + '.conf. Setting SLEEP to 5.')
    SLEEP = 5
try:
    if ( getMergedConf(config_file)['rest']['verbose'].lower() in [ 'f','false','0' ] ):
        VERBOSE = False
    else:
        VERBOSE = True
except:
    VERBOSE = True

try:
    if ( getMergedConf(config_file)['other']['split'].lower() in [ 'f','false','0' ] ):
        SMTP_SPLIT = False
    else:
        SMTP_SPLIT = True
except:
    SMTP_SPLIT = False

try:
    SKIP_DELTA = int(getMergedConf(config_file)['other']['skip_older_than'])
    logging.warning('SKIP_DELTA set to ' + str(SKIP_DELTA) + ' seconds.')
except:
    SKIP_DELTA = -1 
# read additional/alternative mappings from conf files
try:
    for key in list(getMergedConf(config_file)['mappings'].keys()):
        nw_2_splunk[key] = getMergedConf(config_file)['mappings'][key]
except:
    # do nothing
    pass

# read hash mappings from conf files
try:
    for key in list(getMergedConf(config_file)['hashing'].keys()):
        nw_hash[key] = getMergedConf(config_file)['hashing'][key].split(',')
except:
    # do nothing
    pass

# Check that all necessary config settings are available, if not exit with error code (-1)
if ( not config_ok ):
   logging.error('Check settings in ' + config_file + '.conf.')
   sys.exit(-1)

logging.info('Configuration read complete, starting data collection.')
# reopen stdout file descriptor with write mode
# and 0 as the buffer size (unbuffered)
# to index data correctly otherwise there will be delays
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w')

# If TOP_LEVEL_URL is https deploy SSL fix
if ( 'https' in TOP_LEVEL_URL.lower()):
   fix_ssl_version()
   logging.info('HTTPS use detected, deploying SSL fix.')
# Remove URL trailing '/'
if ( TOP_LEVEL_URL[len(TOP_LEVEL_URL)-1] == '/') :
   TOP_LEVEL_URL=TOP_LEVEL_URL[:-1]

# create a password manager opener
opener = create_opener()

while True:
    try:
        start_time = time.time()
        meta_count = session_count = 0 
        STARTID = str(read_last_id(LAST_MID_FILE))
        # With 10.4 changes a summary call is always required
        (mid1, mid2, msize, mmax, pid1, pid2, psize, pmax, time1, time2, ptime1, ptime2, sid1, sid2, ssize, smax, stotalsize, isize, memt, memu, memp, hostname, version) = get_summary()
        # If there's no ID file get the latest MID from a summary call
        if STARTID == "-1" :
           if (mid2 is None):
              logging.warning('Couldn\'t execute summary query. Sleeping 60 seconds...')
              time.sleep(60)
              continue
           else:
              STARTID = mid2
              LASTID = str(int(mid2) + 1)
              write_last_id(LAST_MID_FILE,STARTID)
              logging.info('LAST_MID_FILE didn\'t exist. Starting at Meta_id=' + str(STARTID) )
        else:
           if (mid2 is None):
              logging.warning('Couldn\'t execute summary query. Sleeping 60 seconds...')
              time.sleep(60)
              continue
           else:
              if ( STARTID == mid2):
                 if ( VERBOSE ):
                     logging.info('No new data to process. Start_id=' + STARTID + ' MID2=' + mid2 )
                 STARTID = str(int(STARTID) + 1)
                 LASTID = STARTID
              else:
                 STARTID = str(int(STARTID) + 1)
                 LASTID = mid2

        # Additional check required as with the new API if id1 < id2 results are returned in reverse order
        if ( int(STARTID) < int(LASTID) ):
            a_url = TOP_LEVEL_URL + "/sdk?msg=query&size=" + str(MAX_META) + "&id1=" + STARTID + "&id2=" + LASTID + "&query=" + urllib.parse.quote(NW_QUERY) + "&flags=1&expiry=0&force-content-type=application/json"
            logging.info('URL: ' + str(a_url) )
            (done, last_completed_meta,first_run_last_id) = get_stats(opener, a_url)
            if last_completed_meta != "0" :
               write_last_id(LAST_MID_FILE,last_completed_meta)
            # If more data needs to collected bind the end to the end of meta from first run to avoid a constant running script as the end keeps changing
            while done == 0 :
                a_url = TOP_LEVEL_URL + "/sdk?msg=query&size=" + str(MAX_META) + "&id1=" + str(last_completed_meta) + "&id2=" + str(first_run_last_id)  + "&query=" + urllib.parse.quote(NW_QUERY) + "&flags=1&expiry=0&force-content-type=application/json"
                (done, last_completed_meta,last_id) = get_stats(opener, a_url)
                if last_completed_meta != "0" :
                   write_last_id(LAST_MID_FILE,last_completed_meta)
            if last_completed_meta != "0" :
               write_last_id(LAST_MID_FILE,last_completed_meta)
        else:
            if ( VERBOSE ):
               logging.info('No new data to process. Start_id=' + STARTID + ' MID2=' + mid2 )

        # Print final processing stats before exiting
        end_time = time.time()
        timedelta = end_time - start_time
        sessions_per_sec = int(session_count / timedelta)
        meta_per_sec = int(meta_count / timedelta)
        logging.info('Processing Stats: session_count=' + str(session_count) + ' meta_count=' + str(meta_count) + ' start_time=' + str(start_time) + ' end_time=' + str(end_time) + ' duration=' + str(timedelta) + ' sessions_per_second=' + str(sessions_per_sec) + ' meta_per_second=' + str(meta_per_sec) + ' url=' + TOP_LEVEL_URL )
        time.sleep(SLEEP)
 
    except:
        c = sys.exc_info()[0]
        e = sys.exc_info()[1]
        #Error pulling only one session issue error message and return empty
        logging.error('While trying to process sessions. Reason="' + str(e) + '" Class="' + str(c), exc_info=True)

logging.warning('Restarting to re-read configuration file and authentication credentials.')
sys.exit(0)
