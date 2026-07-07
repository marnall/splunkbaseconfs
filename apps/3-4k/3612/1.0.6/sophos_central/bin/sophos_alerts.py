#!/usr/bin/python

import urllib, urllib2, json, sys, tempfile
import splunk.entity as entity

# access the credentials in /servicesNS/nobody/app_name/admin/passwords
def getCredentials(sessionKey):
   myapp = 'sophos_central'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)
   except Exception, e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials
   for i, c in entities.items():
	if "central.sophos.com" in c['realm']:
            return c['realm'],c['username'], c['clear_password']
   raise Exception("No credentials have been found")

def main():
        # read session key sent from splunkd
        sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
           sys.stderr.write("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           exit(2)

        endpoint, apiKey, auth = getCredentials(sessionKey)
	getAlerts(endpoint,apiKey,auth)


def getAlerts(endpoint, apiKey, auth):
        tmpPath = tempfile.gettempdir()
	#open cursor file
	try:
		lastCursor = open(tmpPath+"/alertCursor","r")
		cursor = lastCursor.read()
		lastCursor.close()
	except IOError as e:
		#print "Err Reading Cursor:" +str(e)
		cursor="" #set the cursor to empty

	path ="/siem/v1/alerts/?limit=1000&cursor="+cursor
	uri = str(endpoint)+str(path)

	req = urllib2.Request(uri)
	req.add_header("x-api-key",str(apiKey))
	req.add_header("Authorization","Basic "+str(auth))

	handler = urllib2.HTTPHandler()
        opener = urllib2.build_opener(handler)
	try:
		connection = opener.open(req)
	except urllib2.HTTPError,e:
		connection = e

	if 200 <= connection.code <= 207:
		responseData = str(connection.read())
		jsonList = json.loads(responseData)

		nextCursor = jsonList['next_cursor']
		newCursor = open(tmpPath+"/alertCursor","w")
		newCursor.write(nextCursor)
		newCursor.close()
		
		alertList = jsonList['items']
		for alert in alertList:
			created_at = str(alert['created_at'])
                        customer_id = str(alert['customer_id'])
                        description = str(alert['description'])
                        id = str(alert['id'])
                        location = str(alert['location'])
                        severity = str(alert['severity'])
                        source = str(alert['source'])
                        threat = str(alert['threat'])
                        threat_cleanable = str(alert['threat_cleanable'])                       
                        type = str(alert['type'])
                        when = str(alert['when'])
                        print when + " customer_id=\""+customer_id+"\" description=\""+description+"\" id=\""+id+"\" location=\""+location+"\" severity=\""+severity+"\" eventsource=\""+source+"\" threat=\""+threat+"\" threat_cleanable=\""+threat_cleanable+"\" type=\""+type+"\" created_at=\""+created_at+"\" vendor=\"Sophos\" product=\"Central Endpoint Protection\""


	else:
		print "errorCode="+str(connection.code)
main()
