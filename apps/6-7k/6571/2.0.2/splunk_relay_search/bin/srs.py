import sys,os,re
import json
import requests
import time
import splunk.entity as entity
import logging
import logging.handlers
import splunk.Intersplunk
from requests.structures import CaseInsensitiveDict
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import threading
from queue import Queue
from datetime import datetime

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
myqueue = Queue()
realm = 'default'
data = ""
veri = False

def setup_logger(level):
 logger = logging.getLogger('splunk_relay_search')
 logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
 logger.setLevel(level)
 file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/splunk_relay_search.log', maxBytes=25000000, backupCount=5)
 formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
 file_handler.setFormatter(formatter)
 logger.addHandler(file_handler)
 return logger

logger = setup_logger(logging.INFO)

def getCredentials(sessionKey,realm):
 myapp = 'splunk_relay_search'
 logger.info(myapp)
 try:
  entities = entity.getEntities("storage/passwords", namespace=myapp,owner='nobody', sessionKey=sessionKey)
 # logger.info(entities)
 except Exception as e:
  raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

 for i, c in entities.items():

  if c['eai:acl']['app'] == myapp and c['realm'] == realm:

   return c['username'], c['clear_password']
 raise Exception("No credentials have been found")

def header_query(string):
 string = "".join(string.lstrip())
 if string[0] == "|":
    stringr = string
 else:
    stringr = "search " + string
 return stringr

def extract_type(text):
 regex = "^(connection|search|app|earliest_time|latest_time|wait)="
 app_reg =  "".join(re.findall(regex, str(text)))
 if not app_reg:
  text = 'no_param'
 else:
  text = app_reg
 return text

def extract_value(chk,arg):
 regex = "^" + chk + "=(.+)"
 app_val = ','.join(re.findall(regex, str(arg)))
 return app_val

def token_user(hosts,headers):
 ur = "/services/authentication/current-context/"
 url = "https://" + hosts + ur

# logger.info(url)
 resp = requests.get(url, headers=headers, verify=veri)
 data = resp.text

 regex = "username\"\>(\S*)\<"
 username = ','.join(re.findall(regex, str(data)))

 logger.info(resp.status_code)
 if resp.status_code == 200:
  logger.info("started search")
 else:
#  raise Exception("Invalid SPL")
  raise Exception(resp.status_code)

 return username

def usr(sessionKey,realm,s_query,earliest_time,latest_time,app,wait,unique_id):

 username, password = getCredentials(sessionKey,realm)
 logger.info("Session key was retrieved")

 user,host,port,tk,auth = username.split(';')

 if auth=="1":
  auth = "Bearer"
 else:
  auth = "Splunk"

 if tk=="1":
  data = sr_user(user,password,host,port,tk,auth,s_query,earliest_time,latest_time,app,wait,unique_id)
 else:
  data = sr_token(user,password,host,port,tk,auth,s_query,earliest_time,latest_time,app,wait,unique_id)

 logger.info("data has return")
 return(data)

def sr_user(user,password,host,port,tk,auth,s_query,earliest_time,latest_time,app,wait,unique_id):

 scheme = 'https'
 hosts = host + ":" + port
 srs = " | eval srs =\"" + host + "\""
 username = user

 search_query = s_query + srs

 logger.info(search_query)

 post_data = { 'id' : unique_id,
  'search' : search_query,
  'earliest_time' : earliest_time,
  'latest_time' : latest_time,
  }

#'earliest_time' : '1', 'latest_time' : 'now'
#This will run the search query for all time

 ur='/servicesNS/' + username + '/'+ app + '/search/jobs'
 ur1=ur +'/'+ unique_id
 ur2=ur1 + '/results?count=0'

 splunk_search_base_url = scheme + '://' + hosts + ur

 resp = requests.post(splunk_search_base_url, data = post_data, verify = veri, auth = (username, password))

 logger.info(resp.status_code)
 if resp.status_code == 201:
  logger.info("started search")
 else:
  raise Exception(resp.status_code)

 is_job_completed = ''
 while(is_job_completed != 'DONE'):
  time.sleep(wait)
  get_data = {'output_mode' : 'json'}
  job_status_base_url = scheme + '://' + hosts + ur1

  resp_job_status = requests.post(job_status_base_url, data = get_data, verify = veri, auth = (username, password))

  resp_job_status_data = resp_job_status.json()
  is_job_completed = resp_job_status_data['entry'][0]['content']['dispatchState']


 splunk_summary_base_url = scheme + '://' + hosts + ur2
 splunk_summary_results = requests.get(splunk_summary_base_url, data = get_data, verify = veri, auth = (username, password))
 splunk_summary_data = splunk_summary_results.json()
 data = json.dumps(splunk_summary_data['results'])
 data = data[1:-1]

 myqueue.put(data)

def sr_token(user,password,host,port,tk,auth,s_query,earliest_time,latest_time,app,wait,unique_id):

 scheme = 'https'
 hosts = host + ":" + port
 srs = " | eval srs =\"" + host + "\""

 headers = CaseInsensitiveDict()
#Get username
 token = password
 headers["Authorization"] =  auth + " " + token
 headers["Accept"] = "application/json"
 username = token_user(hosts,headers)

 logger.info("username retrieve")
 search_query = s_query + srs

 logger.info(search_query)

 post_data = { 'id' : unique_id,
  'search' : search_query,
  'earliest_time' : earliest_time,
  'latest_time' : latest_time,
  }

#'earliest_time' : '1', 'latest_time' : 'now'
#This will run the search query for all time

 ur='/servicesNS/' + username + '/'+ app + '/search/jobs'
 ur1=ur +'/'+ unique_id
 ur2=ur1 + '/results?count=0'

 splunk_search_base_url = scheme + '://' + hosts + ur

 resp = requests.post(splunk_search_base_url, data = post_data, verify = veri, headers = headers)

 logger.info(resp.status_code)
 if resp.status_code == 201:
  logger.info("started search")
 else:
  raise Exception(resp.status_code)

 is_job_completed = ''
 while(is_job_completed != 'DONE'):
  time.sleep(wait)
  get_data = {'output_mode' : 'json'}
  job_status_base_url = scheme + '://' + hosts + ur1

  resp_job_status = requests.post(job_status_base_url, data = get_data, verify = veri, headers = headers)

  resp_job_status_data = resp_job_status.json()
  is_job_completed = resp_job_status_data['entry'][0]['content']['dispatchState']

 splunk_summary_base_url = scheme + '://' + hosts + ur2
 splunk_summary_results = requests.get(splunk_summary_base_url, data = get_data, verify = veri, headers=headers)
 splunk_summary_data = splunk_summary_results.json()
 data = json.dumps(splunk_summary_data['results'])
 data = data[1:-1]

 myqueue.put(data)

def main():

 app='search'
 earliest_time='-15m'
 latest_time='now'
 realm='default'
 wait = float(2)
 curr_dt = datetime.now()
 unique_id  = str(int(round(curr_dt.timestamp())))

 for idx, arg in enumerate(sys.argv):
  val=arg
  chk=extract_type(val)
  if chk == "app":
   app = extract_value(chk,arg)
  if chk == "earliest_time":
   earliest_time = extract_value(chk,arg)
  if chk == "latest_time":
   latest_time = extract_value(chk,arg)
  if chk == "search":
   search = extract_value(chk,arg)
   s_query = header_query(search)
  if chk == "connection":
   realm = extract_value(chk,arg)
  if chk == "wait":
   wait = float(extract_value(chk,arg))

 realm = realm.split(",")
# s_query = header_query(query)
 logger.info("starting to retrieve user")
## added for getting the credential from the sessionkey
 results, unused1, settings = splunk.Intersplunk.getOrganizedResults()
 sessionKey = settings['sessionKey']
 if len(sessionKey) == 0:
  logger.error("Did not receive a session key from splunkd.")
  exit(2)

 threads = [threading.Thread(target=usr, args=(sessionKey,x,s_query,earliest_time,latest_time,app,wait,unique_id,)) for x in realm]

 for j in threads: 
  j.start()
 
 for j in threads:
  j.join()
 
 result = list(myqueue.queue) 
 converted_list = [str(element) for element in result]
 string_result = ",".join(converted_list)
 data = "[" + string_result + "]"
 data = json.loads(data)

 splunk.Intersplunk.outputResults(data)

if __name__ == "__main__":
    main()

