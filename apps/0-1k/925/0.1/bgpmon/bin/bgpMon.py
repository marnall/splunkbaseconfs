#!/usr/bin/python
###!/usr/bin/env python
#
# Retrieves alerts for BGP announces changes with BGPMon
# http://bgpmon.net/
#
# Mathieu Dessus / mdessus@gmail.com
#
# Requires python and suds
# For Debian/Ubuntu: apt-get install python-suds
#

import sys
import socket
from suds.client import Client

# BgpMon.net account
# Demo
login = 'demo@bgpmon.net'
passw = 'demo'
# Parameters for syslog:
# hostname, IPv4 or IPv6 / Port / Protocol: tcp or udp
host = 'localhost'
port = '514'
protocol = 'udp'

# Alert mode: splunk (app) or syslog (note: you can use syslog for Splunk)
# Valid values: 'syslog', 'splunk'
mode = 'splunk'
# Fields and metrics for arcsight or splunk ? ('arcsight' or 'splunk')
format = 'splunk'
# Generate en event even if there is no error
sendReport = 1
debug = 0

# If you a proxy is needed, modify the following variable as below
# proxy = 'myproxy:3128'
proxy = ''

# BgpMon parameters
active = 1
days = 3
maxcode = 100
url = "http://bgpmon.net/soap/server.php?wsdl"


alertCodes = {10:'Origin AS and Prefix changed (more specific) Or Origin AS changed and no valid route object found for this announcement', \
11:'Origin AS and Prefix changed (more specific) Or Origin AS changed. Valid route object', \
12:'Transit AS and Prefix changed (more specific)', \
21:'Possible MITM BGP attack', \
22:'More specific via known ASpath', \
23:'Withdraw of More specific detected', \
31:'Transit AS changed (transit AS was not found in list you entered', \
41:'ASpath Regex didn\'t match', \
60:'New prefix for your AS', \
97:'Withdraw of one of your prefixes', \
99:'Any other kind of update'}


## If used as a Splunk module

#if mode == 'splunk':
#	import splunk.entity as entity
#
#	def getCredentials(sessionKey):
#	   myapp = 'bgpmon'
#	   try:
#	      # list all credentials
#	      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
#	                                    owner='nobody', sessionKey=sessionKey)
#	   except Exception, e:
#	      raise Exception("Could not get %s credentials from splunk. Error: %s"
#	                      % (myapp, str(e)))
#	
#	   # return first set of credentials
#	   for i, c in entities.items():
#	        return c['username'], c['clear_password']
#	
#	   raise Exception("No credentials have been found")  

##	



def openSyslog():
	s = None
	print protocol
	#proto = 'udp'
	if protocol == 'udp':
		sockType = socket.SOCK_DGRAM
	else:
		sockType = socket.SOCK_STREAM
	try:
		for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, sockType):
			af, socktype, proto, canonname, sa = res
			if debug:
				print "Using protocol", proto
			try:
				s = socket.socket(af, socktype, proto)
			except socket.error, msg:
				s = None
				continue
			try:
				s.connect(sa)
			except socket.error, msg:
				s.close()
				s = None
				continue
			break
	except socket.gaierror:
		print "Fatal error: unable to resolve host", host
		sys.exit(1)
	if s is None:
		print 'Fatal error: Unable to open socket to ', host
		sys.exit(1)
	#s.sendall('data')
	#s.close()
	#print 'Sent', data
	return s

def senddata(fd, data):	
	fd.sendall(data)

def closeSyslog(fd):
	### Tests !!!
	fd.close()	
	

def soapRequest():
	#client = Client(url)
	client = Client(url)
	if proxy:
		print "Proxy"
		proxyOpts = {'http': proxy}
		client.set_options(proxy=proxyOpts)
	#proxy_settings = dict(http='http://user:password@host:port',
    #                  https='http://user:password@host:port')
	#print client
	# Params: xs:string login, xs:string bgpmon_password, xs:boolean active, xs:int days, xs:int maxcode
	try:
		results =  client.service.getAlerts(login, passw, active, days, maxcode)
	#except:
	#	print 'Error'
	except Exception, err:
		print 'Fatal error: '+str(err)
		sys.exit(1)
	return results
	
	
#print results

  #(Alert){
   #alert_id = 30803089
   #alert_code = 41
   #no_peers = 1
   #date = "2012-02-04 02:22"
   #monitored_network = "192.175.48.0/24"
   #monitored_AS = 112
   #announced_prefix = "192.175.48.0/24"
   #origin_AS = 112
   #transit_AS = 6509
   #cleared = True




if format == 'splunk':
	sev_high = 'critical'
	sev_med = 'high'
	sev_low = 'medium'
	sev_info = 'low'
else:	# ArcSight
	sev_high = 9
	sev_med = 8
	sev_low = 5
	sev_info = 3

#if mode == 'splunk':
#	# read session key sent from splunkd
#	sessionKey = sys.stdin.readline().strip()
#	if len(sessionKey) == 0:
#		sys.stderr.write("Did not receive a session key from splunkd. " +
#			"Please enable passAuth in inputs.conf for this " +
#			"script\n")
#		exit(2)
#	# now get BgpMon credentials - might exit if no creds are available
#	login, passw = getCredentials(sessionKey)


results = soapRequest()
if mode == 'syslog':
	fd = openSyslog()

for alert in results:
	if debug:
		print alert
	try:
		mesg = '\"'+alertCodes[alert.alert_code]+'"'
	except:
		mesg = "Code "+str(alert.alert_code)+" unknown !"
	if alert.alert_code < 20: 
		severity = sev_high
	elif alert.alert_code < 30:
		severity = sev_med
	elif alert.alert_code < 50:
		severity = sev_low
	else:
		severity = sev_info
	data = 'mesg='+mesg+' severity='+str(severity)+' '
	#for k, v in alert.iteritems():
	#	data += ' '+k+'='+str(v)		 
	#print data
	###if
	content = ['alert_id', 'alert_code', 'no_peers', 'date', 'monitored_network', 'monitored_AS', 'announced_prefix', 'origin_AS', 'transit_AS', 'cleared']
	for x in content:
		if debug:
			print "---> "+x+" "+str(alert[x])
		data += x+"="+str(alert[x])+" "
	data += ' url="http://bgpmon.net/alerts.php?details&alert_id='+str(alert.alert_id)+'"'
	data += ' vendor=bgpmon.net'
	#fd.sendall(data)
	if mode == 'syslog':
		senddata(fd, data)
	else:
		print data+'\n\n'
if mode == 'syslog':
	closeSyslog(fd)


