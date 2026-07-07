import sys, os
import json
from datetime import datetime, timedelta, timezone
from dateutil import tz
from email.parser import BytesParser
from email import policy

from email_trace_api import EmailTrace
from advanced_threat_api import AdvancedThreat
import utils
logger = utils.setup_logging()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators, Integer
from solnlib import utils as solnlib_utils

# annotation for splunk
@Configuration()
class EtpMessageFileCommand(StreamingCommand):
  
  # Class variables
  legacy_id = Option(require=False, validate=Integer())
  etp_message_id = Option(require=False)
  from_last_modified_on = Option(require=False)
  
  def prepare(self):
    self.attribute = {}
    
    try:
      self.access_token = utils.get_secret_global(self, utils.GLOBAL_API_KEY_NAME)
      self.service_region = utils.get_secret_global(self, utils.GLOBAL_SERVICE_REGION_NAME)
    except Exception as e:
      self.error_exit(e, message="Error to fetch global variables")

    # option is set
    if self.from_last_modified_on:
      # this value is ISO format
      self.attribute['from_last_modified_on'] = self.from_last_modified_on
    else: 
      # if from_last_modified_on is not set, use time picker.
      # this value is epoch. e.g. 1691827200.0
      self.attribute['from_last_modified_on'] = self.search_results_info.startTime
    
    self.attribute['from_last_modified_on'] = utils.change_datetime_to_utc(self.attribute['from_last_modified_on'], 24)

    ssl_verify = utils.get_secret_global(self, "ssl_verify")
    ssl_verify = solnlib_utils.is_true(ssl_verify)
    proxies = utils.get_requests_proxies(self)

    self.email_trace = EmailTrace(
      access_token=self.access_token,
      service_region=self.service_region,
      #etp_message_id=self.etp_message_id,
      proxies=proxies,
      ssl_verify=ssl_verify,
    )
    self.advanced_threat = AdvancedThreat(
      access_token=self.access_token,
      service_region=self.service_region,
      from_last_modified_on=self.attribute['from_last_modified_on'],
      proxies=proxies,
      ssl_verify=ssl_verify,
    )

  def stream(self, records):

    for record in records:

      # priority 1: etp_message_id in each record
      if record.get('etp_message_id'):
        self.attribute['etp_message_id'] = record.get('etp_message_id')

      # priority 2: etp_message_id of args
      elif self.etp_message_id:
        self.attribute['etp_message_id'] = self.etp_message_id

      # priority 3: legacy_id in each record
      elif record.get('legacy_id'):
        try:
          self.attribute['legacy_id'] = int(record.get('legacy_id'))
        except:
          logger.error( {'message': 'legacy_id is not integer'} )
          continue

      # priority 4: legacy_id of args
      elif self.legacy_id:
        self.attribute['legacy_id'] = self.legacy_id
      else:
        logger.error( {'message': 'no legacy_id or etp_message_id'} )
        continue

      # set from_last_modified_on in each record if exists
      if record.get('from_last_modified_on'):
        self.attribute['from_last_modified_on'] = utils.change_datetime_to_utc(record.get('from_last_modified_on'), 24)

      # get etp_message_id
      if self.legacy_id:
        
        self.advanced_threat.legacy_id = self.legacy_id
        self.advanced_threat.from_last_modified_on = self.attribute['from_last_modified_on']
        alerts = self.advanced_threat.alert_summary_api()

        # no alerts
        if not alerts:
          logger.error({'message': 'No alerts'})
          continue

        self.etp_message_id = alerts.get('data')[0].get('attributes').get('email').get('etp_message_id')

      # set etp_message_id to record
      record['etp_message_id'] = self.etp_message_id

      # fetch email data
      email_data = self.email_trace.message_file_api(self.etp_message_id)
      if email_data is None:
        record['email_data'] = email_data
      else:
        msg = BytesParser(policy=policy.default).parsebytes(email_data)
        charset = list(set(filter(None.__ne__, msg.get_charsets())))
        if charset:
          charset = charset[0]
        else:
          charset = 'ascii'
        record['email_data'] = email_data.decode(charset)

      yield record

if __name__ == "__main__":
  dispatch(EtpMessageFileCommand, sys.argv, sys.stdin, sys.stdout, __name__)
