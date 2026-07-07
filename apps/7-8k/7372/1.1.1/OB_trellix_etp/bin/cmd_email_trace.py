import sys
import os
import json
from datetime import datetime, timezone
from dateutil import tz

from email_trace_api import EmailTrace
import utils
logger = utils.setup_logging()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import StoragePassword, Service
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from solnlib import utils as solnlib_utils

# annotation for splunk
@Configuration(type='events')
class EtpMailTraceCommand(GeneratingCommand):
  
  subject = Option(require=False)
  from_email = Option(require=False)
  to_email = Option(require=False)
  from_accepted_dt = Option(require=False) # fromAcceptedDateTime
  to_accepted_dt = Option(require=False)
  at_verdict = Option(require=False)
  last_modified_datetime = Option(require=False)
  
  def prepare(self):
    
    splunkd_uri = self._metadata.searchinfo.splunkd_uri
    session_key = self._metadata.searchinfo.session_key

    try: 
      conf_data = utils.get_conf_data(session_key)
      # self.access_token = conf_data.get('additional_parameters').get('api_key')
      self.service_region = conf_data.get('additional_parameters').get('etp_service_region')
      ssl_verify = conf_data.get('additional_parameters').get('ssl_verify')
    except Exception as e:
      self.error_exit(e, message="Error to fetch config data")

    # by default, use last_modified_datetime and then set time picker.
    
    if self.last_modified_datetime is None:
      
      # if no datetime is set, use last_modified_datetime
      if self.from_accepted_dt is None and self.to_accepted_dt is None:
        self.last_modified_datetime = self._metadata.searchinfo.earliest_time

      else:
        if self.from_accepted_dt is None: 
          # startTime returns epoch time
          self.from_accepted_dt = self._metadata.searchinfo.earliest_time
        
        if self.to_accepted_dt is None:
          # endTime returns epoch time
          self.to_accepted_dt = self._metadata.searchinfo.latest_time
      
    else:
      self.from_accepted_dt = None
      self.to_accepted_dt = None

    
    logger.info( { 'from_accepted_dt': self.from_accepted_dt, 'to_accepted_dt': self.to_accepted_dt} )
    logger.info( { 'last_modified_datetime': self.last_modified_datetime} )
    
    try:
      server_info = utils.get_server_info(self.service.token)
      instance_type = 'cloud' if server_info.is_cloud_instance() else None
    except: 
      pass

    ssl_verify = utils.is_enable_ssl_verify(instance_type, ssl_verify)

    proxies = utils.get_requests_proxies(splunkd_uri, session_key)

    self.email_trace = EmailTrace(
      access_token=self.access_token,
      service_region=self.service_region,
      subject=self.subject, 
      from_email=self.from_email,
      to_email=self.to_email,
      from_accepted_dt=self.from_accepted_dt,
      to_accepted_dt=self.to_accepted_dt,
      at_verdict=self.at_verdict,
      last_modified_datetime=self.last_modified_datetime,
      proxies=proxies,
      ssl_verify=ssl_verify,
    )
    

  def generate(self):

    data = []
    while True:

      result = self.email_trace.email_trace_api()
      if result is None:
        break

      data += result.get('data')

      if result.get('meta').get('total') <= result.get('meta').get('size'):
        logger.info({'message': 'complete to fetch email trace'})
        break

      if len(data) >= self.email_trace.EMAIL_LIMITS:
        logger.info({'message': f'limits to {self.email_trace.EMAIL_LIMITS} mails'})
        break

    for d in data:
      datetime_str_gmt = f"{d.get('attributes').get('acceptedDateTime')}+00:00"
      _time_epoch = datetime.fromisoformat(datetime_str_gmt).timestamp()

      yield {
        '_time': _time_epoch,
        'id': d.get('id'),
        '_raw': json.dumps(d.get('attributes'), ensure_ascii=False),
      }

if __name__ == "__main__":
  dispatch(EtpMailTraceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
