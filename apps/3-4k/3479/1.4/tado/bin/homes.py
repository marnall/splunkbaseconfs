#!/usr/bin/python

import urllib, urllib2, json, sys
import splunk.entity as entity


# access the credentials in /servicesNS/nobody/app_name/admin/passwords
def getCredentials(sessionKey):
   myapp = 'tado'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)
   except Exception, e:
      raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

   # return first set of credentials
   for i, c in entities.items():
        return c['username'], c['clear_password']

   raise Exception("No credentials have been found")

def main():
        # read session key sent from splunkd
        sessionKey = sys.stdin.readline().strip()

        if len(sessionKey) == 0:
           sys.stderr.write("Did not receive a session key from splunkd. " +
                            "Please enable passAuth in inputs.conf for this " +
                            "script\n")
           exit(2)

        username, password = getCredentials(sessionKey)
        token = getAuth(username, password)
	homeId = getHomeId(token)
	doRequest(token,homeId)

def getAuth(email, password):

	data = dict(client_id="tado-web-app",grant_type="password",password=password,scope="home.user", username=email,client_secret="wZaRN7rpjn3FoNyF5IFuxg9uMzYJcvOoQ8QWiIqS3hfk6gLhVlG57j5YNoZL2Rtc" )
	authUrl = "https://my.tado.com/oauth/token"
	method = "POST"
	handler = urllib2.HTTPHandler()
	opener = urllib2.build_opener(handler)
	data = urllib.urlencode(data)
	request = urllib2.Request(authUrl, data=data)
	request.get_method = lambda: method
	try:
    		connection = opener.open(request)
	except urllib2.HTTPError,e:
    		connection = e

	if connection.code == 200:
    		responseData = str(connection.read())
		jsonList = json.loads(responseData)

		return jsonList['access_token']
	else:
		print "errorCode="+str(connection.code)

def getHomeId(token):
	url = "https://my.tado.com/api/v2/me"

	req = urllib2.Request(url)
        req.add_header("Authorization","Bearer "+token)

        handler = urllib2.HTTPHandler()
        opener = urllib2.build_opener(handler)
        try:
                connection = opener.open(req)
        except urllib2.HTTPError,e:
                connection = e

        if 200 <= connection.code <= 207:
 		responseData = str(connection.read())
                jsonList = json.loads(responseData)

		return jsonList['homes'][0]['id']
        else:
                print "errorCode="+str(connection.code)

def doRequest(token,homeId):


	url = "https://my.tado.com/api/v2/homes/"+str(homeId)

	req = urllib2.Request(url)
	req.add_header("Authorization","Bearer "+token)

	handler = urllib2.HTTPHandler()
	opener = urllib2.build_opener(handler)
	try:
		connection = opener.open(req)
	except urllib2.HTTPError,e:
		connection = e

	if 200 <= connection.code <= 207:
		print connection.read()
	else:
		print "errorCode="+str(connection.code)

main()
