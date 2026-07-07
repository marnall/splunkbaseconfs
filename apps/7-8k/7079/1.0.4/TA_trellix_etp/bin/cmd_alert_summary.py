import sys, os
import json
from datetime import datetime, timedelta, timezone


from advanced_threat_api import AdvancedThreat
from etp_client import ETPClient
import utils
logger = utils.setup_logging()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators, Integer
from solnlib import utils as solnlib_utils

# annotation for splunk
@Configuration(type='events')
class EtpAlertSummaryCommand(GeneratingCommand):
 
  legacy_id = Option(require=False, validate=Integer())
  etp_message_id = Option(require=False)
  from_last_modified_on = Option(require=False)
  email_status = Option(require=False)

  def prepare(self):

    splunkd_uri = self._metadata.searchinfo.splunkd_uri
    session_key = self._metadata.searchinfo.session_key

    try: 
      conf_data = utils.get_conf_data(session_key)
      self.access_token = conf_data.get('additional_parameters').get('api_key')
      self.service_region = conf_data.get('additional_parameters').get('etp_service_region')
      ssl_verify = conf_data.get('additional_parameters').get('ssl_verify')
    except Exception as e:
      self.error_exit(e, message="Error to fetch config data")
      
    if self.from_last_modified_on is None:
      self.from_last_modified_on = self._metadata.searchinfo.earliest_time

    self.from_last_modified_on = utils.change_datetime_to_utc(self.from_last_modified_on, 24)
    logger.info({ 'from_last_modified_on': self.from_last_modified_on } )
    
    try:
      server_info = utils.get_server_info(self.service.token)
      instance_type = 'cloud' if server_info.is_cloud_instance() else None
    except: 
      pass
    ssl_verify = utils.is_enable_ssl_verify(instance_type, ssl_verify)
    
    proxies = utils.get_requests_proxies(splunkd_uri, session_key)

    self.advanced_threat = AdvancedThreat(
      access_token=self.access_token,
      service_region=self.service_region,
      legacy_id=self.legacy_id,
      etp_message_id=self.etp_message_id,
      from_last_modified_on=self.from_last_modified_on,
      email_status=self.email_status,
      proxies=proxies,
      ssl_verify=ssl_verify,
    )


  def generate(self):
    
    alert_count = 0
    data = []

    while True:

      result = self.advanced_threat.alert_summary_api()
      if result is None:
        break 

      data += result.get('data')

      if result.get('meta').get('total') <= result.get('meta').get('size'):
        logger.info({ 'message': 'complete to fetch alert summary'} )
        break

      if len(data) > self.advanced_threat.EMAIL_LIMITS:
        logger.info({ 'message': f'limits to {self.advanced_threat.EMAIL_LIMITS} mails'} )
        break

    for d in data:

      datetime_str_gmt = f"{d.get('attributes').get('alert').get('timestamp')}+00:00"
      _time_epoch = datetime.fromisoformat(datetime_str_gmt).timestamp()

      yield {
        '_time': _time_epoch,
        'id': d.get('id'),
        'links': d.get('links'),
        '_raw': json.dumps(d.get('attributes'), ensure_ascii=False),
      }


if __name__ == "__main__":
  dispatch(EtpAlertSummaryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
