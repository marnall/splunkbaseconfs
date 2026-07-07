import os
import sys
import json
import requests
import time
import base64
import hmac
import hashlib

#Akamai EAA App dir name
akamai_eaa_dir = 'akamai_eaa'

#Date format
#datef = "%d %b %Y %H:%M"
datef = "%Y-%m-%d %H:%M"

#Add py file paths
#splunk_path from SPLUNK_HOME
splunk_path = os.getenv("SPLUNK_HOME") + '/etc/apps/' + akamai_eaa_dir + '/bin'
#print(splunk_path)
sys.path.append(splunk_path)



import splunk
import splunk.entity as entity
import splunk.auth, splunk.search
import log as logging
from datetime import datetime

LOG = logging.getLogger(__name__)

class Etl(object):
    """ETL"""

    def __init__(self, api_version='v1'):
        self._api_ver = api_version
        self._content_type_json = {'content-type': 'application/json'}
        self._content_type_form = {'content-type': 'application/x-www-form-urlencoded'}
        self._headers = None



    def get_signature(self, access_key_id, secret_access_key):
        signature = hmac.new(
            key=secret_access_key,
            msg=str(access_key_id)+":"+str(secret_access_key),
            digestmod=hashlib.sha256).digest()

        # Base64 encode the signature
        signature = base64.encodestring(signature).strip()

        # Make the signature URL safe, skipping as we are sending signature in header and not in url
        #urlencoded_signature = quote_plus(signature)

        return signature

    def ensure_signature_in_header(self, api_key, secret_key):
        #print "generating signature for header"
        signature = self.get_signature(access_key_id=api_key, secret_access_key=secret_key)
        self._headers = {'Authorization': 'Basic '+api_key+':'+signature}
        self._headers.update(self._content_type_json)


    def get_logs(self, mgmt_url, api_key, secret_key,  drpc_args):
        scroll_id = None
        try:
            """fetches the logs for given drpc args"""
            #print 'in get_logs'
            api_url = '{}/api/{}/analytics/ops'.format(
                mgmt_url,
                self._api_ver
            )

            #LOG.info('get_logs api url= '+api_url)
            #LOG.info('get_logs api_key= '+api_key)
            #LOG.info('get_logs secret_key= '+secret_key)
            #LOG.info("get_logs drpc_args= "+drpc_args)
            #w = sys.stdin.readline().strip()

            self.ensure_signature_in_header(api_key=api_key, secret_key=secret_key)
            #print 'headers:',self._headers

            resp = requests.post(
                api_url,
                data=drpc_args,
                headers=self._headers, verify=False
            )
            if resp.status_code != requests.codes.ok:
                return None

            #print resp
            #print resp.text
            #print resp.status
            resj = resp.json()
            #print 'resj'
            #print json.dumps(resj)

            #w = sys.stdin.readline().strip()

            if 'message' in resj:
                #print len(resj.get('message')[0])
                #print 'in message'
                #print resj.get('message')[0][1]
                msg = resj.get('message')[0][1]

                #if 'count' in msg:
                #    print "Count: "
                #    print msg.get('count')
                if 'scroll_id' in msg:
                    scroll_id = msg.get('scroll_id')
                    #print "scroll_id: " + scroll_id
                
                count = 0
                for timestamp, response in msg.iteritems():
                    try:
                        gmttime = datetime.fromtimestamp(int(timestamp)/1000)
                        if isinstance(response, dict) and 'flog' in response:
                            print ' '.join([gmttime.isoformat(), response['flog'], '\n'])
                            count += 1
                    except Exception, e:
                        pass
                        #print e

            else:
                LOG.error('Error: no data(message) in response.')
                LOG.error(drpc_args)
                LOG.error(json.dumps(resj))
            resp.close()
        except Exception, e:
            LOG.error(drpc_args)
            LOG.error("Exception in get_logs:")
            LOG.error(e)
            #LOG.error(resp.text)
        return scroll_id


    # access the credentials in /servicesNS/nobody/<MyApp>/admin/passwords
    def getCredentials(self, sk):
        print 'getCredentials'
        try:
            # list all credentials
            #w = sys.stdin.readline().strip()
            #print("Splunk sessionKey= " + sk + "\n")
            #print "Splunk Entities:\n"

            entities = entity.getEntities(['admin', 'passwords'], namespace=akamai_eaa_dir, owner='nobody', sessionKey=sk)
            print entities
        except Exception, e:
            print "Could not get %s credentials from splunk. Error: %s" % (akamai_eaa_dir, str(e))
            raise Exception("Could not get %s credentials from splunk. Error: %s" % (akamai_eaa_dir, str(e)))

            # return first set of credentials
        for i, c in entities.items():
            print c
            return c['username'], c['clear_password'], c['realm']
        print "No credentials from splunk have been found"

        #raise Exception("No credentials from splunk have been found")


#Read password files
etl = Etl();

#Read encoded Splunk user, password
# splunk_user = ""
# splunk_password = ""
# try:
#     with open(splunk_path+'/splunk_akamai_eaa_config_en') as uf:
#         ln = ["",""]
#         i = 0
#         for ul in uf:
#             #print ul
#             #print base64.b64decode(ul)
#             ln[i] = base64.b64decode(ul)
#             i += 1
#         #LOG.info("Splunk User, Password:")
#         #LOG.info(ln[0])
#         #LOG.info(ln[1])
#         splunk_user = ln[0]
#         splunk_password = ln[1]
#         uf.close()
# except IOError:
#     print "User Info File: splunk_akamai_eaa_config_en does not exist. Exiting..."
#     exit()

#w = sys.stdin.readline().strip()

# read session key sent from splunkd
#sessionKey = sys.stdin.readline().strip()
#print "\nsplunk.auth.getSessionKey= "
#sessionKey = splunk.auth.getSessionKey('admin','wapp1234')
#LOG.info("fetching sessionKey")
#sessionKey = splunk.auth.getSessionKey(splunk_user,splunk_password)
#LOG.info(sessionKey +"\n")

#w = sys.stdin.readline().strip()

#print(splunk.auth.getCurrentUser())
#print("splunk.getDefault= ")
#sessionKey = splunk.getDefault("sessionKey")
#print(sessionKey +"\n")
#sk = splunk.getDefault("sessionKey")
#print("sk=")
#print(sk)

# if len(sessionKey) == 0:
#     print "Did not receive a session key from splunkd.  Please enable passAuth in inputs.conf for this script\n"
#     #exit(2)

#w = sys.stdin.readline().strip()

# now get Akamai credentials - might exit if no creds are available
# Splunk server bug. Throws this error when getting credentials
# Error: 'str' object has no attribute 'os_startIndex'
# To be fixed
# api_key, secret_key, realm = etl.getCredentials(sessionKey)

#Begin Workaround for the above Error. Get keys stored in file akamai_eaa_access_keys_en
try:
    with open(splunk_path + '/akamai_eaa_access_keys_en') as uf:
        ln = ["", ""]
        i = 0
        for ul in uf:
            #print ul
            #print base64.b64decode(ul)
            ln[i] = base64.b64decode(ul)
            i += 1
            #print ln
        api_key = ln[0]
        secret_key = ln[1]
        uf.close()
except IOError:
    print("Akamai Enterprise Access Access Keys File: akamai_eaa_access_keys_en does not exist. Exiting...")
    exit()
#End Workaround

#w = sys.stdin.readline().strip()
#print "Logging in Akamai with url/credentials"
# use the credentials to access the data source
#Read encoded Akamai url, user, password
akamai_eaa_url = 'https://manage.akamai-access.com/'
try:
    with open(splunk_path+'/akamai_eaa_etl_config_en') as uf:
        ln = [""]
        i = 0
        for ul in uf:
            #print ul
            #print base64.b64decode(ul)
            ln[i] = base64.b64decode(ul)
            i += 1
            #print ln
        #print ln[0]
        akamai_eaa_url = ln[0]
        #print akamai_eaa_url
        uf.close()
except IOError:
    print("User Info File: akamai_eaa_etl_config_en does not exist. Exiting...")
    #exit()

#print api_key
#print secret_key

#w = sys.stdin.readline().strip()

#1m default
ts_1m = 60000
ts_block_m = 1
ts_block = ts_block_m * ts_1m

#cur time - 1m
time_now = long(time.mktime(time.localtime()) - 60)
dates = time.strftime(datef, time.localtime(time_now))
#ms
time_now = time_now * 1000

#Read sts
sts = 0
try:
    with open(splunk_path+'/akamai_eaa_etl_time.txt','r') as trf:
        i = 0
        for line in trf:
            if i == 0:
                dates = line.strip()
                #print "sts from file "
                #print dates
                sts = long(time.mktime(time.strptime(dates, datef))*1000)
                #print sts
            #else:
            #    if i == 1:
            #        ts_block_m = long(line.strip())
            #        if (ts_block_m <=0 ):
            #            ts_block_m = 1
            #        ts_block = ts_block_m * ts_1m
            i+=1
    trf.close()
except IOError:
    #create file
    #print("File akamai_eaa_etl_time.txt does not exist. Creating...")
    f = open(splunk_path+'/akamai_eaa_etl_time.txt','w')
    f.close()

#w = sys.stdin.readline().strip()

# x 10 longer range
ts_block_l = ts_block * 60
if sts <= 0:
    #use long ts range
    sts = time_now - ts_block_l;

#check if diff is > 1hr
ok = True
ets = sts + ts_block
if time_now - sts >= ts_block_l:
    #use longer ts diff range
    ets = sts + ts_block_l
elif ets > time_now:
    #ets too high, ignore and exit
    #print("ets too high");
    ok = False
else:
    #use normal ts diff range
    tdiff_m = int((time_now - sts)/ts_1m)
    ets = sts + tdiff_m * ts_1m

#print("time_now=")
#print(str(time_now))
#print("sts=")
#print(str(sts))
#print("ets=")
#print(str(ets))
#print(ok)

#w = sys.stdin.readline().strip()

if ok:
    #Use scroll paging
    drpc_args = '{"sts":'+ str(sts) +',"ets":'+ str(ets)+ ',"metrics":"logs","es_fields":"flog","limit":"1000","sub_metrics":"scroll","source":"splunk_app"}'
    scroll_id = etl.get_logs(akamai_eaa_url.strip(), api_key, secret_key, drpc_args)
    #check for scroll_id to issue another request
    while (scroll_id != None):
        drpc_args = '{"sts":'+ str(sts) +',"ets":'+ str(ets)+ ',"metrics":"logs","es_fields":"flog","limit":"1000","sub_metrics":"scroll","source":"splunk_app","scroll_id":"'+scroll_id+'"}'
        print drpc_args
        scroll_id = etl.get_logs(akamai_eaa_url.strip(), api_key, secret_key, drpc_args)

    #API keys are present in splunk_akamai_eaa_apikey_config_en which are included in the header of request inside get_logs,
    #API key validation is through in vismgr.

    #etl.logout()

    try:
        #save last ets
        with open(splunk_path+'/akamai_eaa_etl_time.txt','w') as tf:
            dates = time.strftime(datef, time.localtime(ets/1000))
            #print(dates)
            tf.write(dates)
            #tf.write("\n"+str(ts_block_m))
            #print("Updated file: "+splunk_path+"/akamai_eaa_etl_time.txt")
            tf.close()
    except IOError:
        LOG.error("Error in writing file: "+splunk_path+"/akamai_eaa_etl_time.txt")
#else:
#    LOG.error("Error: Can not login to Akamai EAA, exiting...")

#wait
#w = sys.stdin.readline().strip()
