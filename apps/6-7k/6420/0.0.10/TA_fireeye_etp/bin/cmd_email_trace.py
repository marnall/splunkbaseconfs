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
    try:
      self.access_token = utils.get_secret_global(self, utils.GLOBAL_API_KEY_NAME)
      self.service_region = utils.get_secret_global(self, utils.GLOBAL_SERVICE_REGION_NAME)
    except Exception as e:
      self.error_exit(e, message="Error to fetch global variables")

    # by default, use last_modified_datetime and then set time picker.
    # startTime/endTime returns epoch time
    if self.last_modified_datetime is None \
        and self.from_accepted_dt is None and self.to_accepted_dt is None:
      self.last_modified_datetime = self.search_results_info.startTime

    # if self.from_accepted_dt is None:
    #   self.from_accepted_dt = self.search_results_info.startTime

    # if self.to_accepted_dt is None:
    #   self.to_accepted_dt = self.search_results_info.endTime
    
    logger.info( { 'from_accepted_dt': self.from_accepted_dt, 'to_accepted_dt': self.to_accepted_dt} )
    logger.info( { 'last_modified_datetime': self.last_modified_datetime} )
    
    ssl_verify = utils.get_secret_global(self, "ssl_verify")
    ssl_verify = solnlib_utils.is_true(ssl_verify)
    proxies = utils.get_requests_proxies(self)

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
        '_raw': d.get('attributes'),
      }

if __name__ == "__main__":
  dispatch(EtpMailTraceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
