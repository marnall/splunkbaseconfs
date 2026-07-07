import sys,re

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import requests
import json
import time
import os
import ConfigParser

@Configuration()
class haveIBeenPwned(StreamingCommand):
	g_sField = Option(name='field',require=True)
	g_bEnableProxy = False
        g_sHTTP_Proxy = None
        g_sHTTPS_Proxy = None
	g_sAPI_Key = None
	def stream(self,events):
		self.fnGetConfig()
		for event in events:
			result = self.getData(event[self.g_sField])
			event['Pwned_Details'] = result
			yield event

			
	def fnGetConfig(self):
                try:
                        l_sPath = os.path.join(os.environ['SPLUNK_HOME'], 'etc/apps/TA-hibp-api/local/hibpq.conf')
                        l_hConfig = ConfigParser.ConfigParser()
                        l_hConfig.read(l_sPath)
                        if l_hConfig.has_section('settings'):
                                if l_hConfig.has_option('settings', 'is_use_proxy'):
                                        self.g_bEnableProxy = l_hConfig.getboolean('settings', 'is_use_proxy')
                                        if l_hConfig.has_option('settings', 'http_proxy'):
                                                self.g_sHTTP_Proxy = l_hConfig.get('settings', 'http_proxy')
                                        if l_hConfig.has_option('settings', 'https_proxy'):
                                                self.g_sHTTPS_Proxy = l_hConfig.get('settings', 'https_proxy')
                                else:
                                        self.g_bEnableProxy = False
                                if l_hConfig.has_option('settings', 'api_key'):
                                        self.g_sAPI_Key = l_hConfig.get('settings', 'api_key')
                                else:
                                        self.g_sAPI_Key = None
                except Exception,e:
                        raise e	
	def getData(self,email):
		if self.g_bEnableProxy is True:
			proxyDict = { 
              			"http"  : self.g_sHTTP_Proxy, 
              			"https" : self.g_sHTTPS_Proxy
            			}
			
		else:
			proxyDict = {
                                "http"  : None,
                                "https" : None
                                }
		url = "https://haveibeenpwned.com/api/v3/breachedaccount/"+email
		api_key = {'User-Agent': 'Splunk', 'hibp-api-key': self.g_sAPI_Key}
		try:
			r = requests.get(url ,headers=api_key, params={'truncateResponse': 'false'},timeout=10)
			startTime =time.time()	
			eventFull=[]
			if r.status_code ==200:
				data =  r.json()
				for title in data:
    					dc =[]
    					for dataclasses in title['DataClasses']:
        					dc.append(dataclasses.encode("ascii"))
					eventFull.append("Title: "+str(title['Title'].encode("ascii"))+", BreachedDate: "+str(title['BreachDate'].encode("ascii"))+", DataClasses: "+str(dc))
				runTime = int(time.time()-startTime)
				time.sleep(1.5 - runTime)
    				return eventFull
			elif r.status_code==404:
				runTime = int(time.time()-startTime)
				time.sleep(1.5 - runTime)
				return "Not pwned"
			else:
				runTime = int(time.time()-startTime)
                                time.sleep(1.5 - runTime)
                                return "Error: Response Code - "+str(r.status_code)
		
		except Exception as e:
			return "HTTPSConnectionError,You may need to configure proxy"


if __name__ == "__main__":
	dispatch(haveIBeenPwned, sys.argv, sys.stdin, sys.stdout, __name__)
