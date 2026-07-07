
# python phishiq.py __EXECUTE__ 'urls="http://google.com,http://ibm.com"'

import os, sys, time, requests, oauth2, json, urllib

from splunklib.searchcommands import \
  dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration()
class PhishiqCommand(GeneratingCommand):
  urls = Option(require=True)

  def generate(self):
    config = self.get_configuration()
    url = self.get_url(config["api-url"])

    apiKey = ""        

    for passwd in self.service.storage_passwords:  # type: StoragePassword
        if (passwd.realm is None or passwd.realm.strip() == "") and passwd.username == "ps_proxy":
            apiKey = passwd.clear_password

    if apiKey is None or apiKey == "defaults_empty":
        self.error_exit(None, "No API key found. Please re-run the setup.")    

    response = requests.post(url, data=json.dumps({"urls": self.urls.split(',') }), headers = { "Content-Type" : "application/json", "Authorization" : apiKey })

    results = response.json()
    
    if response.status_code != 200:
      yield { 'ERROR': results['error'] }
      return
    
    for result in results["results"]:
      yield self.getRow(result)

  def getRow(self, result):
    event = {'maliciousness': result['maliciousness'], 'percentage': result['percentage'], 'url': result['url']}
    event["_raw"] = json.dumps(result)

    return event

  def get_configuration(self):
    sourcePath = os.path.dirname(os.path.abspath(__file__))
    config_file = open(sourcePath + '/config.json')
    return json.load(config_file)

  def get_url(self, api_url):
    url_params = {}

    """Returns response for API request."""
    # Unsigned URL
    encoded_params = ''
    if url_params:
      encoded_params = urllib.urlencode(url_params)
    url = api_url

    return url

dispatch(PhishiqCommand, sys.argv, sys.stdin, sys.stdout, __name__)
