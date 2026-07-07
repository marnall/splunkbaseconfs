import json
from datetime import datetime, timedelta
from etp_client import ETPClient

import requests

import utils
logger = utils.setup_logging()

# Advanced Threat APIs
## Alert Summary Request
### POST https://<etp-instance>/api/v1/alerts
class AdvancedThreat(ETPClient):

  DEFAULT_HOUR = 24 

  def __init__(self, **kwargs):

    super().__init__(kwargs.get('access_token'), kwargs.get('service_region'))

    self._legacy_id = kwargs.get('legacy_id') 
    self._etp_message_id = kwargs.get('etp_message_id')
    self._email_status = kwargs.get('email_status')
    
    # convert from_last_modified_on to a suitable format for ETP
    self._from_last_modified_on = kwargs.get('from_last_modified_on')

    self._proxies = kwargs.get('proxies') 
    self._ssl_verify = kwargs.get('ssl_verify')

  def _create_attributes(self):
    attributes = {}
    if self._etp_message_id:
      attributes['etp_message_id'] = self._etp_message_id
    elif self._legacy_id:
      attributes['legacy_id'] = self._legacy_id

    if self._email_status:
      attributes['email_status'] = [self._email_status]
    
    return attributes
    

  def alert_summary_api(self):
    url = self.url_base + '/alerts'

    body = {'attributes': self._create_attributes()}
    
    body['size'] = self.MAX_ALERT_SIZE

    if self._from_last_modified_on:
      body['fromLastModifiedOn'] = self._from_last_modified_on
    
    r = requests.post(url, headers=self.headers, json=body, 
                      proxies=self._proxies, 
                      verify=self._ssl_verify)
    r.raise_for_status()

    r_json = r.json()
    meta = r_json.get('meta')
    data = r_json.get('data')
    logger.info(meta)

    if meta is None:
      logger.info({'message': 'No meta'})
      return None
    
    if data is None:
      logger.info({'message': 'No data'})
      return None
    
    if self._from_last_modified_on and meta.get('fromLastModifiedOn').get('end'):
      self._from_last_modified_on = meta.get('fromLastModifiedOn').get('end')

    return r_json

  ## Alert Details Request
  ### GET https://<etp_instance_addr>/api/v1/alerts/<alert_id>
  def alert_details_api(self):
    pass

  ## Download Alert Artifact as ZIP
  ### POST https://<etp_instance_addr>/api/v1/alerts/<alert_id>/downloadzip
  def download_alert_artifact_as_zip_api(self):
    pass

  ## Download Alert Malware Files as zip
  ### POST https://<etp_instance_addr>/api/v1/alerts/<alert_id>/downloadmalware
  def download_alert_malware_as_zip_api(self):
    pass

  ## Download Alert PCAP Files
  ### POST https://<etp_instance_addr>/api/v1/alerts/<alert_id>/downloadpcap
  def download_alert_pcap_as_zip_api(self):
    pass


