import json
from dateutil import tz
from datetime import datetime, timedelta

import requests

from etp_client import ETPClient
import utils
logger = utils.setup_logging()

# Email Trace API
## Email TraceRequeston thenextpage
### POST https://<etp_instance_addr>/api/v1/messages/trace
class EmailTrace(ETPClient):

  DEFAULT_HOUR = 3 

  def __init__(self, **kwargs):

    super().__init__(kwargs.get('access_token'), kwargs.get('service_region'))
    
    self.subject = kwargs.get('subject')
    self.from_email = kwargs.get('from_email')
    self.to_email = kwargs.get('to_email')
    self.at_verdict = kwargs.get('at_verdict') 
    #self.etp_message_id = kwargs.get('etp_message_id') if kwargs.get('etp_message_id') is not None else None
    
    # datetime format
    self.last_modified_priority = False
    if kwargs.get('last_modified_datetime'):
      self.last_modified_priority = True
      self.last_modified_datetime = utils.change_datetime_to_utc(kwargs.get('last_modified_datetime'), self.DEFAULT_HOUR)
    else:
      self.to_accepted_dt = utils.change_datetime_to_utc(kwargs.get('to_accepted_dt'), 0)
      self.from_accepted_dt = utils.change_datetime_to_utc(kwargs.get('from_accepted_dt'), self.DEFAULT_HOUR)    

    self.proxies = kwargs.get('proxies') 
    self.ssl_verify = kwargs.get('ssl_verify') 


  def _create_attributes(self):
    attributes = {}
    if self.from_email:
      attributes['fromEmail'] = {
        'value': [self.from_email], 
        'filter': 'in',
        'includes': ['SMTP', 'HEADER']}

    if self.to_email:
      attributes['recipients'] = {
        'value': [self.to_email], 
        'filter': 'in',
        'includes': ['SMTP', "HEADER"]}

    if self.at_verdict and self.at_verdict in ['fail', 'Pass']:
      attributes['atVerdict'] = {'value': [self.at_verdict], 'filter': 'in'}
    
    if self.subject:
      attributes['subject'] = {'value': [self.subject], 'filter': 'in'}

    if self.last_modified_priority:
      attributes['lastModifiedDateTime'] = {
        'filter': '>=',
        'value': self.last_modified_datetime
      }
    else:
      self.period = {
        'range': {
          'fromAcceptedDateTime': self.from_accepted_dt,
          'toAcceptedDateTime': self.to_accepted_dt
        },
      }
      attributes['period'] = self.period
    return attributes


  def email_trace_api(self):
    url = self.url_base + '/messages/trace'
    
    body = {
      'attributes': self._create_attributes(),
      'size': self.MAX_PAGE_SIZE
    }
    
    r = requests.post(url, headers=self.headers, json=body,
                      proxies=self.proxies, 
                      verify=self.ssl_verify)
    r.raise_for_status()

    r_json = r.json()
    meta = r_json.get('meta')
    data = r_json.get('data')

    if meta is None:
      logger.info({'message': 'No meta'})
      return None
    
    if data is None:
      logger.info({'message': 'No data'})
      return None

    if meta.get('size') == 0:
      logger.info({'message': 'No more data'})
      return None

    # sorted_data = sorted(data, key=lambda x: x['attributes']['acceptedDateTime'])
    logger.info(meta)
    logger.info({ 'first acceptedDateTime': data[0].get('attributes').get('acceptedDateTime'), 
                  'last acceptedDateTime': data[-1].get('attributes').get('acceptedDateTime')})

    if self.last_modified_priority and meta.get('fromLastModifiedOn').get('end'):
      #attributes['lastModifiedDateTime']['value'] = meta.get('fromLastModifiedOn').get('end')
      self.last_modified_datetime = meta.get('fromLastModifiedOn').get('end')
    else: 
      #self.period['range']['fromAcceptedDateTime'] = data[-1].get('attributes').get('acceptedDateTime')
      self.from_accepted_dt = data[-1].get('attributes').get('acceptedDateTime')

    return r_json


  ## Message Trace Information Requeston
  ### GET https://<etp_instance_addr>/api/v1/messages/<etp_message_id>
  def message_trace_information_api(self):
    pass

  ## Original Message ID Requeston
  ### GET https://<etp_instance_addr>/api/v1/messages?original_message_id="<original_message_id>"
  def original_message_id_api(self):
    pass

  ## Message File Requeston
  ### GET https://<etp_instance_addr>/api/v1/messages/<etp_message_id>/email
  def message_file_api(self, etp_message_id):
    url = self.url_base + f"/messages/{etp_message_id}/email"
    try:
      r = requests.get(url, headers=self.headers,
                      proxies=self.proxies, 
                      verify=self.ssl_verify)
    except Exception as e:
      return None

    return r.content