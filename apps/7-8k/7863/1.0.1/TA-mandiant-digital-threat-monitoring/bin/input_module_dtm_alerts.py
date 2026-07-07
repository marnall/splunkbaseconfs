# encoding = utf-8

import json
import time

from datetime import datetime, timedelta, timezone
from mandiant_dtm_constants import APP_VERSION
from mandiant_dtm_client import DtmClient
from mandiant_dtm_helper import build_proxy_config
from ta_mandiant_digital_threat_monitoring_declare import ta_name
from solnlib import conf_manager
from requests import RequestException

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
  """Implement your own validation logic to validate the input stanza configurations"""
  # This example accesses the modular input variable
  # global_account = definition.parameters.get('global_account', None)
  # minimum_m_score = definition.parameters.get('minimum_m_score', None)
  # alert_status = definition.parameters.get('alert_status', None)
  # alert_types = definition.parameters.get('alert_types', None)
  pass


def collect_events(helper, ew):
  start = int(time.time())
  input_name = helper.get_arg("name")
  helper.log_info(
      f"{input_name} | Starting data collection. Version {APP_VERSION}"
  )
  helper.log_debug(f"{input_name} | DEBUG logging is enabled")

  # Get config values
  opt_global_account = helper.get_arg("global_account")
  key_id = opt_global_account.get("key_id", "")
  key_secret = opt_global_account.get("key_secret", "")

  proxy_settings = helper.get_proxy()
  proxy_config = {}
  if proxy_settings:
    proxy_config = build_proxy_config(proxy_settings)
    helper.log_debug(f"{input_name} | Proxy Settings {proxy_config}")

  opt_minimum_m_score = helper.get_arg("minimum_m_score")
  helper.log_debug(f"{input_name} | Min M-score {opt_minimum_m_score}")

  opt_alert_status = helper.get_arg("alert_status")
  helper.log_debug(f"{input_name} | Alert Status Filter: {opt_alert_status}")
  if "*" in opt_alert_status:
    opt_alert_status = []

  opt_alert_types = helper.get_arg("alert_types")
  helper.log_debug(f"{input_name} | Alert Type Filter: {opt_alert_types}")
  if "*" in opt_alert_types:
    opt_alert_types = []

  index = helper.get_arg("index")
  helper.log_debug(f"{input_name} | Index: {index}")

  source = helper.get_input_type()
  helper.log_debug(f"{input_name} | Source: {source}")

  sourcetype = helper.get_sourcetype()
  helper.log_debug(f"{input_name} | Sourcetype: {sourcetype}")

  # Set since date to - 7d
  since = datetime.now(timezone.utc) - timedelta(days=7)

  # If checkpoint override since date to checkpoint value
  # state = helper.get_check_point(input_name)
  # if state:
  #   helper.log_debug(f"{input_name} | Checkpoint found!!")
  #   since = datetime.fromisoformat(state)

  helper.log_info(f"{input_name} | Using since value: {since}")

  index_sensitive_information = False
  try:
    session_key = helper.service.token
    cfm = conf_manager.ConfManager(
        session_key,
        ta_name,
        realm=f"__REST_CREDENTIAL__#{ta_name}#configs/conf-ta_mandiant_digital_threat_monitoring_settings",
    )
    settings_conf = cfm.get_conf(
        "ta_mandiant_digital_threat_monitoring_settings"
    ).get_all()
    dashboard_settings = settings_conf.get("dashboard_settings", {})
    index_sensitive_information = dashboard_settings.get(
        "index_sensitive_information", False
    )
    helper.log_debug(
        f"{input_name} | Index Sensitive Information: {index_sensitive_information}"
    )
  except Exception as e:
    helper.log_error(
        f"{input_name} | Error reading index_sensitive_information setting: {str(e)}. Defaulting to False."
    )

  # Init DTM Client
  dtm_client = DtmClient(
      key_id,
      key_secret,
      proxies=proxy_config,
      index_sensitive_information=index_sensitive_information,
      helper=helper,
  )

  # Get and Ingest alerts
  collected = 0
  ingested = 0

  end_dt = datetime.now(timezone.utc)

  try:
    for alert in dtm_client.get_alerts(
        since, opt_alert_types, opt_alert_status, opt_minimum_m_score
    ):
      collected += 1

      try:
        ew.write_event(
            helper.new_event(
                source=source,
                index=index,
                sourcetype=sourcetype,
                data=json.dumps(alert),
            )
        )
        ingested += 1
      except BrokenPipeError:
        helper.log_error(
            f"{input_name} | Output pipe broken while ingesting event"
        )

  except RequestException as ex:
    helper.log_error(f"{input_name} | Error calling Mandiant API: {str(ex)}")

  # Update checkppoint
  helper.save_check_point(input_name, end_dt.isoformat())
  helper.log_info(f"{input_name} | Checkpoint saved!!")

  helper.log_info(
      f"{input_name} | Collected {collected} alerts. Ingested {ingested} alerts. Process completed in "
      + f"{int(time.time()) - start} seconds"
  )
