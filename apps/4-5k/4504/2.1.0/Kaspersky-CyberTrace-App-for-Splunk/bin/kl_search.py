import os, sys, time, socket, json
import splunk.Intersplunk
import splunklib.client as client

BUFFER_SIZE = 32768
HEADER = b"X-KF-SendFinishedEventX-KF-ReplyBack"
APP_NAME = "Kaspersky-CyberTrace-App-for-Splunk"
VERIFICATION_TEST = {
"Malicious_URL_Data_Feed": "http://fakess123.nu",
"Phishing_URL_Data_Feed": "http://fakess123ap.nu",
"Botnet_C&C_URL_Data_Feed": "http://a7396d61caffe18a4cffbb3b428c9b60.com",
"IP_Reputation_Data_Feed": "192.0.2.0",
"Malicious_Hash_Data_Feed": "C912705B4BBB14EC7E78FA8B370532C9",
"Ransomware_URL_Data_Feed": "http://fakess123r.nu",
"Mobile_Malicious_Hash_Data_Feed": "60300A92E1D0A55C7FDD360EE40A9DC1",
"Mobile_Botnet_Data_Feed": "001F6251169E6916C455495050A3FB8D",
"DEMO Botnet_C&C_URL_Data_Feed": "http://5a015004f9fc05290d87e86d69c4b237.com",
"DEMO IP_Reputation_Data_Feed": "192.0.2.1",
"DEMO Malicious_Hash_Data_Feed": "776735A8CA96DB15B422879DA599F474",
"APT_URL_Data_Feed": "http://b046f5b25458638f6705d53539c79f62.com",
"APT_Hash_Data_Feed": "7A2E65A0F70EE0615EC0CA34240CF082",
"APT_IP_Data_Feed": "192.0.2.4",
"IoT_URL_Data_Feed": "http://e593461621ee0f9134c632d00bf108fd.com/.i",
"Vulnerability_Data_Feed": "D8C1F5B4AD32296649FF46027177C594",
"ICS_Hash_Data_Feed": "7A8F30B40C6564EFF95E678F7C43346C"
}


class Config():
    def __init__(self):
        self.service_addr = '127.0.0.1'
        self.service_port = 9999


def KLLookupCommand(results, config):
    try:
        keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()

        if "verification" in keywords:
            return verification_test(config)
        if len(keywords) > 0:
            lookupvalue = val = keywords[0]
        else:
            lookupvalue, val = prepare_request(argvals)
        if not lookupvalue:
            return splunk.Intersplunk.generateErrorResults("klsearch requires indicator for lookup.")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((config.service_addr, config.service_port))
        s.settimeout(5)
        s.send(HEADER)

        results = []
        s.send(lookupvalue.encode() + b'\n')
        data = ''
        result = {}
        while True:
            data += s.recv(BUFFER_SIZE).decode()
            if '\n' in data:
                break
        if 'matchedIndicator' not in data:
            result['_raw'] = "There is no data in Kaspersky CyberTrace"
        else:
            result['_raw'] = data
        result['LookupIndicator'] = val
        results.append(result)
        s.close()
        return results
    except Exception as e:
        import traceback
        stack = traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))
        return results


def prepare_request(value):
    for ind in value:
        return ('%s=%s ') % (ind, value[ind]), value[ind]


def get_configuration():
    sourcePath = os.path.dirname(os.path.abspath(__file__))
    config_file = open(sourcePath + '/config.json')
    return json.load(config_file)


def verification_test(config):
  try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((config.service_addr, config.service_port))
    s.settimeout(1)
    s.send(HEADER)

    results = []
    for feed in VERIFICATION_TEST:
      try:
         result = {}
         s.send(str(VERIFICATION_TEST[feed]).encode() + b'\n')
         data = s.recv(BUFFER_SIZE).decode()
         if "eventName" in data:
           result['feed'] = feed
           result['status'] = "OK"
         else:
           result['feed'] = feed
           result['status'] = "FALSE"
         results.append(result)
      except socket.timeout:
         result['feed'] = feed
         result['status'] = "FALSE"
         results.append(result)
         continue

    s.close()

  except Exception as e:
        import traceback
        stack = traceback.format_exc()
        results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))
  return results


def get_settings(splunk_from_settings):
    """get settings from Splunk storage"""
    try:
        os.chdir(os.path.dirname(os.path.realpath(__file__)))
        session_key = splunk_from_settings.get("sessionKey")
        restSettings = get_configuration()
        config = Config()
        splunk_kvstore = client.connect(host=restSettings['SplunkRESTAPI'], token=session_key, app=restSettings['APP_NAME'], owner='nobody')
        collection = splunk_kvstore.kvstore['kl_cybertrace_settings']
        collection = collection.data.query()
        if len(collection) > 0:
            config.service_addr = collection[0]['KTCHost']
            config.service_port = int(collection[0]['KTCPort'])
        return config
    except Exception as e:
        import traceback
        stack = traceback.format_exc()
        splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack)))


results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
config = get_settings(settings)
results = KLLookupCommand(results, config)
splunk.Intersplunk.outputResults(results)
