import splunk.entity, splunk.Intersplunk 
import requests, sys
import urllib, os

import logging
import logging.handlers

def setup_logger(level):
     logger = logging.getLogger('my_search_command')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
 
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME']+ '/var/log/splunk/exportpdf.log', maxBytes=25000000, backupCount=5)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
    
     logger.addHandler(file_handler)
    
     return logger


logger = setup_logger(logging.INFO)

dashboard_url   = sys.argv[1]
schedule_param   = sys.argv[2]

logger.info("Starting export pdf %s", dashboard_url)

results,unused1,settings = splunk.Intersplunk.getOrganizedResults()

url = "https://127.0.0.1:8089/servicesNS/"+settings["owner"]+"/" +settings["namespace"]+ "/pdfexport"  

headers = {'Authorization':''}
headers['Authorization'] = 'Splunk ' + settings["sessionKey"]

logger.info("REST API call to  %s %s", url, settings["sessionKey"])

data = [
  ('DashboardURL', dashboard_url),
  ('ScheduleParam', schedule_param),
]

#response = requests.post('https://127.0.0.1:8089/servicesNS/admin/search/pdfexport', data=data, verify=False, headers=headers)
response = requests.post(url, data=data, verify=False, headers=headers)


#logger.info("REST API return code  %s", r.status_code)

splunk.Intersplunk.outputResults(results)
