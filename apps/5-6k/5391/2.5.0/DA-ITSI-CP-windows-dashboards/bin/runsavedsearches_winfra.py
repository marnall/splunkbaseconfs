import json
import os
import splunk.rest as rest
import splunk.entity as entity
import splunk.Intersplunk as intersplunk
import logging
from splunk.clilib.bundle_paths import make_splunkhome_path
from urllib.parse import quote

app_name = "DA-ITSI-ContentLibrary"
owner = 'nobody'
CONF_WEB = 'configs/conf-web'
url = "https://{}/servicesNS/nobody/DA-ITSI-ContentLibrary/saved/searches/{}/dispatch"

# setup the logger
def setup_logger():
    """
    Set up a logger with a rotating file handler for the search command.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger("windows_log_handler")
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log',
      'splunk', 'windows_runsavedsearches.log']), maxBytes=5000000, backupCount=1)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(lineno)d %(message)s'))

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

lookupSavedSearches = ["WinApp_Lookup_Build_Perfmon - Update - Server", 
                      "WinApp_Lookup_Build_Printmon - Update",
                      "WinApp_Lookup_Build_Netmon - Update - Server",
                      "WinApp_Lookup_Build_Hostmon_Process - Update - Detail",
                      "WinApp_Lookup_Build_Hostmon_FS - Update - Detail",
                      "WinApp_Lookup_Build_Hostmon_Machine - Update - Detail",
                      "WinApp_Lookup_Build_Hostmon - Update - Server",
                      "WinApp_Lookup_Build_Event - Update - Server",
                      "ActiveDirectory: Update Computer Lookup",
                      "ActiveDirectory: Update User Lookup",
                      "ActiveDirectory: Update Group Lookup",
                      "ActiveDirectory: Update GPO Lookup",
                      "SiteInfo_Lookup_Update",
                      "tHostInfo_Lookup_Update",
                      "HostToDomain_Lookup_Update",
                      "DomainSelector_Lookup"
                      ]
output = []

def getsessionkey():
    '''
        Get the Session Key
    '''
    results, dummyresults, settings = intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    return session_key

def fillLookup(splunkd_uri, session_key):
  '''
        Run savesearches to fill Host, Database, User Subject lookup
  '''

  for savedSearch in lookupSavedSearches:
    try:
      access_collection_url = url.format(splunkd_uri, quote(savedSearch))
      response, content = rest.simpleRequest(
            access_collection_url,
            sessionKey=session_key,
            method='POST',
            raiseAllErrors=True,
            postargs={"trigger_actions": "1"}
          )
      output.append({'savedSearch' : savedSearch, 'status' : response.status})
    except Exception as e:
        import traceback
        stack = traceback.format_exc()
        logger.error(str(stack))
        output.append({'savedSearch' : savedSearch, 'status' : str(e)})
  logger.info(output)

def main():
    try:
      session_key = getsessionkey()
      splunkd_uri = entity.getEntity(
                      CONF_WEB,
                      'settings',
                      sessionKey=session_key,
                      namespace=app_name,
                      owner=owner
                  ).get('mgmtHostPort', '127.0.0.1:8089')
      logger.info("Filling lookup with savedsearches result")
      fillLookup(splunkd_uri, session_key)
      intersplunk.outputResults(output)
    except Exception as e:
      import traceback
      stack = traceback.format_exc()
      logger.error(str(stack))
      errorMsg = intersplunk.generateErrorResults(
                "Something went wrong. Try again later\n Error : Traceback: " + str(stack)
                )
      intersplunk.outputResults(errorMsg)

if __name__ == "__main__":
    main()