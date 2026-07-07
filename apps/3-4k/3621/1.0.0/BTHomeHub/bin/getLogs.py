#
import urllib, urllib2, re, sys, datetime,hashlib
method = "POST"
handler = urllib2.HTTPHandler()
opener = urllib2.build_opener(handler)

import splunk.entity as entity

sessionKey = sys.stdin.readline().strip()
if len(sessionKey) == 0:
        sys.stderr.write("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
        exit(2)

# access the credentials in /servicesNS/nobody/app_name/admin/passwords
def getCredentials(sessionKey):
   myapp = 'BTHomeHub'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)
   except Exception, e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials
   for i, c in entities.items():
	return c['realm'], c['clear_password']
   raise Exception("No credentials have been found")

host,password = getCredentials(sessionKey)
passMD5 = hashlib.md5(password).hexdigest()

url = "http://"+host
headers={
'Host': host, 
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 
'Accept-Language': 'en-GB,en;q=0.5', 
'Referer':url+'/settings.htm', 
'Cookie': 'defpg=settings.htm; urlpg=settings.htm; urn=72965; menu_sel=; isReloadPage=yes; sec_menu_sel=; third_menu_sel=troubleshooting_event.htm; pageselected=troubleshooting_event.htm', 
'Upgrade-Insecure-Requests': 1 
}

data = urllib.urlencode({'GO':'settings.html','usr':'admin','pws':passMD5})
request = urllib2.Request(url=url, data=data, headers=headers)
request.get_method = lambda: method

try:
	connection = opener.open(request)
except urllib2.HTTPError,e:
	connection = e

if connection.code == 200:
	data = connection.read()
else:
	errorCode = connection.code

eventsRequest = urllib2.urlopen(url+'/cgi/cgi_evtlog.js')
events = eventsRequest.readlines()


def monthNum(x):
    return {
        'Jan': 1,
        'Feb': 2,
        'Mar': 3,
        'Apr': 4,
        'May': 5,
        'Jun': 6,
        'Jul': 7,
        'Aug': 8,
        'Sep': 9,
        'Oct': 10,
        'Nov': 11,
        'Dec': 12
    }.get(x)


thisYear=2017 #update me!
lastMonth=monthNum('Jun')
eventDict = []

#print str(thisYear)+" "+str(lastMonth)
#22:20:03, 17 Jun. Receive a DHCP request
for event in events:
	line = event.strip().strip('[').strip(',').strip(']').strip("'").strip()
	line = line.replace("var evtlog_list=[['","")
	raw = urllib.unquote(line).decode('utf8')
	fields = re.match(r"(?P<time>\d\d:\d\d:\d\d),\s(?P<day>\d\d)\s(?P<month>\w\w\w)\.\s(?P<msg>.*)",raw)
	if fields: #if there is a match
		time = fields.group('time')
		day = fields.group('day')
		month = fields.group('month')
		msg = fields.group('msg')

		thisMonth = monthNum(month)
		if thisMonth > lastMonth:
			thisYear = thisYear - 1
		#print str(thisYear)+"-"+str(thisMonth)+"-"+str(day)+"T"+str(time)+" message=\""+str(msg)+"\""
		eventDict.append(str(thisYear)+"-"+str(thisMonth).zfill(2)+"-"+str(day)+"T"+str(time)+" message=\""+str(msg)+"\"")

		lastMonth = thisMonth

def left(s, amount):
    return s[:amount]

#open cursor file
try:
	lastCursor = open("/tmp/btEventCursor","r")
	cursor = lastCursor.read()
	lastCursor.close()
	cursorTimestamp = datetime.datetime.strptime(cursor, '%Y-%m-%dT%H:%M:%S')
except IOError as e:
	#print "Err Reading Cursor:" +str(e)
	cursor="" #set the cursor to empty
	cursorTimestamp = datetime.datetime.strptime("1971-01-01T00:00:00", '%Y-%m-%dT%H:%M:%S')
	
for event in reversed(eventDict):
	lastTime=left(event, 19)
	timestamp = datetime.datetime.strptime(lastTime, '%Y-%m-%dT%H:%M:%S')
	#print timestamp
	if timestamp > cursorTimestamp:
		print event

cursor = open("/tmp/btEventCursor","w")
cursor.write(lastTime)
cursor.close()


