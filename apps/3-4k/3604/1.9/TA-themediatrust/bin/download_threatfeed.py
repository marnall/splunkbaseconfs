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
    thislogger.debug('getAuth()')
    global sessionKey
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace='TA-themediatrust', owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        thislogger.debug(e)
        raise Exception("Could not get credentials from splunk. ERROR: %s" % e) 
        sys.exit()

    auth = {}

    for i, c in entities.items():
        thislogger.debug('getAuth(): username = ' + c['username'])
        if c['username'] != 'license_key':
            auth['user'] = c['username']
            auth['pw'] = c['clear_password']
            thislogger.info("user:"+auth['user']) 
            return auth

def getLicenseKey():
    global sessionKey
    thislogger.debug('getLicenseKey(): sessionKey = ' + sessionKey)
    try:
        entities = entity.getEntities(['admin', 'passwords'], namespace='TA-themediatrust', owner='nobody', sessionKey=sessionKey)

    except Exception, e:
        thislogger.debug(e)
        raise Exception("Could not get license key from splunk. ERROR: %s" % e) 
        sys.exit()

    license_key = ''
    for i, c in entities.items():
        thislogger.debug('getLicenseKey(): username = ' + c['username'])
        if c['username']  == 'license_key':
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
global SPLUNK_HOME, THISUSER, sourcefile, licensecheckfile,modfile,destmod, destip, localdestip, destdomain, coreSplunk, transformsfile
SPLUNK_HOME=os.environ.get('SPLUNK_HOME')
THISUSER=getpass.getuser()
sourcefile=os.path.join(SPLUNK_HOME,'var','run','st301')
licensecheckfile=os.path.join(SPLUNK_HOME,'var','run','lic301')
modfile=os.path.join(SPLUNK_HOME,'var','run','mod301')
destip=os.path.join(SPLUNK_HOME,'etc','apps','DA-ESS-ThreatIntelligence','local','data','threat_intel','themediatrust_ip.csv')
localdestip=os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','lookups','ip_intel.csv')
destmod=os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','lookups','mod.csv')
destdomain=os.path.join(SPLUNK_HOME,'etc','apps','DA-ESS-ThreatIntelligence','local','data','threat_intel','themediatrust_domain.csv')
transformsfile=os.path.join(SPLUNK_HOME,'etc','apps','TA-themediatrust','local','transforms.conf')
coreSplunk=False

baseurl = 'https://localhost:8089'
myhttp = httplib2.Http()

thislogger=object()
console=object

startdate="2"
riskscore="80"

license_key=''

def validate_destination():
    global destip, localdestip, coreSplunk
    directory = os.path.dirname(destip)
    if not os.path.exists(directory):
	thislogger.debug('The DA-ESS-ThreatIntelligence app doesnt exist.  So we are going to CoreSplunk Route')
	coreSplunk=True
    directory = os.path.dirname(localdestip)
    if not os.path.exists(directory):
	thislogger.debug('We need to do the setups for the appropriate lookups. Doing that now')
	thislogger.debug('First create the directory')
	os.makedirs(directory)

def setup_items():
	global thislogger, console
	ensure_dir(sourcefile)
	ensure_dir(licensecheckfile)
	ensure_dir(modfile)
	log_path=os.path.join(SPLUNK_HOME,'var','log','splunk','threat_feed.log')

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

    response = requests.post(uri, data=params, verify=True, auth=(uid, pwd))
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
        response = requests.post(uri, verify=True, auth=(uid, pwd))
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

    response = requests.get(uri, verify=True, auth=(uid, pwd))
    thislogger.debug('spl results: ' + str(response.text))

    data = str(response.text).replace("\"","")

def groom_current_feed():
	username=''
	app = 'TA-themediatrust'
	global auth
	auth=getAuth()
	splCall('localhost', auth, '| inputlookup ip_intel | search threat_key!="themediatrust*" | outputlookup ip_intel')

def read_configs():
	global startdate, riskscore, license_key
	
        thislogger.debug('BEFORE cli.getConfStanza()')
        cfg = cli.getConfStanza('mediatrustsetup','setupentity')
        thislogger.debug('AFTER cli.getConfStanza()')

        license_key=getLicenseKey()
        if license_key == '' :
           thislogger.error('license_key is invalid.  The list cannot be downloaded')

	startdate=cfg.get('startdate')
	if startdate in [None,'']:
		thislogger.error('startdate is invalid.  going with the default')
		startdate="2"

	thislogger.debug('startdate:'+startdate)

	riskscore=cfg.get('riskscore')

	if riskscore in [None,'']:
		thislogger.error('riskscore is invalid.  going with the default')
		riskscore=50

	thislogger.debug('riskscore:'+riskscore)

def perform_license_check():
	global startdate, riskscore, license_key
	
	license_check_cmd='https://www.themediatrust.com/api?key='+license_key+'&action=license_status'

	if startdate=="2":
		cmd = 'https://www.themediatrust.com/api?key='+license_key+'&action=fjord_base'
	else:
		startdate=int(startdate)
		thislogger.debug('start_date:'+str(startdate))
		d = datetime.today() - timedelta(days=startdate)
		start_date=d.strftime("%Y%m%d")
		thislogger.debug('start_date:'+start_date)
		cmd = 'https://www.themediatrust.com/api?key='+license_key+'&action=fjord_base&start_date='+start_date
		
	urllib.urlretrieve(license_check_cmd, licensecheckfile)
	urllib.urlretrieve(cmd, sourcefile)

	#open source and destination files
	if not os.path.isfile(licensecheckfile):
		thislogger.error('The license check file that we are expecting to read from does not exist, so we are exiting gracefully.')
		sys.exit()

	fi = open(licensecheckfile,'r')

	#read in the file
	linecount=0
	for line in fi:
		linecount=linecount+1
		break

	if linecount == 0:
		thislogger.error('The license check did not download successfully.  Likely issue is that The Media Trust has not added the appropriate IPs to the whitelist.  Please contact The Media Trust at datasupport@themediatrust.com to resolve the issue.')
		if os.path.isfile(localdestip):
			os.remove(localdestip)
		if os.path.isfile(destip):
			os.remove(destip)
		if os.path.isfile(destdomain):
			os.remove(destdomain)
		fi.close()
		return False
	else:
		thislogger.info('The license check was downloaded successfully')

	with open(licensecheckfile) as data_file:    
	    data = json.load(data_file)

	if 'expires' in data:
		thislogger.debug('The license check data had an expires variable')
		expires=data['expires']

		thislogger.debug('expires:'+str(expires))

		now=time.time()

		thislogger.debug('now:'+str(now))

		if int(now)>int(expires):
			thislogger.info('The license key is expired.  We are cleaning the data out of the system')
			if os.path.isfile(destip):
				os.remove(destip)
			if os.path.isfile(destdomain):
				os.remove(destdomain)
			if os.path.isfile(localdestip):
				os.remove(localdestip)
			fi.close()
			return False
		else:
			thislogger.debug('The license key is still valid.')
	else:
		thislogger.debug('The license check data does not have an expires variable')

	fi.close()
	
	return True

def handle_mod():
	global mod_cmd, modfile


	thislogger.debug('we are in handle_mod')

	rightnow=datetime.now()
	date_time=rightnow.strftime("%B %d, %Y @ %H:%M %Z")
	thislogger.debug('after time formatting')

	initialize_message='Last update: '+date_time
	thislogger.debug('initialize_message:'+initialize_message)

	mod=initialize_message
	
	mod_cmd='https://www.themediatrust.com/api?key='+license_key+'&action=custom_message'
	urllib.urlretrieve(mod_cmd, modfile)

	#open source and destination files
	if not os.path.isfile(modfile):
		thislogger.error('The mod file that we are expecting to read from does not exist, so we are exiting gracefully.')
	else:
		fi = open(modfile,'r')

		#read in the file
		linecount=0
		for line in fi:
			linecount=linecount+1
			mod = mod+' '+line

		if linecount == 0:
			thislogger.error('The mod did not download successfully.  Likely issue is that The Media Trust has not added the appropriate IPs to the whitelist.  Please contact The Media Trust at datasupport@themediatrust.com to resolve the issue.')
		else:
			thislogger.info('The mod was downloaded successfully')

		fi.close()
	
	if os.path.isfile(destmod):
		os.remove(destmod)
	fo = open(destmod,'w')

	#write out the header
	fo.write("mod\n")
	fo.write("\""+mod+"\"\n")
	fo.close()
	thislogger.debug('At the end of handle_mod')
	return True

def download_threatfeed():
	#open source and destination files
	if not os.path.isfile(sourcefile):
		thislogger.error('The Threat feed that we are expecting to read from does not exist, so we are exiting gracefully.')
		sys.exit()

	fi = open(sourcefile,'r')

	#read in the file
	linecount=0
	for line in fi:
		linecount=linecount+1
		break

	fi.close()

	if linecount == 0:
		thislogger.error('The Threat feed did not download successfully.  Likely issue is that The Media Trust has not added the appropriate IPs to the whitelist.  Please contact The Media Trust at datasupport@themediatrust.com to resolve the issue.')
		if os.path.isfile(localdestip):
			os.remove(localdestip)
		if os.path.isfile(destip):
			os.remove(destip)
		if os.path.isfile(destdomain):
			os.remove(destdomain)
		return False
	else:
		thislogger.info('The Threat feed was downloaded successfully')

	thislogger.info('Starting movefile script')

	#open source  files
	if not os.path.isfile(sourcefile):
		thislogger.error("The Threat feed that we are expecting to read from does not exist, so we are exiting gracefully.")
		if os.path.isfile(localdestip):
			os.remove(localdestip)
		if os.path.isfile(destip):
			os.remove(destip)
		if os.path.isfile(destdomain):
			os.remove(destdomain)
		return False

	return True

def move_files():
	fi = open(sourcefile,'r')

	if not coreSplunk:
		thislogger.debug ("the required ES Module is available")
		if os.path.isfile(destip):
			os.remove(destip)
		fo = open(destip,'w')
		if os.path.isfile(destdomain):
			os.remove(destdomain)
		fod = open(destdomain,'w')
		
		#write out the header
		fo.write("description,ip,weight\n")
		fod.write("description,domain,weight\n")

		#read in the file
		linecount=0
		for line in fi:
			linecount=linecount+1
			if linecount==1:
				continue
			line=line.strip()
			values=line.split(',')
			outline=':'.join(values)+','+values[0]+','+str(riskscore)+'\n'
			fo.write(outline)
			outline=':'.join(values)+','+values[1]+','+str(riskscore)+'\n'
			fod.write(outline)

		if linecount == 1:
			thislogger.error("The sourcefile is empty, which is unexpected and is considered an Error Condition")

		fo.close()
		fod.close()
	else:
		thislogger.debug ("the required ES Module is NOT available.  Handling as coreSplunk.")
	if os.path.isfile(localdestip):
		os.remove(localdestip)

	fi.close()
	fi = open(sourcefile,'r')

	fo = open(localdestip,'w')

	#write out the header
	fo.write("description,domain,ip,threat_key,time,weight\n")

	#read in the file
	linecount=0
	for line in fi:
		linecount=linecount+1
		if linecount==1:
			continue
		line=line.strip()
		values=line.split(',')
		description=':'.join(values)
		description=description.replace('"','')
		outline=description+',,'+values[0]+',themediatrust_ip,'+values[7]+','+str(riskscore)+'\n'
		fo.write(outline)
		outline=description+','+values[1]+',,themediatrust_domain,'+values[7]+','+str(riskscore)+'\n'
		fo.write(outline)

	if linecount == 1:
		thislogger.error("The sourcefile is empty, which is unexpected and is considered an Error Condition")

	fo.close()


	fi.close()
	'''
	os.remove(sourcefile)
	'''
	thislogger.info ("Ending movefile script")
	

if __name__ == '__main__':
	setup_items()
	
	thislogger.info('Starting download_threatfeed script')

	thislogger.info('SPLUNK_HOME variable:'+SPLUNK_HOME)
	thislogger.info('THISUSER variable:'+THISUSER)

	thislogger.debug('we are getting the credentials to manage the threat feed')

        getSessionKey()
	validate_destination()
	read_configs()
	groom_current_feed()
	
	ret = perform_license_check()
	if ret==False:
		logger.error('Back to main call and license_check was not successful.  Exiting')
		sys.exit()
	'''
	ret = handle_mod()
	if ret==False:
		logger.error('Back to main call and handle_mod was not successful.  Continuing')
	'''
	ret = download_threatfeed()
	if ret==False:
		logger.error('Back to main call and license_check was not successful.  Exiting')
		sys.exit()
	move_files()
	handle_mod()
