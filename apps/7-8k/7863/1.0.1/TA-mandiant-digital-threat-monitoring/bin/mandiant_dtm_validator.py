import splunk.admin as admin

from mandiant_dtm_client import DtmClient
from mandiant_dtm_helper import build_proxy_config
from requests import RequestException
from solnlib import conf_manager
from splunk.clilib.cli_common import getMgmtUri
from splunklib import client
from splunktaucclib.rest_handler.endpoint.validator import Validator
from ta_mandiant_digital_threat_monitoring_declare import ta_name


class SplunkSessionKey(admin.MConfigHandler):
  """To get Splunk session key."""

  def __init__(self):
    """Initialize."""
    self.session_key = self.getSessionKey()


def read_conf_file(session_key, conf_file, stanza=None):
  """
  Get conf file content with conf_manager.

  :param session_key: Splunk session key
  :param conf_file: conf file name
  :param stanza: If stanza name is present then return only that stanza,
                  otherwise return all stanza
  """
  conf_file = conf_manager.ConfManager(
      session_key,
      ta_name,
      realm=f"__REST_CREDENTIAL__#{ta_name}#configs/conf-{conf_file}",
  ).get_conf(conf_file)

  if stanza:
    return conf_file.get(stanza)

  return conf_file.get_all()


def create_service(session_key):
  """Create Service to communicate with splunk."""
  mgmt_port = getMgmtUri().split(":")[-1]
  service = client.connect(port=mgmt_port, token=session_key, app=ta_name)
  return service


class ValidateDtmAccount(Validator):
  """Validator class to test connectivity and AuthN to the DTM API"""

  def validate(self, _, data):
    key_id = data.get("key_id")
    key_secret = data.get("key_secret")

    # Get proxy settings
    session_key = SplunkSessionKey().session_key

    proxy_config = {}
    proxy_settings = read_conf_file(
        session_key,
        "ta_mandiant_digital_threat_monitoring_settings",
        stanza="proxy",
    )

    if proxy_settings and proxy_settings.get("proxy_enabled") == "1":
      proxy_config = build_proxy_config(proxy_settings)

    dtm_client = DtmClient(key_id, key_secret, proxy_config)

    try:
      resp = dtm_client.get_monitors()
    except RequestException as ex:
      self.put_msg(f"Connection error: {str(ex)}")
      return False

    if resp.status_code != 200:
      self.put_msg(
          (
              "Error authenticating with the Mandiant DTM API. "
              f"Error Code: {resp.status_code}"
          )
      )
      return False

    return True


class DtmDashboardSettings(Validator):
  """Validator class to set dashboard settings"""

  def validate(self, _, data):
    # Connect to Splunk
    session_key = SplunkSessionKey().session_key
    service = create_service(session_key)

    # Set Macro Values
    try:
      service.post(
          "properties/macros/mandiant_dtm_index",
          definition=data.get("dashboard_index"),
      )
    except Exception as ex:
      self.put_msg(f"Unexpected error setting macro value: {str(ex)}")
      return False

    return True
