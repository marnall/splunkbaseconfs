import import_declare_test
import sys
from common.collections import CollectionManager
from common.indicator_helper import matched_event
from splunklib.searchcommands import (
  dispatch,
  StreamingCommand,
  Configuration,
  Option
)
from splunklib.client import ConfigurationFile
from solnlib.conf_manager import ConfManager


class NotableSettings:
  """Settings for Notable Alert creation, as derived from a Splunk config"""
  def __init__(self, conf: dict) -> None:
    self.conf = conf

  @property
  def exclude_categories(self) -> list:
    if "exclude_categories" in self.conf and \
      self.conf.get('exclude_categories') != "":
      exclude_categories: list = self.conf.get('exclude_categories').split(",")
    else:
      exclude_categories = []

    return exclude_categories

  @property
  def exclude_actions(self) -> list:
    if "exclude_actions" in self.conf:
      exclude_actions: list = self.conf.get('exclude_actions').split(",")
      exclude_actions = [action.lstrip() for action in exclude_actions]
    else:
      exclude_actions = []

    return exclude_actions

  @property
  def exclude_unattributed(self) -> str:
    if "exclude_unattributed" in self.conf:
      exclude_unattributed: str = self.conf.get('exclude_unattributed')
    else:
      exclude_unattributed = "0"

    return exclude_unattributed

  @property
  def min_ic_score(self) -> str:
    if "min_ic_score" in self.conf:
      min_ic_score: str = self.conf.get('min_ic_score')
    else:
      min_ic_score = "0"

    return min_ic_score

  @property
  def severity_definition(self) -> str:
    if "severity_definition" in self.conf:
      severity_definition: str = self.conf.get('severity_definition')
    else:
      severity_definition = "medium"

    return severity_definition


def get_conf(session_key: str) -> dict:
  cfm = ConfManager(session_key, import_declare_test.ta_name)
  conf = cfm.get_conf('ta_mandiant_advantage_settings').get('matched_events')

  return conf


def category_filter(record: dict, settings: NotableSettings) -> bool:
  should_filter = False
  if "category" in record:
    for category in record.get('category'):
      if category in settings.exclude_categories:
        should_filter = True
        break
  elif "category" not in record and \
    "uncategorized" in settings.exclude_categories:
    should_filter = True

  return should_filter


def action_filter(record: dict, settings: NotableSettings) -> bool:
  should_filter = False
  if "action" in record and record.get('action') in settings.exclude_actions:
    should_filter = True

  return should_filter


def attribution_filter(record: dict, settings: NotableSettings) -> bool:
  should_filter = True
  if settings.exclude_unattributed == "0":
    should_filter = False
    return should_filter

  if "campaign" not in record and "threat_actor" not in record and \
    "malware" not in record:
    should_filter = True
  else:
    should_filter = False

  return should_filter


def ic_score_filter(record: dict, settings: NotableSettings) -> bool:
  should_filter = False
  if int(record.get('ic_score')) < int(settings.min_ic_score):
    should_filter = True

  return should_filter


def get_severity(ic_score: str, severity_definition: str) -> str:
  severity = "medium"
  if severity_definition != "ic_score":
    severity = severity_definition
  elif int(ic_score) == 100:
    severity = "critical"
  elif int(ic_score) >= 80:
    severity = "high"
  elif int(ic_score) >= 60:
    severity = "medium"
  else:
    severity = "low"

  return severity


def transform_record(record: dict, severity_definition: str) -> dict:
  transformed = {
    'event_time': record.get('_time'),
    'index': record.get('index'),
    'sourcetype': record.get('sourcetype'),
    'data_model': record.get('data_model'),
    'action': record.get('action', "unknown"),

    'indicator': record.get('indicator'),
    'calculated_risk_score': record.get('ic_score'),
    'threat_source_type': record.get('type')
  }

  opt_fields = ["src", "src_ip", "dest", "dest_ip", "domain", "url",
                "file_hash", "category", "user"]

  for field in opt_fields:
    if field in record:
      transformed[field] = record.get(field)

  if "malware" in record:
    if isinstance(record.get('malware'), list):
      malware = [m.split("||")[1] for m in record.get('malware')]
    elif "||" in record.get('malware'):
      malware = record.get('malware').split("||")[1]
    else:
      malware = "None"
    transformed['malware_alias'] = malware

  if "threat_actor" in record:
    if isinstance(record.get('threat_actor'), list):
      threat_actor = [t.split("||")[1] for t in record.get('threat_actor')]
    elif "||" in record.get('threat_actor'):
      threat_actor = record.get('threat_actor').split("||")[1]
    else:
      threat_actor = "None"
    transformed['threat_group'] = threat_actor

  # Calculate vendor_severity, urgency, severity
  severity = get_severity(record.get('ic_score'), severity_definition)
  transformed['vendor_severity'] = severity
  transformed['severity'] = severity
  transformed['urgency'] = severity

  return transformed


@Configuration()
class MandiantNotables(StreamingCommand):
  """Filter / transform Mandiant Matched Events based on customer defined
  settings for Notable alerts"""

  def stream(self, records):
    """Entry point for the command, inherits the StreamingCommand class.

    Receives events (records) from the results of a Splunk search, filters and
    transforms based on customer defined Notable alert settings

    Args:
      records: OrderedDict of search results from Splunk

    Yields:
      record: a dict of one of the filtered / transformed search results
    """
    # Get Splunk session key from the inherited StreamingCommand class
    session_key = self.service.token

    # Get settings from conf file
    settings = NotableSettings(get_conf(session_key))

    # Create collection manager for mandiant_matched_events
    matched_events = CollectionManager(session_key, "mandiant_matched_events")

    # Process search results one by one
    for record in records:
      # Skip records where a Notable alert has already been created
      if record.get('notable_created') == "1":
        continue

      # Filter based on settings
      if category_filter(record, settings) is True:
        continue

      if action_filter(record, settings) is True:
        continue

      if attribution_filter(record, settings) is True:
        continue

      if ic_score_filter(record, settings) is True:
        continue

      # Update notable_created in matched_event
      record['notable_created'] = True
      matched_events._update(record.get('key'), record)

      # Transform to return fields compatible with a Notable Alert
      yield transform_record(record, settings.severity_definition)


dispatch(MandiantNotables, sys.argv, sys.stdin, sys.stdout, __name__)
