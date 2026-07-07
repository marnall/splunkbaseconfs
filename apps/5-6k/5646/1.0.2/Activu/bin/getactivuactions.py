from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
import sys, os, json, requests, logging
import logging.handlers
from requests.auth import HTTPDigestAuth
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, splunklib_logger as logger
from splunk.clilib import cli_common as cli

@Configuration(type='reporting')
class getactivuactionsCommand(GeneratingCommand):
  proxies    = Option(require=False)
  unsetProxy = Option(require=False, validate=validators.Boolean())

  def generate(self):
    proxies    = self.parseProxies(self.proxies) if self.proxies != None else None
    unsetProxy = bool(self.unsetProxy)

    logger = setup_logger(logging.DEBUG)
    cfg = cli.getConfStanza('alert_actions','Activu')
#    logger.debug("Configuration stanza parameters are: %s", cfg)
#    logger.debug("Activu URL for the alerts: %s", cfg.get('param.base_url'))
#    logger.debug("Endpoint URL: %s", cfg.get('param.api_endpoint'))
#    logger.debug("Authorization Header: %s", cfg.get('param.aheader'))

    base_url = cfg.get('param.base_url')
    url = cfg.get('param.api_endpoint')
    aheader = cfg.get('param.aheader')

    config = 1
    # Verifying Activu webhook URL (not mandatory). For Splunk Cloud vetting, URLs must start with https://
    if base_url == None:
       logger.warn("Incorrect configuration - Activu URL is not defined.")
       logger.warn("In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts")
    if base_url != None and not base_url.startswith('https://'):
       logger.warn("Incorrect configuration - Activu URL should start with https://, yet it is: %s", base_url)
       logger.warn("In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts")

    # Verifying endpoint URL to pull alerts from (mandatory). For Splunk Cloud vetting, URLs must start with https://
    if url == None:
       logger.error("Incorrect configuration - Endpoint URL is not defined. In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts")
       config = 0
       yield ({"Alerts": {"Name": "Incorrect configuration - Endpoint URL is not defined. In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts"}})
    if url != None and not url.startswith('https://'):
       logger.error("Incorrect configuration - Endpoint URL should start with https://, yet it is: %s", url)
       logger.error("In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts")
       config = 0
       yield ({"Alerts": {"Name": "Incorrect configuration - Endpoint URL should start with https://. In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts"}})

    # Verifying presence of Authentication Header for the endpoint URL
    if aheader == None or aheader == '':
       logger.error("Incorrect configuration - Authorization Header is not defined. In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts")
       config = 0
       yield ({"Alerts": {"Name": "Incorrect configuration - Authorization Header is not defined. In Splunk Web UI this can be done from Apps -> Manage apps -> Set Up action on Activu alerts"}})
    else:
       headers = {'Authorization':aheader}

    # If configuration is ok - load actions from Activu API
    if config == 1:
      # Unset proxy, if unsetProxy = True
      if unsetProxy == True:
        if 'HTTP' in os.environ.keys():
          del os.environ['HTTP']
        if 'HTTPS' in os.environ.keys():
          del os.environ['HTTPS']

      record = {}
      try:
        request = requests.get(url, headers=headers, proxies=proxies, verify=False)
        record = request.json()

      except requests.exceptions.RequestException as err:
        logger.error("Record: %s", record)
        record = ({"Alerts": {"Name": err}})

      logger.info("Record: %s", record)
      yield record

  '''
    Parse proxy into python dict
    @proxy string: Comma separated proxies -> http,https
    @return dict
  '''
  def parseProxies(self, proxies):
    proxies = proxies.split(',')

    return {
      'http': proxies[0].strip(),
      'https' : proxies[1].strip()
    }

  '''
    Convert headers string into dict
    @headers string: Headers as json string
    @return dict
  '''
  def parseHeaders(self, headers):
    return json.loads(
      headers.replace('\'', '"')
    )

def setup_logger(level):
    logger = logging.getLogger('getactivuactions')
    logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/getactivuactions.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger

dispatch(getactivuactionsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
