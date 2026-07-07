import urllib 
import sys
import os
import logging
import getpass
import json
import time
import httplib2
import requests
from xml.etree import ElementTree
import re
from splunk.clilib import cli_common as cli
import splunk.entity as entity
import splunklib.client as client
import splunklib.results as results
import splunk.rest as rest
from datetime import datetime, timedelta
from xml.dom import minidom

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def getAuth():
    global sessionKey
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace='TA-themediatrust', owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        thislogger.debug(e)
        raise Exception("Could not get credentials from splunk. ERROR: %s" % e)
        sys.exit()

    auth = {}

    for i, c in entities.items():
        if c['username'] != 'license_key':
            auth['user'] = c['username']
            auth['pw'] = c['clear_password']
            thislogger.info("user:"+auth['user'])
            return auth

def getLicenseKey():
    global sessionKey
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace='TA-themediatrust', owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        thislogger.debug(e)
        raise Exception("Could not get license key from splunk. ERROR: %s" % e)
        sys.exit()

    license_key = ''
    for i, c in entities.items():
        if c['username'] == 'license_key':
            thislogger.info("license_key:"+c['clear_password'])
            license_key = c['clear_password']

    return license_key

def getSessionKey():
        global sessionKey
        sessionKey=sys.stdin.readline().strip()
        if len(sessionKey)==0:
                thislogger.error("we do not have a good session key")
                sys.exit()
        thislogger.debug("we have a good session key")

#variables
global SPLUNK_HOME, THISUSER, responsefile 
SPLUNK_HOME=os.environ.get('SPLUNK_HOME')
THISUSER=getpass.getuser()
responsefile=os.path.join(SPLUNK_HOME,'var','run','themediatrust_reporting.txt')

baseurl = 'https://localhost:8089'
myhttp = httplib2.Http()

thislogger=object()
console=object

license_key=''

def setup_items():
	global thislogger, console
	log_path=os.path.join(SPLUNK_HOME,'var','log','splunk','report_metrics.log')

	ensure_dir(log_path)
	#setup logger
	logging.basicConfig(level=logging.DEBUG,
		format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
		datefmt='%Y-%m-%d %H:%M:%S',
		filename=log_path,
		filemode='a')
	console=logging.StreamHandler()
	console.setLevel(logging.INFO)
	formatter=logging.Formatter('%(name)-12s %(levelname)-8s %(message)s')
	console.setFormatter(formatter)
	logging.getLogger('').addHandler(console)

	thislogger=logging.getLogger(THISUSER)

def read_configs():
	global license_key
	
	cfg = cli.getConfStanza('mediatrustsetup','setupentity')

        license_key=geLicenseKey()
        if license_key == '' :
                thislogger.error('license_key is invalid.  The list cannot be downloaded')



def splCall(host, auth, spl):
    thislogger.debug('splCall - query')

    uid = auth['user']
    pwd = auth['pw'] 

    #
    # Submit the search job and get its jobid
    #
    uri = 'https://' + host + ':8089/services/search/jobs'
    thislogger.debug('spl job search uri:' + uri)

    params = {'search': spl}

    response = requests.post(uri, data=params, verify=False, auth=(uid, pwd))
    thislogger.debug('right after the post')
    tree = ElementTree.fromstring(str(response.text))
    node = tree.find('sid')
    if node is None:
        thislogger.debug(str(response.text))
        return
    else:
        jobid = node.text

    thislogger.debug('spl search: ' +str(response.text))

    #
    # Query the jobid to get the status
    #
    uri = 'https://' + host + ':8089/services/search/jobs/' + jobid
    thislogger.debug('spl job id uri:' + uri)

    isNotDone = True
    while isNotDone:
        response = requests.post(uri, verify=False, auth=(uid, pwd))
        tree = ElementTree.fromstring(str(response.text))
        node = tree.find('.//*[@name="isDone"]')
        status = node.text

        if status == '1':
            isNotDone = False
        else:
            time.sleep(1)
            thislogger.debug('spl job processing, retrying')

    thislogger.debug('spl job: ' +str(response.text))

    #
    # Submit the search job and get its jobid
    #
    uri = 'https://' + host + ':8089/services/search/jobs/' + jobid + '/results?output_mode=csv'
    thislogger.debug('spl job response uri:' + uri)

    response = requests.get(uri, verify=False, auth=(uid, pwd))
    thislogger.debug('spl results: ' + str(response.text))

    data = str(response.text).replace("\"","")

    return data

def gather_send_metrics():
	username=''
	app = 'TA-themediatrust'
	global sessionKey
	sessionKey=sys.stdin.readline().strip()
	if len(sessionKey)==0:
		thislogger.error("we do not have a good session key")
		sys.exit()
	thislogger.debug("we have a good session key")
	global auth
	auth=getAuth(sessionKey)
	
	'''
	Retrieving Threat Activity By IP
	'''
	call='search index=summary search_name=\"Threat Activity By IP - Summary\" earliest=-30d@d latest=now | stats sum(count) as count'
	thislogger.debug("call:"+call)
	data=splCall('localhost', auth, call)
	thislogger.debug("data:"+data)
	if data=="":
		thislogger.debug("data is empty")
		activity_ip="0"	
	else:
		data=data.splitlines()
		activity_ip=data[1]
	thislogger.debug("activity_ip:"+activity_ip)
	
	'''
	Retrieving Threat Activity By Domain
	'''
	call='search index=summary search_name=\"Threat Activity By Domain - Summary\" earliest=-30d@d latest=now | stats sum(count) as count'
	thislogger.debug("call:"+call)
	data=splCall('localhost', auth, call)
	thislogger.debug("data:"+data+":")
	if data=="":
		thislogger.debug("data is empty")
		activity_domain="0"	
	else:
		data=data.splitlines()
		activity_domain=data[1]
	thislogger.debug("activity_domain:"+activity_domain)
	
	'''
	Retrieving Threat Activity Actions By IP
	'''
	call='search index=summary search_name=\"Threat Activity Actions By IP - Summary\" earliest=-30d@d latest=now | stats sum(count) as count'
	thislogger.debug("call:"+call)
	data=splCall('localhost', auth, call)
	thislogger.debug("data:"+data+":")
	if data=="":
		thislogger.debug("data is empty")
		activity_actions_ip="0"	
	else:
		data=data.splitlines()
		activity_actions_ip=data[1]
	thislogger.debug("activity_actions_ip:"+activity_actions_ip)
	
	'''
	Retrieving Threat Activity Actions By Domain
	'''
	call='search index=summary search_name=\"Threat Activity Actions By Domain - Summary\" earliest=-30d@d latest=now | stats sum(count) as count'
	thislogger.debug("call:"+call)
	data=splCall('localhost', auth, call)
	thislogger.debug("data:"+data+":")
	if data=="":
		thislogger.debug("data is empty")
		activity_actions_domain="0"	
	else:
		data=data.splitlines()
		activity_actions_domain=data[1]
	thislogger.debug("activity_actions_domain:"+activity_actions_domain)
	
	'''
	Here's where we create and send up the JSON payload
	'''

	response_data={}
	response_data['Threat Activity By IP - 30 day summary'] = activity_ip
	response_data['Threat Activity By Domain - 30 day summary'] = activity_domain
	response_data['Threat Activity Actions By IP - 30 day summary'] = activity_actions_ip
	response_data['Threat Activity Actions By Domain - 30 day summary'] = activity_actions_domain

	json_response=json.dumps(response_data)

	global license_key
	
	send_metrics_cmd='https://themediatrust.com/api?key='+license_key+'&action=send_metrics&payload='+json_response

	ensure_dir(responsefile)
	if os.path.isfile(responsefile):
		os.remove(responsefile)

	urllib.urlretrieve(send_metrics_cmd, responsefile)

	thislogger.info('The response was downloaded successfully')
	thislogger.debug("We got to the end")

	return True

if __name__ == '__main__':
	
	setup_items()
	
	thislogger.info('Starting report_metrics script')

	thislogger.info('SPLUNK_HOME variable:'+SPLUNK_HOME)
	thislogger.info('THISUSER variable:'+THISUSER)

	thislogger.debug('we are getting the credentials to manage the threat feed')

        getSessionKey()

	read_configs()
	
	ret = gather_send_metrics()
	if ret==False:
		logger.error('Back to main call and gather_send was not successful.  Exiting')
