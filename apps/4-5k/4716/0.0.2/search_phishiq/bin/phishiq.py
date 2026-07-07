#import os, sys, time, requests, oauth2, json, urllib

#from splunklib.searchcommands import \
#  dispatch, StreamingCommand, Configuration, Option, validators

#@Configuration()
#class PhishiqStreamingCommand(StreamingCommand):
#  fieldname = Option(require=True)
  
#  def stream(self, records):
#    row = next(records, None)
#    yield { 'test' : row['url'], '_time' : 0 }
	  
#dispatch(PhishiqStreamingCommand, sys.argv, sys.stdin, sys.stdout, __name__)

import os, sys, time, requests, oauth2, json, urllib
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option

@Configuration()
class PhishiqStreamingCommand(EventingCommand):
    fieldname = Option(require=True)

    def transform(self, records):    

        apiKey = ""        

        for passwd in self.service.storage_passwords:  # type: StoragePassword
            if (passwd.realm is None or passwd.realm.strip() == "") and passwd.username == "ps_proxy":
                apiKey = passwd.clear_password

        if apiKey is None or apiKey == "defaults_empty":
            self.error_exit(None, "No API key found. Please re-run the setup.")

        url = 'http://api.phishiq.advoqt.com/api/processurls'
        actualRecords = []
        urls = []

        for record in records:

            if len(urls) < 1000:

                urls.append(record[self.fieldname] + '')
                actualRecords.append(record)
            else:
                
                response = requests.post(url, data=json.dumps({"urls": urls }), headers = { "Content-Type" : "application/json", "Authorization" : apiKey })
                results = response.json()

                index = 0
                for rec in actualRecords:
                    rec['phishiq_verifiedurl'] = results['results'][index]['url']
                    if response.status_code == 200:
                        rec['phishiq_percentage'] = int(results['results'][index]['percentage'])
                        rec['phishiq_maliciousness'] = int(results['results'][index]['maliciousness'])
                    else:
                        rec['phishiq_error'] = results['message']
                    index = index + 1
                    yield rec

                urls = []
                actualRecords = []

        if len(urls) > 0:
            response = requests.post(url, data=json.dumps({"urls": urls }), headers = { "Content-Type" : "application/json", "Authorization" : apiKey })
            results = response.json()

            index = 0
            for rec in actualRecords:
                rec['phishiq_verifiedurl'] = results['results'][index]['url']
                if response.status_code == 200:
                    rec['phishiq_percentage'] = int(results['results'][index]['percentage'])
                    rec['phishiq_maliciousness'] = int(results['results'][index]['maliciousness'])
                else:
                    rec['phishiq_error'] = results['message']
                index = index + 1
                yield rec

        #for record in records:

            #url = 'http://api.phishiq.advoqt.com/api/processurls'
            #response = requests.post(url, data=json.dumps({"urls": record['url'].split(',') }), headers = { "Content-Type" : "application/json", "Authorization" : apiKey })
            #results = response.json()

            #if response.status_code != 200:
            #    record['phishiq_percentage'] = -1
            #    record['phishiq_maliciousness'] = -1
            #else:
            #    record['phishiq_percentage'] = int(results['results'][0]['percentage'])
            #    record['phishiq_maliciousness'] = int(results['results'][0]['maliciousness'])
            #yield record


dispatch(PhishiqStreamingCommand, sys.argv, sys.stdin, sys.stdout, __name__)