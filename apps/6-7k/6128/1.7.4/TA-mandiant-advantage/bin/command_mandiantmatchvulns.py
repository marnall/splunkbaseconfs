import json, requests, sys, time
import import_declare_test

from common.collections import CollectionManager
from common.log import get_logger
from common.proxy import transform_proxy_config
from common.utility import get_app_version, read_conf_file
from requests.exceptions import RequestException
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration


logger = get_logger(__file__)


@Configuration()
class MandiantMatchVulns(StreamingCommand):
  """Manage the processing of the VUlnerability Correlation feature"""

  def stream(self, records):
    """Entry point for the command, inherited from the StreamingCommand class.

    Receives events (records) from the results of a Splunk search, attepts to
    match values of provided fields with vulns from the Mandiant API

    Yields:
      record: a dict of one of the processed search results
    """
    # Get session key
    session_key = self.service.token
    logger.info("Splunk session key collected")

    app_version = get_app_version(session_key)
    logger.info(f"Starting Vulnerability Correlation. Version: {app_version}")

    # Get account details, if fails log and exit
    conf_file = read_conf_file(session_key, "ta_mandiant_advantage_settings",
                               stanza="vuln_correlation_parameters")
    account_name = conf_file.get("mandiant_vuln_advantage_account")

    if not account_name:
      err = "Account Name not defined. Select a Mandiant Advantage account in " \
        "the Vulnerability Correlation settings."
      logger.error(err)
      yield {'error': err}

    account_details = read_conf_file(session_key, "ta_mandiant_advantage_account",
                   stanza=account_name)

    if account_details.get('account_type') != "mandiant_advantage":
      err = "Incorrect account type defined. Please select a Mandiant " \
        "Advantage account"
      logger.error(err)
      yield {'error': err}

    logger.info(f"Successfully discovered account details: {account_name}")

    # Initiate Mandiant API Details, if fails log and exit
    api_url = "https://api.intelligence.mandiant.com/v4/vulnerability"
    req_headers = {
      'X-App-Name': f"MA-Splunk-{app_version}",
      'Content-Type': 'application/json'
    }
    access_key = account_details.get('client_id')
    secret_key = account_details.get('client_secret')

    # Generate proxy settings
    if account_details.get('proxy_enabled') == "1":
      proxy_config = {
        'proxy_enabled': account_details.get("proxy_enabled"),
        'proxy_username': account_details.get("proxy_username"),
        'proxy_port': account_details.get("proxy_port"),
        'proxy_type': account_details.get("proxy_type"),
        'proxy_password': account_details.get("proxy_password"),
        'proxy_url': account_details.get("proxy_url")
      }
      proxies = transform_proxy_config(proxy_config)
      logger.info(f"Using proxy: {account_details.get('proxy_url')}")
    else:
      proxies = None
      logger.info(f"Not using proxy, going direct")

    # Setup collection manager
    vuln_collection = CollectionManager(session_key,
                                        "mandiant_vuln_matched_lookup")
    self.existing_matches = vuln_collection._collection_as_dict()
    logger.info("Successfully initialized the mandiant_vuln_matched_lookup "
                "collection")

    # Process events
    for record in records:
      # for each field except host get the CVE value
      for _key in record:
        if _key == "host" or _key == "host_":
          continue

        _value = record.get(_key)
        logger.info(f"Attempting to correlate field: {_key} with value "
                    f"{_value}")

        # if value does not start with CVE log and continue
        if not _value.startswith("CVE-"):
          logger.info(f"Value: {_value} not a CVE, skipping")
          continue

        # check CVE against Mandiant API
        _data = json.dumps({"requests": [{"values": [_value]}]})
        try:
          vuln_resp = requests.post(url=api_url, headers=req_headers,
                             auth=(access_key, secret_key), data=_data,
                             proxies=proxies)
        except RequestException as ex:
          err = f"Error requesting vulnerability {_value} from Mandiant: {str(ex)}"
          logger.error(err)
          yield {'error': err}

        # At this point the request was successful, but we cannot be sure the
        # response is what we expect...Check response is JSON
        if not isinstance(vuln_resp.json(), dict):
          logger.error("Unexpected response from request to Mandiant API. "
                       f"Response: {vuln_resp.text}")
          continue

        # At this point the response is JSON, we still cannot be sure it is the
        # expected response though...Check expected key is in JSON
        if "vulnerabilities" not in vuln_resp.json():
          logger.error("Expected key: vulnerabilities not found in response "
                       "from request to Mandiant API. Response: "
                       f"{json.dumps(vuln_resp.json())}")
          continue

        # At this point the response is JSON and the expected key is found, 
        # one last check to validate the the vulnerabilities key is a list
        if not isinstance(vuln_resp.json().get("vulnerabilities"), list):
          logger.error("Unexpected field type returned from API: " 
                       f"{json.dumps(vuln_resp.json())}")
          continue

        # if CVE not found continue
        if len(vuln_resp.json().get('vulnerabilities')) == 0:
          logger.info(f"Vulnerability {_value} not tracked by Mandiant")
          continue

        # build KV store row
        _row = self._translate_vuln(vuln_resp.json().get('vulnerabilities')[0],
                                    record.get('host_'))
        logger.info(f"Successfully correlated vulnberability: {_value}")

        # submit row to KV store
        vuln_collection._batch_save([_row])
        logger.info(f"Successfully submitted vulnberability: {_value} to KV Store")

        yield _row

  def _translate_vuln(self, vuln: dict, host: str) -> dict:
    """
    Translates a vulnerability response from the Mandiant API and returns a 
    dict ready to be submitted as a row in the mandiant_vuln_matched_lookup 
    KV Store Collection
    
    Params:
    -------
      vuln: the vulnerability response from Mandiant
      host: the value of the host field from the Splunk record
    
    Returns:
    --------
      row: a dict ready to be submitted as a row in the 
      mandiant_vuln_matched_lookup KV Store Collection
    """
    row = {
        "_key":
            vuln.get('cve_id'),
        'hosts':
            self._hosts(vuln.get('cve_id'), host),
        'vuln_id':
            vuln.get('id'),
        'exploitation_state':
            vuln.get('exploitation_state'),
        'risk_rating':
            vuln.get('risk_rating'),
        'cve_last_match_time':
            int(time.time()),
        'available_mitigations':
            vuln.get('available_mitigation'),
        'associated_actor_names':
            self._associated_actors(vuln.get('associated_actors')),
        'cpe_vendor_names':
            self._cpe_vendor_names(vuln.get('vulnerable_cpes')),
        'cpe_vendor_technology_names':
            self._cpe_vendor_tech_names(vuln.get('vulnerable_cpes'))
    }

    return row

  def _hosts(self, cve_id: str, host: str) -> list:
    """Checks if vulnerability has already been matched and returns a list of 
    hosts subject to the vulnerability"""
    if cve_id in self.existing_matches:
      logger.info(f"Vulnerability: {cve_id} already matched, updating hosts")
      hosts = self.existing_matches.get(cve_id).get('hosts')
      for h in hosts:
        host_name = h.split("||")[0]
        if host == host_name:
          hosts.remove(h)
    else:
      hosts = []

    hosts.append(f"{host}||{int(time.time())}")

    return list(hosts)

  @staticmethod
  def _associated_actors(actors: list) -> list:
    actor_list = []
    for actor in actors:
      actor_list.append(actor.get('name'))

    return actor_list

  @staticmethod
  def _cpe_vendor_names(cpes: list) -> list:
    cpe_vendor_names = set()
    for cpe in cpes:
      cpe_vendor_names.add(cpe.get('vendor_name'))

    return list(cpe_vendor_names)

  @staticmethod
  def _cpe_vendor_tech_names(cpes: list) -> list:
    cpe_vendor_tech_names = set()
    for cpe in cpes:
      cpe_vendor_tech_names.add(cpe.get('technology_name'))

    return list(cpe_vendor_tech_names)


dispatch(MandiantMatchVulns, sys.argv, sys.stdin, sys.stdout, __name__)
