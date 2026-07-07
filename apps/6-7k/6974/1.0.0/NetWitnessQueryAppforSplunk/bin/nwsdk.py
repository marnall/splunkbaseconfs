#
# Splunk/NetWitness REST API Session Meta scripted input
# Version : 1.0.0
# Date: 01 Jun 2023
#
#  == CHANGELOG ==
# - Version 1.0.0: 
#   > Extract NetwitnessSessionMetadata by polling NW REST API  
#   > User can provide a NW query in the config file to further filter the metadata collection

import json
import urllib.request, urllib.error, urllib.parse
import sys
import os
import re
import time
#import threading
import multiprocessing
#import Queue
import traceback
import signal


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

# access the credentials in /servicesNS/nobody/NetWitnessQueryAppforSplunk/storage/passwords
def getCredentials(sessionKey):
   import splunk.entity as entity
   myapp = 'NetWitnessQueryAppforSplunk'
   try:
      # list all credentials
      entities = entity.getEntities(['storage', 'passwords'], namespace=myapp,owner='nobody', sessionKey=sessionKey)
   except Exception as e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials
   for i, c in list(entities.items()):
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

def get_meta_ids(opener,s_sid, e_sid):
    q_url = TOP_LEVEL_URL + "/sdk?msg=session&id1=" + s_sid + "&id2=" + e_sid + "&expiry=0&force-content-type=application/json"
    site = opener.open(q_url)
    site = str(site.read(), errors='replace')
    # The json module has a function load for loading from file-like objects,
    # like the one you get from `urllib2.urlopen`.
    meta = json.loads(site)
    return (meta['params']['field1'], meta['params']['field2'])

def get_sessions(opener,l,s_sid, e_sid):
    meta_count = session_count = 0
    start_time = time.time()
    # use the opener to fetch a URL
    (s_mid, e_mid) = get_meta_ids(opener,s_sid, e_sid)
    meta_time = time.time()
    if query_in_config is True:
        q_url = TOP_LEVEL_URL + "/sdk?msg=query&id1=" + s_mid + "&id2=" + e_mid + "&size=" + str(int(e_mid) - int(s_mid) + 1) + "&query=" + urllib.parse.quote(NW_QUERY) + "&expiry=0&force-content-type=application/json"
    else:
        q_url = TOP_LEVEL_URL + "/sdk?msg=query&id1=" + s_mid + "&id2=" + e_mid + "&size=" + str(int(e_mid) - int(s_mid) + 1) + "&expiry=0&force-content-type=application/json"
    
    site = opener.open(q_url)
    site = str(site.read(), errors='replace')
    siteread_time = time.time()

    try:
        group = None
        last_complete_meta_id = 0
        meta = json.loads(site)
        load_time = time.time()

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

                    #with some_rlock:
                    #    f.write(event_str + '\n')
                    #f.write(event_str + '\n')
                    l.acquire()
                    print(event_str)
                    l.release()
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

                try:
                    event_field = nw_2_splunk[type] + '=' + value
                except:
                    event_field = type.replace(".", "_") + '=' + value
                # Check if this combinarion exists before adding it to the end of the event
                if (event_str.find(event_field) == -1):
                    event_str += ' ' + event_field

        process_time = time.time()
        td0 = process_time - start_time
        td1 = meta_time - start_time
        td2 = siteread_time - meta_time
        td3 = load_time - siteread_time
        td4 = process_time - load_time
        if (int(meta_id) == int(last_id) or int(first_id) > int(last_id) or int(last_complete_meta_id) == 0 ):
           if (int(first_id) > int(last_id)):
              last_complete_meta_id = last_id
           else:
              last_complete_meta_id = meta_id
           if ( meta_id == '0'):
              sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + " - INFO: All done. No new data was processed. " + "Completed_id=" + str(last_complete_meta_id) + " Meta_id=" + str(meta_id) + " Last_id=" + str(last_id) + " First_id=" + str(first_id) + "\r\n" )
           else:
              event_str += rest_host
              event_str += conf
              #with some_rlock:
              #    print event_str
              #f.write(event_str + '\n')
              l.acquire()
              print(event_str)
              l.release()
              session_count += 1
              event_str = ''
              #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + " - INFO: All done " + "Completed_id=" + str(last_complete_meta_id) + " Meta_id=" + str(meta_id) + " Last_id=" + str(last_id) + " First_id=" + str(first_id) + "\r\n" )
           return (1, last_complete_meta_id,last_id,td0,td1,td2,td3,td4)
        else:
           #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + " - INFO: More data to process " + "Completed_id=" + str(last_complete_meta_id) + " Meta_id=" + str(meta_id) + " Last_id=" + str(last_id) + " Remaining=" + str(int(last_id)-int(meta_id)) + "\r\n" )
           return (0, last_complete_meta_id,last_id,td0,td1,td2,td3,td4)
    except:
        if s_sid != e_sid:
            mid_sid = int((int(s_sid) + int(e_sid)) / 2)
            # Get the first half of the sessions
            d1 = get_sessions(opener,l,s_sid, str(mid_sid))
            # Get the second half of the sessions
            d2 = get_sessions(opener,l,str(mid_sid + 1), e_sid)
            # Join both results
            d = dict(d1, **d2)
            return d
        else:
            c = sys.exc_info()[0]
            e = sys.exc_info()[1]
            #Error pulling only one session issue error message and return empty
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: While trying to process sessions ( sessionid=' + str(s_sid) + ' ) Reason="' + str(e) + '" Class="' + str(c) + '" Skipping session\r\n')
            return {}

def get_summary(opener):
    s_url = TOP_LEVEL_URL + "/sdk?msg=summary&flags=1&expiry=0&force-content-type=application/json"
    try:
        site = opener.open(s_url)
        meta = json.load(site)
        match = re.search('mid1=(\d+)\s+mid2=(\d+)\s+msize=(\d+)\s+mmax=(\d+)\s+pid1=(\d+)\s+pid2=(\d+)\s+psize=(\d+)\s+pmax=(\d+)\s+time1=(\d+)\s+time2=(\d+)\s+ptime1=(\d+)\s+ptime2=(\d+)\s+sid1=(\d+)\s+sid2=(\d+)\s+ssize=(\d+)\s+smax=(\d+)\s+stotalsize=(\d+)\s+isize=(\d+)\s+memt=(\d+)\s+memu=(\d+)\s+memp=(\d+)\s+hostname=(\S+)\s+version=(.*)', meta['string'])
        return match.groups()
    except urllib.error.URLError as e:
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: ' + str(e) + '\r\n')
        return (None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None)

def exec_query(opener,url):
    s_url = TOP_LEVEL_URL + url + "&expiry=0&force-content-type=application/json"
    site = opener.open(s_url)
    meta = json.load(site)
    return meta['results']['fields']


def read_last_sid():
    try:
        f = open (os.path.expandvars(LAST_SID_FILE), 'r')
    except:
        return -1
    last = f.read()
    try:
        sid = int(last)
    except:
        sid = -1
    f.close()
    return sid

def write_last_sid(s):
    try:
        f = open (os.path.expandvars(LAST_SID_FILE), 'w')
    except:
        return 0
    f.write(str(s))
    f.close()
    return 1


def process_sessions(opener,lock,s_sid, e_sid):
    m = get_sessions(opener,lock,s_sid, e_sid)
    # Extract host information from TOP_LEVEL_URL
    #rex = re.match(r"https?://(?P<host>[^:]+):\d+/?", TOP_LEVEL_URL, re.IGNORECASE)
    #if ( rex != None) :
    #   rest_host = 'rest_host=' + rex.group('host')
    #sid_list = m.keys()
    #sid_list.sort(key=int)
    #for l in sid_list:
    #    k = m[l].keys()
    #    # Add host information from where data was collected.
    #    k.append(rest_host)
    #    k.sort()
    #    s = ' '.join(n for n in k)
    #    with some_rlock:
    #        print s
    #    #print s
    #    l_id = int(l)
    #    #if ((l_id % WRITE_TO_FILE_EVERY_X) == 0):
    #    #    write_last_sid(l_id)
    #if (l_id != int(e_sid)):
    #    # Issue ERROR message and make l_id to be e_sid
    #    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Unexpected last sessionid in batch (was: ' + str(l_id) + ' expected: ' + str(e_sid) + ')\r\n')
    #    l_id = int(e_sid)
    ##write_last_sid(l_id)
    #return l_id
    return m

def worker(opener,name,lock):
    # Ignore SIGINT (Ctrl-C) let the parent handle that and make sure worker completes its tasks
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    #name = (multiprocessing.current_process()).getName()
    while True:
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' available.\r\n')
        (s_sid,e_sid) = q.get()
        #entry = q.get()
        #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' entry=' + str(entry) + '.\r\n')
        if ( e_sid == "Terminate"):
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' received terminate command.\r\n')
            q.task_done()
            break
        else:
            #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' processing sessions ' + str(s_sid) + ' to ' + str(e_sid) + '\r\n')
            try:
                start_time = time.time()
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' Started:  start_session=' + str(s_sid) + ' end_session=' + str(e_sid) + '\r\n')
                #fname = "%s/%s_%014d_%014d.txt" % (os.path.expandvars(SPOOL_PATH),'data',int(s_sid),int(e_sid))
                #f = open (fname, 'w')
                (status, last_complete_meta_id,last_id,td0,td1,td2,td3,td4) = process_sessions(opener,lock,s_sid,e_sid)
                #f.close()
                sessions = int(e_sid) - int(s_sid)
                end_time = time.time()
                timedelta = end_time - start_time
                sessions_per_sec = int(sessions / timedelta)
                #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' Finished: start_session=' + str(s_sid) + ' end_session=' + str(e_sid) + ' session_count=' + str(sessions) + ' start_time=' + str(start_time) + ' end_time=' + str(end_time) + ' duration=' + str(timedelta) + ' sessions_per_second=' + str(sessions_per_sec) + ' result=' + str(result) + '\r\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Thread name=' + name + ' Finished: start_session=' + str(s_sid) + ' end_session=' + str(e_sid) + ' session_count=' + str(sessions) + ' start_time=' + str(start_time) + ' end_time=' + str(end_time) + ' duration=' + str(timedelta) + ' sessions_per_second=' + str(sessions_per_sec) + ' t0=' + str(td0) + ' t1=' + str(td1) + ' t2=' + str(td2) + ' t3=' + str(td3) + ' t4=' + str(td4) + '\r\n')
            except urllib.error.HTTPError as e:
                body = e.read().decode()
                error_msg = json.loads(body)
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: '+str(error_msg['error'])+'. \r\n')
            except urllib.error.URLError as e:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: URLError in Thread name=' + name + ' error=' + str(e) + ' processing sessions ' + str(s_sid) + ' to ' + str(e_sid) + '\r\n')
            except:
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Thread name=' + name + ' error=' + str(sys.exc_info()[0]) + ' Reason=' + str(sys.exc_info()[1]) + ' processing sessions ' + str(s_sid) + ' to ' + str(e_sid) + '\r\n')
                sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
            finally:
                q.task_done()

def handler_stop_signals(signum, frame):
    # Perform cleanup or other actions here
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Recieved Signal - '+ signum +'- Exiting.\r\n') 
    # Terminate the worker processes
    for p in multiprocessing.active_children():
        p.terminate()
        p.join()
    # Terminate the main process
    sys.exit(0)

#MAIN starts here

config_ok = True
query_in_config = False

try:
    # Just take the first parameter passed to the application as the configuration file name.
    config_file = sys.argv[1]
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Using new configuration file: ' + config_file + '.conf\r\n')
except:
    config_file = 'nwsdk'
# read configuration from nwsdk.conf in the app/default or app/local directory
from splunk.clilib.cli_common import getMergedConf
try:
    TOP_LEVEL_URL = getMergedConf(config_file)['rest']['top_level_url']
except:
    config_ok = False
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Couldn\'t read TOP_LEVEL_URL from ' + config_file + '.conf.\r\n')

# Try to get authentication from Splunk PassThrough REST Endpoint
try:
    sessionKey = sys.stdin.readline().strip()
    if len(sessionKey) == 0:
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Did not receive a session key from splunkd. Please enable passAuth in inputs.conf. Trying configuration file ' + config_file + '.conf.\r\n')
        NW_USERNAME = getMergedConf(config_file)['rest']['username']
        NW_PASSWORD = getMergedConf(config_file)['rest']['password']
    else:
        # now get app credentials - might exit if no creds are available
        NW_USERNAME, NW_PASSWORD = getCredentials(sessionKey)
except:
    config_ok = False
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Couldn\'t read authentication details PassAuth or from ' + config_file + '.conf.\r\n')

try:
    NW_QUERY = getMergedConf(config_file)['rest']['query']
    query_in_config = True
except:
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + 'INFO: Couldn\'t read NW_QUERY from ' + config_file + '.conf.\r\n')
    
try:
    LAST_SID_FILE = getMergedConf(config_file)['rest']['last_sid_file']
except:
    config_ok = False
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Couldn\'t read LAST_SID_FILE from ' + config_file + '.conf.\r\n')
try:
    NO_SID_FILE_OPTION = int(getMergedConf(config_file)['rest']['no_sid_file'])
except:
    # If LAST_SID_FILE doesn't exist use NO_SID_FILE_OPTION
    # -2 to start <no_sid_seconds_back> seconds ago
    # -1 to start from highest sessionid in NW DB
    #  0 to start read all available data
    # <any positive integer> to start from that value sessionid
    NO_SID_FILE_OPTION = -1
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read NO_SID_FILE from ' + config_file + '.conf. Setting NO_SID_FILE to start at the end of the database.\r\n')

try:
    NO_SID_SECONDS_BACK = int(getMergedConf(config_file)['rest']['no_sid_seconds_back'])
except:
    # Number of seconds to go back from now to import new data on first run (default: 5 minutes)
    NO_SID_SECONDS_BACK = 300
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read NO_SID_SECONDS_BACK from ' + config_file + '.conf. Setting NO_SID_SECONDS_BACK to 300 seconds.\r\n')

try:
    WRITE_TO_FILE_EVERY_X = int(getMergedConf(config_file)['rest']['write_to_file_every_x'])
except:
    # How oftwn should tracking file be written
    WRITE_TO_FILE_EVERY_X = 5000
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read WRITE_TO_FILE_EVERY_X from ' + config_file + '.conf. Setting WRITE_TO_FILE_EVERY_X to 5000 sessions.\r\n')

try:
    MAX_META = int(getMergedConf(config_file)['rest']['max_meta'])
except:
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read MAX_META from ' + config_file + '.conf. Setting MAX_META to 500000.\r\n')
    MAX_META = 500000
# try:
#     SLEEP = int(getMergedConf(config_file)['rest']['sleep'])
# except:
#     sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read SLEEP from ' + config_file + '.conf. Setting SLEEP to 5 seconds.\r\n')
#     SLEEP = 5
try:
    SPOOL_PATH = int(getMergedConf(config_file)['rest']['spool_path'])
except:
    #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - WARN: Couldn\'t read SPOOL_PATH from ' + config_file + '.conf. Setting SPOOL_PATH to "spool/".\r\n')
    SPOOL_PATH = 'spool/'
try:
    if ( getMergedConf(config_file)['rest']['verbose'].lower() in [ 'f','false','0' ] ):
        VERBOSE = False
    else:
        VERBOSE = True
except:
    VERBOSE = True

# read additional/alternative mappings from conf files
try:
    for key in list(getMergedConf(config_file)['mappings'].keys()):
        nw_2_splunk[key] = getMergedConf(config_file)['mappings'][key]
except:
    # do nothing
    pass
# Check that all necessary config settings are available, if not exit with error code (-1)
if ( not config_ok ):
   sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Check settings in ' + config_file + '.conf.\r\n')
   sys.exit(-1)

# reopen stdout file descriptor with write mode
# and 0 as the buffer size (unbuffered)
# to index data correctly otherwise there will be delays
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w')
# Apply SSL fix if needed
if ( 'https' in TOP_LEVEL_URL.lower()):
    fix_ssl_version()
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: HTTPS use detected, deploying SSL fix.\r\n')

# Create SPOOL_PATH directory if it doesn't exists
#if not os.path.exists(SPOOL_PATH):
#       os.makedirs(SPOOL_PATH)

# create a password manager
password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
# Add the username and password.
# If we knew the realm, we could use it instead of None.
password_mgr.add_password(None, TOP_LEVEL_URL, NW_USERNAME, NW_PASSWORD)

handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
# create "opener" (OpenerDirector instance)
main_opener = urllib.request.build_opener(handler)

try:
    start_time = time.time()
    s_mid = e_mid = meta_count = start_session = end_session = session_count = 0
    (mid1, mid2, msize, mmax, pid1, pid2, psize, pmax, time1, time2, ptime1, ptime2, sid1, sid2, ssize, smax, stotalsize, isize, memt, memu, memp, hostname, version) = get_summary(main_opener)
    # get last sessionid processed start from the next one
    if (sid2 is None):
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Couldn\'t execute summary query. Existing...\r\n')
        sys.exit(1)
    id = last_processed_id = read_last_sid()
    if (id == -1):
        # Couldn't read last sessionid from file do something
        if (NO_SID_FILE_OPTION == -2):
            now = time.time()
            stime = '"' + time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(now - NO_SID_SECONDS_BACK)) + '"'
            etime = '"' + time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(now)) + '"'
            meta = exec_query(main_opener,"/sdk?msg=query&id1=0&id2=0&size=1&query=select%20sessionid%20where%20time=" + urllib.parse.quote(stime) + "-" + urllib.parse.quote(etime))
            try:
                id = int(meta[0]['value'])
            except:
                # query returned an empty list make id the latest sessionid
                id = int(sid2) + 1
        elif (NO_SID_FILE_OPTION == -1):
            # There was no LAST_SID_FILE create a new one with the last sessionid in NWDB
            write_last_sid(int(sid2))
            id = int(sid2) + 1
        elif (NO_SID_FILE_OPTION == 0):
            # There was no LAST_SID_FILE create a new one starting from 0
            write_last_sid('0')
            id = 1
        elif (NO_SID_FILE_OPTION > 0):
            # There was no LAST_SID_FILE create a new one with user provided value
            write_last_sid(int(NO_SID_FILE_OPTION))
            id = int(NO_SID_FILE_OPTION)
        else:
            # Error on NO_SID_FILE_OPTION will read all data for you
            id = 1
    else:
        # read the last processed sessionid from file start on the next one to avoid duplicates
        id += 1
    # Thread spawn
    MAX_THREADS = multiprocessing.cpu_count()
    if MAX_THREADS > 8:
        MAX_THREADS = 8
    
    start_session = id
    session_chunk = int(MAX_META/100)
    # while True:
    session_chunk = int((int(sid2)-int(id))/MAX_THREADS)
    if session_chunk == 0 or session_chunk > int(MAX_META/100):
        session_chunk = int(MAX_META/100)
    if (id > int(sid2)):
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: No new sessions to read from ' + TOP_LEVEL_URL + '\r\n')
        sys.exit(0)
    else :
        sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Processing Stats: start_session=' + str(start_session) + ' end_session=' + sid2 + ' count=' + str(int(sid2)-int(start_session)) + ' batches=' + str(int((int(sid2)-int(start_session))/session_chunk)+1) + ' url=' + TOP_LEVEL_URL + '\r\n')
        #API access check
        try:
            if query_in_config is True:
                q_url_resp = TOP_LEVEL_URL + "/sdk?msg=query&id1=" + str(s_mid) + "&id2=" + str(e_mid) + "&size=" + str(int(e_mid) - int(s_mid) + 1) + "&query=" + urllib.parse.quote(NW_QUERY) + "&expiry=0&force-content-type=application/json"
            else:
                q_url_resp = TOP_LEVEL_URL + "/sdk?msg=query&id1=" + str(s_mid) + "&id2=" + str(e_mid) + "&size=" + str(int(e_mid) - int(s_mid) + 1) + "&expiry=0&force-content-type=application/json"
            site = main_opener.open(q_url_resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            error_msg = json.loads(body)
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: Got an exception while polling the API: error='+str(error_msg['error'])+'. \r\n')
            sys.exit(1)
        except urllib.error.URLError as e:
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: URLError while polling the API: error=' + str(e) + '.\r\n')
            sys.exit(1)
        except:
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR:Got an exception while polling the API: +  error=' + str(sys.exc_info()[0]) + ' Reason=' + str(sys.exc_info()[1]) + '\r\n')
            sys.exit(1)
        
        # read all sessions
        q = multiprocessing.JoinableQueue()
        lock = multiprocessing.Lock()

        signal.signal(signal.SIGINT, handler_stop_signals)
        signal.signal(signal.SIGTERM, handler_stop_signals)
        processes = []
        try:
            for i in range(MAX_THREADS):
                # create a password manager
                password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
                # Add the username and password.
                # If we knew the realm, we could use it instead of None.
                password_mgr.add_password(None, TOP_LEVEL_URL, NW_USERNAME, NW_PASSWORD)

                handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
                # create "opener" (OpenerDirector instance)
                opener = urllib.request.build_opener(handler)

                t = multiprocessing.Process(target=worker,args=(opener,'NW-Worker-'+str(i+1).zfill(2),lock))
                # t.daemon = True
                t.start()
                processes.append(t)
            while (id + session_chunk <= int(sid2)):
                #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Processing sessions ' + str(id) + ' to ' + str(id + session_chunk) + ' (' + str(int(sid2)-int(id)) + ') from ' + TOP_LEVEL_URL + '\r\n')
                q.put((str(id), str(id + session_chunk)))
                #last_id = process_sessions(str(id), str(id + session_chunk))
                # In normal cases last_id will be sid2 so increment it to finish the while loop
                # In the other situations (batching) to avoid reading the same session twice at batch boundaries
                id = int(id) + int(session_chunk) + 1
            if (id < int(sid2)):
                #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Processing final batch. Sessions ' + str(id) + ' to ' + sid2 + ' from ' + TOP_LEVEL_URL + '\r\n')
                q.put((str(id), str(sid2)))
                #id = process_sessions(str(id), sid2)
            #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Queue size is now ' + str(q.qsize()) + ' entries\r\n')
            #q.join()
            # Print final processing stats before exiting
            sessions = int(sid2) - start_session
            end_time = time.time()
            timedelta = end_time - start_time
            sessions_per_sec = int(sessions / timedelta)
                #meta_per_sec = int(meta_count / timedelta)
                #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Processing Stats: start_session=' + str(start_session) + ' end_session=' + sid2 + ' session_count=' + str(sessions) + ' start_meta=' + str(s_mid) + ' end_meta=' + str(e_mid) + ' meta_count=' + str(meta_count) + ' start_time=' + str(start_time) + ' end_time=' + str(end_time) + ' duration=' + str(timedelta) + ' sessions_per_second=' + str(sessions_per_sec) + ' meta_per_second=' + str(meta_per_sec) + ' url=' + TOP_LEVEL_URL + '\r\n')
            #sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - INFO: Queue size is now ' + str(qsize) + ' entries\r\n')
            
            # time.sleep(SLEEP)

            for i in range(MAX_THREADS):
                q.put((None,"Terminate"))
            # Wait for all the items to be processed or an error occurs
            q.join()
            write_last_sid(sid2)
            # # Terminate other worker processes if an error occurred
            # if error_flag:
            #     write_last_sid(last_processed_id)
            #     for process in processes:
            #         process.terminate()
            #         process.join()

            # Wait for the worker processes to complete
            for process in processes:
                process.join()

            # time.sleep(SLEEP)
            # start_time = time.time()
            # s_mid = e_mid = meta_count = start_session = end_session = 0
            # id = start_session = int(sid2) + 1
            # (mid1, mid2, msize, mmax, pid1, pid2, psize, pmax, time1, time2, ptime1, ptime2, sid1, sid2, ssize, smax, stotalsize, isize, memt, memu, memp, hostname, version) = get_summary(main_opener)
        except:
            c = sys.exc_info()[0]
            e = sys.exc_info()[1]
            #Error pulling only one session issue error message and return empty
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' - ERROR: While trying to process sessions. Reason="' + str(e) + '" Class="' + str(c) + '" \r\n')
            sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + ' ' + traceback.format_exc())
            # End All Threads
            for i in range(MAX_THREADS):
                q.put((None,"Terminate"))
            q.join()
            for process in processes:
                process.join()
except Exception as e:
    sys.stderr.write(time.strftime("%Y-%b-%d %H:%M:%S", time.localtime(time.time())) + 'Exception occured, Exiting. ERROR: '+ str(e)+'. \r\n')
    sys.exit(1)